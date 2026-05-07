"""GraphQL AI Inference + Knowledge Graph — main app.

Mounts:
- POST /graphql       — GraphQL HTTP endpoint
- GET  /graphql       — GraphiQL UI
- WS   /graphql       — Subscriptions (graphql-transport-ws + graphql-ws)
- GET  /              — Hand-rolled HTML client (query + WS subscription)
- GET  /health        — Plain liveness for orchestrators / Docker healthchecks
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from strawberry.fastapi import GraphQLRouter
from strawberry.subscriptions import (
    GRAPHQL_TRANSPORT_WS_PROTOCOL,
    GRAPHQL_WS_PROTOCOL,
)

import ollama
from resolvers import make_loaders, schema


@asynccontextmanager
async def lifespan(app: FastAPI):
    available = await ollama.probe()
    print(f"[graphql] Ollama {'connected' if available else 'mock mode'}")
    yield


async def get_context() -> dict:
    """Per-request context — DataLoaders are scoped here so batching works."""
    return make_loaders()


app = FastAPI(title="GraphQL AI Lab", lifespan=lifespan)

graphql_app = GraphQLRouter(
    schema,
    context_getter=get_context,
    subscription_protocols=[
        GRAPHQL_TRANSPORT_WS_PROTOCOL,
        GRAPHQL_WS_PROTOCOL,
    ],
)
app.include_router(graphql_app, prefix="/graphql")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "ollama": ollama.is_available()}


CLIENT_HTML = """\
<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"><title>GraphQL AI Lab</title>
<style>
  body { font-family: system-ui, sans-serif; background: #0f172a; color: #e2e8f0; padding: 2rem; max-width: 900px; margin: auto; line-height: 1.5; }
  h1 { font-size: 1.4rem; margin-bottom: .8rem; }
  h2 { font-size: 1.05rem; margin: 1.2rem 0 .4rem; color: #93c5fd; }
  textarea, input { width: 100%; padding: .5rem; border-radius: .4rem; border: 1px solid #475569; background: #1e293b; color: #e2e8f0; font-family: monospace; font-size: .9rem; }
  textarea { height: 110px; resize: vertical; }
  button { margin-top: .4rem; padding: .5rem 1.2rem; border: none; border-radius: .4rem; background: #2563eb; color: #fff; cursor: pointer; }
  pre { background: #1e293b; padding: .8rem; border-radius: .4rem; white-space: pre-wrap; max-height: 320px; overflow-y: auto; font-size: .85rem; }
  .links a { color: #60a5fa; margin-right: 1rem; }
</style></head>
<body>
<h1>GraphQL AI Lab &mdash; 08</h1>
<p class="links">
  <a href="/graphql">GraphiQL UI &rarr;</a>
  <a href="/health">/health &rarr;</a>
</p>

<h2>1. HTTP query (POST /graphql)</h2>
<textarea id="q">{ health { status ollamaConnected chatModel embedModel } models { id name provider ... on ChatModel { contextWindow supportsStreaming } ... on EmbeddingModel { dimensions } } }</textarea>
<button onclick="runQuery()">Run query</button>
<pre id="qOut"></pre>

<h2>2. Subscription (WebSocket &mdash; graphql-transport-ws)</h2>
<input id="msg" value="Explain embeddings in one sentence."/>
<button onclick="runSub()">Stream tokens</button>
<pre id="subOut"></pre>

<script>
async function runQuery() {
  const q = document.getElementById('q').value;
  const out = document.getElementById('qOut');
  out.textContent = 'Running...';
  const r = await fetch('/graphql', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({query: q}),
  });
  out.textContent = JSON.stringify(await r.json(), null, 2);
}

function runSub() {
  const msg = document.getElementById('msg').value;
  const out = document.getElementById('subOut');
  out.textContent = '';
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  const ws = new WebSocket(proto + '://' + location.host + '/graphql', 'graphql-transport-ws');
  ws.onopen = () => ws.send(JSON.stringify({type: 'connection_init'}));
  ws.onmessage = (e) => {
    const m = JSON.parse(e.data);
    if (m.type === 'connection_ack') {
      ws.send(JSON.stringify({
        id: '1',
        type: 'subscribe',
        payload: {
          query: 'subscription($m: String!) { tokenStream(conversationId: "c1", message: $m) { token done } }',
          variables: {m: msg},
        },
      }));
    } else if (m.type === 'next') {
      const ev = m.payload.data.tokenStream;
      out.textContent += ev.token;
      if (ev.done) ws.close();
    } else if (m.type === 'error') {
      out.textContent += '\\n[error] ' + JSON.stringify(m.payload);
      ws.close();
    } else if (m.type === 'complete') {
      ws.close();
    }
  };
  ws.onerror = () => { out.textContent += '\\n[ws error]'; };
}
</script>
</body></html>
"""


@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    return CLIENT_HTML
