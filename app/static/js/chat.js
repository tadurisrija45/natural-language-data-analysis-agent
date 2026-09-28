document.addEventListener("DOMContentLoaded", () => {
  const chatMessages = document.getElementById("chatMessages");
  const chatForm = document.getElementById("chatForm");
  const questionInput = document.getElementById("questionInput");
  const sendBtn = document.getElementById("sendBtn");
  const analysisId = chatMessages?.dataset?.analysisId;

  // Initialize existing saved charts on page load
  document.querySelectorAll(".chart-canvas").forEach((canvas) => {
    const rawConfig = canvas.dataset.config;
    if (rawConfig) {
      try {
        const config = JSON.parse(rawConfig);
        ChartManager.renderChart(canvas.id, config);
      } catch (e) {
        console.error("Failed to parse chart config:", e);
      }
    }
  });

  // Scroll to bottom
  scrollToBottom();

  if (chatForm) {
    chatForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const question = questionInput.value.trim();
      if (!question) return;

      // 1. Optimistic User Bubble
      appendUserBubble(question);
      questionInput.value = "";
      questionInput.disabled = true;
      sendBtn.disabled = true;
      sendBtn.innerHTML = `<span>Analyzing...</span>`;

      // 2. Loading Placeholder
      const loadingId = appendLoadingIndicator();
      scrollToBottom();

      try {
        const response = await fetch(`/api/analysis/${analysisId}/ask`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question })
        });

        const data = await response.json();
        removeLoadingIndicator(loadingId);

        if (data.success && data.message) {
          appendAgentResponse(data.message);
          // Update header title if updated
          if (data.analysis_title) {
            const titleElem = document.getElementById("analysisSessionTitle");
            if (titleElem) titleElem.textContent = `${data.analysis_icon || "📊"} ${data.analysis_title}`;
          }
        } else {
          appendErrorCard(data.error || "An error occurred while analyzing the question.");
        }
      } catch (err) {
        removeLoadingIndicator(loadingId);
        appendErrorCard("Network error. Please verify server connection and try again.");
      } finally {
        questionInput.disabled = false;
        sendBtn.disabled = false;
        sendBtn.innerHTML = `<span>Send</span>`;
        questionInput.focus();
        scrollToBottom();
      }
    });
  }

  function scrollToBottom() {
    if (chatMessages) {
      chatMessages.scrollTop = chatMessages.scrollHeight;
    }
  }

  function appendUserBubble(text) {
    const row = document.createElement("div");
    row.className = "user-msg-row";
    row.innerHTML = `<div class="user-bubble">${escapeHtml(text)}</div>`;
    chatMessages.appendChild(row);
  }

  function appendLoadingIndicator() {
    const id = "loading_" + Date.now();
    const card = document.createElement("div");
    card.id = id;
    card.className = "agent-response-card";
    card.innerHTML = `
      <div style="display:flex; align-items:center; gap:0.75rem; color:#0F766E;">
        <div style="width:16px; height:16px; border:2px solid #0F766E; border-top-color:transparent; border-radius:50%; animation:spin 1s linear infinite;"></div>
        <span style="font-size:0.9375rem; font-weight:500;">Executing verified analysis on dataset...</span>
      </div>
      <style>@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }</style>
    `;
    chatMessages.appendChild(card);
    return id;
  }

  function removeLoadingIndicator(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
  }

  function appendErrorCard(errText) {
    const card = document.createElement("div");
    card.className = "agent-response-card";
    card.innerHTML = `
      <div style="color:#DC2626; font-weight:600; font-size:1rem;">⚠️ Analysis Notice</div>
      <div style="color:#64748B; font-size:0.875rem;">${escapeHtml(errText)}</div>
    `;
    chatMessages.appendChild(card);
  }

  function appendAgentResponse(msg) {
    const card = document.createElement("div");
    card.className = "agent-response-card";

    const chartCanvasId = `chart_${msg.id || Date.now()}`;
    const hasChart = msg.chart_info && msg.chart_info.data;

    let breakdownHtml = "";
    if (msg.evidence && msg.evidence.breakdown) {
      breakdownHtml = msg.evidence.breakdown.map(b => `
        <div class="evidence-breakdown-item">
          <span style="font-weight:600; color:#0F172A;">${escapeHtml(b.entity)}</span>
          <span style="color:#0F766E; font-weight:700;">${escapeHtml(b.formatted_value)}</span>
        </div>
      `).join("");
    }

    let validationHtml = "";
    if (Array.isArray(msg.validation)) {
      validationHtml = msg.validation.map(v => `
        <li class="validation-item">
          <span style="color:${v.passed ? '#16A34A' : '#DC2626'}; font-weight:700;">${v.passed ? '✓' : '✗'}</span>
          <span><b>${escapeHtml(v.check)}</b>: ${escapeHtml(v.detail)}</span>
        </li>
      `).join("");
    }

    card.innerHTML = `
      <div class="agent-answer-hero">
        ${escapeHtml(msg.answer)}
      </div>

      ${hasChart ? `
        <div class="chart-wrapper">
          <canvas id="${chartCanvasId}"></canvas>
        </div>
      ` : ""}

      <!-- Traceable Evidence -->
      <div class="evidence-card">
        <div class="evidence-header">
          <div class="evidence-title">Traceable Evidence</div>
          <button class="btn btn-secondary btn-sm" onclick="openSourceDataModal(${msg.id})">
            🔍 View Source Data
          </button>
        </div>
        <div style="font-size:0.8125rem; color:#64748B; margin-bottom:0.75rem;">
          Source: <b>${escapeHtml(msg.evidence?.source_dataset || "Uploaded dataset")}</b> &nbsp;&bull;&nbsp; 
          Rows analyzed: <b>${msg.evidence?.rows_analyzed || 0}</b>
        </div>
        <div class="evidence-breakdown-list">
          ${breakdownHtml}
        </div>
      </div>

      <!-- Proof -->
      ${msg.proof ? `
        <div>
          <div style="font-size:0.75rem; font-weight:700; text-transform:uppercase; letter-spacing:0.05em; color:#64748B; margin-bottom:0.375rem;">
            Mathematical Proof
          </div>
          <div class="proof-card">${escapeHtml(msg.proof)}</div>
        </div>
      ` : ""}

      <!-- Validation -->
      <div class="validation-card">
        <div style="font-size:0.8125rem; font-weight:700; color:#166534; margin-bottom:0.5rem; text-transform:uppercase; letter-spacing:0.05em;">
          Verification & Validation
        </div>
        <ul class="validation-list">
          ${validationHtml}
        </ul>
      </div>

      <!-- Insight -->
      ${msg.insight ? `
        <div class="insight-card">
          <span style="font-size:1.25rem;">💡</span>
          <div>
            <div style="font-weight:700; font-size:0.8125rem; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:0.25rem;">
              Executive Insight
            </div>
            <div>${escapeHtml(msg.insight)}</div>
          </div>
        </div>
      ` : ""}
    `;

    chatMessages.appendChild(card);

    if (hasChart) {
      setTimeout(() => {
        ChartManager.renderChart(chartCanvasId, msg.chart_info);
      }, 50);
    }
  }

  function escapeHtml(text) {
    if (!text) return "";
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }
});

