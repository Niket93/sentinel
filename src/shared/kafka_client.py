# from __future__ import annotations
# import json
# from typing import Any, Callable, Optional, Type
# from confluent_kafka import Producer, Consumer
# from confluent_kafka.schema_registry import SchemaRegistryClient, Schema
# from confluent_kafka.schema_registry.error import SchemaRegistryError
# from .events import ClipEvent, ObservationEvent, StationSessionEvent, DecisionEvent, ActionEvent, AuditEvent, schema_for
# from ..config.settings import Settings


# def make_producer(cfg: Settings) -> Producer:
#     return Producer({
#         "bootstrap.servers": cfg.kafka_bootstrap,
#         "security.protocol": cfg.kafka_security_protocol,
#         "sasl.mechanisms": cfg.kafka_sasl_mechanisms,
#         "sasl.username": cfg.kafka_api_key,
#         "sasl.password": cfg.kafka_api_secret,
#         "linger.ms": 5,
#         "acks": "all",
#     })


# def make_consumer(cfg: Settings, group_id: str, topics: list[str], offset_reset: str = "earliest") -> Consumer:
#     c = Consumer({
#         "bootstrap.servers": cfg.kafka_bootstrap,
#         "group.id": group_id,
#         "auto.offset.reset": offset_reset,
#         "enable.auto.commit": True,
#         "security.protocol": cfg.kafka_security_protocol,
#         "sasl.mechanisms": cfg.kafka_sasl_mechanisms,
#         "sasl.username": cfg.kafka_api_key,
#         "sasl.password": cfg.kafka_api_secret,
#     })
#     c.subscribe(topics)
#     return c


# def make_schema_registry(cfg: Settings) -> SchemaRegistryClient:
#     return SchemaRegistryClient({
#         "url": cfg.schema_registry_url,
#         "basic.auth.user.info": f"{cfg.schema_registry_api_key}:{cfg.schema_registry_api_secret}",
#     })


# def _subject_name(topic: str, record_name: str) -> str:
#     return f"{topic}-value"


# def register_json_schema(
#     sr: SchemaRegistryClient,
#     topic: str,
#     record_name: str,
#     schema_dict: dict[str, Any],
# ) -> int:
#     subject = _subject_name(topic, record_name)
#     schema_str = json.dumps(schema_dict)
#     schema = Schema(schema_str, schema_type="JSON")

#     try:
#         schema_id = sr.register_schema(subject, schema)
#         return schema_id
#     except SchemaRegistryError as e:
#         raise RuntimeError(f"Schema Registry error registering {subject}: {e}") from e


# def ensure_schemas(cfg: Settings) -> dict[str, int]:
#     sr = make_schema_registry(cfg)
#     ids: dict[str, int] = {}
#     ids["ClipEvent"] = register_json_schema(sr, cfg.topic_clips, "ClipEvent", schema_for(ClipEvent))
#     ids["ObservationEvent"] = register_json_schema(sr, cfg.topic_observations, "ObservationEvent", schema_for(ObservationEvent))
#     ids["DecisionEvent"] = register_json_schema(sr, cfg.topic_decisions, "DecisionEvent", schema_for(DecisionEvent))
#     ids["ActionEvent"] = register_json_schema(sr, cfg.topic_actions, "ActionEvent", schema_for(ActionEvent))
#     ids["AuditEvent"] = register_json_schema(sr, cfg.topic_audit, "AuditEvent", schema_for(AuditEvent))
#     ids["StationSessionEvent"] = register_json_schema(sr, cfg.topic_sessions, "StationSessionEvent", schema_for(StationSessionEvent))
#     return ids


# MODEL_BY_TOPIC: dict[str, Type] = {}


# def bind_topic_models(cfg: Settings) -> None:
#     global MODEL_BY_TOPIC
#     MODEL_BY_TOPIC = {
#         cfg.topic_clips: ClipEvent,
#         cfg.topic_observations: ObservationEvent,
#         cfg.topic_decisions: DecisionEvent,
#         cfg.topic_actions: ActionEvent,
#         cfg.topic_audit: AuditEvent,
#         cfg.topic_sessions: StationSessionEvent,
#     }


# def produce_model(p: Producer, topic: str, model_obj: Any, key: Optional[str] = None) -> None:
#     payload = model_obj.model_dump(mode="json")
#     data = json.dumps(payload).encode("utf-8")
#     p.produce(topic, value=data, key=(key.encode("utf-8") if key else None))
#     p.flush()


# def consume_loop(c: Consumer, handler: Callable[[dict[str, Any]], None]) -> None:
#     while True:
#         msg = c.poll(1.0)
#         if msg is None:
#             continue
#         if msg.error():
#             print("Kafka error:", msg.error())
#             continue
#         payload = json.loads(msg.value().decode("utf-8"))
#         handler(payload)

