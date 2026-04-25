const LANGUAGES = [
  { code: "en", label: "English" },
  { code: "de", label: "Deutsch" },
  { code: "es", label: "Español" },
  { code: "fr", label: "Français" },
  { code: "it", label: "Italiano" },
  { code: "pl", label: "Polski" },
  { code: "nl", label: "Nederlands" },
  { code: "sv", label: "Svenska" },
  { code: "no", label: "Norsk" },
  { code: "pt-PT", label: "Português (Portugal)" },
  { code: "zh-CN", label: "简体中文" },
  { code: "ko", label: "한국어" },
  { code: "ja", label: "日本語" }
];

const STORAGE_KEY = "roxzone-lang";
const GOOGLE_LANG_CODES = LANGUAGES
  .filter((l) => l.code !== "en")
  .map((l) => l.code);

function getStoredLang() {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored && LANGUAGES.some((l) => l.code === stored)) return stored;
  } catch (e) {
    // localStorage may be blocked; fall through
  }
  return "en";
}

function storeLang(code) {
  try {
    if (code === "en") localStorage.removeItem(STORAGE_KEY);
    else localStorage.setItem(STORAGE_KEY, code);
  } catch (e) {
    // ignore
  }
}

function findGoogleSelect() {
  return document.querySelector("select.goog-te-combo");
}

function waitFor(predicate, timeoutMs) {
  return new Promise((resolve, reject) => {
    const start = Date.now();
    (function check() {
      const value = predicate();
      if (value) return resolve(value);
      if (Date.now() - start > timeoutMs) return reject(new Error("timeout"));
      setTimeout(check, 80);
    })();
  });
}

async function applyLanguage(code) {
  const targetCode = code === "en" ? "" : code;
  let select;
  try {
    select = await waitFor(findGoogleSelect, 8000);
  } catch (err) {
    return;
  }
  if (select.value === targetCode) return;
  select.value = targetCode;
  select.dispatchEvent(new Event("change", { bubbles: true }));
}

function clearGoogleTranslateCookie() {
  const host = window.location.hostname;
  const candidates = ["", host, "." + host];
  if (host && host.includes(".")) {
    candidates.push("." + host.split(".").slice(-2).join("."));
  }
  candidates.forEach((domain) => {
    let cookie = "googtrans=; path=/; max-age=0";
    if (domain) cookie += `; domain=${domain}`;
    document.cookie = cookie;
  });
}

function setLang(code) {
  const previous = getStoredLang();
  storeLang(code);
  updatePickerSelection(code);
  if (code === "en" && previous !== "en") {
    // Google's TranslateElement sets a googtrans cookie on change events,
    // which would auto-re-translate on reload. Clear it before reloading.
    clearGoogleTranslateCookie();
    window.location.reload();
    return;
  }
  applyLanguage(code);
}

function updatePickerSelection(code) {
  document.querySelectorAll(".lang-pill").forEach((pill) => {
    pill.classList.toggle("lang-pill--active", pill.dataset.lang === code);
  });
  const label = document.querySelector("[data-lang-current]");
  if (label) {
    const meta = LANGUAGES.find((l) => l.code === code) || LANGUAGES[0];
    label.textContent = meta.label;
  }
}

function googleTranslateElementInit() {
  // eslint-disable-next-line no-undef
  new google.translate.TranslateElement(
    {
      pageLanguage: "en",
      includedLanguages: GOOGLE_LANG_CODES.join(","),
      autoDisplay: false
    },
    "google_translate_element"
  );
  const stored = getStoredLang();
  if (stored !== "en") {
    applyLanguage(stored);
  }
}
window.googleTranslateElementInit = googleTranslateElementInit;

function buildLangPicker() {
  const root = document.querySelector("[data-lang-picker]");
  if (!root) return;

  const current = getStoredLang();
  const currentMeta = LANGUAGES.find((l) => l.code === current) || LANGUAGES[0];

  const button = document.createElement("button");
  button.type = "button";
  button.className = "lang-button notranslate";
  button.setAttribute("translate", "no");
  button.setAttribute("aria-haspopup", "true");
  button.setAttribute("aria-expanded", "false");
  button.setAttribute("aria-label", "Select language");
  button.innerHTML = `
    <svg class="lang-button__icon" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
      <circle cx="12" cy="12" r="10"></circle>
      <line x1="2" y1="12" x2="22" y2="12"></line>
      <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path>
    </svg>
    <span class="lang-button__label" data-lang-current>${currentMeta.label}</span>
    <svg class="lang-button__chevron" viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
      <polyline points="6 9 12 15 18 9"></polyline>
    </svg>
  `;

  const panel = document.createElement("div");
  panel.className = "lang-panel notranslate";
  panel.setAttribute("translate", "no");
  panel.setAttribute("role", "menu");
  panel.hidden = true;

  LANGUAGES.forEach(({ code, label }) => {
    const pill = document.createElement("button");
    pill.type = "button";
    pill.className = "lang-pill" + (code === current ? " lang-pill--active" : "");
    pill.textContent = label;
    pill.dataset.lang = code;
    pill.setAttribute("role", "menuitem");
    pill.addEventListener("click", () => {
      panel.hidden = true;
      button.setAttribute("aria-expanded", "false");
      if (code === getStoredLang()) return;
      setLang(code);
    });
    panel.appendChild(pill);
  });

  button.addEventListener("click", (event) => {
    event.stopPropagation();
    const willOpen = panel.hidden;
    panel.hidden = !willOpen;
    button.setAttribute("aria-expanded", willOpen ? "true" : "false");
  });

  document.addEventListener("click", (event) => {
    if (!root.contains(event.target)) {
      panel.hidden = true;
      button.setAttribute("aria-expanded", "false");
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !panel.hidden) {
      panel.hidden = true;
      button.setAttribute("aria-expanded", "false");
      button.focus();
    }
  });

  root.appendChild(button);
  root.appendChild(panel);
}

function injectGoogleTranslate() {
  if (document.getElementById("google_translate_script")) return;
  if (!document.getElementById("google_translate_element")) {
    const host = document.createElement("div");
    host.id = "google_translate_element";
    host.setAttribute("aria-hidden", "true");
    document.body.appendChild(host);
  }

  const script = document.createElement("script");
  script.id = "google_translate_script";
  script.src =
    "https://translate.google.com/translate_a/element.js?cb=googleTranslateElementInit";
  script.async = true;
  document.body.appendChild(script);
}

document.addEventListener("DOMContentLoaded", () => {
  buildLangPicker();
  injectGoogleTranslate();
});
