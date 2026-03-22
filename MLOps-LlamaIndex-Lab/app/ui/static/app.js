// =========================================================================
// MLOps-LlamaIndex-Lab — Frontend Logic
// =========================================================================

const API = "";  // same origin

// ── Helpers ─────────────────────────────────────────────────────────────────

function showMsg(text, type) {
    const el = document.getElementById("message");
    el.textContent = text;
    el.className = `show ${type}`;
    setTimeout(() => el.className = "", 6000);
}

function setLoading(btnId, loading) {
    const btn = document.getElementById(btnId);
    btn.disabled = loading;
    const spinner = btn.querySelector(".spinner");
    if (spinner) spinner.style.display = loading ? "inline-block" : "none";
}

// ── Upload ──────────────────────────────────────────────────────────────────

async function uploadFiles() {
    const input = document.getElementById("file-input");
    if (!input.files.length) { showMsg("Select at least one file.", "error"); return; }

    const form = new FormData();
    for (const f of input.files) form.append("files", f);

    setLoading("btn-upload", true);
    try {
        const res = await fetch(`${API}/api/upload`, { method: "POST", body: form });
        const data = await res.json();
        if (data.saved.length) showMsg(`Uploaded: ${data.saved.join(", ")}`, "success");
        if (data.errors.length) showMsg(`Errors: ${JSON.stringify(data.errors)}`, "error");
        input.value = "";
        loadDocuments();
    } catch (e) {
        showMsg(`Upload failed: ${e.message}`, "error");
    } finally {
        setLoading("btn-upload", false);
    }
}

// ── Document List ───────────────────────────────────────────────────────────

async function loadDocuments() {
    try {
        const res = await fetch(`${API}/api/documents`);
        const data = await res.json();
        const list = document.getElementById("doc-list");
        if (!data.documents.length) {
            list.innerHTML = "<li>No documents uploaded yet.</li>";
            return;
        }
        list.innerHTML = data.documents.map(d =>
            `<li><span>${d.name} <small>(${(d.size_bytes / 1024).toFixed(1)} KB)</small></span></li>`
        ).join("");
    } catch (e) {
        console.error("Failed to load documents", e);
    }
}

// ── Ingest ──────────────────────────────────────────────────────────────────

async function runIngest() {
    setLoading("btn-ingest", true);
    try {
        const res = await fetch(`${API}/api/ingest`, { method: "POST" });
        const data = await res.json();
        if (res.ok) {
            showMsg(`Ingested ${data.documents_ingested} document(s) into "${data.collection}".`, "success");
            loadStatus();
        } else {
            showMsg(`Ingestion error: ${data.detail}`, "error");
        }
    } catch (e) {
        showMsg(`Ingestion failed: ${e.message}`, "error");
    } finally {
        setLoading("btn-ingest", false);
    }
}

// ── Query ───────────────────────────────────────────────────────────────────

async function askQuestion() {
    const input = document.getElementById("question-input");
    const question = input.value.trim();
    if (!question) { showMsg("Enter a question first.", "error"); return; }

    setLoading("btn-ask", true);
    document.getElementById("answer-box").textContent = "Thinking…";
    document.getElementById("sources-box").innerHTML = "";

    try {
        const res = await fetch(`${API}/api/query`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question }),
        });
        const data = await res.json();

        if (res.ok) {
            document.getElementById("answer-box").textContent = data.answer;
            const sourcesHtml = data.sources.map(s =>
                `<div class="source-item"><strong>${s.source}</strong> (score: ${s.score})<br>${s.text}</div>`
            ).join("");
            document.getElementById("sources-box").innerHTML = sourcesHtml || "<em>No sources returned.</em>";
        } else {
            document.getElementById("answer-box").textContent = `Error: ${data.detail}`;
        }
    } catch (e) {
        document.getElementById("answer-box").textContent = `Request failed: ${e.message}`;
    } finally {
        setLoading("btn-ask", false);
    }
}

// ── Status ──────────────────────────────────────────────────────────────────

async function loadStatus() {
    try {
        const res = await fetch(`${API}/api/status`);
        const data = await res.json();
        const el = document.getElementById("status-info");
        const reachable = data.qdrant_reachable;
        el.innerHTML = `
            <p>Qdrant: <span class="badge ${reachable ? 'badge-ok' : 'badge-warn'}">${reachable ? 'connected' : 'unreachable'}</span></p>
            ${reachable ? `<p>Vectors: <strong>${data.vectors_count ?? '—'}</strong> | Points: <strong>${data.points_count ?? '—'}</strong></p>` : ''}
            <p>LLM: <strong>${data.llm_provider} / ${data.llm_model}</strong></p>
            <p>Embedding: <strong>${data.embedding_model}</strong></p>
            <p>Chunk: <strong>${data.chunk_size}</strong> / overlap <strong>${data.chunk_overlap}</strong></p>
        `;
    } catch (e) {
        document.getElementById("status-info").innerHTML = "<p>Could not load status.</p>";
    }
}

// ── Init ────────────────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", () => {
    loadDocuments();
    loadStatus();
});
