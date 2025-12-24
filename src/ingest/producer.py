from __future__ import annotations
import os
import threading
from datetime import datetime, timezone
from typing import Optional
from ..config.settings import Settings
from ..shared.kafka_client import make_producer, produce_model
from ..shared.events import ClipEvent
from ..shared.gcs_client import GcsClient
from .clipper import VideoClipper

def _gcs_object_path(
    use_case: str,
    camera_id: str,
    clip_id: str,
    clip_index: int,
    start_ts: datetime,
) -> str:
    d = start_ts.astimezone(timezone.utc)
    return f"{use_case}/{camera_id}/{d.year:04d}/{d.month:02d}/{d.day:02d}/{clip_index:06d}_{clip_id}.mp4"


def publish_clips_from_video(
    cfg: Settings,
    video_path: str,
    camera_id: str,
    use_case: str,
    station_id: Optional[str] = None,
    sku_id: Optional[str] = None,
    max_clips: Optional[int] = None,
    stop_event: Optional[threading.Event] = None,
) -> None:
    producer = make_producer(cfg)
    gcs = GcsClient(project=cfg.gcp_project)
    clipper = VideoClipper(clip_seconds=cfg.clip_seconds, sample_fps=cfg.sample_fps)
    count = 0
    for clip in clipper.iter_clips(video_path):
        if stop_event is not None and stop_event.is_set():
            print(f"[producer] stop_event set → stopping producer for {use_case}")
            break
        local_size = os.path.getsize(clip.path)
        if local_size <= 0:
            print(f"[producer] SKIP zero-byte local clip: {clip.path}")
            continue
        evt = ClipEvent(
            camera_id=camera_id,
            station_id=station_id,
            sku_id=sku_id,
            use_case=use_case,
            clip_index=clip.clip_index,
            clip_start_ts=clip.start_ts,
            clip_end_ts=clip.end_ts,
            gcs_uri="gs://placeholder/will_set",
        )
        with open(clip.path, "rb") as f:
            data = f.read()
        if len(data) == 0:
            print(f"[producer] SKIP read 0 bytes: {clip.path}")
            continue
        obj_path = _gcs_object_path(use_case, camera_id, evt.clip_id, clip.clip_index, clip.start_ts)
        ref = gcs.upload_bytes(
            bucket_name=cfg.gcs_bucket,
            object_path=obj_path,
            data=data,
            content_type="video/mp4",
            metadata={
                "clip_id": evt.clip_id,
                "trace_id": evt.trace_id,
                "camera_id": camera_id,
                "use_case": use_case,
                "clip_index": str(clip.clip_index),
            },
        )
        evt.gcs_uri = ref.gcs_uri
        evt.content_sha256 = ref.sha256
        evt.labels.update({
            "source_video": os.path.basename(video_path),
            "local_clip_bytes": len(data),
        })
        produce_model(producer, cfg.topic_clips, evt, key=camera_id)
        try:
            os.remove(clip.path)
        except OSError:
            pass
        count += 1
        if max_clips is not None and count >= max_clips:
            print(f"[producer] reached max_clips={max_clips}, stopping.")
            break
    print(f"[producer] stopped for use_case={use_case}, clips_published={count}")