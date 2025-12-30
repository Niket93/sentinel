from __future__ import annotations
import json
import threading
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from google.cloud import bigquery
from ..config.settings import Settings
from ..shared.vertex_client import init_vertex
from ..rag.vertex_search_answer import answer_query
from ..ingest.producer import publish_clips_from_video


class ChatIn(BaseModel):
    question: str
    limit: int = 200
    use_case: str | None = None
    session_id: str | None = None


class StreamReq(BaseModel):
    use_case: str

def _home_html(
    linkedin_url: str,
    github_url: str,
    youtube_embed_url: str,
) -> str:

    return f"""
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <title>Sentinel • Universal Video Intelligence</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
      :root {{ color-scheme: dark; }}
      html, body {{ height: 100%; }}

      .t-12 {{ font-size: 12px; line-height: 18px; }}
      .t-14 {{ font-size: 14px; line-height: 20px; }}
      .t-16 {{ font-size: 16px; line-height: 24px; }}
      .t-18 {{ font-size: 18px; line-height: 26px; }}
      .t-22 {{ font-size: 22px; line-height: 30px; }}
      .t-26 {{ font-size: 26px; line-height: 34px; }}

      @keyframes fadeIn {{
        from {{ opacity: 0; transform: translateY(-6px); }}
        to {{ opacity: 1; transform: translateY(0); }}
      }}
    </style>
  </head>

  <body class="min-h-screen bg-zinc-950 text-zinc-50 antialiased">
    <!-- Background (matches /ui) -->
    <div class="fixed inset-0 -z-10">
      <div class="absolute inset-0 bg-[radial-gradient(900px_circle_at_20%_10%,rgba(16,185,129,0.14),transparent_45%),radial-gradient(900px_circle_at_80%_0%,rgba(99,102,241,0.10),transparent_40%),radial-gradient(900px_circle_at_50%_90%,rgba(244,63,94,0.08),transparent_45%)]"></div>
      <div class="absolute inset-0 opacity-20 bg-[linear-gradient(to_right,rgba(255,255,255,0.04)_1px,transparent_1px),linear-gradient(to_bottom,rgba(255,255,255,0.04)_1px,transparent_1px)] bg-[size:72px_72px]"></div>
    </div>

    <div class="w-full max-w-none px-4 sm:px-6 lg:px-10 2xl:px-12 py-6">

      <!-- Header (same density/typography as /ui) -->
      <header class="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div class="leading-tight min-w-0">
          <div class="t-26 font-semibold tracking-tight truncate">Sentinel</div>
          <div class="t-16 text-zinc-300">
            Agentic Video Intelligence Platform with <span class="text-emerald-300">Confluent</span> + <span class="text-violet-300">Vertex AI</span>
          </div>
          <div class="t-16 text-zinc-400 mt-2 max-w-5xl">
            Vision → Decision → Action: Transform any video feed into governed event streams that drive real-time, explainable actions across manufacturing, healthcare, retail, logistics, and beyond, with an audit-grade evidence trail you can replay.
          </div>
        </div>

        <div class="flex flex-wrap items-center gap-3 shrink-0">
          <a href="/ui"
            class="rounded-2xl bg-emerald-500/15 px-5 py-3 t-16 font-medium text-emerald-200 ring-1 ring-emerald-500/25 hover:ring-emerald-500/60">
            Open Demo UI
          </a>

          <a href="{github_url}" target="_blank" rel="noreferrer noopener"
            class="rounded-2xl bg-zinc-900/60 px-5 py-3 t-16 font-medium text-zinc-200 ring-1 ring-zinc-800 hover:ring-zinc-600">
            GitHub
          </a>

          <a href="{linkedin_url}" target="_blank" rel="noreferrer noopener"
            class="rounded-2xl bg-zinc-900/60 px-5 py-3 t-16 font-medium text-zinc-200 ring-1 ring-zinc-800 hover:ring-zinc-600">
            LinkedIn
          </a>
        </div>
      </header>

      <!-- Hero banner panel -->
      <section class="mt-5 rounded-3xl border border-zinc-800/70 bg-zinc-900/35 backdrop-blur overflow-hidden shadow-[0_0_0_1px_rgba(255,255,255,0.03)]">
        <div class="px-6 py-5">
          <div class="text-center">
            <div class="t-22 font-semibold text-zinc-100">
              Powered by <span class="text-emerald-300">Confluent Cloud Streaming</span> + <span class="text-violet-300">Vertex AI Intelligence</span>
            </div>
            <div class="t-16 text-zinc-400 mt-2">
              Sentinel turns video into governed event streams and explainable actions - with replayable evidence.
            </div>
          </div>
        </div>
      </section>

      <!-- YouTube -->
      <section class="mt-5 rounded-3xl border border-zinc-800/70 bg-zinc-900/30 backdrop-blur overflow-hidden shadow-[0_0_0_1px_rgba(255,255,255,0.03)]">
        <div class="px-6 py-5 border-b border-zinc-800/70">
          <div class="t-18 font-semibold text-zinc-100">🎬 Demo Video</div>
        </div>
        <div class="bg-black">
          <div class="w-full aspect-video">
            <iframe
              class="w-full h-full"
              src="{youtube_embed_url}"
              title="Sentinel Demo Video"
              frameborder="0"
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
              allowfullscreen>
            </iframe>
          </div>
        </div>
      </section>

      <!-- Full content: no accordions, no shortening -->
      <main class="mt-6 space-y-6">

        <!-- Title block -->
        <section class="rounded-3xl border border-zinc-800/70 bg-zinc-900/30 backdrop-blur overflow-hidden shadow-[0_0_0_1px_rgba(255,255,255,0.03)]">
          <div class="px-6 py-6">
            <div class="t-26 font-semibold tracking-tight text-zinc-100">Sentinel</div>
            <div class="t-18 text-zinc-200 mt-1">Universal Video Intelligence Platform with Confluent + Vertex AI</div>
            <div class="t-16 text-zinc-300 mt-3">
              Vision → Decision → Action: Transform any video feed into governed event streams that drive real-time, explainable actions across manufacturing, healthcare, retail, logistics, and beyond, with an audit-grade evidence trail you can replay.
            </div>
          </div>
        </section>

        <!-- Inspiration -->
        <section class="rounded-3xl border border-zinc-800/70 bg-zinc-900/30 backdrop-blur overflow-hidden shadow-[0_0_0_1px_rgba(255,255,255,0.03)]">
          <div class="px-6 py-6 space-y-4">
            <div>
              <div class="t-22 font-semibold text-zinc-100">💡 Inspiration - The Problem We're Solving</div>
              <div class="t-16 text-zinc-200 mt-3">
                Organizations across every industry deploy thousands of cameras - factories, warehouses, hospitals, retail stores, construction sites, farms, energy infrastructure, and smart cities. Yet most footage remains reactive, reviewed only after incidents occur, when the damage is already done.
              </div>
              <div class="t-16 text-zinc-200 mt-4">The cost of waiting is universal and staggering:</div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
              <div class="rounded-2xl bg-zinc-950/40 ring-1 ring-zinc-800/70 px-4 py-4">
                <div class="t-12 text-zinc-500">Downtime</div>
                <div class="t-16 text-zinc-100 font-semibold">$36K–$2.3M per hour</div>
                <div class="t-14 text-zinc-400 mt-1">Siemens 2024</div>
              </div>
              <div class="rounded-2xl bg-zinc-950/40 ring-1 ring-zinc-800/70 px-4 py-4">
                <div class="t-12 text-zinc-500">Major outages</div>
                <div class="t-16 text-zinc-100 font-semibold">54% &gt; $100K; 20% &gt; $1M</div>
                <div class="t-14 text-zinc-400 mt-1">Uptime Institute 2024</div>
              </div>
              <div class="rounded-2xl bg-zinc-950/40 ring-1 ring-zinc-800/70 px-4 py-4">
                <div class="t-12 text-zinc-500">Safety incidents</div>
                <div class="t-16 text-zinc-100 font-semibold">$176.5B annual injury costs</div>
                <div class="t-14 text-zinc-400 mt-1">NSC 2023 • ~$43K per injury</div>
              </div>
              <div class="rounded-2xl bg-zinc-950/40 ring-1 ring-zinc-800/70 px-4 py-4">
                <div class="t-12 text-zinc-500">Operational impact</div>
                <div class="t-16 text-zinc-100 font-semibold">90%+ &gt; $300K/hour</div>
                <div class="t-14 text-zinc-400 mt-1">ITIC 2024</div>
              </div>
            </div>

            <div class="t-16 text-zinc-200">
              The opportunity: Video represents ~80% of global data by 2025 (175 zettabytes projected) - IDC/Seagate 2018, yet organizations across all industries struggle to operationalize multimodal AI in real-time with governance, cost control, and auditability.
            </div>

            <div class="t-16 text-zinc-200">
              Sentinel closes that gap, not for one industry, but for every industry where visual monitoring matters.
            </div>
          </div>
        </section>

        <!-- What it does -->
        <section class="rounded-3xl border border-zinc-800/70 bg-zinc-900/30 backdrop-blur overflow-hidden shadow-[0_0_0_1px_rgba(255,255,255,0.03)]">
          <div class="px-6 py-6 space-y-6">
            <div>
              <div class="t-22 font-semibold text-zinc-100">🎯 What It Does</div>
              <div class="t-16 text-zinc-200 mt-3">
                Sentinel is a agentic video intelligence platform that continuously converts raw video into governed operational intelligence across any industry:
              </div>
            </div>

            <div class="rounded-2xl bg-zinc-950/40 ring-1 ring-zinc-800/70 p-5">
              <div class="t-16 text-zinc-400">End-to-End Pipeline</div>
              <pre class="mt-3 t-16 text-zinc-200 whitespace-pre-wrap font-mono">
📹 Video Feed
    ↓ (Motion Detection + Sampling)
🔍 Observe (Gemini Multimodal Analysis)
    ↓ (Structured JSON Observations)
🧠 Think (Reasoning + Domain Knowledge Grounding via Vertex AI Search)
    ↓ (Explainable Decisions with Citations)
⚡ Act (Automated Alerts / Actions / webhooks)
    ↓ (Deduped, Cooldown-Protected)
📊 Audit + Real-Time KPIs (BigQuery + Flink SQL)
              </pre>
            </div>

            <div>
              <div class="t-18 font-semibold text-zinc-100">Cross-Industry Applications</div>
              <div class="t-16 text-zinc-200 mt-2">The same architecture solves different problems across verticals:</div>

              <div class="mt-4 overflow-x-auto rounded-2xl ring-1 ring-zinc-800/70">
                <table class="min-w-[1100px] w-full bg-zinc-950/40">
                  <thead class="text-left">
                    <tr class="border-b border-zinc-800/70">
                      <th class="px-4 py-3 t-16 text-zinc-300">Industry</th>
                      <th class="px-4 py-3 t-16 text-zinc-300">Use Case</th>
                      <th class="px-4 py-3 t-16 text-zinc-300">Detection</th>
                      <th class="px-4 py-3 t-16 text-zinc-300">Action</th>
                      <th class="px-4 py-3 t-16 text-zinc-300">Impact</th>
                    </tr>
                  </thead>
                  <tbody class="t-16 text-zinc-200">
                    <tr class="border-b border-zinc-800/50">
                      <td class="px-4 py-3">Manufacturing</td>
                      <td class="px-4 py-3">Equipment anomaly detection</td>
                      <td class="px-4 py-3">Abnormal vibrations, leaks, smoke</td>
                      <td class="px-4 py-3">Predictive maintenance alert</td>
                      <td class="px-4 py-3">Prevent $2M/hour downtime</td>
                    </tr>
                    <tr class="border-b border-zinc-800/50">
                      <td class="px-4 py-3">Healthcare</td>
                      <td class="px-4 py-3">Patient safety monitoring</td>
                      <td class="px-4 py-3">Fall detection, mobility issues</td>
                      <td class="px-4 py-3">Immediate staff alert</td>
                      <td class="px-4 py-3">Reduce adverse events</td>
                    </tr>
                    <tr class="border-b border-zinc-800/50">
                      <td class="px-4 py-3">Retail</td>
                      <td class="px-4 py-3">Queue &amp; service optimization</td>
                      <td class="px-4 py-3">Long wait times, checkout bottlenecks</td>
                      <td class="px-4 py-3">Staff reallocation</td>
                      <td class="px-4 py-3">Improve customer experience</td>
                    </tr>
                    <tr class="border-b border-zinc-800/50">
                      <td class="px-4 py-3">Logistics</td>
                      <td class="px-4 py-3">Loading dock safety</td>
                      <td class="px-4 py-3">Forklift near-misses, improper stacking</td>
                      <td class="px-4 py-3">Stop operations, supervisor alert</td>
                      <td class="px-4 py-3">Prevent $43K injuries</td>
                    </tr>
                    <tr class="border-b border-zinc-800/50">
                      <td class="px-4 py-3">Agriculture</td>
                      <td class="px-4 py-3">Crop &amp; livestock monitoring</td>
                      <td class="px-4 py-3">Irrigation issues, animal distress</td>
                      <td class="px-4 py-3">Automated intervention</td>
                      <td class="px-4 py-3">Prevent yield loss</td>
                    </tr>
                    <tr class="border-b border-zinc-800/50">
                      <td class="px-4 py-3">Energy</td>
                      <td class="px-4 py-3">Infrastructure monitoring</td>
                      <td class="px-4 py-3">Pipeline leaks, equipment corrosion</td>
                      <td class="px-4 py-3">Emergency shutdown</td>
                      <td class="px-4 py-3">Prevent environmental disasters</td>
                    </tr>
                    <tr class="border-b border-zinc-800/50">
                      <td class="px-4 py-3">Construction</td>
                      <td class="px-4 py-3">Site safety compliance</td>
                      <td class="px-4 py-3">Missing PPE, unsafe scaffolding</td>
                      <td class="px-4 py-3">Stop work order</td>
                      <td class="px-4 py-3">Reduce OSHA violations</td>
                    </tr>
                    <tr>
                      <td class="px-4 py-3">Smart Cities</td>
                      <td class="px-4 py-3">Traffic &amp; crowd management</td>
                      <td class="px-4 py-3">Congestion, crowd density</td>
                      <td class="px-4 py-3">Dynamic signal control</td>
                      <td class="px-4 py-3">Optimize urban flow</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            <div class="space-y-3">
              <div class="t-18 font-semibold text-zinc-100">Demo Implementations (Included)</div>
              <div class="t-16 text-zinc-200">We've built two use-case examples to showcase the platform's flexibility:</div>

              <div class="rounded-2xl bg-zinc-950/40 ring-1 ring-zinc-800/70 p-5 space-y-2">
                <div class="t-16 font-semibold text-zinc-100">1. Security &amp; Safety Monitoring</div>
                <ul class="list-disc ml-5 t-16 text-zinc-200 space-y-1">
                  <li>Detects violations in real-time (PPE missing, unsafe behavior, spills)</li>
                  <li>Evaluates severity with confidence scores</li>
                  <li>Executes stop-line commands or alerts with full evidence chain</li>
                  <li>Shows trace-linked video clips and reasoning</li>
                </ul>
              </div>

              <div class="rounded-2xl bg-zinc-950/40 ring-1 ring-zinc-800/70 p-5 space-y-2">
                <div class="t-16 font-semibold text-zinc-100">2. Assembly SOP Compliance</div>
                <ul class="list-disc ml-5 t-16 text-zinc-200 space-y-1">
                  <li>Sessionizes station workflows into discrete work units</li>
                  <li>Validates completion against SOP requirements</li>
                  <li>Identifies missing steps with citations to procedure documents</li>
                  <li>Provides operator-ready corrective instructions</li>
                </ul>
              </div>

              <div class="t-16 text-zinc-200">
                The key insight: Both demos use the exact same streaming architecture, only the prompts, knowledge bases, and action handlers change. This proves the platform's universality.
              </div>
            </div>
          </div>
        </section>

        <!-- Architecture -->
        <section class="rounded-3xl border border-zinc-800/70 bg-zinc-900/30 backdrop-blur overflow-hidden shadow-[0_0_0_1px_rgba(255,255,255,0.03)]">
          <div class="px-6 py-6 space-y-6">
            <div>
              <div class="t-22 font-semibold text-zinc-100">🏗️ How We Built It - Architecture</div>
              <div class="t-16 text-zinc-400 mt-1">Three-layer design: Streaming (Confluent), Intelligence (Vertex AI), and Audit (BigQuery + Flink)</div>
            </div>

            <div class="space-y-4">
              <div class="t-18 font-semibold text-zinc-100">Three-Plane Design</div>

              <div class="rounded-2xl bg-zinc-950/40 ring-1 ring-zinc-800/70 p-5 space-y-2">
                <div class="t-16 font-semibold text-zinc-100">1. Streaming Plane (Confluent Cloud)</div>
                <ul class="list-disc ml-5 t-16 text-zinc-200 space-y-1">
                  <li>Multi-stage event choreography through Kafka topics</li>
                  <li>Schema-governed contracts via Schema Registry (JSON Schema)</li>
                  <li>Independent scaling per agent via consumer groups</li>
                  <li>Replay-first architecture for forensics and iteration</li>
                </ul>
              </div>

              <div class="rounded-2xl bg-zinc-950/40 ring-1 ring-zinc-800/70 p-5 space-y-2">
                <div class="t-16 font-semibold text-zinc-100">2. Intelligence Plane (Vertex AI)</div>
                <ul class="list-disc ml-5 t-16 text-zinc-200 space-y-1">
                  <li>Gemini multimodal: Zero-shot video understanding</li>
                  <li>Gemini reasoning: Severity assessment and action planning</li>
                  <li>Vertex AI Search: RAG-grounded SOP lookups with citations</li>
                  <li>Embeddings API: Semantic retrieval for knowledge base</li>
                </ul>
              </div>

              <div class="rounded-2xl bg-zinc-950/40 ring-1 ring-zinc-800/70 p-5 space-y-2">
                <div class="t-16 font-semibold text-zinc-100">3. Audit &amp; Analytics Plane</div>
                <ul class="list-disc ml-5 t-16 text-zinc-200 space-y-1">
                  <li>BigQuery: Immutable audit logs with correlated trace IDs</li>
                  <li>Flink SQL: Real-time KPIs computed directly over Kafka streams</li>
                  <li>Cloud Storage: Clip archival for evidence replay</li>
                </ul>
              </div>
            </div>

            <div class="space-y-3">
              <div class="t-18 font-semibold text-zinc-100">Multi-Agent Streaming Architecture</div>
              <pre class="rounded-2xl bg-zinc-950/40 ring-1 ring-zinc-800/70 p-5 t-16 text-zinc-200 whitespace-pre-wrap font-mono">
video.clips → [Observer Agent]
    ↓
video.observations → [Sessionizer Agent]
    ↓
station.sessions → [Thinker Agent + SOP Grounding]
    ↓
sop.decisions → [Action Agent + Dedup]
    ↓
workflow.actions → [Audit Sink]
    ↓
audit.events (BigQuery)
              </pre>

              <div class="t-16 text-zinc-200">
                Key Innovation: Each agent is an independent service consuming/producing from Kafka topics. This enables:
              </div>
              <ul class="list-disc ml-5 t-16 text-zinc-200 space-y-1">
                <li>Horizontal Scaling where it matters (e.g., 10x Observer instances for 100 cameras)</li>
                <li>Independent Evolution (swap models/prompts without downstream rewrites)</li>
                <li>Fault Isolation (one agent failure doesn't crash the pipeline)</li>
                <li>Clean Contracts (Schema Registry ensures safe evolution)</li>
              </ul>
            </div>
          </div>
        </section>

        <!-- Technical Implementation -->
        <section class="rounded-3xl border border-zinc-800/70 bg-zinc-900/30 backdrop-blur overflow-hidden shadow-[0_0_0_1px_rgba(255,255,255,0.03)]">
          <div class="px-6 py-6 space-y-6">
            <div class="t-22 font-semibold text-zinc-100">🔧 Technical Implementation - Why This Works at Scale</div>

            <div class="space-y-3">
              <div class="t-18 font-semibold text-zinc-100">1️⃣ Cost-Controlled Multimodal Inference</div>
              <div class="t-16 text-zinc-200">Video AI inference can bankrupt a deployment. We built multiple cost gates:</div>
              <div class="rounded-2xl bg-zinc-950/40 ring-1 ring-zinc-800/70 p-5 space-y-2">
                <div class="t-16 font-semibold text-zinc-100">Motion Detection Prefilter</div>
                <ul class="list-disc ml-5 t-16 text-zinc-200 space-y-1">
                  <li>Pixel-change detection + background subtraction</li>
                  <li>Filters 80-90% of "quiet" clips before inference</li>
                  <li>Turns "impossible economics" into viable deployment</li>
                </ul>

                <div class="t-16 font-semibold text-zinc-100 mt-4">Smart Sampling &amp; Segmentation</div>
                <ul class="list-disc ml-5 t-16 text-zinc-200 space-y-1">
                  <li>Configurable clip length and FPS</li>
                  <li>Prevents redundant processing of static scenes</li>
                </ul>

                <div class="t-16 font-semibold text-zinc-100 mt-4">Streaming Deduplication</div>
                <ul class="list-disc ml-5 t-16 text-zinc-200 space-y-1">
                  <li>Cooldown windows prevent alert storms</li>
                  <li>Action-level dedup across topics</li>
                </ul>

                <div class="t-16 text-zinc-200 mt-4">Cost Model:</div>
                <pre class="t-16 text-zinc-200 whitespace-pre-wrap font-mono">
API Calls/day ≈ (N_cameras × 1440 minutes/day) / (T_clip × (1 - filter_rate))

Example: 10 cameras, 30-sec clips, 80% filtered
= (10 × 1440) / (0.5 × 0.2) = 144,000 calls/day
With 80% prefilter → 28,800 calls/day
                </pre>
              </div>
            </div>

            <div class="space-y-3">
              <div class="t-18 font-semibold text-zinc-100">2️⃣ Explainability &amp; Governance as First-Class Output</div>
              <div class="t-16 text-zinc-200">Every decision includes:</div>
              <ul class="list-disc ml-5 t-16 text-zinc-200 space-y-1">
                <li>Evidence: Exact clip timestamp range</li>
                <li>Rationale: Human-readable explanation</li>
                <li>Confidence scores: Per-signal uncertainty</li>
                <li>Citations: When grounded in SOP/policy (via Vertex AI Search)</li>
                <li>Trace ID: Correlates across all pipeline stages</li>
              </ul>
              <div class="t-16 text-zinc-200">
                Operators trust the system because they can see why it decided, not just what it decided.
              </div>
            </div>

            <div class="space-y-3">
              <div class="t-18 font-semibold text-zinc-100">3️⃣ Real-Time KPIs Without Extra Infrastructure</div>
              <div class="t-16 text-zinc-200">
                The same Kafka streams that drive actions also power analytics:
              </div>
              <div class="t-16 text-zinc-200 font-semibold">Flink SQL Queries (examples included):</div>
              <ul class="list-disc ml-5 t-16 text-zinc-200 space-y-1">
                <li>Rule hit rates by violation type</li>
                <li>Stop-line frequency trends</li>
                <li>Confidence distribution analysis</li>
                <li>P95 end-to-end latency tracking</li>
                <li>Alert storm detection windows</li>
              </ul>
              <div class="t-16 text-zinc-200">
                Value: No separate analytics pipeline, KPIs are computed in-stream.
              </div>
            </div>

            <div class="space-y-3">
              <div class="t-18 font-semibold text-zinc-100">4️⃣ Production-Grade Replay &amp; Forensics</div>
              <div class="t-16 text-zinc-200">Kafka's retention + correlated trace_id enables:</div>
              <ul class="list-disc ml-5 t-16 text-zinc-200 space-y-1">
                <li>Incident investigation: Replay exactly what the system saw</li>
                <li>Model tuning: Re-run decisions with updated prompts</li>
                <li>Compliance audits: Full evidence chain for regulatory review</li>
                <li>A/B testing: Compare model outputs on same event history</li>
              </ul>
            </div>
          </div>
        </section>

        <!-- Confluent Usage -->
        <section class="rounded-3xl border border-zinc-800/70 bg-zinc-900/30 backdrop-blur overflow-hidden shadow-[0_0_0_1px_rgba(255,255,255,0.03)]">
          <div class="px-6 py-6 space-y-6">
            <div>
              <div class="t-22 font-semibold text-zinc-100">🚀 Confluent Cloud Usage</div>
              <div class="t-16 text-zinc-200 mt-2">This project is Confluent-native by design.</div>
              <div class="t-16 text-zinc-200 mt-2">What We Used &amp; Why It Matters</div>
            </div>

            <div class="overflow-x-auto rounded-2xl ring-1 ring-zinc-800/70">
              <table class="min-w-[1000px] w-full bg-zinc-950/40">
                <thead class="text-left">
                  <tr class="border-b border-zinc-800/70">
                    <th class="px-4 py-3 t-16 text-zinc-300">Confluent Feature</th>
                    <th class="px-4 py-3 t-16 text-zinc-300">How We Use It</th>
                    <th class="px-4 py-3 t-16 text-zinc-300">Business Value</th>
                  </tr>
                </thead>
                <tbody class="t-16 text-zinc-200">
                  <tr class="border-b border-zinc-800/50">
                    <td class="px-4 py-3">Kafka Topics</td>
                    <td class="px-4 py-3">Multi-agent backbone with topic-per-stage pattern</td>
                    <td class="px-4 py-3">Decoupling, fault isolation, clean evolution</td>
                  </tr>
                  <tr class="border-b border-zinc-800/50">
                    <td class="px-4 py-3">Consumer Groups</td>
                    <td class="px-4 py-3">Scale Observer instances (10x) independently from Thinker (2x)</td>
                    <td class="px-4 py-3">Cost-efficient horizontal scaling</td>
                  </tr>
                  <tr class="border-b border-zinc-800/50">
                    <td class="px-4 py-3">Schema Registry</td>
                    <td class="px-4 py-3">JSON Schema contracts generated from Pydantic models</td>
                    <td class="px-4 py-3">Safe prompt/model evolution, fewer breakages</td>
                  </tr>
                  <tr class="border-b border-zinc-800/50">
                    <td class="px-4 py-3">Replayability</td>
                    <td class="px-4 py-3">Replay by trace_id for forensics and iteration</td>
                    <td class="px-4 py-3">Incident investigation, compliance, A/B testing</td>
                  </tr>
                  <tr>
                    <td class="px-4 py-3">Flink SQL</td>
                    <td class="px-4 py-3">Real-time KPIs + stream-side cost filters</td>
                    <td class="px-4 py-3">Operational visibility, upstream cost gates</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div class="rounded-2xl bg-zinc-950/40 ring-1 ring-zinc-800/70 p-5">
              <div class="t-16 text-zinc-200 font-semibold">Critical Design Decision:</div>
              <div class="t-16 text-zinc-200 mt-2">
                We chose event choreography over orchestration. Each agent is autonomous, consuming from upstream topics and producing to downstream topics. This creates natural backpressure, enables independent scaling, and makes the system resilient to partial failures.
              </div>
            </div>
          </div>
        </section>

        <!-- Vertex Usage -->
        <section class="rounded-3xl border border-zinc-800/70 bg-zinc-900/30 backdrop-blur overflow-hidden shadow-[0_0_0_1px_rgba(255,255,255,0.03)]">
          <div class="px-6 py-6 space-y-6">
            <div>
              <div class="t-22 font-semibold text-zinc-100">🧠 Vertex AI Usage</div>
              <div class="t-16 text-zinc-200 mt-2">What We Used &amp; Why It Matters</div>
            </div>

            <div class="overflow-x-auto rounded-2xl ring-1 ring-zinc-800/70">
              <table class="min-w-[1000px] w-full bg-zinc-950/40">
                <thead class="text-left">
                  <tr class="border-b border-zinc-800/70">
                    <th class="px-4 py-3 t-16 text-zinc-300">Vertex AI Feature</th>
                    <th class="px-4 py-3 t-16 text-zinc-300">How We Use It</th>
                    <th class="px-4 py-3 t-16 text-zinc-300">Business Value</th>
                  </tr>
                </thead>
                <tbody class="t-16 text-zinc-200">
                  <tr class="border-b border-zinc-800/50">
                    <td class="px-4 py-3">Gemini Multimodal</td>
                    <td class="px-4 py-3">Observer agent reads video clips, emits structured signals</td>
                    <td class="px-4 py-3">Zero-shot understanding, no CV pipeline required</td>
                  </tr>
                  <tr class="border-b border-zinc-800/50">
                    <td class="px-4 py-3">Gemini Reasoning</td>
                    <td class="px-4 py-3">Thinker + Doer convert signals → severity → actions</td>
                    <td class="px-4 py-3">Operational judgment with consistent JSON</td>
                  </tr>
                  <tr class="border-b border-zinc-800/50">
                    <td class="px-4 py-3">Vertex AI Search</td>
                    <td class="px-4 py-3">RAG grounding for SOP compliance checks</td>
                    <td class="px-4 py-3">Citation-backed decisions, reduced hallucinations</td>
                  </tr>
                  <tr>
                    <td class="px-4 py-3">Embeddings API</td>
                    <td class="px-4 py-3">Semantic SOP chunk retrieval</td>
                    <td class="px-4 py-3">Scalable knowledge grounding</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div class="rounded-2xl bg-zinc-950/40 ring-1 ring-zinc-800/70 p-5">
              <div class="t-16 text-zinc-200 font-semibold">Critical Design Decision:</div>
              <div class="t-16 text-zinc-200 mt-2">
                We use structured output prompting (strict JSON schemas) to ensure Gemini outputs are Kafka-ready events, not unstructured text. This makes the pipeline reliable and testable.
              </div>
            </div>
          </div>
        </section>

        <!-- Challenges -->
        <section class="rounded-3xl border border-zinc-800/70 bg-zinc-900/30 backdrop-blur overflow-hidden shadow-[0_0_0_1px_rgba(255,255,255,0.03)]">
          <div class="px-6 py-6 space-y-6">
            <div class="t-22 font-semibold text-zinc-100">💪 Challenges We Overcame</div>

            <div class="rounded-2xl bg-zinc-950/40 ring-1 ring-zinc-800/70 p-5 space-y-2">
              <div class="t-18 font-semibold text-zinc-100">1. Latency vs. Cost Trade-off</div>
              <div class="t-16 text-zinc-200">
                Problem: High-resolution video at 30 FPS = 1,800 frames/minute. At $0.05/frame, that's $90/minute = $129,600/day per camera. Impossible.
              </div>
              <div class="t-16 text-zinc-200 font-semibold mt-2">Solution:</div>
              <ul class="list-disc ml-5 t-16 text-zinc-200 space-y-1">
                <li>Motion detection cuts inference by 80-90%</li>
                <li>Segment into 15-30 second clips</li>
                <li>Sample at 1-2 FPS for analysis</li>
              </ul>
              <div class="t-16 text-zinc-200 mt-2">
                Result: ~$10-20/day per camera (economically viable)
              </div>
            </div>

            <div class="rounded-2xl bg-zinc-950/40 ring-1 ring-zinc-800/70 p-5 space-y-2">
              <div class="t-18 font-semibold text-zinc-100">2. Multi-Agent Coordination Without Brittle Orchestration</div>
              <div class="t-16 text-zinc-200">
                Problem: Centralized orchestrators become single points of failure and bottlenecks.
              </div>
              <div class="t-16 text-zinc-200 font-semibold mt-2">Solution:</div>
              <ul class="list-disc ml-5 t-16 text-zinc-200 space-y-1">
                <li>Event choreography via Kafka topics</li>
                <li>Schema Registry enforces contracts between agents</li>
                <li>Each agent scales independently</li>
                <li>Natural backpressure prevents cascade failures</li>
              </ul>
            </div>

            <div class="rounded-2xl bg-zinc-950/40 ring-1 ring-zinc-800/70 p-5 space-y-2">
              <div class="t-18 font-semibold text-zinc-100">3. Trust &amp; Explainability for Compliance Use Cases</div>
              <div class="t-16 text-zinc-200">
                Problem: "AI said stop the line" isn't acceptable in regulated environments.
              </div>
              <div class="t-16 text-zinc-200 font-semibold mt-2">Solution:</div>
              <ul class="list-disc ml-5 t-16 text-zinc-200 space-y-1">
                <li>Vertex AI Search grounds decisions in actual SOP documents</li>
                <li>Every decision includes citations to specific procedure sections</li>
                <li>Full audit trail with correlated trace IDs</li>
                <li>Operators can replay incidents to understand "why"</li>
              </ul>
            </div>
          </div>
        </section>

        <!-- Potential Value Applications -->
        <section class="rounded-3xl border border-zinc-800/70 bg-zinc-900/30 backdrop-blur overflow-hidden shadow-[0_0_0_1px_rgba(255,255,255,0.03)]">
          <div class="px-6 py-6 space-y-4">
            <div class="t-22 font-semibold text-zinc-100">Potential Value Applications</div>

            <div class="t-18 font-semibold text-zinc-100">Manufacturing &amp; Industrial:</div>
            <ul class="list-disc ml-5 t-16 text-zinc-200 space-y-1">
              <li>Downtime prevention: Early detection of equipment issues addresses documented $36K–$2.3M/hour costs</li>
              <li>Predictive maintenance: Faster awareness of visual anomalies (smoke, leaks, vibrations)</li>
              <li>Quality control: Real-time visual inspection of assembly processes</li>
            </ul>

            <div class="t-18 font-semibold text-zinc-100 mt-3">Safety &amp; Compliance:</div>
            <ul class="list-disc ml-5 t-16 text-zinc-200 space-y-1">
              <li>Injury prevention: With $43K average cost per workplace injury, early hazard detection has measurable value</li>
              <li>Compliance monitoring: Automated verification of safety protocols</li>
              <li>Regulatory support: Documented audit trails for incident investigation</li>
            </ul>

            <div class="t-18 font-semibold text-zinc-100 mt-3">Operational Efficiency:</div>
            <ul class="list-disc ml-5 t-16 text-zinc-200 space-y-1">
              <li>Process monitoring: Visual verification of workflow completion</li>
              <li>Audit support: Reduced time spent on manual video review</li>
              <li>Quality feedback: Faster identification of process deviations</li>
            </ul>

            <div class="t-18 font-semibold text-zinc-100 mt-3">Healthcare &amp; Patient Safety:</div>
            <ul class="list-disc ml-5 t-16 text-zinc-200 space-y-1">
              <li>Fall detection: Addressing documented hospital fall costs</li>
              <li>Early intervention: Real-time alerts for patient mobility issues</li>
              <li>Staff support: Automated monitoring between routine checks</li>
            </ul>

            <div class="t-18 font-semibold text-zinc-100 mt-3">Retail &amp; Customer Experience:</div>
            <ul class="list-disc ml-5 t-16 text-zinc-200 space-y-1">
              <li>Queue optimization: Visual monitoring of checkout wait times</li>
              <li>Loss prevention: Automated detection of unusual activity</li>
              <li>Service quality: Real-time awareness of customer service needs</li>
            </ul>
          </div>
        </section>

        <!-- What's Next -->
        <section class="rounded-3xl border border-zinc-800/70 bg-zinc-900/30 backdrop-blur overflow-hidden shadow-[0_0_0_1px_rgba(255,255,255,0.03)]">
          <div class="px-6 py-6 space-y-4">
            <div class="t-22 font-semibold text-zinc-100">🎯 What's Next</div>
            <div class="t-16 text-zinc-200">We built Sentinel as a architectural foundation. Natural next steps for us are:</div>

            <div class="t-18 font-semibold text-zinc-100">Near-Term (1-3 Months)</div>
            <ul class="list-disc ml-5 t-16 text-zinc-200 space-y-1">
              <li>Flink-first cost gating: Move motion/signal thresholds into stream processing (materialized views)</li>
              <li>Connector ecosystem: Slack, PagerDuty, ServiceNow, Jira (action handlers already modular)</li>
              <li>Policy pack system: Plug-in SOP libraries per station/site/customer with version control</li>
            </ul>

            <div class="t-18 font-semibold text-zinc-100 mt-3">Medium-Term (3-6 Months)</div>
            <ul class="list-disc ml-5 t-16 text-zinc-200 space-y-1">
              <li>Vector Search hardening: Upgrade SOP retrieval to Vertex Vector Search for lower latency</li>
              <li>Multi-modal expansion: Add audio analysis (machine sounds, alarms) to video</li>
              <li>Edge deployment: Run Observer agents closer to cameras for ultra-low latency</li>
            </ul>

            <div class="t-18 font-semibold text-zinc-100 mt-3">Long-Term (6-12 Months)</div>
            <ul class="list-disc ml-5 t-16 text-zinc-200 space-y-1">
              <li>Federated learning: Train station-specific anomaly models on local data</li>
              <li>Predictive maintenance: Correlate visual signals with equipment telemetry</li>
              <li>Cross-site benchmarking: Compare SOP adherence across facilities</li>
            </ul>
          </div>
        </section>

        <!-- Built With -->
        <section class="rounded-3xl border border-zinc-800/70 bg-zinc-900/30 backdrop-blur overflow-hidden shadow-[0_0_0_1px_rgba(255,255,255,0.03)]">
          <div class="px-6 py-6 space-y-4">
            <div class="t-22 font-semibold text-zinc-100">🛠️ Built With</div>

            <div class="t-18 font-semibold text-zinc-100">Confluent Cloud (Core Platform)</div>
            <ul class="list-disc ml-5 t-16 text-zinc-200 space-y-1">
              <li>Kafka Topics: Multi-agent event backbone</li>
              <li>Consumer Groups: Independent scaling per agent type</li>
              <li>Schema Registry: Governed JSON Schema contracts</li>
              <li>Flink SQL: Real-time KPIs and stream analytics</li>
              <li>Replayability: Forensic replay by trace ID</li>
            </ul>

            <div class="t-18 font-semibold text-zinc-100 mt-3">Google Cloud Vertex AI (Intelligence Layer)</div>
            <ul class="list-disc ml-5 t-16 text-zinc-200 space-y-1">
              <li>Gemini 2.5 Flash (Multimodal): Video understanding</li>
              <li>Gemini 2.5 Pro (Reasoning): Decision synthesis</li>
              <li>Vertex AI Search: RAG-grounded SOP retrieval</li>
              <li>Embeddings API: Semantic knowledge base</li>
            </ul>

            <div class="t-18 font-semibold text-zinc-100 mt-3">Google Cloud Infrastructure</div>
            <ul class="list-disc ml-5 t-16 text-zinc-200 space-y-1">
              <li>Cloud Storage: Clip archival</li>
              <li>BigQuery: Audit log warehouse</li>
              <li>Cloud Run: FastAPI control plane (demo UI)</li>
              <li>Secret Manager: API key governance</li>
            </ul>
          </div>
        </section>

        <!-- Try It Yourself -->
        <section class="rounded-3xl border border-zinc-800/70 bg-zinc-900/30 backdrop-blur overflow-hidden shadow-[0_0_0_1px_rgba(255,255,255,0.03)]">
          <div class="px-6 py-6 space-y-3">
            <div class="t-22 font-semibold text-zinc-100">🎬 Try It Yourself</div>
            <div class="t-16 text-zinc-200">Demo Video: <span class="text-zinc-300 font-mono">{youtube_embed_url}</span></div>
            <div class="t-16 text-zinc-200">Code Repository: <span class="text-zinc-300 font-mono">{github_url}</span></div>
          </div>
        </section>

        <!-- Team -->
        <section class="rounded-3xl border border-zinc-800/70 bg-zinc-900/30 backdrop-blur overflow-hidden shadow-[0_0_0_1px_rgba(255,255,255,0.03)]">
          <div class="px-6 py-6 space-y-2">
            <div class="t-22 font-semibold text-zinc-100">👥 Team</div>
            <div class="t-16 text-zinc-200">Niket Shah - <a class="text-emerald-300 hover:text-emerald-200 underline decoration-emerald-500/30 hover:decoration-emerald-300/60" href="{linkedin_url}" target="_blank" rel="noreferrer noopener">LinkedIn</a></div>
          </div>
        </section>

        <!-- Why This Matters -->
        <section class="rounded-3xl border border-zinc-800/70 bg-zinc-900/30 backdrop-blur overflow-hidden shadow-[0_0_0_1px_rgba(255,255,255,0.03)]">
          <div class="px-6 py-6 space-y-4">
            <div class="t-22 font-semibold text-zinc-100">🏆 Why This Matters</div>

            <div class="t-16 text-zinc-200">
              Real-time video intelligence is hard to operationalize. Most approaches either sacrifice cost-efficiency, explainability, or governance. Sentinel demonstrates that you don't have to choose.
            </div>

            <div class="t-16 text-zinc-200">
              ✅ Solves Documented Problems<br/>
              Addresses $36K–$2.3M/hour downtime costs and $43K workplace injury costs with a practical, economically viable approach.
            </div>

            <div class="t-16 text-zinc-200">
              ✅ Production-First Design<br/>
              Cost controls aren't an afterthought, they're built into the architecture. Motion detection, sampling strategies, and deduplication make multimodal AI inference economically feasible at scale.
            </div>

            <div class="t-16 text-zinc-200">
              ✅ Deep Sponsor Integration<br/>
              This isn't a shallow integration. We use Confluent's event choreography for multi-agent coordination, Schema Registry for safe evolution, and Flink SQL for real-time KPIs. Vertex AI powers zero-shot video understanding, grounded reasoning with RAG, and citation-backed decisions.
            </div>

            <div class="t-16 text-zinc-200">
              ✅ Explainability as Output<br/>
              Every decision includes evidence, rationale, confidence scores, and citations. This isn't a black box, it's a system operators can trust and auditors can verify.
            </div>

            <div class="t-16 text-zinc-200">
              ✅ Demonstrates Architectural Thinking<br/>
              Two different use cases running on the same infrastructure proves the approach is adaptable. The streaming backbone doesn't change, only prompts and knowledge bases do.
            </div>

            <div class="t-16 text-zinc-200">
              Sentinel shows how Confluent and Vertex AI can work together to make video intelligence operationally viable: governed, explainable, cost-controlled, and production-ready.
            </div>
          </div>
        </section>

      </main>

      <!-- Footer -->
      <footer class="mt-10 pb-8 t-14 text-zinc-500 flex flex-col md:flex-row md:items-center md:justify-between gap-3">
        <div>© Sentinel • Vision-to-Action</div>
        <div class="flex gap-3">
          <a class="hover:text-zinc-300 underline decoration-zinc-700 hover:decoration-zinc-400" href="/ui">Open Demo UI</a>
          <a class="hover:text-zinc-300 underline decoration-zinc-700 hover:decoration-zinc-400" href="{github_url}" target="_blank" rel="noreferrer noopener">GitHub</a>
          <a class="hover:text-zinc-300 underline decoration-zinc-700 hover:decoration-zinc-400" href="{linkedin_url}" target="_blank" rel="noreferrer noopener">LinkedIn</a>
        </div>
      </footer>
    </div>
  </body>
</html>
"""

