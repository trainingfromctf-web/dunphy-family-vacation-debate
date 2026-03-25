from __future__ import annotations

import asyncio
import json
import threading
from datetime import datetime
from typing import List

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, PlainTextResponse, StreamingResponse

from discussion.orchestrator import FamilyDiscussionOrchestrator
from discussion.transcript import build_transcript_markdown

load_dotenv()

app = FastAPI(title="Dunphy Family Vacation Discussion")

orchestrator = FamilyDiscussionOrchestrator()
_event_lock = threading.Lock()
_events: List[dict] = []
_event_seq = 0


def _push_event(kind: str, payload: dict) -> None:
    global _event_seq
    _event_seq += 1
    event = {
        "id": _event_seq,
        "kind": kind,
        "payload": payload,
        "ts": datetime.now().isoformat(timespec="seconds"),
    }
    with _event_lock:
        _events.append(event)
    # Server-side trace helps diagnose stalls in browser UI mode.
    print(f"[event] {kind}: {payload}")


def _wire_callbacks() -> None:
    orchestrator.on_message = lambda speaker, text: _push_event(
        "message", {"speaker": speaker, "text": text}
    )
    orchestrator.on_phase_change = lambda phase_number: _push_event(
        "phase", {"phase_number": phase_number}
    )
    orchestrator.on_discussion_complete = lambda: _push_event("complete", {"done": True})
    orchestrator.on_error = lambda text: _push_event("error", {"text": text})
    orchestrator.on_failure_options = lambda _agent: _push_event(
        "paused", {"paused": True, "hint": "Use retry/skip controls"}
    )
    orchestrator.on_metrics_update = lambda metrics: _push_event("metrics", metrics)