from __future__ import annotations
import json
import os
from typing import Any, Callable, Optional, Type
from confluent_kafka import Producer, Consumer
from confluent_kafka.schema_registry import SchemaRegistryClient, Schema
from confluent_kafka.schema_registry.error import SchemaRegistryError
from .events import ClipEvent, ObservationEvent, StationSessionEvent, DecisionEvent, ActionEvent, AuditEvent, schema_for
from ..config.settings import Settings


def make_producer(cfg: Settings) -> Producer:
    return Producer({
        "bootstrap.servers": cfg.kafka_bootstrap,
        "security.protocol": cfg.kafka_security_protocol,
        "sasl.mechanisms": cfg.kafka_sasl_mechanisms,
        "sasl.username": cfg.kafka_api_key,
        "sasl.password": cfg.kafka_api_secret,
        "linger.ms": 5,
        "acks": "all",
    })


def make_consumer(cfg: Settings, group_id: str, topics: list[str], offset_reset: str = "earliest") -> Consumer:
    offset_reset = os.getenv("KAFKA_OFFSET_RESET", offset_reset)
    c = Consumer({
        "bootstrap.servers": cfg.kafka_bootstrap,
        "group.id": group_id,
        "auto.offset.reset": offset_reset,
        "enable.auto.commit": True,
        "security.protocol": cfg.kafka_security_protocol,
        "sasl.mechanisms": cfg.kafka_sasl_mechanisms,
        "sasl.username": cfg.kafka_api_key,
        "sasl.password": cfg.kafka_api_secret,
    })
    c.subscribe(topics)
    return c


def make_schema_registry(cfg: Settings) -> SchemaRegistryClient:
    return SchemaRegistryClient({
        "url": cfg.schema_registry_url,
        "basic.auth.user.info": f"{cfg.schema_registry_api_key}:{cfg.schema_registry_api_secret}",
    })


def _subject_name(topic: str, record_name: str) -> str:
    return f"{topic}-value"


def register_json_schema(
    sr: SchemaRegistryClient,
    topic: str,
    record_name: str,
    schema_dict: dict[str, Any],
) -> int:
    subject = _subject_name(topic, record_name)
    schema_str = json.dumps(schema_dict)
    schema = Schema(schema_str, schema_type="JSON")
    try:
        schema_id = sr.register_schema(subject, schema)
        return schema_id
    except SchemaRegistryError as e:
        raise RuntimeError(f"Schema Registry error registering {subject}: {e}") from e


def ensure_schemas(cfg: Settings) -> dict[str, int]:
    sr = make_schema_registry(cfg)
    ids: dict[str, int] = {}
    ids["ClipEvent"] = register_json_schema(sr, cfg.topic_clips, "ClipEvent", schema_for(ClipEvent))
    ids["ObservationEvent"] = register_json_schema(sr, cfg.topic_observations, "ObservationEvent", schema_for(ObservationEvent))
    ids["DecisionEvent"] = register_json_schema(sr, cfg.topic_decisions, "DecisionEvent", schema_for(DecisionEvent))
    ids["ActionEvent"] = register_json_schema(sr, cfg.topic_actions, "ActionEvent", schema_for(ActionEvent))
    ids["AuditEvent"] = register_json_schema(sr, cfg.topic_audit, "AuditEvent", schema_for(AuditEvent))
    ids["StationSessionEvent"] = register_json_schema(sr, cfg.topic_sessions, "StationSessionEvent", schema_for(StationSessionEvent))
    return ids


MODEL_BY_TOPIC: dict[str, Type] = {}


def bind_topic_models(cfg: Settings) -> None:
    global MODEL_BY_TOPIC
    MODEL_BY_TOPIC = {
        cfg.topic_clips: ClipEvent,
        cfg.topic_observations: ObservationEvent,
        cfg.topic_decisions: DecisionEvent,
        cfg.topic_actions: ActionEvent,
        cfg.topic_audit: AuditEvent,
        cfg.topic_sessions: StationSessionEvent,
    }


def produce_model(p: Producer, topic: str, model_obj: Any, key: Optional[str] = None) -> None:
    payload = model_obj.model_dump(mode="json")
    data = json.dumps(payload).encode("utf-8")
    p.produce(topic, value=data, key=(key.encode("utf-8") if key else None))


def consume_loop(c: Consumer, handler: Callable[[dict[str, Any]], None]) -> None:
    while True:
        msg = c.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            print("Kafka error:", msg.error())
            continue
        payload = json.loads(msg.value().decode("utf-8"))
        handler(payload)