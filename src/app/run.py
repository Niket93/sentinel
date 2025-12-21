from __future__ import annotations
import threading
import uvicorn
from ..config.settings import load_settings
from ..shared.kafka_client import ensure_schemas, bind_topic_models
from ..ingest.producer import publish_clips_from_video
from ..agents.observer.observer import ObserverService
from ..agents.sessionizer.sessionizer import SessionizerService
from ..agents.thinker.thinker import ThinkerService
from ..agents.doer.doer import DoerService
from ..audit.bq_writer import BigQueryAuditWriter
from ..chat.api import build_app
from ..rag.ingest_sop import ingest_sop_to_vertex


def main():
    cfg = load_settings(".env")

    ids = ensure_schemas(cfg)
    bind_topic_models(cfg)
    print("[run] Schema Registry OK. Schema IDs:", ids)
    INGEST_SOP_ON_START = False
    if INGEST_SOP_ON_START:
        ingest_sop_to_vertex(cfg)
    observer = ObserverService(cfg)
    sessionizer = SessionizerService(cfg)
    thinker = ThinkerService(cfg)
    doer = DoerService(cfg)
    audit = BigQueryAuditWriter(cfg)

    threading.Thread(target=observer.run, daemon=True).start()
    threading.Thread(target=sessionizer.run, daemon=True).start()
    threading.Thread(target=thinker.run, daemon=True).start()
    threading.Thread(target=doer.run, daemon=True).start()
    threading.Thread(target=audit.run, daemon=True).start()

    RUN_ASSEMBLY = False
    RUN_SECURITY = False

    if RUN_ASSEMBLY:
        def assembly_producer_job():
            publish_clips_from_video(
                cfg=cfg,
                video_path=cfg.assembly_video_path,
                camera_id="cam-assembly-s4",
                use_case="assembly",
                station_id="S4",
                sku_id="S1345780",
                max_clips=None,
            )
        threading.Thread(target=assembly_producer_job, daemon=True).start()

    if RUN_SECURITY:
        def security_producer_job():
            publish_clips_from_video(
                cfg=cfg,
                video_path=cfg.security_video_path,
                camera_id="cam-security-1",
                use_case="security",
                station_id=None,
                sku_id=None,
                max_clips=None,
            )
        threading.Thread(target=security_producer_job, daemon=True).start()

    app = build_app(cfg)
    print(f"[run] Chat API: http://{cfg.chat_host}:{cfg.chat_port}")
    print(f"[run] Demo UI: http://{cfg.chat_host}:{cfg.chat_port}/ui")
    uvicorn.run(app, host=cfg.chat_host, port=cfg.chat_port, access_log=False)

if __name__ == "__main__":
    main()