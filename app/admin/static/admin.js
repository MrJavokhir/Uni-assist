// Uni Assist admin — kichik interaktiv yaxshilanishlar (SQLAdmin ustiga).

(function () {
  "use strict";

  // 1. Ro'yxatdagi qatorni bosish — yozuv tafsilotlariga o'tadi.
  //    Havola/tugma/checkbox bosilganda aralashmaydi.
  function enableRowClick() {
    document.querySelectorAll("table tbody tr").forEach(function (row) {
      var actionsCell = row.querySelector("td.text-end");
      if (!actionsCell) return;

      var detailsLink = actionsCell.querySelector('a[href*="/details/"]');
      if (!detailsLink) return;

      row.dataset.uaHref = detailsLink.getAttribute("href");
      row.addEventListener("click", function (event) {
        if (event.target.closest("a, button, input, label, .dropdown")) return;
        if (window.getSelection && String(window.getSelection())) return;
        window.location.href = row.dataset.uaHref;
      });
    });
  }

  // 2. "/" tugmasi — qidiruv maydoniga fokus (brauzer qidiruvi emas).
  function enableSearchShortcut() {
    var search = document.querySelector('input[name="search"], #search-input, input[type="search"]');
    if (!search) return;

    document.addEventListener("keydown", function (event) {
      if (event.key !== "/" || event.metaKey || event.ctrlKey) return;
      var tag = (document.activeElement && document.activeElement.tagName) || "";
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
      event.preventDefault();
      search.focus();
      search.select();
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    enableRowClick();
    enableSearchShortcut();
  });
})();
