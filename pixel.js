/* Meta pixel with consent.
 *
 * Runs only on these public store pages - never on the signed-in account
 * pages at /me and never inside the watch app. What it reports: page views,
 * a checkout being started, and a completed purchase. No email, no results,
 * no watch data.
 *
 * Consent: visitors in the EU, EEA, UK and Switzerland see a banner and the
 * pixel stays off until they allow it. Everyone else gets the pixel by default
 * with the same banner offering to turn it off. The choice is kept in
 * localStorage (rz_consent = "granted" | "denied") and can be changed from
 * the privacy policy. Set EU_ONLY_GATE to false to ask everyone.
 *
 * With PIXEL_ID empty this file does nothing at all, so it is safe to ship
 * before the id exists. */
(function () {
  "use strict";
  var PIXEL_ID = "";            // paste the Meta pixel id here
  var EU_ONLY_GATE = true;
  var KEY = "rz_consent";

  if (!PIXEL_ID) { return; }

  function stored() {
    try { return localStorage.getItem(KEY); } catch (e) { return null; }
  }
  function remember(v) {
    try { localStorage.setItem(KEY, v); } catch (e) {}
  }
  function needsConsentFirst() {
    // ?consent=eu forces the banner for testing.
    if (/[?&]consent=eu\b/.test(location.search)) { return true; }
    if (!EU_ONLY_GATE) { return true; }
    var tz = "";
    try { tz = Intl.DateTimeFormat().resolvedOptions().timeZone || ""; } catch (e) {}
    return /^Europe\//.test(tz) ||
      /^Atlantic\/(Reykjavik|Canary|Madeira|Faroe|Azores)$/.test(tz);
  }

  var queue = [];
  var loaded = false;

  function loadPixel() {
    if (loaded) { return; }
    loaded = true;
    /* Meta's standard loader. */
    !function(f,b,e,v,n,t,s){if(f.fbq)return;n=f.fbq=function(){n.callMethod?
    n.callMethod.apply(n,arguments):n.queue.push(arguments)};if(!f._fbq)f._fbq=n;
    n.push=n;n.loaded=!0;n.version='2.0';n.queue=[];t=b.createElement(e);t.async=!0;
    t.src=v;s=b.getElementsByTagName(e)[0];s.parentNode.insertBefore(t,s)}(window,
    document,'script','https://connect.facebook.net/en_US/fbevents.js');
    window.fbq("init", PIXEL_ID);
    window.fbq("track", "PageView");
    for (var i = 0; i < queue.length; i++) { window.fbq.apply(null, queue[i]); }
    queue = [];
  }

  // Pages call this; events wait until the pixel is allowed and loaded, and
  // are dropped if it never is.
  window.rzPixelTrack = function (name, params, opts) {
    var args = opts ? ["track", name, params || {}, opts] : ["track", name, params || {}];
    if (loaded && window.fbq) { window.fbq.apply(null, args); }
    else if (stored() !== "denied") { queue.push(args); }
  };

  // ---- banner ----
  var privacyHref = /\/(userguide|faq|privacy|refund|success|unlock|restore)\//.test(location.pathname)
    ? "../privacy/#advertising" : "./privacy/#advertising";

  function showBanner(mode) {
    if (document.getElementById("rz-consent")) { return; }
    var el = document.createElement("div");
    el.id = "rz-consent";
    el.className = "consent";
    el.setAttribute("role", "dialog");
    el.setAttribute("aria-label", "Cookie choice");
    var text = mode === "ask"
      ? "We'd like to know whether our Instagram ads bring people here. A Meta pixel would count page views, checkouts and purchases on these store pages - nothing from your account or your watch. OK with you?"
      : "So we know whether our Instagram ads work, these store pages count page views, checkouts and purchases with a Meta pixel. Nothing from your account or your watch - and you can switch it off.";
    el.innerHTML =
      '<p class="consent__text">' + text + ' <a href="' + privacyHref + '">Details</a></p>' +
      '<div class="consent__acts">' +
      '<button type="button" class="consent__btn" data-choice="denied">' + (mode === "ask" ? "No thanks" : "Switch off") + '</button>' +
      '<button type="button" class="consent__btn consent__btn--yes" data-choice="granted">' + (mode === "ask" ? "OK" : "Fine by me") + '</button>' +
      '</div>';
    el.addEventListener("click", function (e) {
      var b = e.target.closest("[data-choice]");
      if (!b) { return; }
      var v = b.getAttribute("data-choice");
      remember(v);
      el.remove();
      if (v === "granted") { loadPixel(); }
      else { queue = []; }
    });
    document.body.appendChild(el);
  }

  // The privacy policy's "change your choice" button.
  window.rzConsentOpen = function () {
    try { localStorage.removeItem(KEY); } catch (e) {}
    var old = document.getElementById("rz-consent");
    if (old) { old.remove(); }
    showBanner("ask");
  };

  // Checkout start: every pay button on the store page.
  document.addEventListener("click", function (e) {
    if (e.target.closest(".pay-button")) {
      window.rzPixelTrack("InitiateCheckout", { content_name: "ROXZONE lifetime unlock" });
    }
  }, true);

  function start() {
    var choice = stored();
    if (choice === "granted") { loadPixel(); return; }
    if (choice === "denied") { return; }
    if (needsConsentFirst()) { showBanner("ask"); }
    else { loadPixel(); showBanner("notice"); }
  }
  if (document.readyState === "loading") { document.addEventListener("DOMContentLoaded", start); }
  else { start(); }
})();
