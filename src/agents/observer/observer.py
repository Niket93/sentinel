from __future__ import annotations
import json, re, time
from datetime import datetime, timezone
from typing import Any, Dict
from vertexai.generative_models import GenerativeModel, Part
from ...config.settings import Settings
from ...shared.events import ClipEvent, ObservationEvent
from ...shared.kafka_client import make_consumer, make_producer, consume_loop, produce_model
from ...shared.gcs_client import GcsClient
from ...shared.vertex_client import init_vertex
from .prompts import ASSEMBLY_OBSERVER_PROMPT, SECURITY_OBSERVER_PROMPT

def _parse_json(text: str) -> Dict[str, Any]:
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return {"summary": text.strip(), "signals": {"uncertainty": "high", "confidence_note": "no_json"}}
    return json.loads(m.group(0))


class ObserverService:
    def __init__(self, cfg: Settings):
        self.cfg = cfg
        init_vertex(cfg)
        self.gcs = GcsClient(project=cfg.gcp_project)
        self.model = GenerativeModel(cfg.gemini_observer_model)
        self.producer = make_producer(cfg)
        self.consumer = make_consumer(cfg, group_id="observer-v2", topics=[cfg.topic_clips], offset_reset="latest")
    

    def handle_clip(self, clip_msg: dict):
        clip = ClipEvent(**clip_msg)
        t0 = time.time()
        video_bytes = self.gcs.download_bytes(clip.gcs_uri)
        if not video_bytes or len(video_bytes) < 1024:
            return
        prompt = ASSEMBLY_OBSERVER_PROMPT if clip.use_case == "assembly" else SECURITY_OBSERVER_PROMPT
        resp = self.model.generate_content(
            [
                prompt,
                Part.from_data(data=video_bytes, mime_type="video/mp4"),
            ],
            generation_config={"temperature": 0.0, "max_output_tokens": 10000},
        )
        out = _parse_json(resp.text)
        latency_ms = int((time.time() - t0) * 1000)
        summary = out.get("summary", "")
        signals = out.get("signals", {}) if isinstance(out.get("signals", {}), dict) else {}
        obs = ObservationEvent(
            trace_id=clip.trace_id,
            clip_id=clip.clip_id,
            clip_gcs_uri=clip.gcs_uri,
            camera_id=clip.camera_id,
            use_case=clip.use_case,
            clip_index=clip.clip_index,
            ts=datetime.now(timezone.utc),
            summary=summary,
            entities=[],
            signals=signals,
            model={"name": self.cfg.gemini_observer_model, "latency_ms": latency_ms},
        )
        produce_model(self.producer, self.cfg.topic_observations, obs, key=clip.camera_id)

    def run(self):
        consume_loop(self.consumer, self.handle_clip)