def _ui_html() -> str:
    return r"""
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <title>Sentinel • Vision-to-Action</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
      :root { color-scheme: dark; }
      html, body { height: 100%; }

      .t-12 { font-size: 12px; line-height: 18px; }
      .t-14 { font-size: 14px; line-height: 20px; }
      .t-16 { font-size: 16px; line-height: 24px; }
      .t-18 { font-size: 18px; line-height: 26px; }
      .t-22 { font-size: 22px; line-height: 30px; }
      .t-26 { font-size: 26px; line-height: 34px; }

      summary::-webkit-details-marker { display: none; }

      @keyframes fadeIn {
        from { opacity: 0; transform: translateY(-6px); }
        to { opacity: 1; transform: translateY(0); }
      }
    </style>
  </head>

  <body class="min-h-screen bg-zinc-950 text-zinc-50 antialiased">
    <div class="fixed inset-0 -z-10">
      <div class="absolute inset-0 bg-[radial-gradient(900px_circle_at_20%_10%,rgba(16,185,129,0.14),transparent_45%),radial-gradient(900px_circle_at_80%_0%,rgba(99,102,241,0.10),transparent_40%),radial-gradient(900px_circle_at_50%_90%,rgba(244,63,94,0.08),transparent_45%)]"></div>
      <div class="absolute inset-0 opacity-20 bg-[linear-gradient(to_right,rgba(255,255,255,0.04)_1px,transparent_1px),linear-gradient(to_bottom,rgba(255,255,255,0.04)_1px,transparent_1px)] bg-[size:72px_72px]"></div>
    </div>

    <div class="w-full max-w-none px-4 sm:px-6 lg:px-10 2xl:px-12 py-6">

      <header class="flex items-center justify-between gap-4">
        <div class="leading-tight min-w-0">
          <div class="t-26 font-semibold tracking-tight truncate">Sentinel</div>
          <div class="t-16 text-zinc-300 truncate">
            Operational Video Intelligence - from Detection to Response.
          </div>
        </div>

        <div class="flex items-center gap-3 shrink-0">
          <div class="flex rounded-2xl bg-zinc-900/60 ring-1 ring-zinc-800 overflow-hidden">
            <button id="ucSecurity" class="px-4 py-2 t-16 font-medium text-zinc-200 hover:bg-zinc-800/60">Security</button>
            <button id="ucAssembly" class="px-4 py-2 t-16 font-medium text-zinc-200 hover:bg-zinc-800/60">Assembly</button>
          </div>

          <div class="inline-flex items-center gap-2 rounded-2xl bg-zinc-900/60 ring-1 ring-zinc-800 px-3 py-2">
            <span id="statusDot" class="h-2 w-2 rounded-full bg-rose-400"></span>
            <span id="statusText" class="t-16 text-zinc-200">Stopped</span>
          </div>
        </div>
      </header>

      <section class="mt-5 rounded-3xl border border-zinc-800/70 bg-zinc-900/35 backdrop-blur overflow-hidden shadow-[0_0_0_1px_rgba(255,255,255,0.03)]">
        <div class="px-6 py-5">
          <div class="text-center">
            <div class="t-22 font-semibold text-zinc-100">
              Powered by <span class="text-emerald-300">Confluent Cloud Streaming</span> + <span class="text-violet-300">Vertex AI Intelligence</span>
            </div>
            <div class="t-14 text-zinc-400 mt-2">
              Agentic video intelligence - continuously observing, escalating, acting, and answering “why” from a trusted audit trail.
            </div>
          </div>

          <div class="mt-5 grid grid-cols-1 md:grid-cols-4 gap-4 items-center text-center">
            <div class="rounded-2xl bg-zinc-950/40 ring-1 ring-zinc-800/70 px-4 py-3">
              <div class="t-12 text-zinc-500">Streaming</div>
              <div class="t-16 text-zinc-100 font-semibold" id="metaStreaming">Confluent Cloud</div>
            </div>
            <div class="rounded-2xl bg-zinc-950/40 ring-1 ring-zinc-800/70 px-4 py-3">
              <div class="t-12 text-zinc-500">AI</div>
              <div class="t-16 text-zinc-100 font-semibold" id="metaAI">Vertex AI (-)</div>
            </div>
            <div class="rounded-2xl bg-zinc-950/40 ring-1 ring-zinc-800/70 px-4 py-3">
              <div class="t-12 text-zinc-500">Schema</div>
              <div class="t-16 text-zinc-100 font-semibold" id="metaSchema">Schema Registry (-)</div>
            </div>
            <div class="rounded-2xl bg-zinc-950/40 ring-1 ring-zinc-800/70 px-4 py-3">
              <div class="t-12 text-zinc-500">Kafka</div>
              <div class="t-16 text-zinc-100 font-semibold" id="metaKafka">-</div>
            </div>
          </div>
        </div>
      </section>

      <section class="mt-5 rounded-3xl border border-zinc-800/70 bg-zinc-900/30 backdrop-blur overflow-hidden shadow-[0_0_0_1px_rgba(255,255,255,0.03)]">
        <div class="px-6 py-5">
          <div class="flex items-center justify-between gap-4">
            <div>
              <div class="t-18 font-semibold text-zinc-100">Operational KPIs</div>
              <div class="t-14 text-zinc-400">Computed from the audit log (last 24 hours)</div>
            </div>
            <div class="flex items-center gap-2 shrink-0">
              <button id="btnRefreshKpi" class="rounded-2xl bg-zinc-950/40 px-4 py-2 t-16 ring-1 ring-zinc-800 hover:ring-zinc-600">
                Refresh
              </button>
            </div>
          </div>

          <div class="mt-4 grid grid-cols-1 md:grid-cols-4 gap-4">
            <div class="rounded-2xl bg-zinc-950/40 ring-1 ring-zinc-800/70 px-4 py-3">
              <div class="t-12 text-zinc-500">Critical Incidents</div>
              <div class="t-22 text-rose-200 font-semibold" id="kpiStop24h">-</div>
              <div class="t-14 text-zinc-400 mt-1" id="kpiStopLast">Last: -</div>
            </div>

            <div class="rounded-2xl bg-zinc-950/40 ring-1 ring-zinc-800/70 px-4 py-3">
              <div class="t-12 text-zinc-500">Alerts</div>
              <div class="t-22 text-amber-200 font-semibold" id="kpiAlert24h">-</div>
              <div class="t-14 text-zinc-400 mt-1">Last 24h</div>
            </div>

            <div class="rounded-2xl bg-zinc-950/40 ring-1 ring-zinc-800/70 px-4 py-3">
              <div class="t-12 text-zinc-500">Decisions</div>
              <div class="t-22 text-violet-200 font-semibold" id="kpiDec24h">-</div>
              <div class="t-14 text-zinc-400 mt-1">Last 24h</div>
            </div>

            <div class="rounded-2xl bg-zinc-950/40 ring-1 ring-zinc-800/70 px-4 py-3">
              <div class="t-12 text-zinc-500">Observations</div>
              <div class="t-22 text-sky-200 font-semibold" id="kpiObs24h">-</div>
              <div class="t-14 text-zinc-400 mt-1">Last 24h</div>
            </div>
          </div>

          <div class="mt-4 grid grid-cols-1 lg:grid-cols-3 gap-4">
            <div class="rounded-2xl bg-zinc-950/40 ring-1 ring-zinc-800/70 px-4 py-3">
              <div class="t-14 font-semibold text-zinc-100">By Use-Case (Last 24h)</div>
              <div class="mt-3 space-y-2 t-16 text-zinc-200">
                <div>Security - Stop: <span class="text-rose-200 font-semibold" id="kpiStopSec">-</span> • Alerts: <span class="text-amber-200 font-semibold" id="kpiAlertSec">-</span></div>
                <div>Assembly - Stop: <span class="text-rose-200 font-semibold" id="kpiStopAsm">-</span> • Alerts: <span class="text-amber-200 font-semibold" id="kpiAlertAsm">-</span></div>
              </div>
            </div>

            <div class="rounded-2xl bg-zinc-950/40 ring-1 ring-zinc-800/70 px-4 py-3">
              <div class="t-14 font-semibold text-zinc-100">Priority Distribution (Last 24h)</div>
              <div class="mt-3 space-y-2 t-16 text-zinc-200">
                <div>P1: <span class="font-semibold text-rose-200" id="kpiP1">-</span></div>
                <div>P2: <span class="font-semibold text-amber-200" id="kpiP2">-</span></div>
                <div>P3: <span class="font-semibold text-zinc-200" id="kpiP3">-</span></div>
              </div>
            </div>

            <div class="rounded-2xl bg-zinc-950/40 ring-1 ring-zinc-800/70 px-4 py-3">
              <div class="t-14 font-semibold text-zinc-100">Top Rules (Decisions Last 24h)</div>
              <div class="mt-3 space-y-2 t-16 text-zinc-200" id="kpiRules">
                <div class="t-16 text-zinc-400">-</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <div class="mt-6 flex items-center justify-between gap-4">
        <div class="min-w-0">
          <div id="cameraTitle" class="t-18 font-semibold text-zinc-100 truncate">Security Feed</div>
          <div id="subtitle" class="t-16 text-zinc-400 mt-1 truncate">
            Detect restricted-zone / walkway violations and open panel/guard while machine is operating.
          </div>
        </div>

        <div class="flex items-center gap-2 shrink-0">
          <button id="btnReplay" class="rounded-2xl bg-zinc-950/40 px-4 py-2 t-16 ring-1 ring-zinc-800 hover:ring-zinc-600">
            Replay
          </button>
          <button id="btnClear" class="rounded-2xl bg-zinc-950/40 px-4 py-2 t-16 ring-1 ring-zinc-800 hover:ring-zinc-600">
            Clear
          </button>
        </div>
      </div>

      <main class="mt-6 space-y-6">
        <section class="rounded-3xl border border-zinc-800/70 bg-zinc-900/30 backdrop-blur overflow-hidden shadow-[0_0_0_1px_rgba(255,255,255,0.03)]">
          <div class="px-6 py-5 flex items-center justify-between border-b border-zinc-800/70">
            <div class="min-w-0">
              <div class="t-14 text-zinc-400">Video</div>
              <div class="t-18 font-semibold text-zinc-100 mt-0.5 truncate" id="videoTitle">Live camera</div>
            </div>
            <div class="t-14 text-zinc-400 hidden sm:block">Clip → Observe → Decide → Act → Audit</div>
          </div>

          <div class="bg-black">
            <video id="video" class="w-full aspect-video" controls autoplay muted playsinline>
              <source id="videoSrc" src="/video?use_case=security" type="video/mp4" />
            </video>
          </div>

          <div class="px-6 py-5 border-t border-zinc-800/70 flex justify-center">
            <div class="flex gap-3">
              <button id="btnStartStream" class="rounded-2xl bg-emerald-500/15 px-5 py-3 t-16 font-medium text-emerald-200 ring-1 ring-emerald-500/25 hover:ring-emerald-500/60 hidden">
                ▶ Start Streaming
              </button>
              <button id="btnStopStream" class="rounded-2xl bg-rose-500/15 px-5 py-3 t-16 font-medium text-rose-200 ring-1 ring-rose-500/25 hover:ring-rose-500/60 hidden">
                ■ Stop Streaming
              </button>
            </div>
          </div>
        </section>

        <section class="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div class="rounded-3xl border border-zinc-800/70 bg-zinc-900/30 backdrop-blur overflow-hidden shadow-[0_0_0_1px_rgba(255,255,255,0.03)] flex flex-col min-h-0">
            <div class="px-6 py-5 border-b border-zinc-800/70">
              <div class="t-14 text-zinc-400">Event stream (Confluent Cloud)</div>
              <div class="t-18 font-semibold text-zinc-100 mt-0.5">Observations • Decisions • Actions</div>
            </div>
            <div id="feed" class="p-5 space-y-4 h-[560px] overflow-auto"></div>
          </div>

          <div class="rounded-3xl border border-zinc-800/70 bg-zinc-900/30 backdrop-blur overflow-hidden shadow-[0_0_0_1px_rgba(255,255,255,0.03)] flex flex-col min-h-0">
            <div class="px-6 py-5 border-b border-zinc-800/70">
              <div class="t-14 text-zinc-400">Decision detail (Gemini Reasoning)</div>
              <div class="t-18 font-semibold text-zinc-100 mt-0.5">Latest Decision Breakdown</div>
            </div>
            <div class="p-5 h-[560px] overflow-auto" id="thinkingPanel">
              <div class="rounded-2xl bg-zinc-950/40 ring-1 ring-zinc-800/70 p-5">
                <div class="t-16 text-zinc-200">No decision yet.</div>
                <div class="t-14 text-zinc-500 mt-2">Once a decision arrives, details appear here.</div>
              </div>
            </div>
          </div>

          <div class="rounded-3xl border border-zinc-800/70 bg-zinc-900/30 backdrop-blur overflow-hidden shadow-[0_0_0_1px_rgba(255,255,255,0.03)] flex flex-col min-h-0">
            <div class="px-6 py-5 border-b border-zinc-800/70">
              <div class="t-14 text-zinc-400">Audit Chat (Vertex Grounded)</div>
              <div class="t-18 font-semibold text-zinc-100 mt-0.5">Ask Questions About Events...</div>
            </div>

            <div id="chatLog" class="p-5 space-y-4 h-[440px] overflow-auto"></div>

            <form id="chatForm" class="p-5 border-t border-zinc-800/70 flex gap-2">
              <input
                id="chatInput"
                class="flex-1 rounded-2xl bg-zinc-950/60 px-4 py-3 t-16 ring-1 ring-zinc-800 focus:outline-none focus:ring-emerald-500/55"
                placeholder="Ask: Why did we stop the line? Which clip shows it?"
              />
              <button
                class="rounded-2xl bg-emerald-500/15 px-5 py-3 t-16 font-medium text-emerald-200 ring-1 ring-emerald-500/25 hover:ring-emerald-500/60"
                type="submit"
              >
                Send
              </button>
            </form>

            <div class="px-6 pb-5 t-14 text-zinc-500">
              Answers are grounded in the audit log.
            </div>
          </div>
        </section>
      </main>
    </div>

    <div id="toastContainer" class="fixed top-4 right-4 z-50 space-y-3 w-[420px] max-w-[92vw]"></div>

    <script>
      let useCase = "security";
      let seen = new Set();
      let traceToGcs = new Map();
      let latestDecision = null;

      const feedEl = document.getElementById("feed");
      const thinkingPanel = document.getElementById("thinkingPanel");

      const btnClear = document.getElementById("btnClear");
      const btnReplay = document.getElementById("btnReplay");
      const btnRefreshKpi = document.getElementById("btnRefreshKpi");

      const btnStartStream = document.getElementById("btnStartStream");
      const btnStopStream = document.getElementById("btnStopStream");

      const videoEl = document.getElementById("video");
      const videoSrc = document.getElementById("videoSrc");

      const ucSecurity = document.getElementById("ucSecurity");
      const ucAssembly = document.getElementById("ucAssembly");

      const subtitle = document.getElementById("subtitle");
      const cameraTitle = document.getElementById("cameraTitle");
      const videoTitle = document.getElementById("videoTitle");

      const chatLog = document.getElementById("chatLog");
      const chatForm = document.getElementById("chatForm");
      const chatInput = document.getElementById("chatInput");

      const statusDot = document.getElementById("statusDot");
      const statusText = document.getElementById("statusText");

      function escapeHtml(s) {
        return (s || "").replace(/[&<>"']/g, (c) => ({
          "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"
        }[c]));
      }

      function fmtIsoShort(iso) {
        if (!iso) return "-";
        try {
          const d = new Date(iso);
          return d.toISOString().replace("T"," ").slice(0,16);
        } catch (_) {
          return iso;
        }
      }

      function toast(html, ttlMs = 6500) {
        const container = document.getElementById("toastContainer");
        if (!container) return;

        const el = document.createElement("div");
        el.className =
          "rounded-2xl bg-zinc-950/90 ring-1 ring-rose-500/40 shadow-lg p-4 backdrop-blur " +
          "animate-[fadeIn_.15s_ease-out]";

        el.innerHTML = html;

        // Dismiss on click
        el.addEventListener("click", () => {
          try { el.remove(); } catch (_) {}
        });

        container.prepend(el);

        // Auto-dismiss
        setTimeout(() => {
          try { el.remove(); } catch (_) {}
        }, ttlMs);
      }

      function isStopLineDecision(payload) {
        const actions = Array.isArray(payload?.recommended_actions) ? payload.recommended_actions : [];
        if (!actions.length) return false;
        const t = String(actions[0]?.type || "").toLowerCase();
        return t === "stop_line";
      }

      function isStopLineAction(payload) {
        const t = String(payload?.action?.type || "").toLowerCase();
        return t === "stop_line";
      }

      function pill(label, cls) {
        return `<span class="inline-flex items-center rounded-full px-2.5 py-1 t-12 ring-1 ${cls}">${escapeHtml(label)}</span>`;
      }

      function gcsToConsoleUrl(gsUri) {
        if (!gsUri || typeof gsUri !== "string") return "";
        if (!gsUri.startsWith("gs://")) return "";
        const rest = gsUri.slice(5);
        const slash = rest.indexOf("/");
        const bucket = slash >= 0 ? rest.slice(0, slash) : rest;
        const objectPath = slash >= 0 ? rest.slice(slash + 1) : "";
        if (!bucket) return "";
        const enc = encodeURIComponent(objectPath);
        return `https://console.cloud.google.com/storage/browser/_details/${encodeURIComponent(bucket)}/${enc}`;
      }

      function clipLinksHtml(traceId) {
        const gs = traceToGcs.get(traceId) || "";
        if (!gs) return "";
        const consoleUrl = gcsToConsoleUrl(gs);
        const gsEsc = escapeHtml(gs);

        const a = consoleUrl
          ? `<a class="text-emerald-300 hover:text-emerald-200 underline decoration-emerald-500/30 hover:decoration-emerald-300/60" href="${consoleUrl}" target="_blank" rel="noreferrer">Open clip</a>`
          : "";

        return `
          <div class="mt-3 t-14 text-zinc-400">
            ${a ? a + `<span class="mx-2 text-zinc-700">•</span>` : ""}
            <span class="font-mono">${gsEsc}</span>
          </div>
        `;
      }

      function maybeToastCritical(ev) {
        if (!ev || !ev.payload) return;
        const kind = ev.kind || "";
        const payload = ev.payload || {};
        const traceId = ev.trace_id || "";
        const ts = ev.ts || "";

        let actionMsg = "";
        let priority = "";

        if (kind === "decision" && isStopLineDecision(payload)) {
          const a0 = (payload.recommended_actions || [])[0] || {};
          actionMsg = String(a0.message || "Stop line recommended.");
          priority = String(a0.priority || "");
        } else if (kind === "action" && isStopLineAction(payload)) {
          const a = payload.action || {};
          actionMsg = String(a.message || "Stop line executed.");
          priority = String(a.priority || "");
        } else {
          return;
        }

        const clipHtml = clipLinksHtml(traceId);
        const badge = `<span class="inline-flex items-center rounded-full px-2.5 py-1 t-12 ring-1 bg-rose-500/15 text-rose-200 ring-rose-500/25">CRITICAL • STOP LINE</span>`;

        toast(`
          <div class="flex items-start justify-between gap-3">
            <div>
              <div class="t-16 font-semibold text-zinc-100">Critical incident detected</div>
              <div class="t-14 text-zinc-400 mt-1">${escapeHtml(ts)}</div>
            </div>
            <div class="shrink-0">${badge}</div>
          </div>

          <div class="mt-3 t-16 text-zinc-100 whitespace-pre-wrap">${escapeHtml(actionMsg)}</div>

          ${clipHtml ? `<div class="mt-3">${clipHtml}</div>` : ""}

          <div class="mt-3 t-14 text-zinc-500">
            Click to dismiss
          </div>
        `);
      }

      async function loadMeta() {
        try {
          const r = await fetch("/meta");
          const m = await r.json();

          document.getElementById("metaKafka").textContent = m.kafka_bootstrap || "-";
          const sr = m.schema_registry || "-";
          document.getElementById("metaSchema").textContent = "Schema Registry (" + sr + ")";

          const obsModel = m.vertex?.observer_model || "gemini";
          const thinkModel = m.vertex?.thinker_model || "gemini";
          document.getElementById("metaAI").textContent = "Vertex AI (" + thinkModel + " / " + obsModel + ")";

          document.getElementById("metaStreaming").textContent = "Confluent Cloud";
        } catch (e) {}
      }

      async function loadKpi() {
        try {
          const r = await fetch("/kpi");
          const k = await r.json();

          document.getElementById("kpiStop24h").textContent = String(k.stop_line_24h ?? "-");
          document.getElementById("kpiAlert24h").textContent = String(k.alert_24h ?? "-");
          document.getElementById("kpiDec24h").textContent = String(k.decisions_24h ?? "-");
          document.getElementById("kpiObs24h").textContent = String(k.observations_24h ?? "-");

          document.getElementById("kpiStopLast").textContent = "Last: " + fmtIsoShort(k.last_stop_line_ts);

          document.getElementById("kpiStopSec").textContent = String(k.by_use_case?.security?.stop_line ?? "0");
          document.getElementById("kpiAlertSec").textContent = String(k.by_use_case?.security?.alert ?? "0");
          document.getElementById("kpiStopAsm").textContent = String(k.by_use_case?.assembly?.stop_line ?? "0");
          document.getElementById("kpiAlertAsm").textContent = String(k.by_use_case?.assembly?.alert ?? "0");

          document.getElementById("kpiP1").textContent = String(k.priorities?.P1 ?? "0");
          document.getElementById("kpiP2").textContent = String(k.priorities?.P2 ?? "0");
          document.getElementById("kpiP3").textContent = String(k.priorities?.P3 ?? "0");

          const rulesEl = document.getElementById("kpiRules");
          rulesEl.innerHTML = "";
          const rules = Array.isArray(k.top_rules) ? k.top_rules : [];
          if (!rules.length) {
            rulesEl.innerHTML = `<div class="t-16 text-zinc-400">-</div>`;
          } else {
            rules.slice(0,5).forEach(r => {
              const row = document.createElement("div");
              row.className = "t-16 text-zinc-200";
              row.innerHTML = `<span class="text-zinc-500">•</span> ${escapeHtml(r.rule_id)} <span class="text-zinc-500">(${r.count})</span>`;
              rulesEl.appendChild(row);
            });
          }
        } catch (e) {}
      }

      async function refreshStreamStatus() {
        try {
          const r = await fetch("/stream/status");
          const s = await r.json();
          const running = !!s.running?.[useCase];

          if (running) {
            statusDot.className = "h-2 w-2 rounded-full bg-emerald-400";
            statusText.textContent = "Streaming";

            // ✅ Toggle visible buttons
            btnStartStream.classList.add("hidden");
            btnStopStream.classList.remove("hidden");

            btnStartStream.disabled = false;
            btnStopStream.disabled = false;
          } else {
            statusDot.className = "h-2 w-2 rounded-full bg-rose-400";
            statusText.textContent = "Stopped";

            // ✅ Toggle visible buttons
            btnStopStream.classList.add("hidden");
            btnStartStream.classList.remove("hidden");

            btnStartStream.disabled = false;
            btnStopStream.disabled = false;
          }
        } catch (e) {}
      }

      btnStartStream.addEventListener("click", async () => {
        btnStartStream.disabled = true;
        await fetch("/stream/start", {
          method: "POST",
          headers: {"Content-Type":"application/json"},
          body: JSON.stringify({use_case: useCase})
        });
        refreshStreamStatus();
      });

      btnStopStream.addEventListener("click", async () => {
        btnStopStream.disabled = true;
        await fetch("/stream/stop", {
          method: "POST",
          headers: {"Content-Type":"application/json"},
          body: JSON.stringify({use_case: useCase})
        });
        refreshStreamStatus();
      });

      function decisionSubtype(payload) {
        const actions = Array.isArray(payload?.recommended_actions) ? payload.recommended_actions : [];
        const t = actions.length ? String(actions[0]?.type || "").toLowerCase() : "";
        return t;
      }

      function rightPill(kind, payload) {
        if (kind === "observation") return pill("OBSERVATION", "bg-sky-500/10 text-sky-200 ring-sky-500/20");

        if (kind === "decision") {
          const sub = decisionSubtype(payload);
          if (sub === "stop_line") return pill("DECISION • STOP LINE", "bg-rose-500/10 text-rose-200 ring-rose-500/20");
          if (sub === "alert") return pill("DECISION • ALERT", "bg-amber-500/10 text-amber-200 ring-amber-500/20");
          return pill("DECISION", "bg-violet-500/10 text-violet-200 ring-violet-500/20");
        }

        if (kind === "action") {
          const t = String(payload?.action?.type || "").toLowerCase();
          if (t === "stop_line") return pill("STOP LINE", "bg-rose-500/10 text-rose-200 ring-rose-500/20");
          if (t === "alert") return pill("ALERT", "bg-amber-500/10 text-amber-200 ring-amber-500/20");
          return pill("ACTION", "bg-violet-500/10 text-violet-200 ring-violet-500/20");
        }

        return "";
      }

      function relevantToUseCase(payload) {
        const uc = payload?.use_case;
        if (!uc) return false;
        return String(uc).toLowerCase() === useCase;
      }

      function describeEvent(kind, payload) {
        if (kind === "observation") return String(payload?.summary || "").trim() || "Observation recorded.";
        if (kind === "decision") {
          const actions = Array.isArray(payload?.recommended_actions) ? payload.recommended_actions : [];
          const msg = actions.length ? String(actions[0]?.message || "").trim() : "";
          if (msg) return msg;
          const a = payload?.assessment || {};
          const rule = a.rule_id ? String(a.rule_id) : "";
          const risk = a.risk ? String(a.risk) : "";
          if (rule && risk) return `${rule} - ${risk}`;
          return rule || risk || "Decision generated.";
        }
        if (kind === "action") return String(payload?.action?.message || "").trim() || "Action executed.";
        return "";
      }

      function learnClipUri(ev) {
        const kind = ev.kind || "";
        const traceId = ev.trace_id || "";
        const payload = ev.payload || {};
        if (!traceId) return;

        if (kind === "clip") {
          const gs = payload?.gcs_uri;
          if (typeof gs === "string" && gs.startsWith("gs://")) traceToGcs.set(traceId, gs);
        }
        if (kind === "observation") {
          const gs = payload?.clip_gcs_uri;
          if (typeof gs === "string" && gs.startsWith("gs://")) traceToGcs.set(traceId, gs);
        }
        if (kind === "session") {
          const gs = payload?.session_video_gcs_uri;
          if (typeof gs === "string" && gs.startsWith("gs://")) traceToGcs.set(traceId, gs);
        }
      }

      function kvRow(k, v) {
        return `
          <div class="flex items-start justify-between gap-4">
            <div class="t-14 text-zinc-400">${escapeHtml(k)}</div>
            <div class="t-14 text-zinc-200 text-right break-words">${escapeHtml(String(v ?? ""))}</div>
          </div>
        `;
      }

      function renderDecisionPanel(decEv) {
        if (!decEv) {
          thinkingPanel.innerHTML = `
            <div class="rounded-2xl bg-zinc-950/40 ring-1 ring-zinc-800/70 p-5">
              <div class="t-16 text-zinc-200">No Decision Yet.</div>
              <div class="t-14 text-zinc-500 mt-2">Once a decision arrives, details appear here.</div>
            </div>
          `;
          return;
        }

        const payload = decEv.payload || {};
        const traceId = decEv.trace_id || "";
        const assessment = payload.assessment || {};
        const rationale = payload.rationale || {};
        const evidence = payload.evidence || {};
        const actions = Array.isArray(payload.recommended_actions) ? payload.recommended_actions : [];
        const action0 = actions.length ? actions[0] : {};
        const citations = Array.isArray(rationale?.citations) ? rationale.citations : [];

        const actionType = String(action0?.type || "");
        const actionMsg = String(action0?.message || "");
        const priority = String(action0?.priority || "");

        const sev = String(assessment?.severity || "");
        const conf = assessment?.confidence;
        const rule = String(assessment?.rule_id || "");
        const risk = String(assessment?.risk || "");
        const reason = String(evidence?.reason || "");
        const clipRange = Array.isArray(evidence?.clip_range) ? evidence.clip_range : null;

        const clipLink = clipLinksHtml(traceId);

        thinkingPanel.innerHTML = `
          <div class="rounded-2xl bg-zinc-950/45 ring-1 ring-zinc-800/70 p-5">
            <div class="flex items-start justify-between gap-3">
              <div>
                <div class="t-18 font-semibold text-zinc-100">Decision</div>
                <div class="t-14 text-zinc-500 mt-1">${escapeHtml(decEv.ts || "")} • trace ${escapeHtml((traceId || "").slice(0,8))}</div>
              </div>
              <div class="shrink-0">${rightPill("decision", payload)}</div>
            </div>

            <div class="mt-4 space-y-4">
              <div class="rounded-xl bg-zinc-950/35 ring-1 ring-zinc-800/70 p-4">
                <div class="t-14 text-zinc-400">Recommended action</div>
                <div class="mt-1 t-18 font-semibold text-zinc-100">${escapeHtml(actionType || "unknown")} ${priority ? `• ${escapeHtml(priority)}` : ""}</div>
                <div class="mt-1 t-16 text-zinc-200">${escapeHtml(actionMsg || "-")}</div>
              </div>

              <div class="rounded-xl bg-zinc-950/35 ring-1 ring-zinc-800/70 p-4 space-y-2">
                <div class="t-14 text-zinc-400">Assessment</div>
                ${sev ? kvRow("severity", sev) : ""}
                ${conf !== undefined ? kvRow("confidence", conf) : ""}
                ${rule ? kvRow("rule_id", rule) : ""}
                ${risk ? kvRow("risk", risk) : ""}
              </div>

              <div class="rounded-xl bg-zinc-950/35 ring-1 ring-zinc-800/70 p-4">
                <div class="t-14 text-zinc-400">Rationale</div>
                <div class="mt-1 t-16 text-zinc-200">${escapeHtml(String(rationale?.short || "-"))}</div>
              </div>

              ${citations.length ? `
              <div class="rounded-xl bg-zinc-950/35 ring-1 ring-zinc-800/70 p-4">
                <div class="t-14 text-zinc-400">Citations</div>
                <div class="mt-2 space-y-2">
                  ${citations.map(c => `
                    <div class="t-14 text-zinc-200">
                      <span class="text-zinc-500">•</span>
                      ${escapeHtml(String(c.step_id || c.chunk_id || "source"))}
                    </div>
                  `).join("")}
                </div>
              </div>` : ""}

              <div class="rounded-xl bg-zinc-950/35 ring-1 ring-zinc-800/70 p-4 space-y-2">
                <div class="t-14 text-zinc-400">Evidence</div>
                ${kvRow("reason", reason || "-")}
                ${clipRange ? kvRow("clip_range", `${clipRange[0]} → ${clipRange[1]}`) : kvRow("clip_range", "-")}
                ${clipLink ? `<div class="mt-2">${clipLink}</div>` : ""}
              </div>
            </div>
          </div>
        `;
      }

      function renderCard(ev) {
        const ts = ev.ts || "";
        const kind = ev.kind || "";
        const traceShort = (ev.trace_id || "").slice(0, 8);
        const traceId = ev.trace_id || "";
        const payload = ev.payload || {};

        if (!relevantToUseCase(payload)) return "";
        if (kind !== "observation" && kind !== "decision" && kind !== "action") return "";

        const desc = describeEvent(kind, payload);
        const topRight = rightPill(kind, payload);
        const link = clipLinksHtml(traceId);
        const clickHint = kind === "decision" ? `data-click="decision"` : "";

        return `
          <div class="rounded-2xl bg-zinc-950/45 ring-1 ring-zinc-800/70 p-5 hover:ring-zinc-600/80 transition cursor-${kind === "decision" ? "pointer" : "default"}"
               ${clickHint}
               data-audit-id="${escapeHtml(ev.audit_id || "")}">
            <div class="flex items-start justify-between gap-3">
              <div class="min-w-0">
                <div class="t-18 font-semibold text-zinc-100">${escapeHtml(kind.charAt(0).toUpperCase() + kind.slice(1))}</div>
                <div class="t-14 text-zinc-500 mt-1">${escapeHtml(ts)} • ${escapeHtml(kind)} • trace ${escapeHtml(traceShort)}</div>
              </div>
              <div class="shrink-0">${topRight}</div>
            </div>

            <div class="mt-3 t-16 text-zinc-200 whitespace-pre-wrap">${escapeHtml(desc)}</div>
            ${link}
          </div>
        `;
      }

      async function poll() {
        try {
          const r = await fetch("/recent?limit=260");
          const items = await r.json();

          items.forEach(learnClipUri);

          items.reverse().forEach(ev => {
            const auditId = ev.audit_id || "";
            if (!auditId) return;
            if (seen.has(auditId)) return;

            const html = renderCard(ev);
            if (html) {
              feedEl.insertAdjacentHTML("beforeend", html);
              feedEl.scrollTop = feedEl.scrollHeight;

              if (ev.kind === "decision" && relevantToUseCase(ev.payload || {})) {
                latestDecision = ev;
                renderDecisionPanel(latestDecision);
              }

              if (relevantToUseCase(ev.payload || {})) {
                maybeToastCritical(ev);
              }
            }
            seen.add(auditId);
          });

        } catch (e) {}
      }

      // Click-to-pin decision
      feedEl.addEventListener("click", (e) => {
        const card = e.target.closest('[data-click="decision"]');
        if (!card) return;
        const auditId = card.getAttribute("data-audit-id");
        (async () => {
          try {
            const r = await fetch("/recent?limit=260");
            const items = await r.json();
            const found = items.find(x => x.audit_id === auditId);
            if (found && found.kind === "decision") {
              latestDecision = found;
              renderDecisionPanel(latestDecision);
            }
          } catch (_) {}
        })();
      });

      btnClear.addEventListener("click", () => {
        feedEl.innerHTML = "";
        seen = new Set();
        traceToGcs = new Map();
        latestDecision = null;
        renderDecisionPanel(null);
        chatLog.innerHTML = "";
      });

      btnReplay.addEventListener("click", () => {
        videoEl.currentTime = 0;
        videoEl.play();
      });

      btnRefreshKpi.addEventListener("click", loadKpi);

      function setUseCase(next) {
        useCase = next;

        const active = "bg-zinc-50/10 text-zinc-50";
        const inactive = "text-zinc-200";

        if (useCase === "security") {
          ucSecurity.className = "px-4 py-2 t-16 font-medium " + active;
          ucAssembly.className = "px-4 py-2 t-16 font-medium hover:bg-zinc-800/60 " + inactive;
          subtitle.textContent = "Real-time Video Monitoring for Safety and Security.";
          cameraTitle.textContent = "Security Feed";
          videoTitle.textContent = "Industrial Floor • Security Camera Feed";
        } else {
          ucAssembly.className = "px-4 py-2 t-16 font-medium " + active;
          ucSecurity.className = "px-4 py-2 t-16 font-medium hover:bg-zinc-800/60 " + inactive;
          subtitle.textContent = "Session-based Video Monitoring for SOP and Process Compliance.";
          cameraTitle.textContent = "Assembly • Station S4";
          videoTitle.textContent = "Assembly Line • Station Camera Feed";
        }

        videoSrc.src = "/video?use_case=" + encodeURIComponent(useCase);
        videoEl.load();
        videoEl.play();

        feedEl.innerHTML = "";
        seen = new Set();
        traceToGcs = new Map();
        latestDecision = null;
        renderDecisionPanel(null);

        refreshStreamStatus();
        poll();
      }

      ucSecurity.addEventListener("click", () => setUseCase("security"));
      ucAssembly.addEventListener("click", () => setUseCase("assembly"));

      function addChat(role, text) {
        const align = role === "user" ? "justify-end" : "justify-start";
        const bubble = role === "user"
          ? "bg-emerald-500/15 ring-1 ring-emerald-500/25 text-emerald-50"
          : "bg-zinc-950/45 ring-1 ring-zinc-800/70 text-zinc-50";
        const label = role === "user" ? "You" : "Sentinel";

        const html = `
          <div class="flex ${align}">
            <div class="max-w-[92%] rounded-3xl px-4 py-3 ${bubble}">
              <div class="t-12 text-zinc-400 mb-1">${label}</div>
              <div class="t-16 whitespace-pre-wrap">${escapeHtml(text)}</div>
            </div>
          </div>
        `;
        chatLog.insertAdjacentHTML("beforeend", html);
        chatLog.scrollTop = chatLog.scrollHeight;
      }

      chatForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const q = (chatInput.value || "").trim();
        if (!q) return;
        chatInput.value = "";
        addChat("user", q);

        try {
          const resp = await fetch("/chat", {
            method: "POST",
            headers: {"Content-Type":"application/json"},
            body: JSON.stringify({question: q, limit: 260, use_case: useCase})
          });
          const data = await resp.json();
          addChat("assistant", data.answer || "(no answer)");
        } catch (err) {
          addChat("assistant", "Chat request failed. Check server logs.");
        }
      });

      loadMeta();
      loadKpi();
      setUseCase("security");
      poll();
      refreshStreamStatus();

      setInterval(poll, 1000);
      setInterval(loadKpi, 15000);
      setInterval(refreshStreamStatus, 3000);
    </script>
  </body>
</html>
"""


