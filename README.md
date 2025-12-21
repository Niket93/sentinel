# Sentinel

> **Vision-to-Action System for Streaming Data**

Sentinel is a reference architecture for converting raw input video or sensor streams into structured observations, decisions with evidence, and operator-ready actions, backed by a durable audit log.

This repository demonstrates an end-to-end "Vision-to-Action" pipeline built from modular agents that communicate through typed events. The emphasis is on **system design**—how perception, reasoning, action, and audit fit together.

---

## Table of Contents

- [What the System Does](#what-the-system-does)
- [Key Properties](#key-properties)
- [High-Level Data Flow](#high-level-data-flow)
- [Repository Layout](#repository-layout)
- [Prerequisites](#prerequisites)
- [Configuration](#configuration)
- [Running the System](#running-the-system)
- [Demo Guide](#demo-guide)
- [Extending Sentinel](#extending-sentinel)

---

## What the System Does

Sentinel implements a continuous loop:

```
Capture → Clip → Observe → Aggregate → Decide → Act → Audit → Explain
```

### Pipeline Stages

**Capture/Clip**  
Takes a input video (or a stream) and segments it into short clips.

**Observe**  
Runs multimodal perception on each clip to produce a human-readable summary plus structured signals.

**Aggregate**
Groups multiple observations into a higher-level "session" to provide context to act as a running memory.

**Decide**  
Applies policy and reasoning to observations to produce a decision with evidence and recommended actions.

**Act**  
Produces operator-ready, execution-oriented instructions for the recommended actions.

**Audit**  
Stores observations, sessions, decisions, and actions in an audit log.

**Explain**  
A UI and chat endpoint surface "what happened and why" grounded in the audit log.

---

## Key Properties

- **Event-driven**: Each service is decoupled and communicates via Kafka topics.
- **Typed contracts**: Messages between services follow explicit schemas.
- **Evidence-first decisions**: Every decision includes rationale and evidence references.
- **Audit-first storage**: The audit log is the source of truth for UI, analytics, and Q&A.
- **Replaceable components**: Swap models, policies, sinks, or storage without rewriting the pipeline.

---

## High-Level Data Flow

```
Video Source
    ↓
ClipEvent
    ↓
ObservationEvent
    ↓
StationSessionEvent (Running Memory)
    ↓
DecisionEvent
    ↓
ActionEvent
    ↓
Audit Log
    ↓
UI and Chat API
```

---

## Repository Layout

```
data/
├── videos/          # Sample demo videos used for generating events
└── sop/             # Example reference documents used for retrieval (optional)

src/
├── ingest/
│   ├── clipper.py   # ffmpeg-based clip segmentation
│   └── producer.py  # Uploads clips to storage and publishes ClipEvent
│
├── agents/
│   ├── observer/    # Clip perception → ObservationEvent
│   ├── sessionizer/ # Aggregation → StationSessionEvent
│   ├── thinker/     # Reasoning/policy → DecisionEvent
│   └── doer/        # Operator instructions → ActionEvent
│
├── audit/
│   └── bq_writer.py # Writes events into the audit table
│
├── chat/
│   └── api.py       # UI endpoints + chat endpoint backed by audit log
│
├── rag/             # Utilities for reference document ingestion
│
└── shared/
    ├── events.py        # Event schemas
    ├── kafka_client.py  # Kafka + schema registry helpers
    ├── gcs_client.py    # Storage helpers
    └── vertex_client.py # Vertex initialization
```

---

## Prerequisites

### Python
- **Python 3.10+** recommended

### System Dependencies
**ffmpeg** must be installed as a system binary:
- **macOS**: `brew install ffmpeg`
- **Ubuntu/Debian**: `sudo apt-get update && sudo apt-get install -y ffmpeg`

### Python Dependencies
```bash
pip install -r requirements.txt
```

### Cloud Services
- **Kafka + Schema Registry** (for event transport and schema registration)
- **Google Cloud Storage** (for clip storage)
- **Vertex AI** (multimodal perception and reasoning)
- **BigQuery** (audit log storage and UI backend)
- **Vertex AI Search Engine** (Retrieval for chat/policy grounding)

### Authentication
Google Cloud access uses **Application Default Credentials (ADC)**. Ensure your environment is authenticated:
```bash
gcloud auth application-default login
```

---

## Configuration

1. Create a `.env` file from `.env.example`:
   ```bash
   cp .env.example .env
   ```

2. Fill in the required configuration:
   - Kafka bootstrap + credentials
   - Schema registry URL + credentials
   - Google Cloud project, region, bucket
   - BigQuery dataset/table
   - Model IDs (Vertex AI)
   - Retrieval config (Discovery Engine) if enabled
   - Paths to local demo videos and optional reference documents

---

## Running the System

1. **Install prerequisites**
   - System: `ffmpeg`
   - Python: `pip install -r requirements.txt`

2. **Configure** `.env` with your credentials and settings

3. **Start the pipeline and UI**:
   ```bash
   python -m src.app.run
   ```

4. **Access the interfaces**:
   - **UI**: http://127.0.0.1:8000/ui
   - **API docs**: http://127.0.0.1:8000/docs

---

## Demo Guide

### What to Look for During a Demo

1. **Event stream**: Watch the flow from Observation → Decision → Action

2. **Decision detail**: Examine the recommended action, severity/confidence, rationale, and evidence

3. **Clip links**: Decisions/actions reference supporting clips stored in cloud storage

4. **Audit chat**: Ask questions and receive answers grounded in audit history

---

## Extending Sentinel

### Common Extension Points

**Observer**  
Change the perception prompt and signal schema to match your domain.

**Sessionizer**  
Add different session boundary logic for different workflows.

**Thinker**  
Implement new policy logic (rules, LLM reasoning, hybrid) while preserving the DecisionEvent contract.

**Doer**  
Add integrations (Slack, PagerDuty, ticketing, PLC, email) by consuming ActionEvents.

**Audit**  
Replace BigQuery with another durable store as long as you keep the audit schema.

---

## License

This project is licensed under the MIT License - see the LICENSE file for details.