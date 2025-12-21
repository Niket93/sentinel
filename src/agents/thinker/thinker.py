from __future__ import annotations
import json
import re
import time
from typing import Any, Dict, List, Tuple
from datetime import datetime, timezone
from vertexai.generative_models import GenerativeModel, Part
from ...config.settings import Settings
from ...shared.events import StationSessionEvent, ObservationEvent, DecisionEvent
from ...shared.kafka_client import make_consumer, make_producer, consume_loop, produce_model
from ...shared.vertex_client import init_vertex
from ...shared.gcs_client import GcsClient
from ...rag.vertex_search_answer import answer_query
from .prompts import ASSEMBLY_THINKER_SYSTEM, SECURITY_THINKER_SYSTEM

def _parse_json(text: str) -> Dict[str, Any]:
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        raise ValueError(f"No JSON returned by model. Raw: {text[:200]}")
    return json.loads(m.group(0))


def _parse_json_soft(text: str) -> Dict[str, Any]:
    try:
        return _parse_json(text)
    except Exception:
        return {
            "assessment": {"violation": False, "severity": "low", "confidence": 0.0, "risk": "unparsed_llm_output"},
            "recommended_actions": [],
            "rationale": {"short": "LLM output could not be parsed as JSON.", "citations": []},
            "evidence": {"reason": "security_llm_parse_fail", "clip_range": [0, 0]},
        }


def _canonical_action_type(t: str) -> str:
    s = (t or "").strip().lower().replace("-", "_").replace(" ", "_")
    if s in {"stop", "stopline", "stop_line", "halt", "shutdown", "stop_machine", "stop_the_line"}:
        return "stop_line"
    if s in {"alert", "warn", "warning", "notify", "notification", "flag"}:
        return "alert"
    return s or "alert"


def _canonical_priority(p: str) -> str:
    s = (p or "").strip().upper()
    if s in {"P1", "P2", "P3"}:
        return s
    if s in {"1", "2", "3"}:
        return f"P{s}"
    return "P2"


def _normalize_recommended_actions(actions: Any) -> List[Dict[str, Any]]:
    if not isinstance(actions, list):
        return []
    out: List[Dict[str, Any]] = []
    for a in actions:
        if not isinstance(a, dict):
            continue
        at = _canonical_action_type(str(a.get("type", "")))
        msg = str(a.get("message", "") or "").strip()
        target = str(a.get("target", "console") or "console").strip() or "console"
        pr = _canonical_priority(str(a.get("priority", "")))
        if not msg:
            msg = "Action recommended."
        out.append({"type": at, "target": target, "message": msg, "priority": pr})
    return out[:1]


def _yn(v: object) -> str:
    if isinstance(v, str):
        s = v.strip().lower()
        if s in ("yes", "no", "uncertain"):
            return s
    return "uncertain"

