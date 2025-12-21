from __future__ import annotations
import json
from datetime import datetime, timezone
from google.cloud import bigquery
from ..config.settings import Settings
from ..shared.kafka_client import make_consumer
from ..shared.events import AuditEvent

def ensure_audit_table(cfg: Settings) -> None:
    bq = bigquery.Client(project=cfg.gcp_project)
    table_id = f"{cfg.gcp_project}.{cfg.bigquery_dataset}.{cfg.bigquery_audit_table}"
    schema = [
        bigquery.SchemaField("audit_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("ts", "TIMESTAMP", mode="REQUIRED"),
        bigquery.SchemaField("kind", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("trace_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("payload_json", "STRING", mode="REQUIRED"),
    ]
    try:
        bq.get_table(table_id)
    except Exception:
        table = bigquery.Table(table_id, schema=schema)
        bq.create_table(table)
        print("[audit] created BigQuery audit table:", table_id)


class BigQueryAuditWriter:
    def __init__(self, cfg: Settings):
        self.cfg = cfg
        ensure_audit_table(cfg)
        self.bq = bigquery.Client(project=cfg.gcp_project)
        self.consumer = make_consumer(
            cfg,
            group_id="audit-writer-v3",
            topics=[
                cfg.topic_observations,
                cfg.topic_sessions,
                cfg.topic_decisions,
                cfg.topic_actions,
            ],
            offset_reset="latest",
        )

    def _insert(self, kind: str, trace_id: str, payload: dict):
        table_id = f"{self.cfg.gcp_project}.{self.cfg.bigquery_dataset}.{self.cfg.bigquery_audit_table}"
        evt = AuditEvent(
            ts=datetime.now(timezone.utc),
            kind=kind,
            trace_id=trace_id,
            payload=payload,
        )
        row = {
            "audit_id": evt.audit_id,
            "ts": evt.ts.isoformat(),
            "kind": evt.kind,
            "trace_id": evt.trace_id,
            "payload_json": json.dumps(evt.payload),
        }
        errors = self.bq.insert_rows_json(table_id, [row])
        if errors:
            print("[audit] BigQuery insert errors:", errors)

    def run(self):
        import json as _json

        while True:
            msg = self.consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                print("[audit] Kafka error:", msg.error())
                continue
            payload = _json.loads(msg.value().decode("utf-8"))
            if "action_id" in payload:
                kind, trace = "action", payload.get("trace_id", "")
            elif "decision_id" in payload:
                kind, trace = "decision", payload.get("trace_id", "")
            elif "session_id" in payload:
                kind, trace = "session", payload.get("trace_id", "")
            elif "observation_id" in payload:
                kind, trace = "observation", payload.get("trace_id", "")
            elif "clip_id" in payload and "gcs_uri" in payload:
                kind, trace = "clip", payload.get("trace_id", "")
            else:
                kind, trace = "unknown", payload.get("trace_id", "")
            self._insert(kind, trace, payload)