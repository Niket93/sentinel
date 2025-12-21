from __future__ import annotations
import os
import shutil
import tempfile
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from ...config.settings import Settings
from ...shared.events import ObservationEvent, StationSessionEvent
from ...shared.kafka_client import make_consumer, make_producer, consume_loop, produce_model
from ...shared.gcs_client import GcsClient


@dataclass
class OpenSession:
    trace_id: str
    camera_id: str
    use_case: str
    station_id: Optional[str]
    sku_id: Optional[str]
    start_ts: datetime
    start_clip_index: int
    last_ts: datetime
    last_clip_index: int
    clip_uris: List[str]
    timeline: List[Dict[str, Any]]


class SessionizerService:
    def __init__(self, cfg: Settings):
        self.cfg = cfg
        self.gcs = GcsClient(project=cfg.gcp_project)
        self.producer = make_producer(cfg)
        self.consumer = make_consumer(
            cfg,
            group_id="sessionizer-simple-v1",
            topics=[cfg.topic_observations],
            offset_reset="latest",
        )
        self.open_sessions: Dict[str, OpenSession] = {}

    def _make_montage(self, sess: OpenSession) -> Optional[str]:
        if shutil.which("ffmpeg") is None:
            print("[sessionizer] ffmpeg not found; montage skipped.")
            return None
        tmpdir = tempfile.mkdtemp(prefix="session_")
        try:
            local_files: List[str] = []
            for i, uri in enumerate(sess.clip_uris):
                data = self.gcs.download_bytes(uri)
                if not data or len(data) < 1024:
                    continue
                fp = os.path.join(tmpdir, f"clip_{i:06d}.mp4")
                with open(fp, "wb") as f:
                    f.write(data)
                local_files.append(fp)
            if len(local_files) < 2:
                return None
            list_path = os.path.join(tmpdir, "concat.txt")
            with open(list_path, "w", encoding="utf-8") as f:
                for fp in local_files:
                    f.write(f"file '{fp}'\n")
            out_path = os.path.join(tmpdir, "session.mp4")
            subprocess.run(
                [
                    "ffmpeg", "-hide_banner", "-loglevel", "error",
                    "-f", "concat", "-safe", "0", "-i", list_path,
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "28",
                    "-pix_fmt", "yuv420p",
                    "-an",
                    out_path,
                ],
                check=True,
            )

            if os.path.getsize(out_path) <= 0:
                return None
            d = sess.start_ts.astimezone(timezone.utc)
            object_path = f"sessions/{sess.camera_id}/{d.year:04d}/{d.month:02d}/{d.day:02d}/{sess.trace_id}.mp4"
            with open(out_path, "rb") as f:
                montage_bytes = f.read()
            ref = self.gcs.upload_bytes(
                bucket_name=self.cfg.gcs_bucket,
                object_path=object_path,
                data=montage_bytes,
                content_type="video/mp4",
                metadata={"camera_id": sess.camera_id, "trace_id": sess.trace_id, "kind": "session_montage"},
            )
            return ref.gcs_uri
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def _start_session(self, obs: ObservationEvent):
        cam = obs.camera_id
        self.open_sessions[cam] = OpenSession(
            trace_id=obs.trace_id,
            camera_id=cam,
            use_case=obs.use_case,
            station_id=None,
            sku_id=None,
            start_ts=obs.ts,
            start_clip_index=obs.clip_index,
            last_ts=obs.ts,
            last_clip_index=obs.clip_index,
            clip_uris=[obs.clip_gcs_uri],
            timeline=[{"clip_index": obs.clip_index, "summary": obs.summary, "signals": obs.signals or {}}],
        )
        print(f"[sessionizer] START cam={cam} clip={obs.clip_index}")

    def _append(self, obs: ObservationEvent):
        cam = obs.camera_id
        sess = self.open_sessions.get(cam)
        if not sess:
            return
        sess.last_ts = obs.ts
        sess.last_clip_index = obs.clip_index
        sess.clip_uris.append(obs.clip_gcs_uri)
        sess.timeline.append({"clip_index": obs.clip_index, "summary": obs.summary, "signals": obs.signals or {}})

    def _close_session(self, cam: str):
        sess = self.open_sessions.pop(cam, None)
        if not sess:
            print(f"[debug][sessionizer][END ] cam={cam} (no open session to close)")
            return
        montage_uri = self._make_montage(sess)
        summary = f"Board session {sess.start_clip_index}->{sess.last_clip_index}. Last: {sess.timeline[-1]['summary'] if sess.timeline else ''}"

        evt = StationSessionEvent(
            trace_id=sess.trace_id,
            camera_id=sess.camera_id,
            use_case=sess.use_case,
            station_id=sess.station_id,
            sku_id=sess.sku_id,
            start_ts=sess.start_ts,
            end_ts=sess.last_ts,
            start_clip_index=sess.start_clip_index,
            end_clip_index=sess.last_clip_index,
            clip_gcs_uris=sess.clip_uris,
            session_video_gcs_uri=montage_uri,
            timeline=sess.timeline,
            summary=summary,
        )
        produce_model(self.producer, self.cfg.topic_sessions, evt, key=sess.camera_id)
        print(f"[sessionizer] END cam={cam} clips={len(sess.clip_uris)} montage={bool(montage_uri)}")

    def handle_observation(self, msg: dict):
        obs = ObservationEvent(**msg)
        if obs.use_case != "assembly":
            return
        phase = str((obs.signals or {}).get("phase", "uncertain")).lower()
        cam = obs.camera_id
        if phase == "board_in":
            if cam in self.open_sessions:
                self._close_session(cam)
            self._start_session(obs)
            return
        if cam in self.open_sessions:
            self._append(obs)
            if phase == "board_out":
                self._close_session(cam)

    def run(self):
        consume_loop(self.consumer, self.handle_observation)