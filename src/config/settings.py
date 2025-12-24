from __future__ import annotations

import os
from dataclasses import dataclass
from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    kafka_bootstrap: str
    kafka_security_protocol: str
    kafka_sasl_mechanisms: str
    kafka_api_key: str
    kafka_api_secret: str
    schema_registry_url: str
    schema_registry_api_key: str
    schema_registry_api_secret: str
    topic_clips: str
    topic_observations: str
    topic_sessions: str
    topic_decisions: str
    topic_actions: str
    topic_audit: str
    gcp_project: str
    gcp_region: str
    gcs_bucket: str
    bigquery_dataset: str
    bigquery_audit_table: str
    gemini_observer_model: str
    gemini_thinker_model: str
    vertex_embed_model: str
    vertex_search_location: str
    vertex_search_engine_id: str
    vertex_search_prompt_preamble: str
    assembly_video_path: str
    security_video_path: str
    assembly_sop_path: str
    clip_seconds: float
    sample_fps: int
    chat_host: str
    chat_port: int


def _require(name: str) -> str:
    v = os.getenv(name, "").strip()
    if not v:
        raise RuntimeError(f"Missing required env var: {name}")
    return v


def _optional(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def load_settings(env_path: str = ".env") -> Settings:
    load_dotenv(env_path)

    return Settings(
        kafka_bootstrap=_require("KAFKA_BOOTSTRAP"),
        kafka_security_protocol=_optional("KAFKA_SECURITY_PROTOCOL", "SASL_SSL"),
        kafka_sasl_mechanisms=_optional("KAFKA_SASL_MECHANISMS", "PLAIN"),
        kafka_api_key=_require("KAFKA_API_KEY"),
        kafka_api_secret=_require("KAFKA_API_SECRET"),
        schema_registry_url=_require("SCHEMA_REGISTRY_URL"),
        schema_registry_api_key=_require("SCHEMA_REGISTRY_API_KEY"),
        schema_registry_api_secret=_require("SCHEMA_REGISTRY_API_SECRET"),
        topic_clips=_optional("TOPIC_CLIPS", "video.clips"),
        topic_observations=_optional("TOPIC_OBSERVATIONS", "video.observations"),
        topic_sessions=_optional("TOPIC_SESSIONS", "station.sessions"),
        topic_decisions=_optional("TOPIC_DECISIONS", "sop.decisions"),
        topic_actions=_optional("TOPIC_ACTIONS", "workflow.actions"),
        topic_audit=_optional("TOPIC_AUDIT", "audit.events"),
        gcp_project=_require("GCP_PROJECT"),
        gcp_region=_optional("GCP_REGION", "us-central1"),
        gcs_bucket=_require("GCS_BUCKET"),
        bigquery_dataset=_require("BIGQUERY_DATASET"),
        bigquery_audit_table=_optional("BIGQUERY_AUDIT_TABLE", "audit_events"),
        gemini_observer_model=_optional("GEMINI_OBSERVER_MODEL", "gemini-2.5-flash"),
        gemini_thinker_model=_optional("GEMINI_THINKER_MODEL", "gemini-2.5-flash"),
        vertex_embed_model=_optional("VERTEX_EMBED_MODEL", "gemini-embedding-001"),
        vertex_search_location=_optional("VERTEX_SEARCH_LOCATION", "us"),
        vertex_search_engine_id=_require("VERTEX_SEARCH_ENGINE_ID"),
        vertex_search_prompt_preamble=_optional("VERTEX_SEARCH_PROMPT_PREAMBLE", ""),
        assembly_video_path=_require("ASSEMBLY_VIDEO_PATH"),
        security_video_path=_require("SECURITY_VIDEO_PATH"),
        assembly_sop_path=_require("ASSEMBLY_SOP_PATH"),
        clip_seconds=float(_optional("CLIP_SECONDS", "1.5")),
        sample_fps=int(_optional("SAMPLE_FPS", "10")),
        chat_host=_optional("CHAT_HOST", "127.0.0.1"),
        chat_port=int(_optional("CHAT_PORT", os.getenv("PORT", "8000"))),
    )