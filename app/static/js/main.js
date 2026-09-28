document.addEventListener("DOMContentLoaded", () => {
  // Mobile sidebar toggle
  const mobileToggle = document.getElementById("mobileToggle");
  const sidebar = document.getElementById("appSidebar");
  if (mobileToggle && sidebar) {
    mobileToggle.addEventListener("click", () => {
      sidebar.classList.toggle("open");
    });
  }

  // Auto-dismiss flash alerts after 5 seconds
  const alerts = document.querySelectorAll(".flash-alert");
  alerts.forEach(alert => {
    setTimeout(() => {
      alert.style.opacity = "0";
      alert.style.transition = "opacity 0.4s ease";
      setTimeout(() => alert.remove(), 400);
    }, 5000);
  });
});

function closeFlash(btn) {
  const alert = btn.closest(".flash-alert");
  if (alert) alert.remove();
}
