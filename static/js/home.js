/**
 * Operational homepage — SVG morph (various shapes → content box) via Flubber + GSAP.
 * Triggers only when card is fully in view; respects prefers-reduced-motion.
 */
(function () {
  "use strict";

  var R = 24;

  function roundedRectPath(w, h) {
    var r = Math.min(R, w / 4, h / 4);
    return (
      "M " +
      r +
      ",0 L " +
      (w - r) +
      ",0 Q " +
      w +
      ",0 " +
      w +
      "," +
      r +
      " L " +
      w +
      "," +
      (h - r) +
      " Q " +
      w +
      "," +
      h +
      " " +
      (w - r) +
      "," +
      h +
      " L " +
      r +
      "," +
      h +
      " Q 0," +
      h +
      " 0," +
      (h - r) +
      " L 0," +
      r +
      " Q 0,0 " +
      r +
      ",0 Z"
    );
  }

  function circlePath(w, h) {
    var cx = w / 2;
    var cy = h / 2;
    var r = Math.min(w, h) / 2 - 8;
    return (
      "M " +
      (cx + r) +
      "," +
      cy +
      " A " +
      r +
      "," +
      r +
      " 0 0 1 " +
      (cx - r) +
      "," +
      cy +
      " A " +
      r +
      "," +
      r +
      " 0 0 1 " +
      (cx + r) +
      "," +
      cy +
      " Z"
    );
  }

  function squarePath(w, h) {
    var m = 10;
    return "M " + m + "," + m + " L " + (w - m) + "," + m + " L " + (w - m) + "," + (h - m) + " L " + m + "," + (h - m) + " Z";
  }

  function trianglePath(w, h) {
    return "M " + w / 2 + ",12 L " + (w - 12) + "," + (h - 12) + " L 12," + (h - 12) + " Z";
  }

  function blobPath(w, h) {
    return (
      "M " + w * 0.5 + "," + h * 0.08 +
      " C " + w * 0.68 + "," + h * 0.05 + " " + w * 0.92 + "," + h * 0.2 + " " + w * 0.92 + "," + h * 0.43 +
      " C " + w * 0.96 + "," + h * 0.64 + " " + w * 0.89 + "," + h * 0.84 + " " + w * 0.76 + "," + h * 0.93 +
      " C " + w * 0.6 + "," + h * 1.01 + " " + w * 0.39 + "," + h * 0.99 + " " + w * 0.25 + "," + h * 0.85 +
      " C " + w * 0.06 + "," + h * 0.74 + " " + w * 0.06 + "," + h * 0.49 + " " + w * 0.07 + "," + h * 0.26 +
      " C " + w * 0.08 + "," + h * 0.07 + " " + w * 0.38 + "," + h * 0.07 + " " + w * 0.5 + "," + h * 0.08 +
      " Z"
    );
  }

  function getStartPath(shape, w, h) {
    switch (shape) {
      case "circle":
        return circlePath(w, h);
      case "square":
        return squarePath(w, h);
      case "triangle":
        return trianglePath(w, h);
      case "blob":
      default:
        return blobPath(w, h);
    }
  }

  function parseViewBox(svg) {
    var vb = svg.getAttribute("viewBox");
    if (!vb) return { w: 380, h: 220 };
    var parts = vb.split(/\s+/);
    return {
      w: parseInt(parts[2], 10) || 380,
      h: parseInt(parts[3], 10) || 220,
    };
  }

  function runMorphs() {
    if (typeof flubber === "undefined" || typeof gsap === "undefined") return;

    var cards = document.querySelectorAll(".card-morph");
    var reducedMotion =
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    var duration = reducedMotion ? 0 : 0.9;

    cards.forEach(function (card) {
      var path = card.querySelector(".card-morph__path");
      var svg = card.querySelector(".card-morph__svg");
      if (!path || !svg) return;

      var shape = (card.getAttribute("data-shape") || "blob").toLowerCase();
      var box = parseViewBox(svg);
      var w = box.w;
      var h = box.h;

      var startPath = getStartPath(shape, w, h);
      var endPath = roundedRectPath(w, h);
      var interpolator = flubber.interpolate(startPath, endPath);

      /* Trigger only when the entire card is in the viewport */
      var observer = new IntersectionObserver(
        function (entries) {
          entries.forEach(function (entry) {
            if (!entry.isIntersecting) return;
            observer.unobserve(entry.target);
            var el = entry.target;
            if (el.dataset.morphed === "true") return;
            el.dataset.morphed = "true";

            if (duration === 0) {
              path.setAttribute("d", endPath);
              el.classList.add("is-morphed");
              return;
            }

            var obj = { t: 0 };
            gsap.to(obj, {
              t: 1,
              duration: duration,
              ease: "power2.out",
              onUpdate: function () {
                path.setAttribute("d", interpolator(obj.t));
              },
              onComplete: function () {
                path.setAttribute("d", endPath);
                el.classList.add("is-morphed");
              },
            });
          });
        },
        { rootMargin: "0px", threshold: 0.99 }
      );

      observer.observe(card);
    });
  }

  var SCROLL_THRESHOLD = 80;

  function setupHeaderScroll() {
    var header = document.querySelector(".page-header");
    if (!header) return;

    function onScroll() {
      if (window.scrollY > SCROLL_THRESHOLD) {
        header.classList.add("page-header--scrolled");
      } else {
        header.classList.remove("page-header--scrolled");
      }
    }

    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
  }

  function init() {
    document.documentElement.classList.remove("no-js");
    document.documentElement.classList.add("js");
    setupHeaderScroll();
    runMorphs();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
