from __future__ import annotations
import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, List
from vertexai.generative_models import GenerativeModel
from ...config.settings import Settings
from ...shared.events import DecisionEvent, ActionEvent
from ...shared.kafka_client import make_consumer, make_producer, consume_loop, produce_model
from ...shared.vertex_client import init_vertex
from .prompts import DOER_SYSTEM


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


def _parse_json_soft(text: str) -> Dict[str, Any]:
    try:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
    except Exception:
        pass
    return {"actions": []}


class DoerService:
    def __init__(self, cfg: Settings):
        self.cfg = cfg
        init_vertex(cfg)
        self.model = GenerativeModel(cfg.gemini_thinker_model)
        self.producer = make_producer(cfg)
        self.consumer = make_consumer(cfg, group_id="doer-llm-v1", topics=[cfg.topic_decisions],offset_reset="latest")
        self.last: Dict[str, float] = {}

    def _dedup(self, key: str, cooldown_s: int = 20) -> bool:
        now = time.time()
        if key in self.last and now - self.last[key] < cooldown_s:
            return False
        self.last[key] = now
        return True

    def _llm_enrich_actions(self, dec: DecisionEvent) -> List[Dict[str, Any]]:
        in_actions = dec.recommended_actions or []
        safe_actions = []
        for a in in_actions:
            if not isinstance(a, dict):
                continue
            safe_actions.append(
                {
                    "type": _canonical_action_type(str(a.get("type", ""))),
                    "target": str(a.get("target", "console") or "console"),
                    "priority": _canonical_priority(str(a.get("priority", ""))),
                    "message": str(a.get("message", "") or "").strip(),
                }
            )
        prompt_obj = {
            "camera_id": dec.camera_id,
            "use_case": dec.use_case,
            "clip_index": dec.clip_index,
            "assessment": dec.assessment,
            "rationale": dec.rationale,
            "evidence": dec.evidence,
            "recommended_actions": safe_actions,
        }
        raw = self.model.generate_content(
            [DOER_SYSTEM, f"DECISION={json.dumps(prompt_obj)}"],
            generation_config={"temperature": 0.2, "max_output_tokens": 10000},
        ).text
        out = _parse_json_soft(raw)
        actions = out.get("actions", [])
        if not isinstance(actions, list) or not actions:
            return safe_actions
        enriched: List[Dict[str, Any]] = []
        for a in actions:
            if not isinstance(a, dict):
                continue
            at = _canonical_action_type(str(a.get("type", "")))
            if at not in {x["type"] for x in safe_actions}:
                continue
            enriched.append(
                {
                    "type": at,
                    "target": str(a.get("target", "console") or "console"),
                    "priority": _canonical_priority(str(a.get("priority", ""))),
                    "message": str(a.get("message", "") or "").strip() or "Action recommended.",
                    "execution_steps": a.get("execution_steps", []),
                    "notes": str(a.get("notes", "") or "").strip(),
                }
            )

        return enriched[:1] if enriched else safe_actions

    def handle_decision(self, dec_msg: dict):
        dec = DecisionEvent(**dec_msg)
        sev = str(dec.assessment.get("severity", "low")).lower()
        base_key = f"{dec.camera_id}:{dec.use_case}:{sev}"
        enriched_actions = self._llm_enrich_actions(dec)
        for a in enriched_actions:
            a_type = _canonical_action_type(str(a.get("type", "")))
            key = f"{base_key}:{a_type}"
            if not self._dedup(key):
                evt = ActionEvent(
                    trace_id=dec.trace_id,
                    decision_id=dec.decision_id,
                    camera_id=dec.camera_id,
                    use_case=dec.use_case,
                    ts=datetime.now(timezone.utc),
                    action=a,
                    status="skipped",
                    provider="dedup",
                )
                produce_model(self.producer, self.cfg.topic_actions, evt, key=dec.camera_id)
                continue

            msg = str(a.get("message", "") or "")
            if a_type == "stop_line":
                print(f"🚨 [DOER][LLM] STOP LINE: camera={dec.camera_id} clip={dec.clip_index} :: {msg}")
            else:
                print(f"⚠️  [DOER][LLM] ALERT: camera={dec.camera_id} clip={dec.clip_index} :: {msg}")

            evt = ActionEvent(
                trace_id=dec.trace_id,
                decision_id=dec.decision_id,
                camera_id=dec.camera_id,
                use_case=dec.use_case,
                ts=datetime.now(timezone.utc),
                action=a,
                status="sent",
                provider="gemini",
            )
            produce_model(self.producer, self.cfg.topic_actions, evt, key=dec.camera_id)

    def run(self):
        consume_loop(self.consumer, self.handle_decision)