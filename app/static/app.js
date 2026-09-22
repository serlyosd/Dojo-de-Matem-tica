const $ = (selector) => document.querySelector(selector);
let currentDraft = null;
let audioBlob = null;
let mediaRecorder = null;
let mediaStream = null;

function busy(active) { $("#busy").hidden = !active; }
function error(message) {
  const toast = $("#toast");
  toast.textContent = message;
  toast.hidden = false;
  setTimeout(() => { toast.hidden = true; }, 7000);
}

function actionRequired(message) {
  // O clique no botão permite ao navegador tocar este aviso sem depender de arquivos externos.
  try {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    const context = new AudioContext();
    const oscillator = context.createOscillator();
    const gain = context.createGain();
    oscillator.frequency.value = 880;
    gain.gain.setValueAtTime(0.12, context.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, context.currentTime + 0.25);
    oscillator.connect(gain).connect(context.destination);
    oscillator.addEventListener("ended", () => context.close());
    oscillator.start();
    oscillator.stop(context.currentTime + 0.25);
  } catch {
    // A instrução visual continua disponível se o navegador bloquear o som.
  }
  $("#mic-state").textContent = message;
}

async function request(url, options = {}) {
  busy(true);
  try {
    const response = await fetch(url, options);
    let data;
    try { data = await response.json(); } catch { data = {}; }
    if (!response.ok) throw new Error(data.detail || "O aplicativo não conseguiu concluir esta ação.");
    return data;
  } finally { busy(false); }
}

function showConfirmation(data) {
  currentDraft = data.draft_id;
  $("#confirmed-reading").value = data.reading;
  $("#confirmation").hidden = false;
  $("#result").hidden = true;
  $("#confirmation").scrollIntoView({ behavior: "smooth" });
  $("#confirmed-reading").focus();
}

document.querySelectorAll(".tab").forEach((tab) => tab.addEventListener("click", () => {
  document.querySelectorAll(".tab").forEach((item) => {
    const active = item === tab;
    item.classList.toggle("active", active);
    item.setAttribute("aria-selected", String(active));
  });
  document.querySelectorAll(".input-panel").forEach((panel) => {
    const active = panel.id === tab.dataset.panel;
    panel.hidden = !active;
    panel.classList.toggle("active", active);
  });
}));

$("#send-text").addEventListener("click", async () => {
  const text = $("#text-answer").value.trim();
  if (!text) return error("Digite uma resposta antes de continuar.");
  try {
    showConfirmation(await request("/api/drafts/text", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text })
    }));
  } catch (reason) { error(reason.message); }
});

$("#photo-input").addEventListener("change", () => {
  const file = $("#photo-input").files[0];
  $("#send-photo").disabled = !file;
  if (file) {
    $("#photo-preview").src = URL.createObjectURL(file);
    $("#photo-preview").hidden = false;
  }
});

$("#send-photo").addEventListener("click", async () => {
  const file = $("#photo-input").files[0];
  if (!file) return;
  const form = new FormData(); form.append("file", file);
  try { showConfirmation(await request("/api/drafts/photo", { method: "POST", body: form })); }
  catch (reason) { error(reason.message); }
});

async function microphonePermission() {
  if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
    throw new Error("Este navegador não oferece a gravação necessária. Use Edge, Chrome ou Firefox atualizado.");
  }
  if (navigator.permissions?.query) {
    try {
      const permission = await navigator.permissions.query({ name: "microphone" });
      if (permission.state === "denied") throw new Error("O microfone está bloqueado. Libere a permissão nas configurações do navegador.");
    } catch (reason) {
      if (reason.message?.includes("bloqueado")) throw reason;
      // Alguns navegadores não expõem a consulta de microfone; getUserMedia ainda confirma a permissão.
    }
  }
  actionRequired("Ação necessária: clique em Permitir para liberar o microfone.");
  mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
  $("#mic-state").textContent = "Microfone permitido e pronto. Grave uma explicação curta.";
  $("#record").disabled = false;
}

$("#check-mic").addEventListener("click", async () => {
  try { await microphonePermission(); }
  catch (reason) {
    $("#mic-state").textContent = "Microfone indisponível ou sem permissão.";
    error(reason.name === "NotAllowedError" ? "Permissão recusada. Clique no cadeado do navegador e permita o microfone." : reason.message);
  }
});

$("#record").addEventListener("click", async () => {
  if (mediaRecorder?.state === "recording") { mediaRecorder.stop(); return; }
  if (!mediaStream) {
    try { await microphonePermission(); } catch (reason) { return error(reason.message); }
  }
  const preferred = ["audio/webm;codecs=opus", "audio/ogg;codecs=opus", "audio/mp4"]
    .find((type) => MediaRecorder.isTypeSupported(type));
  const chunks = [];
  mediaRecorder = preferred ? new MediaRecorder(mediaStream, { mimeType: preferred }) : new MediaRecorder(mediaStream);
  mediaRecorder.addEventListener("dataavailable", (event) => { if (event.data.size) chunks.push(event.data); });
  mediaRecorder.addEventListener("stop", () => {
    audioBlob = new Blob(chunks, { type: mediaRecorder.mimeType || "audio/webm" });
    $("#audio-preview").src = URL.createObjectURL(audioBlob);
    $("#audio-preview").hidden = false;
    $("#send-audio").disabled = false;
    $("#record").textContent = "● Gravar novamente";
    $("#record").classList.remove("recording");
    $("#mic-state").textContent = "Gravação pronta. Ouça antes de transcrever.";
  });
  mediaRecorder.start();
  $("#record").textContent = "■ Parar gravação";
  $("#record").classList.add("recording");
  $("#mic-state").textContent = "Gravando… fale perto do microfone.";
});

$("#send-audio").addEventListener("click", async () => {
  if (!audioBlob) return;
  const extension = audioBlob.type.includes("ogg") ? "ogg" : audioBlob.type.includes("mp4") ? "m4a" : "webm";
  const form = new FormData(); form.append("file", audioBlob, `gravacao.${extension}`);
  try { showConfirmation(await request("/api/drafts/audio", { method: "POST", body: form })); }
  catch (reason) { error(reason.message); }
});

$("#confirm-analysis").addEventListener("click", async () => {
  const correctedText = $("#confirmed-reading").value.trim();
  if (!correctedText) return error("A leitura confirmada não pode ficar vazia.");
  try {
    const data = await request("/api/analyze", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ draft_id: currentDraft, corrected_text: correctedText })
    });
    $("#analysis-text").textContent = data.analysis;
    $("#result").hidden = false;
    $("#result").scrollIntoView({ behavior: "smooth" });
  } catch (reason) { error(reason.message); }
});

$("#restart").addEventListener("click", () => {
  currentDraft = null; $("#confirmation").hidden = true; $("#result").hidden = true;
  window.scrollTo({ top: 0, behavior: "smooth" });
});

$("#status-button").addEventListener("click", async () => {
  $("#status-dialog").showModal();
  try {
    const data = await request("/api/status");
    const list = $("#status-list");
    list.replaceChildren();
    Object.entries(data).forEach(([name, item]) => {
      const component = document.createElement("div");
      component.className = `component ${item.ready ? "ready" : "missing"}`;
      const title = document.createElement("strong");
      title.textContent = name;
      component.append(title, document.createElement("br"), document.createTextNode(item.message));
      list.append(component);
    });
  } catch (reason) { error(reason.message); }
});
$("#close-status").addEventListener("click", () => $("#status-dialog").close());
window.addEventListener("beforeunload", () => mediaStream?.getTracks().forEach((track) => track.stop()));
