document.addEventListener("DOMContentLoaded", () => {
  const dropZone = document.getElementById("dropZone");
  const fileInput = document.getElementById("fileInput");
  const filePreviewList = document.getElementById("filePreviewList");
  const startBtn = document.getElementById("startAnalysisBtn");

  if (!dropZone || !fileInput) return;

  dropZone.addEventListener("click", () => fileInput.click());

  dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("dragover");
  });

  dropZone.addEventListener("dragleave", () => {
    dropZone.classList.remove("dragover");
  });

  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("dragover");
    if (e.dataTransfer.files.length > 0) {
      fileInput.files = e.dataTransfer.files;
      renderFileList(fileInput.files);
    }
  });

  fileInput.addEventListener("change", () => {
    renderFileList(fileInput.files);
  });

  function formatBytes(bytes) {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
  }

  function renderFileList(files) {
    filePreviewList.innerHTML = "";
    if (files.length === 0) {
      startBtn.disabled = true;
      return;
    }

    startBtn.disabled = false;
    const now = new Date();
    const dateStr = now.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
    const timeStr = now.toLocaleTimeString("en-US", { hour: "numeric", minute: "numeric", hour12: true });

    Array.from(files).forEach((file) => {
      const ext = file.name.split(".").pop().toUpperCase();
      const item = document.createElement("div");
      item.className = "file-preview-item";
      item.innerHTML = `
        <div style="display:flex; align-items:center; gap:0.75rem;">
          <span style="color:#0F766E; font-weight:700;">✓</span>
          <div>
            <div style="font-weight:600; color:#0F172A;">${file.name}</div>
            <div style="font-size:0.75rem; color:#64748B;">
              ${ext} &bull; ${dateStr}, ${timeStr}
            </div>
          </div>
        </div>
        <div style="font-weight:500; font-size:0.8125rem; color:#64748B;">
          ${formatBytes(file.size)}
        </div>
      `;
      filePreviewList.appendChild(item);
    });
  }
});
