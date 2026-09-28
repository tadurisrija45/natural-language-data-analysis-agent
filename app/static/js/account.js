document.addEventListener("DOMContentLoaded", () => {
  const pwdForm = document.getElementById("changePasswordForm");
  if (pwdForm) {
    pwdForm.addEventListener("submit", (e) => {
      const np = document.getElementById("new_password")?.value;
      const cp = document.getElementById("confirm_password")?.value;
      if (np && cp && np !== cp) {
        e.preventDefault();
        alert("New passwords do not match.");
      }
    });
  }
});
