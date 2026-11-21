/* The phone header tucks away while you scroll down and slides back as soon
 * as you scroll up, so it costs no screen while reading and is one flick
 * away when you want it.
 *
 * Shared by the store pages and the account pages (the worker loads it from
 * roxzone.app). It only toggles a class on the element marked
 * data-headroom; each stylesheet decides what "tucked" looks like and only
 * does so at phone widths, so on larger screens this is a no-op.
 *
 * Deliberately not tied to requestAnimationFrame: the work per scroll event
 * is a comparison and a class toggle. */
(function () {
  "use strict";
  var bar = document.querySelector("[data-headroom]");
  if (!bar) { return; }

  var phone = window.matchMedia("(max-width: 640px)");
  var THRESHOLD = 8;        // px of travel before we react, so a resting thumb does not flicker it
  var lastY = Math.max(0, window.scrollY);
  var tucked = false;

  function set(state) {
    if (state === tucked) { return; }
    tucked = state;
    bar.classList.toggle("is-tucked", state);
  }

  function onScroll() {
    var y = Math.max(0, window.scrollY);          // iOS reports negative values at the top
    if (!phone.matches) { set(false); lastY = y; return; }
    // Never hide while a menu inside the bar is open.
    if (bar.querySelector(".lang-panel:not([hidden])") || bar.classList.contains("is-menu-open")) { set(false); lastY = y; return; }
    // Near the top the bar is part of the page; always show it.
    if (y <= bar.offsetHeight) { set(false); lastY = y; return; }
    // The rubber-band bounce at the bottom scrolls "up" without the reader
    // asking for anything; ignore it.
    var bottom = document.documentElement.scrollHeight - window.innerHeight;
    if (y >= bottom - 2) { lastY = y; return; }

    var dy = y - lastY;
    if (Math.abs(dy) < THRESHOLD) { return; }
    set(dy > 0);
    lastY = y;
  }

  window.addEventListener("scroll", onScroll, {passive: true});
  // Keyboard users tabbing into the bar must be able to see it.
  bar.addEventListener("focusin", function () { set(false); });
  // Rotating to landscape or resizing past the phone width shows it again.
  phone.addEventListener("change", function () { set(false); lastY = Math.max(0, window.scrollY); closeMenu(); });

  // The store's phone menu: Guide, FAQ and Blog behind one button. The
  // account pages have their own drawer and no .topbar__burger, so this
  // part does nothing there. styles.css shows the list while the bar has
  // .is-menu-open; the scrim takes the tap that closes it.
  var burger = bar.querySelector(".topbar__burger");
  var scrim = null;

  function closeMenu() {
    if (!burger) { return; }
    bar.classList.remove("is-menu-open");
    burger.setAttribute("aria-expanded", "false");
  }

  if (burger) {
    scrim = document.createElement("div");
    scrim.className = "topbar__scrim";
    scrim.setAttribute("aria-hidden", "true");
    bar.appendChild(scrim);

    burger.addEventListener("click", function (event) {
      event.stopPropagation();
      var open = !bar.classList.contains("is-menu-open");
      // One list at a time: opening the menu closes the language list.
      var langButton = bar.querySelector('.lang-button[aria-expanded="true"]');
      if (open && langButton) { langButton.click(); }
      bar.classList.toggle("is-menu-open", open);
      burger.setAttribute("aria-expanded", open ? "true" : "false");
    });
    scrim.addEventListener("click", function (event) { event.stopPropagation(); closeMenu(); });
    document.addEventListener("click", function (event) {
      if (!event.target.closest || !event.target.closest(".topbar__nav")) { closeMenu(); }
    });
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && bar.classList.contains("is-menu-open")) { closeMenu(); burger.focus(); }
    });
    // Back from another page with the menu left open (bfcache): start closed.
    window.addEventListener("pageshow", closeMenu);
  }
})();
