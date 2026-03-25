"""
WebSocket AI Agent Chat — Real-time bidirectional demo

The server simulates an AI agent that processes a user query through
multiple steps (thinking, tool calls, final answer) and streams
status events back over a WebSocket connection.
"""

import asyncio
import json
import time

import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

OLLAMA_BASE = "http://localhost:11434"
CHAT_MODEL = "gemma3:1b"

app = FastAPI(title="WebSocket AI Agent Chat")

# ---------------------------------------------------------------------------
# Check Ollama availability
# ---------------------------------------------------------------------------
ollama_available = False


@app.on_event("startup")
async def _probe_ollama():
    global ollama_available
    try:
        async with httpx.AsyncClient(timeout=3) as c:
            r = await c.get(f"{OLLAMA_BASE}/api/tags")
            ollama_available = r.status_code == 200
    except httpx.ConnectError:
        pass
    print(f"[ws-agent] Ollama {'connected' if ollama_available else 'mock mode'}")


# ---------------------------------------------------------------------------
# Serve the browser client
# ---------------------------------------------------------------------------
CLIENT_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI Agent Chat (WebSocket)</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: system-ui, sans-serif; background: #0f172a; color: #e2e8f0; height: 100vh; display: flex; flex-direction: column; }
  #chat { flex: 1; overflow-y: auto; padding: 1rem; display: flex; flex-direction: column; gap: .5rem; }
  .msg { padding: .6rem 1rem; border-radius: .5rem; max-width: 80%; word-wrap: break-word; }
  .user { background: #1e40af; align-self: flex-end; }
  .event { background: #334155; align-self: flex-start; font-size: .85rem; }
  .event .tag { font-weight: 700; margin-right: .4rem; }
  .tag-agent_started { color: #38bdf8; }
  .tag-tool_calling { color: #fbbf24; }
  .tag-tool_finished { color: #a78bfa; }
  .tag-final_answer { color: #4ade80; }
  .tag-error { color: #f87171; }
  #bar { display: flex; padding: .75rem; gap: .5rem; background: #1e293b; }
  #bar input { flex: 1; padding: .5rem; border-radius: .4rem; border: 1px solid #475569; background: #0f172a; color: #e2e8f0; font-size: 1rem; }
  #bar button { padding: .5rem 1.2rem; border: none; border-radius: .4rem; background: #2563eb; color: #fff; cursor: pointer; font-size: 1rem; }
</style>
</head>
<body>
<div id="chat"></div>
<div id="bar">
  <input id="inp" placeholder="Ask the AI agent..." autofocus />
  <button onclick="send()">Send</button>
</div>
<script>
const chat = document.getElementById('chat');
const inp  = document.getElementById('inp');
const ws   = new WebSocket(`ws://${location.host}/ws`);

ws.onmessage = (e) => {
  const data = JSON.parse(e.data);
  const div  = document.createElement('div');
  div.className = 'msg event';
  div.innerHTML = `<span class="tag tag-${data.event}">[${data.event}]</span>${data.data || ''}`;
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
};

function send() {
  const text = inp.value.trim();
  if (!text) return;
  const div = document.createElement('div');
  div.className = 'msg user';
  div.textContent = text;
  chat.appendChild(div);
  ws.send(text);
  inp.value = '';
  chat.scrollTop = chat.scrollHeight;
}

inp.addEventListener('keydown', (e) => { if (e.key === 'Enter') send(); });
</script>
</body>
</html>
"""


@app.get("/")
async def index():
    return HTMLResponse(CLIENT_HTML)


# ---------------------------------------------------------------------------
# WebSocket endpoint — simulates an AI agent pipeline
# ---------------------------------------------------------------------------

async def _emit(ws: WebSocket, event: str, data: str = ""):
    await ws.send_text(json.dumps({"event": event, "data": data}))


async def _handle_query(ws: WebSocket, query: str):
    """Simulate a multi-step agent run with real-time status updates."""
    start = time.perf_counter()

    # Step 1 — agent_started
    await _emit(ws, "agent_started", f"Processing: {query}")
    await asyncio.sleep(0.3)

    # Step 2 — tool_calling (simulate a search tool)
    await _emit(ws, "tool_calling", "Running tool: knowledge_search")
    await asyncio.sleep(0.8)

    await _emit(ws, "tool_finished", "knowledge_search returned 3 results")
    await asyncio.sleep(0.2)

    # Step 3 — call LLM for final answer
    await _emit(ws, "tool_calling", "Generating answer with LLM…")

    if ollama_available:
        try:
            async with httpx.AsyncClient(timeout=60) as c:
                r = await c.post(
                    f"{OLLAMA_BASE}/api/generate",
                    json={"model": CHAT_MODEL, "prompt": query, "stream": False},
                )
                r.raise_for_status()
                answer = r.json().get("response", "(empty)")
        except httpx.HTTPError as exc:
            answer = f"[error] Ollama call failed: {exc}"
    else:
        await asyncio.sleep(1)
        answer = f'[mock] The answer to "{query}" is 42.'

    elapsed = round((time.perf_counter() - start) * 1000)
    await _emit(ws, "final_answer", f"{answer}  ({elapsed} ms)")


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            query = await ws.receive_text()
            await _handle_query(ws, query)
    except WebSocketDisconnect:
        pass