// Global Source Data Modal Function
async function openSourceDataModal(messageId) {
  const modal = document.getElementById("sourceDataModal");
  const modalContent = document.getElementById("sourceDataContent");
  if (!modal || !modalContent) return;

  modal.classList.add("open");
  modalContent.innerHTML = `<div style="text-align:center; padding:2rem; color:#64748B;">Loading verified source rows...</div>`;

  try {
    const res = await fetch(`/api/message/${messageId}/source-data`);
    const data = await res.json();

    if (data.success && data.records && data.records.length > 0) {
      const cols = data.columns || Object.keys(data.records[0]);
      let thead = cols.map(c => `<th style="padding:8px 12px; background:#F8FAFC; border:1px solid #E2E8F0; font-size:0.8125rem; text-align:left;">${c}</th>`).join("");
      let tbody = data.records.map(r => {
        let cells = cols.map(c => `<td style="padding:8px 12px; border:1px solid #E2E8F0; font-size:0.8125rem;">${r[c] !== undefined ? r[c] : ''}</td>`).join("");
        return `<tr>${cells}</tr>`;
      }).join("");

      modalContent.innerHTML = `
        <div style="margin-bottom:1rem; font-size:0.875rem; color:#64748B;">
          Dataset: <b>${data.source_dataset}</b> &nbsp;&bull;&nbsp; Total rows analyzed: <b>${data.rows_analyzed}</b>
        </div>
        <div style="overflow-x:auto;">
          <table style="width:100%; border-collapse:collapse;">
            <thead><tr>${thead}</tr></thead>
            <tbody>${tbody}</tbody>
          </table>
        </div>
      `;
    } else {
      modalContent.innerHTML = `<div style="text-align:center; padding:2rem; color:#64748B;">No source records to display.</div>`;
    }
  } catch (e) {
    modalContent.innerHTML = `<div style="color:#DC2626; padding:1.5rem;">Failed to load source data.</div>`;
  }
}

function closeSourceDataModal() {
  const modal = document.getElementById("sourceDataModal");
  if (modal) modal.classList.remove("open");
}
