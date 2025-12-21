from __future__ import annotations
import json
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from google.cloud import bigquery
from ..config.settings import Settings
from ..shared.vertex_client import init_vertex
from ..rag.vertex_search_answer import answer_query

class ChatIn(BaseModel):
    question: str
    limit: int = 200
    use_case: str | None = None
    session_id: str | None = None


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
      /* Consistent typography scale (no surprises) */
      .t-11 { font-size: 11px; line-height: 16px; }
      .t-12 { font-size: 12px; line-height: 18px; }
      .t-14 { font-size: 14px; line-height: 20px; }
      .t-16 { font-size: 16px; line-height: 22px; }
      .t-18 { font-size: 18px; line-height: 24px; }
    </style>
  </head>

  <body class="min-h-screen bg-zinc-950 text-zinc-50 antialiased">
    <!-- Background -->
    <div class="fixed inset-0 -z-10">
      <div class="absolute inset-0 bg-[radial-gradient(900px_circle_at_20%_10%,rgba(16,185,129,0.14),transparent_45%),radial-gradient(900px_circle_at_80%_0%,rgba(99,102,241,0.10),transparent_40%),radial-gradient(900px_circle_at_50%_90%,rgba(244,63,94,0.08),transparent_45%)]"></div>
      <div class="absolute inset-0 opacity-20 bg-[linear-gradient(to_right,rgba(255,255,255,0.04)_1px,transparent_1px),linear-gradient(to_bottom,rgba(255,255,255,0.04)_1px,transparent_1px)] bg-[size:72px_72px]"></div>
    </div>

    <!-- App Shell: full width -->
    <div class="w-full max-w-none px-4 sm:px-6 lg:px-8 2xl:px-10 py-6">
      <!-- Top Bar -->
      <header class="flex items-center justify-between gap-4">
        <div class="flex items-center gap-3 min-w-0">
          <div class="h-10 w-10 rounded-2xl bg-emerald-500/12 ring-1 ring-emerald-500/20 grid place-items-center shrink-0">
            <span class="text-emerald-300 font-semibold tracking-tight t-14">S</span>
          </div>
          <div class="leading-tight min-w-0">
            <div class="t-16 font-semibold tracking-tight truncate">Sentinel</div>
            <div class="t-12 text-zinc-400 truncate">Always-on decision copilot for real-world operations</div>
          </div>
        </div>

        <div class="flex items-center gap-3 shrink-0">
          <!-- Use case toggle -->
          <div class="flex rounded-2xl bg-zinc-900/60 ring-1 ring-zinc-800 overflow-hidden">
            <button id="ucSecurity" class="px-4 py-2 t-14 font-medium text-zinc-200 hover:bg-zinc-800/60">Security</button>
            <button id="ucAssembly" class="px-4 py-2 t-14 font-medium text-zinc-200 hover:bg-zinc-800/60">Assembly</button>
          </div>

          <!-- Live indicator -->
          <div class="inline-flex items-center gap-2 rounded-2xl bg-zinc-900/60 ring-1 ring-zinc-800 px-3 py-2">
            <span id="statusDot" class="h-2 w-2 rounded-full bg-emerald-400"></span>
            <span id="statusText" class="t-14 text-zinc-200">Live</span>
          </div>
        </div>
      </header>

      <!-- Subheader -->
      <div class="mt-4 flex items-center justify-between gap-4">
        <div class="min-w-0">
          <div id="cameraTitle" class="t-14 font-semibold text-zinc-100 truncate">Security Feed</div>
          <div id="subtitle" class="t-12 text-zinc-400 mt-1 truncate">
            Detect restricted-zone / walkway violations and open panel/guard while machine is operating.
          </div>
        </div>

        <div class="flex items-center gap-2 shrink-0">
          <button id="btnReplay" class="rounded-2xl bg-zinc-900/60 px-4 py-2 t-14 ring-1 ring-zinc-800 hover:ring-zinc-600">
            Replay
          </button>
          <button id="btnClear" class="rounded-2xl bg-zinc-900/60 px-4 py-2 t-14 ring-1 ring-zinc-800 hover:ring-zinc-600">
            Clear
          </button>
        </div>
      </div>

      <main class="mt-6 space-y-6">
        <!-- Video Card -->
        <section class="rounded-3xl border border-zinc-800/70 bg-zinc-900/30 backdrop-blur overflow-hidden shadow-[0_0_0_1px_rgba(255,255,255,0.03)]">
          <div class="px-5 py-4 flex items-center justify-between border-b border-zinc-800/70">
            <div class="min-w-0">
              <div class="t-12 text-zinc-400">Video</div>
              <div class="t-14 font-semibold text-zinc-100 mt-0.5 truncate" id="videoTitle">Live camera</div>
            </div>
            <div class="t-12 text-zinc-400 hidden sm:block">Clip → Observe → Decide → Act → Audit</div>
          </div>

          <div class="bg-black">
            <video id="video" class="w-full aspect-video" controls autoplay muted playsinline>
              <source id="videoSrc" src="/video?use_case=security" type="video/mp4" />
            </video>
          </div>
        </section>

        <!-- 3 Panels: fill width -->
        <section class="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <!-- Feed -->
          <div class="rounded-3xl border border-zinc-800/70 bg-zinc-900/30 backdrop-blur overflow-hidden shadow-[0_0_0_1px_rgba(255,255,255,0.03)] flex flex-col min-h-0">
            <div class="px-5 py-4 border-b border-zinc-800/70">
              <div class="t-12 text-zinc-400">Event stream</div>
              <div class="t-14 font-semibold text-zinc-100 mt-0.5">Observations • Decisions • Actions</div>
            </div>
            <div id="feed" class="p-4 space-y-3 h-[520px] lg:h-[560px] overflow-auto"></div>
            <div class="px-5 py-4 border-t border-zinc-800/70">
              <div class="flex flex-wrap gap-2 t-12">
                <span class="inline-flex items-center rounded-full bg-sky-500/10 text-sky-200 ring-1 ring-sky-500/20 px-2.5 py-1">Observation</span>
                <span class="inline-flex items-center rounded-full bg-violet-500/10 text-violet-200 ring-1 ring-violet-500/20 px-2.5 py-1">Decision</span>
                <span class="inline-flex items-center rounded-full bg-amber-500/10 text-amber-200 ring-1 ring-amber-500/20 px-2.5 py-1">Alert</span>
                <span class="inline-flex items-center rounded-full bg-rose-500/10 text-rose-200 ring-1 ring-rose-500/20 px-2.5 py-1">Stop line</span>
              </div>
            </div>
          </div>

          <!-- Decision detail -->
          <div class="rounded-3xl border border-zinc-800/70 bg-zinc-900/30 backdrop-blur overflow-hidden shadow-[0_0_0_1px_rgba(255,255,255,0.03)] flex flex-col min-h-0">
            <div class="px-5 py-4 border-b border-zinc-800/70">
              <div class="t-12 text-zinc-400">Decision detail</div>
              <div class="t-14 font-semibold text-zinc-100 mt-0.5">Latest decision breakdown</div>
            </div>
            <div class="p-4 h-[520px] lg:h-[560px] overflow-auto" id="thinkingPanel">
              <div class="rounded-2xl bg-zinc-950/40 ring-1 ring-zinc-800/70 p-4">
                <div class="t-14 text-zinc-200">No decision yet.</div>
                <div class="t-12 text-zinc-500 mt-2">Once a decision arrives, details appear here.</div>
              </div>
            </div>
          </div>

          <!-- Chat -->
          <div class="rounded-3xl border border-zinc-800/70 bg-zinc-900/30 backdrop-blur overflow-hidden shadow-[0_0_0_1px_rgba(255,255,255,0.03)] flex flex-col min-h-0">
            <div class="px-5 py-4 border-b border-zinc-800/70">
              <div class="t-12 text-zinc-400">Audit chat</div>
              <div class="t-14 font-semibold text-zinc-100 mt-0.5">Ask questions about events</div>
            </div>

            <div id="chatLog" class="p-4 space-y-3 h-[410px] lg:h-[450px] overflow-auto"></div>

            <form id="chatForm" class="p-4 border-t border-zinc-800/70 flex gap-2">
              <input
                id="chatInput"
                class="flex-1 rounded-2xl bg-zinc-950/60 px-4 py-3 t-14 ring-1 ring-zinc-800 focus:outline-none focus:ring-emerald-500/55"
                placeholder="Ask: Why did we stop the line? Which clip shows it?"
              />
              <button
                class="rounded-2xl bg-emerald-500/15 px-5 py-3 t-14 font-medium text-emerald-200 ring-1 ring-emerald-500/25 hover:ring-emerald-500/60"
                type="submit"
              >
                Send
              </button>
            </form>

            <div class="px-5 pb-4 t-12 text-zinc-500">
              Answers are grounded in the audit log.
            </div>
          </div>
        </section>
      </main>
    </div>

    <script>
      // ----------------------------
      // State
      // ----------------------------
      let useCase = "security"; // "security" | "assembly"
      let seen = new Set();
      let traceToGcs = new Map();
      let latestDecision = null;

      const feedEl = document.getElementById("feed");
      const thinkingPanel = document.getElementById("thinkingPanel");

      const btnClear = document.getElementById("btnClear");
      const btnReplay = document.getElementById("btnReplay");

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

      function escapeHtml(s) {
        return (s || "").replace(/[&<>"']/g, (c) => ({
          "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"
        }[c]));
      }

      function setUseCase(next) {
        useCase = next;

        const active = "bg-zinc-50/10 text-zinc-50";
        const inactive = "text-zinc-200";

        if (useCase === "security") {
          ucSecurity.className = "px-4 py-2 t-14 font-medium " + active;
          ucAssembly.className = "px-4 py-2 t-14 font-medium hover:bg-zinc-800/60 " + inactive;
          subtitle.textContent = "Detect restricted-zone / walkway violations and open panel/guard while machine is operating.";
          cameraTitle.textContent = "Security Feed";
          videoTitle.textContent = "Industrial floor • Security camera";
        } else {
          ucAssembly.className = "px-4 py-2 t-14 font-medium " + active;
          ucSecurity.className = "px-4 py-2 t-14 font-medium hover:bg-zinc-800/60 " + inactive;
          subtitle.textContent = "Detect SOP compliance across a station session and trigger interventions when steps are missed.";
          cameraTitle.textContent = "Assembly • Station S4";
          videoTitle.textContent = "Assembly line • Station camera";
        }

        videoSrc.src = "/video?use_case=" + encodeURIComponent(useCase);
        videoEl.load();
        videoEl.play();

        // reset UI state
        feedEl.innerHTML = "";
        seen = new Set();
        traceToGcs = new Map();
        latestDecision = null;
        renderDecisionPanel(null);

        poll();
      }

      function pill(label, cls) {
        return `<span class="inline-flex items-center rounded-full px-2.5 py-1 t-12 ring-1 ${cls}">${escapeHtml(label)}</span>`;
      }

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
          if (rule && risk) return `${rule} — ${risk}`;
          return rule || risk || "Decision generated.";
        }
        if (kind === "action") return String(payload?.action?.message || "").trim() || "Action executed.";
        return "";
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

      function clipLinksHtml(traceId) {
        const gs = traceToGcs.get(traceId) || "";
        if (!gs) return "";
        const consoleUrl = gcsToConsoleUrl(gs);
        const gsEsc = escapeHtml(gs);

        const a = consoleUrl
          ? `<a class="text-emerald-300 hover:text-emerald-200 underline decoration-emerald-500/30 hover:decoration-emerald-300/60" href="${consoleUrl}" target="_blank" rel="noreferrer">Open clip</a>`
          : "";

        return `
          <div class="mt-3 t-12 text-zinc-400">
            ${a ? a + `<span class="mx-2 text-zinc-700">•</span>` : ""}
            <span class="font-mono">${gsEsc}</span>
          </div>
        `;
      }

      function kvRow(k, v) {
        return `
          <div class="flex items-start justify-between gap-4">
            <div class="t-12 text-zinc-400">${escapeHtml(k)}</div>
            <div class="t-12 text-zinc-200 text-right break-words">${escapeHtml(String(v ?? ""))}</div>
          </div>
        `;
      }

      function renderDecisionPanel(decEv) {
        if (!decEv) {
          thinkingPanel.innerHTML = `
            <div class="rounded-2xl bg-zinc-950/40 ring-1 ring-zinc-800/70 p-4">
              <div class="t-14 text-zinc-200">No decision yet.</div>
              <div class="t-12 text-zinc-500 mt-2">Once a decision arrives, details appear here.</div>
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
          <div class="rounded-2xl bg-zinc-950/45 ring-1 ring-zinc-800/70 p-4">
            <div class="flex items-start justify-between gap-3">
              <div>
                <div class="t-14 font-semibold text-zinc-100">Decision</div>
                <div class="t-12 text-zinc-500 mt-0.5">${escapeHtml(decEv.ts || "")} • trace ${escapeHtml((traceId || "").slice(0,8))}</div>
              </div>
              <div class="shrink-0">${rightPill("decision", payload)}</div>
            </div>

            <div class="mt-4 space-y-3">
              <div class="rounded-xl bg-zinc-950/35 ring-1 ring-zinc-800/70 p-3">
                <div class="t-12 text-zinc-400">Recommended action</div>
                <div class="mt-1 t-14 font-semibold text-zinc-100">${escapeHtml(actionType || "unknown")} ${priority ? `• ${escapeHtml(priority)}` : ""}</div>
                <div class="mt-1 t-14 text-zinc-200">${escapeHtml(actionMsg || "—")}</div>
              </div>

              <div class="rounded-xl bg-zinc-950/35 ring-1 ring-zinc-800/70 p-3 space-y-2">
                <div class="t-12 text-zinc-400">Assessment</div>
                ${sev ? kvRow("severity", sev) : ""}
                ${conf !== undefined ? kvRow("confidence", conf) : ""}
                ${rule ? kvRow("rule_id", rule) : ""}
                ${risk ? kvRow("risk", risk) : ""}
              </div>

              <div class="rounded-xl bg-zinc-950/35 ring-1 ring-zinc-800/70 p-3">
                <div class="t-12 text-zinc-400">Rationale</div>
                <div class="mt-1 t-14 text-zinc-200">${escapeHtml(String(rationale?.short || "—"))}</div>
              </div>

              <div class="rounded-xl bg-zinc-950/35 ring-1 ring-zinc-800/70 p-3 space-y-2">
                <div class="t-12 text-zinc-400">Evidence</div>
                ${kvRow("reason", reason || "—")}
                ${clipRange ? kvRow("clip_range", `${clipRange[0]} → ${clipRange[1]}`) : kvRow("clip_range", "—")}
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
          <div class="rounded-2xl bg-zinc-950/45 ring-1 ring-zinc-800/70 p-4 hover:ring-zinc-600/80 transition cursor-${kind === "decision" ? "pointer" : "default"}"
               ${clickHint}
               data-audit-id="${escapeHtml(ev.audit_id || "")}">
            <div class="flex items-start justify-between gap-3">
              <div class="min-w-0">
                <div class="t-14 font-semibold text-zinc-100">${escapeHtml(kind.charAt(0).toUpperCase() + kind.slice(1))}</div>
                <div class="t-12 text-zinc-500 mt-0.5">${escapeHtml(ts)} • ${escapeHtml(kind)} • trace ${escapeHtml(traceShort)}</div>
              </div>
              <div class="shrink-0">${topRight}</div>
            </div>

            <div class="mt-3 t-14 text-zinc-200 whitespace-pre-wrap">${escapeHtml(desc)}</div>
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
            }
            seen.add(auditId);
          });

          document.getElementById("statusDot").className = "h-2 w-2 rounded-full bg-emerald-400";
          document.getElementById("statusText").textContent = "Live";
        } catch (e) {
          document.getElementById("statusDot").className = "h-2 w-2 rounded-full bg-rose-400";
          document.getElementById("statusText").textContent = "Disconnected";
        }
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
              <div class="t-11 text-zinc-400 mb-1">${label}</div>
              <div class="t-14 whitespace-pre-wrap">${escapeHtml(text)}</div>
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

      // Start
      setUseCase("security");
      poll();
      setInterval(poll, 1000);
    </script>
  </body>
</html>
"""


def build_app(cfg: Settings) -> FastAPI:
    app = FastAPI()
    init_vertex(cfg)
    bq = bigquery.Client(project=cfg.gcp_project)
    table_id = f"{cfg.gcp_project}.{cfg.bigquery_dataset}.{cfg.bigquery_audit_table}"

    @app.get("/ui", response_class=HTMLResponse)
    def ui():
        return _ui_html()

    @app.get("/video")
    def video(use_case: str = "security"):
        if use_case == "assembly":
            path = cfg.assembly_video_path
        else:
            path = cfg.security_video_path
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
        for r in rows:
            out.append(
                {
                    "audit_id": r["audit_id"],
                    "ts": r["ts"].isoformat(),
                    "kind": r["kind"],
                    "trace_id": r["trace_id"],
                    "payload": json.loads(r["payload_json"]),
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