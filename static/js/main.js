/* Techmiary Technology Concepts — progressive enhancement.
   Nothing here is required for the site to work: navigation, forms and
   content all function with JavaScript disabled. */
(function () {
  "use strict";

  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var canReveal = "IntersectionObserver" in window && !reduceMotion;
  if (canReveal) document.documentElement.classList.add("js");

  /* ---- Sticky header shadow --------------------------------------------- */
  var nav = document.querySelector(".site-nav");
  if (nav) {
    var onScroll = function () { nav.classList.toggle("is-scrolled", window.scrollY > 8); };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
  }

  /* ---- Desktop dropdown / mega menus ------------------------------------ */
  var dropdowns = Array.prototype.slice.call(document.querySelectorAll(".nav-item--has-panel"));

  function closeAll(except) {
    dropdowns.forEach(function (item) {
      if (item === except) return;
      item.classList.remove("is-open");
      var trigger = item.querySelector(".nav-link");
      if (trigger) trigger.setAttribute("aria-expanded", "false");
    });
  }

  dropdowns.forEach(function (item) {
    var trigger = item.querySelector(".nav-link");
    if (!trigger) return;
    var closeTimer;

    function open() {
      window.clearTimeout(closeTimer);
      closeAll(item);
      item.classList.add("is-open");
      trigger.setAttribute("aria-expanded", "true");
    }
    function close(delay) {
      window.clearTimeout(closeTimer);
      closeTimer = window.setTimeout(function () {
        item.classList.remove("is-open");
        trigger.setAttribute("aria-expanded", "false");
      }, delay || 0);
    }

    trigger.addEventListener("click", function (event) {
      event.preventDefault();
      if (item.classList.contains("is-open")) { close(); } else { open(); }
    });
    item.addEventListener("mouseenter", open);
    item.addEventListener("mouseleave", function () { close(140); });
    item.addEventListener("focusin", open);
    item.addEventListener("focusout", function (event) {
      if (!item.contains(event.relatedTarget)) close(0);
    });
  });

  document.addEventListener("click", function (event) {
    if (!event.target.closest(".nav-item--has-panel")) closeAll(null);
  });

  /* ---- Mobile drawer ----------------------------------------------------- */
  var drawer = document.getElementById("site-drawer");
  var backdrop = document.querySelector("[data-backdrop]");
  var openBtn = document.querySelector("[data-drawer-open]");
  var closeBtn = document.querySelector("[data-drawer-close]");

  function setDrawer(open) {
    if (!drawer) return;
    drawer.classList.toggle("is-open", open);
    if (backdrop) backdrop.classList.toggle("is-open", open);
    drawer.setAttribute("aria-hidden", open ? "false" : "true");
    if (openBtn) openBtn.setAttribute("aria-expanded", open ? "true" : "false");
    document.body.style.overflow = open ? "hidden" : "";
    if (open) {
      var focusable = drawer.querySelector("button, a");
      if (focusable) focusable.focus();
    } else if (openBtn) {
      openBtn.focus();
    }
  }

  if (openBtn) openBtn.addEventListener("click", function () { setDrawer(!drawer.classList.contains("is-open")); });
  if (closeBtn) closeBtn.addEventListener("click", function () { setDrawer(false); });
  if (backdrop) backdrop.addEventListener("click", function () { setDrawer(false); });
  document.addEventListener("keydown", function (e) {
    if (e.key !== "Escape") return;
    if (drawer && drawer.classList.contains("is-open")) setDrawer(false);
    closeAll(null);
  });
  if (drawer) {
    drawer.querySelectorAll("a").forEach(function (link) {
      link.addEventListener("click", function () { setDrawer(false); });
    });
  }

  /* ---- Drawer accordions ------------------------------------------------- */
  document.querySelectorAll("[data-drawer-toggle]").forEach(function (button) {
    button.addEventListener("click", function () {
      var section = button.closest(".drawer__section");
      if (!section) return;
      var open = section.classList.toggle("is-open");
      button.setAttribute("aria-expanded", open ? "true" : "false");
    });
  });

  /* ---- Scroll reveal ----------------------------------------------------- */
  var revealables = document.querySelectorAll(".reveal");
  if (revealables.length) {
    if (!canReveal) {
      revealables.forEach(function (el) { el.classList.add("is-visible"); });
    } else {
      var observer = new IntersectionObserver(
        function (entries) {
          entries.forEach(function (entry) {
            if (!entry.isIntersecting) return;
            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
          });
        },
        { rootMargin: "0px 0px -6% 0px", threshold: 0.06 }
      );
      revealables.forEach(function (el) { observer.observe(el); });
    }
  }

})();