class ThinkerService:

    def __init__(
        self,
        cfg: Settings,
        security_emit_cooldown_s: int = 6,
    ):
        self.cfg = cfg
        init_vertex(cfg)
        self.model = GenerativeModel(cfg.gemini_thinker_model)
        self.gcs = GcsClient(project=cfg.gcp_project)
        self.producer = make_producer(cfg)
        self.consumer = make_consumer(
            cfg,
            group_id="thinker-router-v2-llm-security-singleclip",
            topics=[cfg.topic_sessions, cfg.topic_observations],
            offset_reset="latest",
        )
        self.security_emit_cooldown_s = int(security_emit_cooldown_s)
        self._security_last_emit: Dict[str, float] = {}

    def _security_cooldown_ok(self, key: str) -> bool:
        if self.security_emit_cooldown_s <= 0:
            return True
        now = time.time()
        last = self._security_last_emit.get(key, 0.0)
        if now - last < self.security_emit_cooldown_s:
            return False
        self._security_last_emit[key] = now
        return True

    def _security_should_trigger(self, obs: ObservationEvent) -> Tuple[bool, str]:
        s = obs.signals or {}
        walkway = _yn(s.get("walkway_violation")) == "yes"
        restricted = _yn(s.get("restricted_area_entry")) == "yes"
        prox = _yn(s.get("unsafe_proximity_to_machine")) == "yes"
        machine = _yn(s.get("machine_operating")) == "yes"
        panel = _yn(s.get("panel_open")) == "yes"
        guard = _yn(s.get("guard_open")) == "yes"
        if panel and machine:
            return True, "panel_open_while_operating"
        if guard and machine:
            return True, "guard_open_while_operating"
        if prox and machine:
            return True, "unsafe_proximity_while_operating"
        if restricted:
            return True, "restricted_area_entry"
        if walkway:
            return True, "walkway_violation"
        if prox:
            return True, "unsafe_proximity"
        return False, ""

    def _security_llm_decide_single_clip(self, obs: ObservationEvent, trigger_rule: str) -> Dict[str, Any]:
        payload = {
            "camera_id": obs.camera_id,
            "use_case": obs.use_case,
            "ts": obs.ts.isoformat(),
            "clip_index": obs.clip_index,
            "summary": obs.summary,
            "signals": obs.signals or {},
            "trigger_rule": trigger_rule,
        }
        raw = self.model.generate_content(
            [SECURITY_THINKER_SYSTEM, f"OBS={json.dumps(payload)}"],
            generation_config={"temperature": 0.1, "max_output_tokens": 10000},
        ).text
        out = _parse_json_soft(raw)
        out["recommended_actions"] = _normalize_recommended_actions(out.get("recommended_actions"))
        if not isinstance(out.get("evidence"), dict):
            out["evidence"] = {}
        out["evidence"].setdefault("reason", "security_single_clip_llm")
        out["evidence"].setdefault("clip_range", [obs.clip_index, obs.clip_index])
        if not isinstance(out.get("assessment"), dict):
            out["assessment"] = {"violation": False, "severity": "low", "confidence": 0.0, "risk": "missing_assessment"}
        out["assessment"].setdefault("rule_id", trigger_rule or "security_triggered")
        return out

    def handle_security_observation(self, msg: dict) -> None:
        obs = ObservationEvent(**msg)
        if obs.use_case != "security":
            return
        should_trigger, trigger_rule = self._security_should_trigger(obs)
        if not should_trigger:
            return
        dedup_key = f"{obs.camera_id}:{trigger_rule}"
        if not self._security_cooldown_ok(dedup_key):
            return
        out = self._security_llm_decide_single_clip(obs, trigger_rule)
        assessment = out.get("assessment", {}) if isinstance(out.get("assessment"), dict) else {}
        violation = bool(assessment.get("violation", False))
        actions = out.get("recommended_actions", [])
        if not violation or not actions:
            return
        confidence = float(assessment.get("confidence", 0.0) or 0.0)
        sev = str(assessment.get("severity", "medium"))
        risk = str(assessment.get("risk", "security_risk"))
        rule_id = str(assessment.get("rule_id", trigger_rule))
        decision = DecisionEvent(
            trace_id=obs.trace_id,
            clip_id=obs.clip_id,
            observation_id=obs.observation_id,
            camera_id=obs.camera_id,
            use_case=obs.use_case,
            clip_index=obs.clip_index,
            ts=datetime.now(timezone.utc),
            assessment={
                "violation": True,
                "rule_id": rule_id,
                "severity": sev,
                "confidence": confidence,
                "risk": risk,
            },
            recommended_actions=actions,
            rationale=out.get("rationale", {"short": "LLM security decision.", "citations": []}),
            evidence=out.get("evidence", {"reason": "security_clip", "clip_range": [obs.clip_index, obs.clip_index]}),
            model={"name": self.cfg.gemini_thinker_model, "latency_ms": 0},
        )
        produce_model(self.producer, self.cfg.topic_decisions, decision, key=obs.camera_id)


    def handle_assembly_session(self, msg: dict) -> None:
        sess = StationSessionEvent(**msg)
        station = sess.station_id or "S4"
        sku = sess.sku_id or "S1345780"
        sop_query = (
            f"SOP for process Board Assembly at station {station} for SKU {sku}. "
            f"List the complete steps in order with step_id with necessary info like expected tool, expected part, action, order_index."
        )
        sr = answer_query(self.cfg, sop_query)
        sop_chunks = []
        if sr.snippets:
            for i, snip in enumerate(sr.snippets[:6]):
                sop_chunks.append(
                    {"chunk_id": f"search_snip_{i}", "chunk_text": snip, "metadata": {"source": "vertex_ai_search"}}
                )
        else:
            sop_chunks.append(
                {"chunk_id": "search_answer", "chunk_text": sr.answer_text, "metadata": {"source": "vertex_ai_search"}}
            )
        timeline = sess.timeline[-30:]
        parts: List[Any] = [
            ASSEMBLY_THINKER_SYSTEM,
            f"SOP_CHUNKS={json.dumps(sop_chunks)}\nSESSION={json.dumps(sess.model_dump(mode='json'))}\nTIMELINE={json.dumps(timeline)}",
        ]
        if sess.session_video_gcs_uri:
            video_bytes = self.gcs.download_bytes(sess.session_video_gcs_uri)
            if video_bytes and len(video_bytes) > 1024:
                parts.append(Part.from_data(data=video_bytes, mime_type="video/mp4"))
        t0 = time.time()
        raw = self.model.generate_content(
            parts,
            generation_config={"temperature": 0.1, "max_output_tokens": 10000},
        ).text
        latency_ms = int((time.time() - t0) * 1000)
        out = _parse_json(raw)
        out["recommended_actions"] = _normalize_recommended_actions(out.get("recommended_actions"))
        assessment = out.get(
            "assessment",
            {"sop_violation": False, "severity": "low", "confidence": 0.2, "risk": "unknown"},
        )
        missing = out.get("missing_steps", []) or []
        completed = out.get("completed_steps", []) or []
        if assessment.get("sop_violation") or missing:
            message = "Potential SOP violation detected."
            if missing:
                message = f"Missing steps: {', '.join([m.get('step_id','?') for m in missing])}"
            recommended = out.get("recommended_actions") or [
                {"type": "stop_line", "target": "console", "message": message, "priority": "P1"}
            ]
            recommended = _normalize_recommended_actions(recommended)
            decision = DecisionEvent(
                trace_id=sess.trace_id,
                clip_id=sess.session_id,
                observation_id=sess.session_id,
                camera_id=sess.camera_id,
                use_case=sess.use_case,
                clip_index=sess.end_clip_index,
                ts=datetime.now(timezone.utc),
                assessment=assessment,
                recommended_actions=recommended,
                rationale=out.get("rationale", {"short": "Session-level SOP evaluation.", "citations": []}),
                evidence=out.get(
                    "evidence",
                    {"reason": "session_sop_inference", "clip_range": [sess.start_clip_index, sess.end_clip_index]},
                ),
                model={"name": self.cfg.gemini_thinker_model, "latency_ms": latency_ms},
            )
            produce_model(self.producer, self.cfg.topic_decisions, decision, key=sess.camera_id)
            print(
                f"[thinker][assembly] session={sess.session_id} missing={len(missing)} completed={len(completed)} severity={assessment.get('severity')}"
            )
        else:
            print(f"[thinker][assembly] session={sess.session_id} no violation (conf={assessment.get('confidence')})")

    def handle_message(self, msg: dict) -> None:
        if "session_id" in msg:
            try:
                if str(msg.get("use_case", "")).lower() == "assembly":
                    self.handle_assembly_session(msg)
            except Exception as e:
                print("[thinker][assembly] error:", e)
            return
        if "observation_id" in msg:
            try:
                if str(msg.get("use_case", "")).lower() == "security":
                    self.handle_security_observation(msg)
            except Exception as e:
                print("[thinker][security] error:", e)
            return
        return

    def run(self) -> None:
        consume_loop(self.consumer, self.handle_message)