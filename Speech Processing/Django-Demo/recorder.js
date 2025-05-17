let mediaRecorder, audioChunks = [];
const recordBtn = document.getElementById('recordBtn');
const stopBtn = document.getElementById('stopBtn');

recordBtn.onclick = async () => {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  mediaRecorder = new MediaRecorder(stream);
  mediaRecorder.start();
  audioChunks = [];

  mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
  mediaRecorder.onstart = () => {
    recordBtn.disabled = true;
    stopBtn.disabled = false;
  };
  mediaRecorder.onstop = sendAudio;
};

stopBtn.onclick = () => {
  mediaRecorder.stop();
  recordBtn.disabled = false;
  stopBtn.disabled = true;
};

async function sendAudio() {
  const blob = new Blob(audioChunks, { type: 'audio/webm' });
  const form = new FormData();
  form.append('audio', blob, 'input.webm');

  const res = await fetch('/process_audio/', {
    method: 'POST',
    body: form,
  });
  const data = await res.json();
  document.getElementById('transcript').textContent = data.transcript;
  document.getElementById('answer').textContent = data.answer;

  // play TTS
  const audioEl = document.getElementById('player');
  audioEl.src = 'data:audio/wav;base64,' + data.tts_audio;
  audioEl.play();
}