_wire_callbacks()


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return """<!DOCTYPE html>
<html class="dark" lang="en">
<head>
<meta charset="utf-8"/>
<meta content="width=device-width, initial-scale=1.0" name="viewport"/>
<title>Dunphy Family Vacation Discussion</title>
<script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=Space_Grotesk:wght@300;400;500;600;700&display=swap" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet"/>
<script>
      tailwind.config = {
        darkMode: "class",
        theme: {
          extend: {
            colors: {
              "error": "#ffb4ab",
              "on-primary-fixed": "#001a41",
              "tertiary-fixed": "#ffe08b",
              "on-tertiary-fixed": "#241a00",
              "on-primary": "#002e69",
              "on-primary-fixed-variant": "#004493",
              "secondary-fixed": "#ffdada",
              "inverse-surface": "#e5e2e1",
              "surface-container-lowest": "#0e0e0e",
              "on-secondary-fixed-variant": "#920027",
              "surface": "#131313",
              "secondary": "#ffb3b5",
              "on-secondary": "#680019",
              "surface-container-highest": "#353534",
              "surface-variant": "#353534",
              "on-error": "#690005",
              "outline-variant": "#414755",
              "on-primary-container": "#00285c",
              "on-tertiary": "#3d2f00",
              "secondary-container": "#de0541",
              "on-secondary-container": "#fff1f1",
              "surface-container-low": "#1c1b1b",
              "on-secondary-fixed": "#40000c",
              "surface-bright": "#3a3939",
              "on-tertiary-container": "#4f3d00",
              "primary-fixed": "#d8e2ff",
              "error-container": "#93000a",
              "secondary-fixed-dim": "#ffb3b5",
              "on-surface": "#e5e2e1",
              "on-error-container": "#ffdad6",
              "background": "#131313",
              "on-surface-variant": "#c1c6d7",
              "surface-container-high": "#2a2a2a",
              "tertiary": "#f1c100",
              "outline": "#8b90a0",
              "surface-container": "#201f1f",
              "tertiary-container": "#d0a600",
              "surface-tint": "#adc6ff",
              "on-background": "#e5e2e1",
              "inverse-primary": "#005bc1",
              "inverse-on-surface": "#313030",
              "tertiary-fixed-dim": "#f1c100",
              "primary": "#adc6ff",
              "primary-container": "#4b8eff",
              "primary-fixed-dim": "#adc6ff",
              "surface-dim": "#131313",
              "on-tertiary-fixed-variant": "#584400"
            },
            fontFamily: {
              "headline": ["Inter"],
              "body": ["Inter"],
              "label": ["Space Grotesk"]
            },
            borderRadius: {"DEFAULT": "0.25rem", "lg": "0.5rem", "xl": "0.75rem", "full": "9999px"},
          },
        },
      }
</script>
<style>
      .material-symbols-outlined {
        font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24;
      }
      ::-webkit-scrollbar { width: 4px; }
      ::-webkit-scrollbar-track { background: transparent; }
      ::-webkit-scrollbar-thumb { background: #353534; border-radius: 10px; }
</style>
</head>
<body class="bg-surface text-on-surface font-body overflow-hidden h-screen flex flex-col">
<main class="flex flex-1 overflow-hidden">
<!-- SideNavBar -->
<aside class="hidden lg:flex flex-col h-full w-64 bg-[#1c1b1b] border-r border-transparent docked left-0">
<div class="p-6">
<div class="text-[#adc6ff] font-bold text-lg mb-1">Agents</div>
<div class="font-['Space_Grotesk'] text-[0.65rem] tracking-widest uppercase text-[#8b90a0]">Discussion Analytics</div>
</div>
<nav class="flex-1 px-3 space-y-1">
<div class="flex items-center gap-3 bg-[#4b8eff] text-white rounded-lg p-3 Active: translate-x-1 duration-200 cursor-pointer">
<span class="material-symbols-outlined">forum</span>
<span class="font-['Space_Grotesk'] text-sm tracking-widest uppercase">Live Chat</span>
</div>
</nav>
<div class="p-4 mt-auto">
<div class="bg-surface-container-highest rounded-xl p-4 flex items-center gap-3">
<div class="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-on-primary font-bold text-xs">SM</div>
<div>
<div class="text-xs font-bold">System Monitor</div>
<div class="text-[10px] text-outline">v1.0.0</div>
</div>
</div>
</div>
</aside>
<!-- Main Discussion Canvas -->
<section class="flex-1 flex flex-col md:flex-row h-full overflow-hidden bg-surface">
<!-- LEFT PANEL: Chat Window -->
<div class="flex-1 flex flex-col min-w-0 bg-surface relative">
<!-- Chat Header -->
<div class="px-8 py-4 bg-surface-container-low flex justify-between items-center z-10">
<div class="flex items-center gap-4">
<div class="flex -space-x-3">
<div class="w-10 h-10 rounded-full border-2 border-surface bg-primary flex items-center justify-center text-[10px] font-bold">PD</div>
<div class="w-10 h-10 rounded-full border-2 border-surface bg-secondary flex items-center justify-center text-[10px] font-bold">CD</div>
<div class="w-10 h-10 rounded-full border-2 border-surface bg-tertiary flex items-center justify-center text-[10px] font-bold">HD</div>
</div>
<div>
<h2 class="text-xl font-bold tracking-tight">Dunphy Family Vacation Discussion</h2>
<p class="text-xs text-outline font-label uppercase tracking-widest">6 participants active</p>
</div>
</div>
<div class="flex items-center gap-2">
<select id="model" class="bg-surface-container-highest text-on-surface border border-outline-variant/30 rounded-lg px-3 py-2 text-xs font-label focus:outline-none focus:ring-1 focus:ring-primary">
<option value="mock">mock</option>
<option value="gemini">gemini</option>
</select>
<button id="btn-start" class="bg-primary-container text-white px-4 py-2 rounded-lg text-xs font-label font-bold uppercase tracking-wider hover:opacity-90 transition-opacity">Start</button>
<button id="btn-reset" class="bg-surface-container-highest text-on-surface px-4 py-2 rounded-lg text-xs font-label font-bold uppercase tracking-wider hover:opacity-90 transition-opacity">Reset</button>
<button id="btn-retry" class="bg-surface-container-highest text-on-surface px-3 py-2 rounded-lg text-xs font-label uppercase tracking-wider hover:opacity-90 transition-opacity">Retry</button>
<button id="btn-skip" class="bg-surface-container-highest text-on-surface px-3 py-2 rounded-lg text-xs font-label uppercase tracking-wider hover:opacity-90 transition-opacity">Skip</button>
<button id="btn-export" class="bg-surface-container-highest text-on-surface px-3 py-2 rounded-lg text-xs font-label uppercase tracking-wider hover:opacity-90 transition-opacity flex items-center gap-1">
<span class="material-symbols-outlined text-sm">download</span> Export
</button>
</div>
</div>
<!-- Messages Area -->
<div id="messages" class="flex-1 overflow-y-auto p-8 space-y-6"></div>
<!-- Bottom Status Bar -->
<div class="px-8 py-3 bg-surface-container-lowest border-t border-outline-variant/10 flex items-center gap-3">
<div id="status-dot" class="w-2 h-2 rounded-full bg-outline"></div>
<span id="status-text" class="text-[10px] font-label uppercase tracking-widest text-outline">Idle</span>
</div>
</div>
<!-- RIGHT PANEL: Agent Sidebar -->
<div class="w-full md:w-[320px] bg-surface-container-low border-l border-outline-variant/15 flex flex-col">
<div class="p-8 pb-4">
<h3 class="text-2xl font-bold tracking-tight mb-6">Agents</h3>
<div class="space-y-6">
<!-- Agent Phil -->
<div class="flex items-center justify-between group">
<div class="flex items-center gap-3">
<div class="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-[10px] font-bold text-on-primary">PD</div>
<div>
<div class="text-sm font-bold">Phil Dunphy</div>
<div class="text-[10px] font-label text-outline">LOGIC_OPTIMIST</div>
</div>
</div>
<div class="text-right">
<div id="tokens-Phil" class="text-xs font-label text-primary">0</div>
<div id="cost-Phil" class="text-[9px] font-label text-outline">$0.000000</div>
</div>
</div>
<!-- Agent Claire -->
<div class="flex items-center justify-between group">
<div class="flex items-center gap-3">
<div class="w-8 h-8 rounded-full bg-secondary flex items-center justify-center text-[10px] font-bold text-on-secondary">CD</div>
<div>
<div class="text-sm font-bold">Claire Dunphy</div>
<div class="text-[10px] font-label text-outline">CRITIC_MANAGER</div>
</div>
</div>
<div class="text-right">
<div id="tokens-Claire" class="text-xs font-label text-secondary">0</div>
<div id="cost-Claire" class="text-[9px] font-label text-outline">$0.000000</div>
</div>
</div>
<!-- Agent Haley -->
<div class="flex items-center justify-between group">
<div class="flex items-center gap-3">
<div class="w-8 h-8 rounded-full bg-tertiary flex items-center justify-center text-[10px] font-bold text-on-tertiary">HD</div>
<div>
<div class="text-sm font-bold">Haley Dunphy</div>
<div class="text-[10px] font-label text-outline">TREND_ANALYST</div>
</div>
</div>
<div class="text-right">
<div id="tokens-Haley" class="text-xs font-label text-tertiary">0</div>
<div id="cost-Haley" class="text-[9px] font-label text-outline">$0.000000</div>
</div>
</div>
<!-- Agent Alex -->
<div class="flex items-center justify-between group">
<div class="flex items-center gap-3">
<div class="w-8 h-8 rounded-full bg-outline flex items-center justify-center text-[10px] font-bold text-surface">AD</div>
<div>
<div class="text-sm font-bold">Alex Dunphy</div>
<div class="text-[10px] font-label text-outline">SYSTEM_ANALYST</div>
</div>
</div>
<div class="text-right">
<div id="tokens-Alex" class="text-xs font-label text-outline">0</div>
<div id="cost-Alex" class="text-[9px] font-label text-outline">$0.000000</div>
</div>
</div>
<!-- Agent Luke -->
<div class="flex items-center justify-between group">
<div class="flex items-center gap-3">
<div class="w-8 h-8 rounded-full bg-error flex items-center justify-center text-[10px] font-bold text-on-error">LD</div>
<div>
<div class="text-sm font-bold">Luke Dunphy</div>
<div class="text-[10px] font-label text-outline">RANDOM_WALK</div>
</div>
</div>
<div class="text-right">
<div id="tokens-Luke" class="text-xs font-label text-error">0</div>
<div id="cost-Luke" class="text-[9px] font-label text-outline">$0.000000</div>
</div>
</div>
<!-- Agent Manny -->
<div class="flex items-center justify-between group">
<div class="flex items-center gap-3">
<div class="w-8 h-8 rounded-full bg-primary-container flex items-center justify-center text-[10px] font-bold text-white">MD</div>
<div>
<div class="text-sm font-bold">Manny Delgado</div>
<div class="text-[10px] font-label text-outline">SOUL_REFLECTOR</div>
</div>
</div>
<div class="text-right">
<div id="tokens-Manny" class="text-xs font-label text-primary-container">0</div>
<div id="cost-Manny" class="text-[9px] font-label text-outline">$0.000000</div>
</div>
</div>
</div>
</div>
<div class="mt-auto p-8 border-t border-outline-variant/15 space-y-4">
<div class="flex justify-between items-center">
<span class="text-[10px] font-label uppercase tracking-widest text-outline">Total Tokens</span>
<span id="total-tokens" class="text-sm font-label text-primary">0</span>
</div>
<div class="flex justify-between items-center">
<span class="text-[10px] font-label uppercase tracking-widest text-outline">Total Cost</span>
<span id="total-cost" class="text-xl font-label text-on-surface">$0.000000</span>
</div>
<div class="pt-4">
<p class="text-[9px] italic text-outline leading-relaxed">Estimated at $3 / 1M tokens. Rates may vary based on specific model orchestration tiers.</p>
</div>
</div>
</div>
</section>
</main>

<script>
const messagesEl = document.getElementById('messages');
const statusDot = document.getElementById('status-dot');
const statusText = document.getElementById('status-text');
let lastEventId = 0;
let lastPhaseBanner = null;
const renderedIds = new Set();

const AGENTS = {
    "Phil": { initials: "PD", colorClass: "bg-primary", textClass: "text-on-primary", nameColor: "text-primary" },
    "Claire": { initials: "CD", colorClass: "bg-secondary", textClass: "text-on-secondary", nameColor: "text-secondary" },
    "Haley": { initials: "HD", colorClass: "bg-tertiary", textClass: "text-on-tertiary", nameColor: "text-tertiary" },
    "Alex": { initials: "AD", colorClass: "bg-outline", textClass: "text-surface", nameColor: "text-outline" },
    "Luke": { initials: "LD", colorClass: "bg-error", textClass: "text-on-error", nameColor: "text-error" },
    "Manny": { initials: "MD", colorClass: "bg-primary-container", textClass: "text-white", nameColor: "text-primary-container" },
    "System": { initials: "SY", colorClass: "bg-surface-container-highest", textClass: "text-on-surface", nameColor: "text-outline" },
};

function resolveAgent(speaker) {
    if (!speaker) return AGENTS["System"];
    for (const key of Object.keys(AGENTS)) {
        if (speaker.startsWith(key) || speaker === key) return AGENTS[key];
    }
    return AGENTS["System"];
}

function setStatus(text, pulse) {
    statusText.textContent = text;
    if (pulse) {
        statusDot.className = 'w-2 h-2 rounded-full bg-tertiary animate-pulse';
    } else {
        statusDot.className = 'w-2 h-2 rounded-full bg-outline';
    }
}

function addPhaseBanner(phaseNumber) {
    if (lastPhaseBanner === phaseNumber) return;
    lastPhaseBanner = phaseNumber;
    const wrapper = document.createElement('div');
    wrapper.className = 'flex justify-center';
    const pill = document.createElement('div');
    pill.className = 'bg-surface-container-high border border-outline-variant/20 text-outline rounded-full px-5 py-1.5 text-[11px] font-label font-bold uppercase tracking-widest';
    pill.textContent = 'Phase ' + phaseNumber;
    wrapper.appendChild(pill);
    messagesEl.appendChild(wrapper);
    messagesEl.scrollTop = messagesEl.scrollHeight;
}

function addBubble(speaker, text) {
    const agent = resolveAgent(speaker);
    const row = document.createElement('div');
    row.className = 'flex items-start gap-4';

    const avatar = document.createElement('div');
    avatar.className = 'flex-shrink-0 w-10 h-10 rounded-full ' + agent.colorClass + ' flex items-center justify-center ' + agent.textClass + ' font-bold text-sm';
    avatar.textContent = agent.initials;

    const content = document.createElement('div');
    content.className = 'max-w-[80%]';

    const nameEl = document.createElement('span');
    nameEl.className = 'text-xs font-bold ' + agent.nameColor + ' mb-1 block';
    nameEl.textContent = speaker || 'System';

    const bubble = document.createElement('div');
    bubble.className = 'bg-surface-container-highest text-on-surface px-5 py-3 rounded-xl rounded-tl-sm';
    bubble.textContent = text || '';

    content.appendChild(nameEl);
    content.appendChild(bubble);
    row.appendChild(avatar);
    row.appendChild(content);
    messagesEl.appendChild(row);
    messagesEl.scrollTop = messagesEl.scrollHeight;
}

function addError(text) {
    const wrapper = document.createElement('div');
    wrapper.className = 'flex justify-center';
    const pill = document.createElement('div');
    pill.className = 'bg-error-container text-on-error-container rounded-xl px-5 py-2 text-xs font-label';
    pill.textContent = 'ERROR: ' + text;
    wrapper.appendChild(pill);
    messagesEl.appendChild(wrapper);
    messagesEl.scrollTop = messagesEl.scrollHeight;
}

function updateMetrics(payload) {
    const agents = payload.agents || {};
    for (const [name, data] of Object.entries(agents)) {
        const tokens = data.total_tokens || 0;
        const cost = data.cost_usd || 0;
        const tokEl = document.getElementById('tokens-' + name);
        const costEl = document.getElementById('cost-' + name);
        if (tokEl) tokEl.textContent = tokens.toLocaleString();
        if (costEl) costEl.textContent = data.cost_display || ('$' + cost.toFixed(6));
    }
    const summary = payload.summary || {};
    const totalTokens = summary.total_tokens || 0;
    const totalCost = summary.cost_usd || 0;
    document.getElementById('total-tokens').textContent = totalTokens.toLocaleString();
    document.getElementById('total-cost').textContent = summary.cost_display || ('$' + totalCost.toFixed(6));
}

function renderEvent(e) {
    if (!e || renderedIds.has(e.id)) return;
    renderedIds.add(e.id);
    if (typeof e.id === 'number') lastEventId = Math.max(lastEventId, e.id);

    const payload = e.payload || {};
    const kind = e.kind || '';

    if (kind === 'phase') {
        addPhaseBanner(payload.phase_number);
        setStatus('Phase ' + payload.phase_number + ' in progress...', true);
    }
    else if (kind === 'message') addBubble(payload.speaker, payload.text);
    else if (kind === 'error') addError(payload.text || 'Unknown error');
    else if (kind === 'complete') {
        const wrapper = document.createElement('div');
        wrapper.className = 'flex justify-center';
        const pill = document.createElement('div');
        pill.className = 'bg-surface-container-high border border-primary/30 text-primary rounded-full px-5 py-1.5 text-[11px] font-label font-bold uppercase tracking-widest';
        pill.textContent = 'Discussion Complete';
        wrapper.appendChild(pill);
        messagesEl.appendChild(wrapper);
        messagesEl.scrollTop = messagesEl.scrollHeight;
        setStatus('Discussion complete', false);
    }
    else if (kind === 'paused') {
        addError('Paused: a turn failed. Click Retry or Skip.');
        setStatus('Paused', false);
    }
    else if (kind === 'status') setStatus(payload.text || '', true);
    else if (kind === 'metrics') updateMetrics(payload);
    else if (payload.speaker && payload.text) addBubble(payload.speaker, payload.text);
}

async function post(path, body={}) {
    const r = await fetch(path, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)});
    if (!r.ok) {
        const t = await r.text();
        throw new Error(t);
    }
    return r.json();
}

document.getElementById('btn-start').onclick = async () => {
    try {
        const model = document.getElementById('model').value;
        messagesEl.textContent = '';
        renderedIds.clear();
        lastEventId = 0;
        lastPhaseBanner = null;
        await post('/start', {model});
        setStatus('Running (' + model + ')', true);
    } catch (e) {
        addError(e.message);
    }
};

document.getElementById('btn-retry').onclick = async () => {
    try { await post('/retry'); } catch (e) { addError(e.message); }
};
document.getElementById('btn-skip').onclick = async () => {
    try { await post('/skip'); } catch (e) { addError(e.message); }
};
document.getElementById('btn-reset').onclick = async () => {
    try {
        await post('/reset');
        setStatus('Idle', false);
        messagesEl.textContent = '';
        renderedIds.clear();
        lastEventId = 0;
        lastPhaseBanner = null;
        // Reset sidebar metrics
        for (const name of Object.keys(AGENTS)) {
            const tokEl = document.getElementById('tokens-' + name);
            const costEl = document.getElementById('cost-' + name);
            if (tokEl) tokEl.textContent = '0';
            if (costEl) costEl.textContent = '$0.000000';
        }
        document.getElementById('total-tokens').textContent = '0';
        document.getElementById('total-cost').textContent = '$0.000000';
    } catch (e) {
        addError(e.message);
    }
};

document.getElementById('btn-export').onclick = async () => {
    try {
        const r = await fetch('/export');
        if (!r.ok) {
            const t = await r.text();
            throw new Error(t);
        }
        const blob = await r.blob();
        const cd = r.headers.get('content-disposition') || '';
        const nameMatch = cd.match(/filename="?([^";]+)"?/i);
        const filename = (nameMatch && nameMatch[1]) || 'family-vacation-discussion-transcript.md';
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.URL.revokeObjectURL(url);
    } catch (e) {
        addError(e.message);
    }
};

// SSE connection
const es = new EventSource('/events');
es.onmessage = (ev) => {
    try {
        const e = JSON.parse(ev.data);
        renderEvent(e);
    } catch (_e) {
        addError('Failed to parse event payload');
    }
};
es.onerror = () => {
    const note = document.createElement('div');
    note.className = 'flex justify-center';
    const span = document.createElement('span');
    span.className = 'text-[10px] font-label text-outline';
    span.textContent = 'Event stream reconnecting...';
    note.appendChild(span);
    messagesEl.appendChild(note);
};

// Polling fallback
setInterval(async () => {
    try {
        const r = await fetch('/status');
        const s = await r.json();
        if (s.complete) setStatus('Discussion complete', false);
        else if (s.paused) setStatus('Paused', false);
        else if (s.active) {
            if (!statusText.textContent.toLowerCase().includes('progress') &&
                !statusText.textContent.toLowerCase().includes('running')) {
                setStatus('Running', true);
            }
        }
        else if (!statusText.textContent.toLowerCase().includes('complete')) {
            setStatus('Idle', false);
        }

        const evResp = await fetch('/events_snapshot?after_id=' + lastEventId);
        const evData = await evResp.json();
        const list = evData.events || [];
        for (const e of list) renderEvent(e);
    } catch (_e) {}
}, 1000);
</script>
</body>
</html>"""


