from __future__ import annotations
import json
import uuid
from typing import Any, Dict, List
from google.cloud import bigquery
from ..config.settings import Settings
from .sop_chunker import sop_to_chunks
from .vertex_embed import VertexEmbedder


def ensure_sop_table(cfg: Settings) -> None:
    bq = bigquery.Client(project=cfg.gcp_project)
    table_id = f"{cfg.gcp_project}.{cfg.bigquery_dataset}.sop_chunks"
    schema = [
        bigquery.SchemaField("chunk_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("chunk_text", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("metadata_json", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("embedding_json", "STRING", mode="REQUIRED"),
    ]
    try:
        bq.get_table(table_id)
    except Exception:
        table = bigquery.Table(table_id, schema=schema)
        bq.create_table(table)
        print("[rag] created table sop_chunks")


def ingest_sop_to_vertex(cfg: Settings) -> None:
    with open(cfg.assembly_sop_path, "r", encoding="utf-8") as f:
        sop = json.load(f)
    chunks = sop_to_chunks(sop)
    texts = [c["chunk_text"] for c in chunks]
    embedder = VertexEmbedder(cfg)
    vectors = embedder.embed(texts)
    ensure_sop_table(cfg)
    bq = bigquery.Client(project=cfg.gcp_project)
    table_id = f"{cfg.gcp_project}.{cfg.bigquery_dataset}.sop_chunks"
    rows = []
    for c, v in zip(chunks, vectors):
        chunk_id = str(uuid.uuid4())
        rows.append({
            "chunk_id": chunk_id,
            "chunk_text": c["chunk_text"],
            "metadata_json": json.dumps(c["metadata"]),
            "embedding_json": json.dumps(v),
        })
    errors = bq.insert_rows_json(table_id, rows)
    if errors:
        raise RuntimeError(f"BigQuery insert errors (sop_chunks): {errors}")
    print(f"[rag] ingested {len(rows)} SOP chunks into BigQuery sop_chunks")

    print("[rag] NOTE: Vector Search datapoint upsert step depends on your index config.")
    print("[rag] For hackathon, we can retrieve via BigQuery embedding search OR wire Vector Search upsert next.")