def build_app(cfg: Settings) -> FastAPI:
    app = FastAPI()
    init_vertex(cfg)
    bq = bigquery.Client(project=cfg.gcp_project)
    table_id = f"{cfg.gcp_project}.{cfg.bigquery_dataset}.{cfg.bigquery_audit_table}"

    stream_stop_events: dict[str, threading.Event] = {}
    stream_threads: dict[str, threading.Thread] = {}
    stream_running: dict[str, bool] = {"security": False, "assembly": False}

    def _start_stream(use_case: str) -> None:
        use_case = str(use_case or "").lower().strip()
        if use_case not in ("security", "assembly"):
            return
        if stream_running.get(use_case):
            return

        ev = threading.Event()
        stream_stop_events[use_case] = ev

        if use_case == "security":
            args = dict(
                cfg=cfg,
                video_path=cfg.security_video_path,
                camera_id="cam-security-1",
                use_case="security",
                station_id=None,
                sku_id=None,
                max_clips=None,
                stop_event=ev,
            )
        else:
            args = dict(
                cfg=cfg,
                video_path=cfg.assembly_video_path,
                camera_id="cam-assembly-s4",
                use_case="assembly",
                station_id="S4",
                sku_id="S1345780",
                max_clips=None,
                stop_event=ev,
            )

        def job():
            stream_running[use_case] = True
            try:
                publish_clips_from_video(**args)
            finally:
                stream_running[use_case] = False

        t = threading.Thread(target=job, daemon=True)
        stream_threads[use_case] = t
        t.start()

    def _stop_stream(use_case: str) -> None:
        use_case = str(use_case or "").lower().strip()
        ev = stream_stop_events.get(use_case)
        if ev:
            ev.set()

    @app.get("/meta")
    def meta():
        def red(s: str) -> str:
            if not s:
                return ""
            return s.replace("https://", "").replace("http://", "").split("@")[-1].split("/")[0]

        return {
            "confluent_cloud": True,
            "kafka_bootstrap": red(cfg.kafka_bootstrap),
            "schema_registry": red(cfg.schema_registry_url),
            "topics": {
                "clips": cfg.topic_clips,
                "observations": cfg.topic_observations,
                "sessions": cfg.topic_sessions,
                "decisions": cfg.topic_decisions,
                "actions": cfg.topic_actions,
                "audit": cfg.topic_audit,
            },
            "vertex": {
                "region": cfg.gcp_region,
                "observer_model": cfg.gemini_observer_model,
                "thinker_model": cfg.gemini_thinker_model,
            },
        }

    @app.get("/stream/status")
    def stream_status():
        return {"running": stream_running}

    @app.post("/stream/start")
    def stream_start(req: StreamReq):
        _start_stream(req.use_case)
        return {"ok": True, "running": stream_running}

    @app.post("/stream/stop")
    def stream_stop(req: StreamReq):
        _stop_stream(req.use_case)
        return {"ok": True, "running": stream_running}

    @app.get("/kpi")
    def kpi():
        q = f"""
        WITH recent AS (
          SELECT kind, ts, payload_json
          FROM `{table_id}`
          WHERE ts >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
        ),
        actions AS (
          SELECT
            ts,
            JSON_VALUE(payload_json, '$.use_case') AS use_case,
            JSON_VALUE(payload_json, '$.action.type') AS action_type,
            JSON_VALUE(payload_json, '$.action.priority') AS priority
          FROM recent
          WHERE kind = 'action'
        )
        SELECT
          (SELECT COUNT(*) FROM actions WHERE action_type = 'stop_line') AS stop_line_24h,
          (SELECT COUNT(*) FROM actions WHERE action_type = 'alert') AS alert_24h,
          (SELECT COUNT(*) FROM recent WHERE kind = 'decision') AS decisions_24h,
          (SELECT COUNT(*) FROM recent WHERE kind = 'observation') AS observations_24h,
          (SELECT MAX(ts) FROM actions WHERE action_type = 'stop_line') AS last_stop_line_ts,
          (SELECT COUNT(*) FROM actions WHERE use_case = 'security' AND action_type = 'stop_line') AS stop_sec,
          (SELECT COUNT(*) FROM actions WHERE use_case = 'security' AND action_type = 'alert') AS alert_sec,
          (SELECT COUNT(*) FROM actions WHERE use_case = 'assembly' AND action_type = 'stop_line') AS stop_asm,
          (SELECT COUNT(*) FROM actions WHERE use_case = 'assembly' AND action_type = 'alert') AS alert_asm,
          (SELECT COUNT(*) FROM actions WHERE priority = 'P1') AS p1,
          (SELECT COUNT(*) FROM actions WHERE priority = 'P2') AS p2,
          (SELECT COUNT(*) FROM actions WHERE priority = 'P3') AS p3
        """
        rows = list(bq.query(q).result())
        if not rows:
            return {
                "stop_line_24h": 0,
                "alert_24h": 0,
                "decisions_24h": 0,
                "observations_24h": 0,
                "last_stop_line_ts": None,
                "by_use_case": {"security": {"stop_line": 0, "alert": 0}, "assembly": {"stop_line": 0, "alert": 0}},
                "priorities": {"P1": 0, "P2": 0, "P3": 0},
                "top_rules": [],
            }

        r = rows[0]

        q_rules = f"""
        WITH recent_decisions AS (
          SELECT JSON_VALUE(payload_json, '$.assessment.rule_id') AS rule_id
          FROM `{table_id}`
          WHERE kind = 'decision'
            AND ts >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
        )
        SELECT rule_id, COUNT(*) AS cnt
        FROM recent_decisions
        WHERE rule_id IS NOT NULL AND rule_id != ''
        GROUP BY rule_id
        ORDER BY cnt DESC
        LIMIT 8
        """
        rules_rows = list(bq.query(q_rules).result())
        top_rules = [{"rule_id": rr["rule_id"], "count": int(rr["cnt"])} for rr in rules_rows]

        return {
            "stop_line_24h": int(r["stop_line_24h"] or 0),
            "alert_24h": int(r["alert_24h"] or 0),
            "decisions_24h": int(r["decisions_24h"] or 0),
            "observations_24h": int(r["observations_24h"] or 0),
            "last_stop_line_ts": (r["last_stop_line_ts"].isoformat() if r["last_stop_line_ts"] else None),
            "by_use_case": {
                "security": {"stop_line": int(r["stop_sec"] or 0), "alert": int(r["alert_sec"] or 0)},
                "assembly": {"stop_line": int(r["stop_asm"] or 0), "alert": int(r["alert_asm"] or 0)},
            },
            "priorities": {"P1": int(r["p1"] or 0), "P2": int(r["p2"] or 0), "P3": int(r["p3"] or 0)},
            "top_rules": top_rules,
        }

    @app.get("/ui", response_class=HTMLResponse)
    def ui():
        return _ui_html()

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    def home():
        return _home_html(linkedin_url="https://www.linkedin.com/in/niketshah-9033959570", github_url="https://github.com/Niket93/sentinel", youtube_embed_url="https://www.youtube.com/embed/n2nL2sf2FAU")

    @app.get("/video")
    def video(use_case: str = "security"):
        path = cfg.assembly_video_path if use_case == "assembly" else cfg.security_video_path
        return FileResponse(path, media_type="video/mp4")

    @app.get("/recent")
    def recent(limit: int = 80):
        q = f"""
        SELECT audit_id, ts, kind, trace_id, payload_json
        FROM `{table_id}`
        ORDER BY ts DESC
        LIMIT {int(limit)}
        """
        rows = bq.query(q).result()
        out = []
        for rr in rows:
            out.append(
                {
                    "audit_id": rr["audit_id"],
                    "ts": rr["ts"].isoformat(),
                    "kind": rr["kind"],
                    "trace_id": rr["trace_id"],
                    "payload": json.loads(rr["payload_json"]),
                }
            )
        return out

    @app.post("/chat")
    def chat(inp: ChatIn):
        q = (inp.question or "").strip()
        if not q:
            return {"answer": "Please provide a question.", "source": "vertex_ai_search"}
        sr = answer_query(cfg, q, session_id=inp.session_id)
        answer = sr.answer_text.strip() if sr.answer_text else ""
        if not answer:
            if sr.snippets:
                answer = "No direct answer text returned. Relevant SOP snippets were found."
            else:
                answer = "I don't know."
        return {
            "answer": answer,
            "source": "vertex_ai_search",
            "snippets": sr.snippets[:8],
            "snippets_count": len(sr.snippets),
        }

    return app