# Sentinel

> **Multi-Agent Vision-to-Action Platform for Real-Time Video Analytics**

Sentinel is a production-ready reference architecture that transforms raw video streams into autonomous decisions and intelligent actions. Built on **Confluent Cloud** and **Google Cloud Vertex AI**, this system demonstrates how event-driven streaming and multimodal AI create powerful video analytics pipelines that perceive, reason, and act in real-time.

[![Confluent Cloud](https://img.shields.io/badge/Confluent-Cloud-00A5E6?style=flat-square&logo=apache-kafka)](https://confluent.cloud)
[![Google Vertex AI](https://img.shields.io/badge/Google_Cloud-Vertex_AI-4285F4?style=flat-square&logo=google-cloud)](https://cloud.google.com/vertex-ai)
[![Apache Flink](https://img.shields.io/badge/Apache-Flink_SQL-E6526F?style=flat-square)](https://flink.apache.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

---

## Table of Contents

- [What the System Does](#what-the-system-does)
- [Key Capabilities](#key-capabilities)
- [Multi-Agent Architecture](#multi-agent-architecture)
- [Technology Stack](#technology-stack)
- [Use Cases](#use-cases)
- [Prerequisites](#prerequisites)
- [Configuration](#configuration)
- [Running the System](#running-the-system)
- [API Reference](#api-reference)
- [Real-Time Analytics with Flink SQL](#real-time-analytics-with-flink-sql)
- [KPI Dashboard](#kpi-dashboard)
- [BigQuery Analytics](#bigquery-analytics)
- [Extending Sentinel](#extending-sentinel)

---

## What the System Does

Sentinel implements a continuous autonomous loop powered by specialized AI agents:

1. **Ingest**: Video streams segmented into temporal clips with configurable frame sampling
2. **Observe**: Vision Language Models (VLMs) extract structured observations from each clip
3. **Think**: Reasoning agents evaluate observations using rules, context, and RAG-enhanced knowledge
4. **Act**: Autonomous action handlers trigger real-world responses (alerts, webhooks, database updates)
5. **Audit**: Complete decision trail logged evidence chains and confidence scores

The system processes video streams in real-time, making intelligent decisions while maintaining full observability, human oversight, and sub-second latency from observation to action.

---

## Key Capabilities

### 🎥 Vision Language Model (VLM) Processing
Native video understanding using Vertex AI Gemini for multimodal perception—no pre-trained object detection models required. Supports zero-shot detection of any object, activity, or anomaly through natural language prompts.

### 🤖 Multi-Agent Architecture
Loosely-coupled autonomous agents communicate through typed Kafka events. Each agent (Observer, Thinker, Action Handler) operates independently with single-responsibility design, enabling horizontal scaling and fault isolation.

### 📊 Real-Time Stream Analytics
Apache Flink SQL for continuous queries, windowed aggregations, complex event processing, and materialized views. Monitor decision latency, throughput, confidence distributions, and custom KPIs in real-time.

### 🔍 Retrieval-Augmented Generation (RAG)
Vertex AI Search provides contextual knowledge to decision agents. Ground decisions in organizational policies, historical incidents, and domain expertise without retraining models.

### ⚡ Event-Driven with Confluent
Built on Confluent Cloud's fully managed Kafka platform. Avro schemas enforce type safety, Schema Registry handles evolution, and Kafka guarantees ordering, durability, and exactly-once semantics.

### 🎛️ Operator Control & Monitoring
RESTful API and real-time dashboard for status monitoring, manual decision override, and KPI visualization. BigQuery-backed analytics for compliance reporting and system optimization.

---

## Multi-Agent Architecture

### System Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                     VIDEO INPUT SOURCES                          │
│          RTSP • MP4 Files • Cloud Storage • Live Cameras         │
└──────────────────────────────────────────────────────────────────┘
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                    CLIP PRODUCER AGENT                           │
│     Temporal Segmentation • Frame Sampling • GCS Upload          │
└──────────────────────────────────────────────────────────────────┘
                              ▼
                      [clips] Kafka Topic
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                     OBSERVER AGENT                               │
│   Gemini Vision VLM • Object/Activity Detection • Scene Context  │
└──────────────────────────────────────────────────────────────────┘
                              ▼
                   [observations] Kafka Topic
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                     THINKER AGENT                                │
│  Gemini Reasoning • Vertex AI Search (RAG) • Rule Evaluation     │
└──────────────────────────────────────────────────────────────────┘
                              ▼
                    [decisions] Kafka Topic
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                  ACTION HANDLER AGENT                            │
│       Alerts • API Calls • Database Updates • Webhooks           │
└──────────────────────────────────────────────────────────────────┘
                              ▼
                     [actions] Kafka Topic
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                   AUDIT LOGGER AGENT                             │
│          BigQuery Streaming • Event Correlation                  │
└──────────────────────────────────────────────────────────────────┘
                              ▼
        ┌─────────────────────────────────────────────┐
        │         ANALYTICS & CONTROL PLANE           │
        │  Flink SQL • KPI Dashboard • Control API    │
        └─────────────────────────────────────────────┘
```

### Agent Responsibilities

**Clip Producer**: Ingests video streams, performs temporal segmentation, samples frames, uploads to GCS, publishes clip metadata to Kafka.

**Observer Agent**: Consumes clip events, sends video to Gemini Vision API, extracts structured observations (objects, activities, anomalies, scene context), publishes to observations topic.

**Thinker Agent**: Consumes observations, queries Vertex AI Search for relevant context, evaluates against configurable rules using Gemini reasoning, produces decisions with confidence scores and evidence chains.

**Action Handler**: Consumes decisions, executes configured actions (send alerts, call webhooks, update databases), publishes action results with status and timestamps.

**Audit Logger**: Consumes all events, streams to BigQuery for compliance, analytics, and decision replay.

### Why Multi-Agent Design?

**Autonomy**: Each agent operates independently without tight coupling or shared state.

**Scalability**: Scale agents horizontally based on workload (e.g., 10 observers, 3 thinkers, 1 action handler).

**Resilience**: Agent failures don't cascade; Kafka durability ensures no message loss.

**Flexibility**: Swap model versions, add new agents, or modify logic without system-wide redeployment.

**Testability**: Test agents in isolation using synthetic Kafka events.

---

## Technology Stack

### Confluent Cloud: The Streaming Foundation

**Apache Kafka - Event Backbone**

Sentinel uses Confluent Cloud's fully managed Kafka platform for all inter-agent communication. Every event flows through partitioned, replicated Kafka topics with guaranteed ordering and durability.

- **Partitioned Topics**: High-throughput parallel processing with consumer groups
- **Exactly-Once Semantics**: Critical decisions processed without duplication
- **Cross-Region Replication**: Geo-distributed deployments for global operations
- **99.99% Uptime SLA**: Production-grade reliability with automatic failover

**Schema Registry - Data Governance**

All Kafka events use Avro serialization with schemas registered in Confluent's Schema Registry. This enforces type safety, enables schema evolution with compatibility checks, and reduces payload size by 40-60% compared to JSON.

**Apache Flink SQL - Stream Analytics**

Confluent Cloud's managed Flink SQL service powers real-time analytics without custom code. Continuous queries compute windowed aggregations, joins, and complex event patterns directly on Kafka topics.

- **Windowed Aggregations**: Tumbling, sliding, and session windows for KPI calculation
- **Stream-to-Table Joins**: Enrich events with reference data
- **Materialized Views**: Pre-computed aggregates for dashboard queries
- **Exactly-Once Guarantees**: Consistent results even with failures

**ksqlDB - Streaming Transformations**

Real-time data transformations, filtering, and enrichment using SQL statements. Pre-process high-volume streams before expensive AI inference.

### Google Cloud Vertex AI: The Intelligence Layer

**Gemini Vision VLMs - Visual Understanding**

Sentinel uses Vertex AI's Gemini models for native video understanding. Unlike traditional computer vision pipelines requiring pre-trained detectors, VLMs understand video through natural language prompts and detect any object or activity zero-shot.

- **gemini-3.0-flash**: Fast inference for real-time processing at 2-5 FPS
- **gemini-2.5-pro**: Enhanced reasoning for complex multi-object scenes
- **Native Video API**: Process video blobs directly without frame extraction
- **JSON Structured Output**: Reliable parsing of observation schemas
- **1M Token Context**: Analyze extended video sequences in single API calls

**Gemini Reasoning Models - Decision Intelligence**

Gemini's reasoning capabilities evaluate observations against business rules, historical context, and retrieved knowledge to produce explainable decisions.

- **gemini-2.0-flash-001**: Low-latency reasoning for sub-second decision making
- **Chain-of-Thought**: Step-by-step reasoning traces for audit compliance
- **Function Calling**: Dynamic rule evaluation with external context
- **Confidence Scoring**: Probabilistic outputs for threshold-based actions

**Vertex AI Embeddings - Semantic Search**

Convert observations and rules to semantic vectors for similarity search and contextual retrieval using gemini-embedding-001 for 768-dimensional embeddings.

**Vertex AI Search - Retrieval-Augmented Generation**

Custom search engine indexes organizational knowledge (safety protocols, incident history, standard operating procedures). The Thinker agent queries this index to ground decisions in relevant context.

- **Semantic Ranking**: Retrieve most relevant documents for each observation
- **Real-Time Indexing**: Add new policies without retraining models
- **Source Attribution**: Track which documents influenced decisions
- **Reduced Hallucinations**: Constrain model outputs to factual context

### Google Cloud Infrastructure

**Cloud Storage**: Durable video clip storage with lifecycle policies (Standard → Nearline → Archive) for cost optimization.

**BigQuery**: High-performance analytics warehouse for audit logs. Streaming inserts provide immediate query availability. Columnar storage enables fast aggregation queries over billions of events.

---

## Use Cases

### Manufacturing Quality Control
Inspect production lines for defects, assembly errors, and safety violations. Stop production lines automatically when critical issues detected.

### Smart City Traffic Management
Monitor intersections for congestion, accidents, and traffic violations. Automatically dispatch emergency services, adjust signal timing, and alert traffic control centers.

### Retail Loss Prevention
Detect shoplifting behaviors, unattended items, and restricted area access. Generate alerts for security personnel with video evidence and confidence scores.

### Healthcare Patient Safety
Monitor patient rooms for falls, equipment failures, and medication errors. Alert nursing staff with room number and incident description.

### Warehouse Operations
Track inventory movement, detect forklift safety violations, and optimize loading dock utilization. Generate shift reports with KPIs.

---

## Prerequisites

- Python 3.10+
- Confluent Cloud account with Kafka cluster and Schema Registry
- Google Cloud Platform project with:
  - Vertex AI API enabled
  - BigQuery dataset created
  - Cloud Storage bucket configured
  - Service account with Vertex AI User, BigQuery Data Editor, Storage Admin roles
- Video input source (file, RTSP stream, USB camera)

---

## Configuration

Copy the template and configure your environment:

```bash
cp .env.template .env
```

### Confluent Cloud Configuration

```bash
KAFKA_BOOTSTRAP=pkc-xxxxx.us-east-1.aws.confluent.cloud:9092
KAFKA_SECURITY_PROTOCOL=SASL_SSL
KAFKA_SASL_MECHANISMS=PLAIN
KAFKA_API_KEY=your_kafka_api_key
KAFKA_API_SECRET=your_kafka_api_secret

SCHEMA_REGISTRY_URL=https://psrc-xxxxx.us-east-1.aws.confluent.cloud
SCHEMA_REGISTRY_API_KEY=your_schema_registry_key
SCHEMA_REGISTRY_API_SECRET=your_schema_registry_secret
```

### Kafka Topics

```bash
TOPIC_CLIPS=sentinel.clips
TOPIC_OBSERVATIONS=sentinel.observations
TOPIC_DECISIONS=sentinel.decisions
TOPIC_ACTIONS=sentinel.actions
TOPIC_AUDIT=sentinel.audit
TOPIC_SESSIONS=sentinel.sessions
```

### Google Cloud Configuration

```bash
GCP_PROJECT=your-gcp-project-id
GCP_REGION=us-central1
GCS_BUCKET=sentinel-video-clips
BIGQUERY_DATASET=sentinel_analytics
BIGQUERY_AUDIT_TABLE=audit_log
```

### Vertex AI Models

```bash
GEMINI_OBSERVER_MODEL=gemini-3.0-flash
GEMINI_THINKER_MODEL=gemini-2.5-pro
VERTEX_EMBED_MODEL=gemini-embedding-001
VERTEX_SEARCH_LOCATION=global
VERTEX_SEARCH_ENGINE_ID=your_search_engine_id
VERTEX_SEARCH_PROMPT_PREAMBLE=You are analyzing video surveillance data for safety and security.
```

### Processing Configuration

```bash
CLIP_SECONDS=10
SAMPLE_FPS=2
CHAT_HOST=127.0.0.1
CHAT_PORT=8000
```

---

## Running the System

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Initialize Infrastructure

```bash
# Create Kafka topics
python scripts/create_topics.py

# Initialize BigQuery schema
python scripts/init_bigquery.py
```

### Start Control API

```bash
python api/control_server.py
```

### Start Agent Pipeline

Open separate terminals for each agent:

```bash
python agents/observer.py
python agents/thinker.py
python agents/action_handler.py
python agents/audit_logger.py
```

### Start Video Ingestion

```bash
python producers/clip_producer.py --source /path/to/video.mp4

python producers/clip_producer.py --source rtsp://camera-ip:554/stream

python producers/clip_producer.py --source 0
```

---

## API Reference

### Stream Control

**Start Stream**

```http
POST /stream/start
Content-Type: application/json

{
  "stream_id": "camera-01",
  "source": "/path/to/video.mp4",
  "clip_duration": 10,
  "sample_fps": 2
}
```

**Stop Stream**

```http
POST /stream/stop
Content-Type: application/json

{
  "stream_id": "camera-01"
}
```

**Get Stream Status**

```http
GET /stream/status/{stream_id}
```

Returns current status, clips produced, observations count, decisions made, and performance metrics.

**List Active Streams**

```http
GET /streams
```

**Manual Decision Override**

```http
POST /decision/override
Content-Type: application/json

{
  "observation_id": "obs-12345",
  "decision": "approve",
  "operator": "john.doe",
  "reason": "Manual review completed"
}
```

---

## Real-Time Analytics with Flink SQL

Sentinel integrates Confluent Cloud's managed Flink SQL for continuous stream analytics. Deploy these queries to compute real-time KPIs, detect patterns, and trigger alerts directly on Kafka topics.

### Windowed Decision Metrics

```sql
SELECT
  stream_id,
  TUMBLE_START(event_time, INTERVAL '1' MINUTE) as window_start,
  COUNT(*) as decisions_per_minute,
  AVG(decision_latency_ms) as avg_latency_ms,
  PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY decision_latency_ms) as p95_latency_ms,
  COUNT(CASE WHEN confidence > 0.9 THEN 1 END) as high_confidence_count
FROM decisions_stream
GROUP BY stream_id, TUMBLE(event_time, INTERVAL '1' MINUTE);
```

### Complex Event Processing

```sql
SELECT
  stream_id,
  HOP_START(event_time, INTERVAL '1' MINUTE, INTERVAL '5' MINUTE) as window_start,
  COUNT(*) as alert_count,
  COLLECT_LIST(decision_id) as alert_ids
FROM decisions_stream
WHERE decision_type = 'alert' AND confidence > 0.85
GROUP BY stream_id, HOP(event_time, INTERVAL '1' MINUTE, INTERVAL '5' MINUTE)
HAVING COUNT(*) >= 3;
```

### Materialized Views for Dashboards

```sql
CREATE MATERIALIZED VIEW hourly_kpis AS
SELECT
  stream_id,
  DATE_FORMAT(event_time, 'yyyy-MM-dd HH:00:00') as hour,
  COUNT(DISTINCT clip_id) as clips_processed,
  COUNT(DISTINCT observation_id) as observations_made,
  COUNT(DISTINCT decision_id) as decisions_made,
  AVG(confidence) as avg_confidence
FROM audit_stream
GROUP BY stream_id, DATE_FORMAT(event_time, 'yyyy-MM-dd HH:00:00');
```

---

## KPI Dashboard

Access the real-time dashboard at `/dashboard`

### Available Metrics

**Processing Metrics**: Clips processed, observations generated, decisions made, actions executed

**Performance Metrics**: Average decision latency, P95 latency, throughput per minute, action success rate

**Quality Metrics**: Decision confidence distribution, high-confidence decisions, top decision types, alert rate

**System Health**: Active streams, agent status, Kafka consumer lag, error rate

### KPI Endpoint

```http
GET /kpi?period=24h&stream_id=camera-01
```

Query parameters: `period` (1h, 24h, 7d, 30d), `stream_id` (optional filter)

Returns aggregated metrics including clips processed, observations generated, decisions made, latencies, confidence distributions, and top decision types.

---

## BigQuery Analytics

### Schema

```sql
CREATE TABLE sentinel_analytics.audit_log (
  event_id STRING NOT NULL,
  event_type STRING NOT NULL,
  stream_id STRING,
  timestamp TIMESTAMP NOT NULL,
  clip_id STRING,
  observation_id STRING,
  decision_id STRING,
  action_id STRING,
  payload JSON,
  metadata JSON,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY DATE(timestamp)
CLUSTER BY stream_id, event_type;
```

### Sample Queries

**Decision Performance Analysis**

```sql
SELECT
  DATE(timestamp) as date,
  stream_id,
  COUNT(*) as total_decisions,
  AVG(CAST(JSON_VALUE(payload, '$.confidence') AS FLOAT64)) as avg_confidence,
  COUNTIF(JSON_VALUE(payload, '$.decision_type') = 'alert') as alert_count
FROM `sentinel_analytics.audit_log`
WHERE event_type = 'decision'
  AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
GROUP BY date, stream_id
ORDER BY date DESC;
```

**Decision Latency Analysis**

```sql
WITH observations AS (
  SELECT observation_id, timestamp as obs_time
  FROM `sentinel_analytics.audit_log`
  WHERE event_type = 'observation'
),
decisions AS (
  SELECT 
    JSON_VALUE(payload, '$.observation_id') as observation_id,
    timestamp as decision_time
  FROM `sentinel_analytics.audit_log`
  WHERE event_type = 'decision'
)
SELECT
  AVG(TIMESTAMP_DIFF(d.decision_time, o.obs_time, MILLISECOND)) as avg_latency_ms,
  APPROX_QUANTILES(TIMESTAMP_DIFF(d.decision_time, o.obs_time, MILLISECOND), 100)[OFFSET(95)] as p95_latency_ms
FROM observations o
JOIN decisions d ON o.observation_id = d.observation_id
WHERE o.obs_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR);
```

---

## Extending Sentinel

### Adding Custom Observation Types

Create new Avro schemas in `schemas/observations/` and register with Schema Registry:

```bash
python scripts/register_schema.py --schema schemas/observations/custom_observation.avsc
```

### Building New Action Handlers

Implement the `ActionHandler` interface with custom logic for external system integration (Slack, databases, ticketing systems).

### Integrating External Systems

Use Action Handlers to bridge to ticketing systems (Jira, ServiceNow), communication platforms (Slack, PagerDuty), security systems, or data lakes (Snowflake, Databricks).

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## Acknowledgments

Built for the **Confluent + Google Cloud AI Partner Catalyst Hackathon**.

Sentinel demonstrates the power of combining Confluent's event streaming platform with Google Cloud's multimodal AI capabilities to create intelligent, autonomous video analytics systems that operate at scale.

**Technologies**: Apache Kafka • Apache Flink SQL • Vertex AI Gemini • Vertex AI Search • BigQuery • Cloud Storage

**Architecture Pattern**: Event-Driven • Multi-Agent Systems • Vision Language Models • Retrieval-Augmented Generation