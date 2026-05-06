(function () {
  "use strict";

  var SCROLL_THRESHOLD = 24;

  function setupHeaderScroll() {
    var header = document.getElementById("site-header");
    if (!header) return;
    var shell = header.querySelector(".header-shell");
    if (!shell) return;

    function onScroll() {
      if (window.scrollY > SCROLL_THRESHOLD) {
        shell.classList.add(
          "bg-white/90",
          "border-slate-200",
          "shadow-lg",
          "backdrop-blur"
        );
      } else {
        shell.classList.remove(
          "bg-white/90",
          "border-slate-200",
          "shadow-lg",
          "backdrop-blur"
        );
      }
    }

    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
  }

  function init() {
    setupHeaderScroll();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
