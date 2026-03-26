const connectBtn = document.getElementById("connect");
const recordBtn = document.getElementById("record");
const stopBtn = document.getElementById("stop");
const interruptBtn = document.getElementById("interrupt");
const transcriptEl = document.getElementById("transcript");
const assistantEl = document.getElementById("assistant");
const debugEl = document.getElementById("debug");
const domainEl = document.getElementById("domain");

let socket;
let audioContext;
let sourceNode;
let processor;
let stream;
let sessionId = `session-${crypto.randomUUID()}`;
let turnId = "turn-0";
let sequenceId = 0;

function appendLine(element, text) {
  element.textContent = `${element.textContent}${text}\n`;
  element.scrollTop = element.scrollHeight;
}

function pcmToBase64(float32Array) {
  const buffer = new ArrayBuffer(float32Array.length * 2);
  const view = new DataView(buffer);
  let offset = 0;
  for (let i = 0; i < float32Array.length; i += 1) {
    const sample = Math.max(-1, Math.min(1, float32Array[i]));
    view.setInt16(offset, sample * 0x7fff, true);
    offset += 2;
  }
  const bytes = new Uint8Array(buffer);
  let binary = "";
  bytes.forEach((byte) => {
    binary += String.fromCharCode(byte);
  });
  return btoa(binary);
}

function playAudio(base64Audio, mimeType) {
  const binary = atob(base64Audio);
  const bytes = Uint8Array.from(binary, (char) => char.charCodeAt(0));
  const blob = new Blob([bytes], { type: mimeType || "audio/wav" });
  const audio = new Audio(URL.createObjectURL(blob));
  audio.play().catch(() => {});
}

function sendControl(command, value = "") {
  socket.send(
    JSON.stringify({
      type: "control",
      command,
      value,
      session_id: sessionId,
      turn_id: turnId,
      domain: domainEl.value,
    }),
  );
}

connectBtn.addEventListener("click", async () => {
  socket = new WebSocket(`ws://${window.location.host}/ws/session`);
  socket.onopen = () => {
    appendLine(debugEl, "connected");
    sendControl("set_domain", domainEl.value);
    recordBtn.disabled = false;
    interruptBtn.disabled = false;
  };
  socket.onmessage = (event) => {
    const payload = JSON.parse(event.data);
    if (payload.type === "transcript.partial" || payload.type === "transcript.final") {
      transcriptEl.textContent = payload.text;
    }
    if (payload.type === "llm.token") {
      assistantEl.textContent += payload.text;
    }
    if (payload.type === "llm.final") {
      appendLine(debugEl, "assistant turn complete");
    }
    if (payload.type === "tts.chunk" && payload.audio_b64) {
      playAudio(payload.audio_b64, payload.mime_type);
    }
    if (payload.type === "timing") {
      appendLine(debugEl, `${payload.payload.stage}: ${payload.payload.duration_ms}ms`);
    }
    if (payload.type === "tool.call" || payload.type === "tool.result" || payload.type === "rag.context") {
      appendLine(debugEl, `${payload.type}: ${JSON.stringify(payload.payload)}`);
    }
  };
});

recordBtn.addEventListener("click", async () => {
  if (!socket || socket.readyState !== WebSocket.OPEN) {
    return;
  }
  turnId = `turn-${crypto.randomUUID().slice(0, 8)}`;
  transcriptEl.textContent = "";
  assistantEl.textContent = "";
  audioContext = new AudioContext({ sampleRate: 16000 });
  stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  sourceNode = audioContext.createMediaStreamSource(stream);
  processor = audioContext.createScriptProcessor(4096, 1, 1);
  processor.onaudioprocess = (event) => {
    sequenceId += 1;
    socket.send(
      JSON.stringify({
        type: "audio",
        session_id: sessionId,
        turn_id: turnId,
        domain: domainEl.value,
        sequence_id: sequenceId,
        sample_rate: 16000,
        audio_b64: pcmToBase64(event.inputBuffer.getChannelData(0)),
        end_of_turn: false,
      }),
    );
  };
  sourceNode.connect(processor);
  processor.connect(audioContext.destination);
  recordBtn.disabled = true;
  stopBtn.disabled = false;
});

stopBtn.addEventListener("click", () => {
  if (!socket || socket.readyState !== WebSocket.OPEN) {
    return;
  }
  if (processor) {
    processor.disconnect();
  }
  if (sourceNode) {
    sourceNode.disconnect();
  }
  if (stream) {
    stream.getTracks().forEach((track) => track.stop());
  }
  if (audioContext) {
    audioContext.close();
  }
  socket.send(
    JSON.stringify({
      type: "audio",
      session_id: sessionId,
      turn_id: turnId,
      domain: domainEl.value,
      sample_rate: 16000,
      audio_b64: "",
      end_of_turn: true,
      sequence_id: sequenceId + 1,
    }),
  );
  stopBtn.disabled = true;
  recordBtn.disabled = false;
});

interruptBtn.addEventListener("click", () => {
  if (!socket || socket.readyState !== WebSocket.OPEN) {
    return;
  }
  sendControl("interrupt");
});

