document.addEventListener("DOMContentLoaded", () => {
  const searchInput = document.getElementById("historySearchInput");
  const searchForm = document.getElementById("historySearchForm");

  if (searchInput && searchForm) {
    let timeout = null;
    searchInput.addEventListener("input", () => {
      clearTimeout(timeout);
      timeout = setTimeout(() => {
        searchForm.submit();
      }, 500);
    });
  }
});
