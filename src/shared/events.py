from __future__ import annotations

from typing import Any, Literal, Optional, Dict, List
from datetime import datetime
from pydantic import BaseModel, Field
import uuid

def new_id() -> str:
    return str(uuid.uuid4())

UseCase = Literal["assembly", "security"]

class ClipEvent(BaseModel):
    clip_id: str = Field(default_factory=new_id)
    trace_id: str = Field(default_factory=new_id)
    camera_id: str
    station_id: Optional[str] = None
    sku_id: Optional[str] = None
    use_case: UseCase
    clip_index: int
    clip_start_ts: datetime
    clip_end_ts: datetime
    gcs_uri: str
    content_sha256: Optional[str] = None
    labels: Dict[str, Any] = Field(default_factory=dict)


class ObservationEvent(BaseModel):
    observation_id: str = Field(default_factory=new_id)
    trace_id: str
    clip_id: str
    clip_gcs_uri: Optional[str] = None
    camera_id: str
    use_case: UseCase
    clip_index: int
    ts: datetime
    summary: str
    entities: List[Dict[str, Any]] = Field(default_factory=list)
    signals: Dict[str, Any] = Field(default_factory=dict)
    model: Dict[str, Any] = Field(default_factory=dict)


class StationSessionEvent(BaseModel):
    session_id: str = Field(default_factory=new_id)
    trace_id: str
    camera_id: str
    use_case: UseCase
    station_id: Optional[str] = None
    sku_id: Optional[str] = None
    start_ts: datetime
    end_ts: datetime
    start_clip_index: int
    end_clip_index: int
    clip_gcs_uris: List[str] = Field(default_factory=list)
    session_video_gcs_uri: Optional[str] = None
    timeline: List[Dict[str, Any]] = Field(default_factory=list)
    summary: str = ""


class DecisionEvent(BaseModel):
    decision_id: str = Field(default_factory=new_id)
    trace_id: str

    clip_id: str
    observation_id: str
    camera_id: str
    use_case: UseCase
    clip_index: int
    ts: datetime
    assessment: Dict[str, Any]
    recommended_actions: List[Dict[str, Any]]
    rationale: Dict[str, Any]
    evidence: Dict[str, Any] = Field(default_factory=dict)
    model: Dict[str, Any] = Field(default_factory=dict)


class ActionEvent(BaseModel):
    action_id: str = Field(default_factory=new_id)
    trace_id: str
    decision_id: str
    camera_id: str
    use_case: UseCase
    ts: datetime
    action: Dict[str, Any]
    status: Literal["sent", "skipped", "failed"]
    provider: str
    error: Optional[str] = None


class AuditEvent(BaseModel):
    audit_id: str = Field(default_factory=new_id)
    ts: datetime
    kind: Literal["clip", "observation", "session", "decision", "action", "chat"]
    trace_id: str
    payload: Dict[str, Any]


def schema_for(model_cls: type[BaseModel]) -> Dict[str, Any]:
    return model_cls.model_json_schema()