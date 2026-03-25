"""
WebRTC Voice AI — Signaling Server + Audio Pipeline Skeleton

Provides:
1. A WebSocket signaling server for WebRTC peer connection setup
2. A browser UI that captures microphone audio
3. Architecture for connecting to STT → LLM → TTS pipeline

This is a signaling skeleton — full media relay requires a TURN server
and real STT/TTS services. The demo shows the signaling flow and
captures real audio from the browser microphone.
"""

import json

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

app = FastAPI(title="WebRTC Voice AI Signaling")

# Store connected peers for signaling relay
peers: dict[str, WebSocket] = {}

CLIENT_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>WebRTC Voice AI</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: system-ui, sans-serif; background: #0f172a; color: #e2e8f0; display: flex; flex-direction: column; align-items: center; padding: 2rem; }
  h1 { margin-bottom: .5rem; }
  .sub { color: #94a3b8; margin-bottom: 2rem; font-size: .9rem; }
  .panel { background: #1e293b; border-radius: .75rem; padding: 1.5rem; width: 100%; max-width: 600px; margin-bottom: 1rem; }
  .panel h2 { font-size: 1rem; margin-bottom: .75rem; color: #38bdf8; }
  button { padding: .6rem 1.4rem; border: none; border-radius: .4rem; font-size: 1rem; cursor: pointer; margin: .25rem; }
  .btn-start { background: #16a34a; color: #fff; }
  .btn-stop  { background: #dc2626; color: #fff; }
  .btn-send  { background: #2563eb; color: #fff; }
  #log { font-family: monospace; font-size: .82rem; background: #0f172a; padding: .75rem; border-radius: .4rem; max-height: 300px; overflow-y: auto; white-space: pre-wrap; line-height: 1.5; }
  .log-signal { color: #fbbf24; }
  .log-audio  { color: #4ade80; }
  .log-info   { color: #94a3b8; }
  #viz { width: 100%; height: 60px; background: #0f172a; border-radius: .4rem; }
</style>
</head>
<body>
<h1>WebRTC Voice AI</h1>
<p class="sub">Microphone capture + WebRTC signaling skeleton</p>

<div class="panel">
  <h2>Microphone</h2>
  <button class="btn-start" onclick="startMic()">Start Mic</button>
  <button class="btn-stop" onclick="stopMic()">Stop Mic</button>
  <canvas id="viz"></canvas>
</div>

<div class="panel">
  <h2>Signaling</h2>
  <button class="btn-send" onclick="createOffer()">Create Offer (simulate)</button>
  <button class="btn-send" onclick="sendPing()">Ping Server</button>
</div>

<div class="panel">
  <h2>Event Log</h2>
  <div id="log"></div>
</div>

<script>
const log = document.getElementById('log');
const canvas = document.getElementById('viz');
const ctx = canvas.getContext('2d');
let stream = null, audioCtx = null, analyser = null, animId = null;

function addLog(cls, msg) {
  const line = document.createElement('span');
  line.className = 'log-' + cls;
  line.textContent = `[${new Date().toLocaleTimeString()}] ${msg}\\n`;
  log.appendChild(line);
  log.scrollTop = log.scrollHeight;
}

// --- WebSocket signaling ---
const ws = new WebSocket(`ws://${location.host}/signal`);
ws.onopen = () => addLog('signal', 'Signaling channel connected');
ws.onmessage = (e) => {
  const data = JSON.parse(e.data);
  addLog('signal', `Server: ${data.type} — ${data.data || ''}`);
};
ws.onerror = () => addLog('signal', 'WebSocket error');

function sendPing() {
  ws.send(JSON.stringify({type: 'ping'}));
  addLog('signal', 'Sent ping');
}

function createOffer() {
  // Simulate SDP offer creation
  const mockSdp = 'v=0\\r\\no=- 123456 2 IN IP4 127.0.0.1\\r\\ns=-\\r\\n...';
  ws.send(JSON.stringify({type: 'offer', sdp: mockSdp}));
  addLog('signal', 'Sent SDP offer (simulated)');
}

// --- Microphone capture + visualization ---
async function startMic() {
  try {
    stream = await navigator.mediaDevices.getUserMedia({audio: true});
    audioCtx = new AudioContext();
    const source = audioCtx.createMediaStreamSource(stream);
    analyser = audioCtx.createAnalyser();
    analyser.fftSize = 256;
    source.connect(analyser);
    addLog('audio', `Mic active — sampleRate=${audioCtx.sampleRate}`);
    drawViz();
  } catch(e) {
    addLog('info', 'Mic access denied: ' + e.message);
  }
}

function stopMic() {
  if (stream) {
    stream.getTracks().forEach(t => t.stop());
    stream = null;
  }
  if (audioCtx) { audioCtx.close(); audioCtx = null; }
  if (animId) { cancelAnimationFrame(animId); animId = null; }
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  addLog('audio', 'Mic stopped');
}

function drawViz() {
  if (!analyser) return;
  const data = new Uint8Array(analyser.frequencyBinCount);
  canvas.width = canvas.clientWidth;
  canvas.height = canvas.clientHeight;

  function frame() {
    analyser.getByteFrequencyData(data);
    ctx.fillStyle = '#0f172a';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    const barW = canvas.width / data.length;
    for (let i = 0; i < data.length; i++) {
      const h = (data[i] / 255) * canvas.height;
      ctx.fillStyle = `hsl(${200 + i}, 80%, 55%)`;
      ctx.fillRect(i * barW, canvas.height - h, barW - 1, h);
    }
    animId = requestAnimationFrame(frame);
  }
  frame();
}
</script>
</body>
</html>
"""


@app.get("/")
async def index():
    return HTMLResponse(CLIENT_HTML)


@app.websocket("/signal")
async def signaling(ws: WebSocket):
    """
    Minimal signaling server for WebRTC peer connection negotiation.

    In a real voice AI system, this would relay SDP offers/answers and
    ICE candidates between the browser and a media server that connects
    to the STT → LLM → TTS pipeline.
    """
    await ws.accept()
    peer_id = id(ws)
    peers[peer_id] = ws
    print(f"[signal] Peer {peer_id} connected ({len(peers)} total)")

    try:
        while True:
            raw = await ws.receive_text()
            msg = json.loads(raw)
            msg_type = msg.get("type", "unknown")

            if msg_type == "ping":
                await ws.send_text(json.dumps({
                    "type": "pong",
                    "data": f"peers_online={len(peers)}",
                }))

            elif msg_type == "offer":
                # In production: relay to media server, return SDP answer
                print(f"[signal] Received SDP offer from {peer_id}")
                await ws.send_text(json.dumps({
                    "type": "answer",
                    "data": "SDP answer would be generated by media server",
                }))

            elif msg_type == "ice-candidate":
                print(f"[signal] ICE candidate from {peer_id}")
                await ws.send_text(json.dumps({
                    "type": "ice-ack",
                    "data": "ICE candidate received",
                }))

            else:
                await ws.send_text(json.dumps({
                    "type": "error",
                    "data": f"Unknown message type: {msg_type}",
                }))

    except WebSocketDisconnect:
        del peers[peer_id]
        print(f"[signal] Peer {peer_id} disconnected")