@app.post("/start")
def start(payload: dict):
    model = (payload.get("model") or "gemini").strip().lower()
    if model not in {"gemini", "mock"}:
        raise HTTPException(status_code=400, detail="model must be 'gemini' or 'mock'")

    if orchestrator.is_active and not orchestrator.is_complete:
        raise HTTPException(status_code=409, detail="discussion already running")

    with _event_lock:
        _events.clear()
    _push_event("status", {"text": f"Starting discussion (model={model})..."})

    orchestrator.start_discussion(model=model, mode="ai_led")
    return {"ok": True, "model": model}


@app.post("/retry")
def retry_failed():
    orchestrator.retry_failed_agent()
    return {"ok": True}


@app.post("/skip")
def skip_failed():
    orchestrator.skip_failed_agent()
    return {"ok": True}


@app.post("/reset")
def reset():
    orchestrator.reset_discussion()
    with _event_lock:
        _events.clear()
    return {"ok": True}


@app.get("/events")
async def events():
    async def event_generator():
        idx = 0
        while True:
            batch = []
            with _event_lock:
                if idx > len(_events):
                    # Event buffer was reset (new discussion). Re-sync stream cursor.
                    idx = 0
                if idx < len(_events):
                    batch = _events[idx:]
                    idx = len(_events)

            for e in batch:
                yield f"data: {json.dumps(e)}\n\n"

            await asyncio.sleep(0.25)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/status")
def status():
    return {
        "active": orchestrator.is_active,
        "paused": orchestrator.is_paused,
        "complete": orchestrator.is_complete,
    }


@app.get("/export")
def export_transcript():
    history = orchestrator.get_history()
    if not history:
        raise HTTPException(status_code=400, detail="No transcript available yet.")

    mode = "AI-Led" if orchestrator.mode == "ai_led" else "User-Led"
    markdown = build_transcript_markdown(history, model=orchestrator.model, mode=mode)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"family-vacation-discussion-transcript-{ts}.md"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return PlainTextResponse(content=markdown, media_type="text/markdown", headers=headers)


@app.get("/events_snapshot")
def events_snapshot(after_id: int = 0):
    with _event_lock:
        pending = [e for e in _events if int(e.get("id", 0)) > after_id]
    return {"events": pending}


if __name__ == "__main__":
    uvicorn.run("browser_app:app", host="127.0.0.1", port=8080, reload=False)
