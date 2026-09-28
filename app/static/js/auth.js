document.addEventListener("DOMContentLoaded", () => {
  // Client-side signup validation check
  const signupForm = document.getElementById("signupForm");
  if (signupForm) {
    signupForm.addEventListener("submit", (e) => {
      const pwd = document.getElementById("password")?.value;
      const confirmPwd = document.getElementById("confirm_password")?.value;

      if (pwd && confirmPwd && pwd !== confirmPwd) {
        e.preventDefault();
        alert("Passwords do not match!");
      }
    });
  }
});
