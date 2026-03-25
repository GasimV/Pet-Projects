"""
SSE Token Streaming — Server-Sent Events demo

Client sends a prompt via POST; the server streams tokens back as SSE events.
Uses Ollama streaming when available, otherwise simulates token-by-token output.
"""

import asyncio
import json

import httpx
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

OLLAMA_BASE = "http://localhost:11434"
CHAT_MODEL = "gemma3:1b"

app = FastAPI(title="SSE Token Streaming")

ollama_available = False


@app.on_event("startup")
async def _probe():
    global ollama_available
    try:
        async with httpx.AsyncClient(timeout=3) as c:
            r = await c.get(f"{OLLAMA_BASE}/api/tags")
            ollama_available = r.status_code == 200
    except httpx.ConnectError:
        pass
    print(f"[sse] Ollama {'connected' if ollama_available else 'mock mode'}")


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class PromptRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4096)


# ---------------------------------------------------------------------------
# SSE streaming endpoint
# ---------------------------------------------------------------------------
async def _token_generator(prompt: str):
    """Yield SSE-formatted token events."""
    if ollama_available:
        async with httpx.AsyncClient(timeout=120) as c:
            async with c.stream(
                "POST",
                f"{OLLAMA_BASE}/api/generate",
                json={"model": CHAT_MODEL, "prompt": prompt, "stream": True},
            ) as resp:
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    chunk = json.loads(line)
                    token = chunk.get("response", "")
                    if token:
                        yield {"event": "token", "data": token}
                    if chunk.get("done"):
                        break
    else:
        # Mock: emit a sentence word-by-word
        words = f"This is a mock streamed response to your prompt: {prompt}".split()
        for w in words:
            yield {"event": "token", "data": w + " "}
            await asyncio.sleep(0.08)

    yield {"event": "done", "data": "[DONE]"}


@app.post("/stream")
async def stream(req: PromptRequest):
    return EventSourceResponse(_token_generator(req.prompt))


# ---------------------------------------------------------------------------
# Browser client
# ---------------------------------------------------------------------------
CLIENT_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SSE Token Streaming</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: system-ui, sans-serif; background: #0f172a; color: #e2e8f0; padding: 2rem; max-width: 700px; margin: auto; }
  h1 { margin-bottom: 1rem; font-size: 1.4rem; }
  textarea { width: 100%; height: 80px; padding: .6rem; border-radius: .4rem; border: 1px solid #475569; background: #1e293b; color: #e2e8f0; font-size: 1rem; resize: vertical; }
  button { margin-top: .5rem; padding: .5rem 1.2rem; border: none; border-radius: .4rem; background: #2563eb; color: #fff; cursor: pointer; font-size: 1rem; }
  #output { margin-top: 1.5rem; padding: 1rem; background: #1e293b; border-radius: .5rem; min-height: 60px; white-space: pre-wrap; line-height: 1.6; }
</style>
</head>
<body>
<h1>SSE Token Streaming</h1>
<textarea id="prompt" placeholder="Enter a prompt…">Explain what embeddings are in two sentences.</textarea>
<button onclick="run()">Generate</button>
<div id="output"></div>
<script>
async function run() {
  const out = document.getElementById('output');
  const prompt = document.getElementById('prompt').value;
  out.textContent = '';

  const resp = await fetch('/stream', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({prompt})
  });

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buf = '';

  while (true) {
    const {done, value} = await reader.read();
    if (done) break;
    buf += decoder.decode(value, {stream: true});
    const lines = buf.split('\\n');
    buf = lines.pop();
    for (const line of lines) {
      if (line.startsWith('data:')) {
        const data = line.slice(5).trim();
        if (data === '[DONE]') return;
        out.textContent += data;
      }
    }
  }
}
</script>
</body>
</html>
"""


@app.get("/")
async def index():
    return HTMLResponse(CLIENT_HTML)
