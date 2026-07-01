const API_BASE = "https://hyrox-unlock-worker.roxzone.workers.dev";

function query(name) {
  const params = new URLSearchParams(window.location.search);
  return params.get(name) || "";
}

function setText(id, value) {
  const node = document.getElementById(id);
  if (node) {
    node.textContent = value;
  }
}

function setStatus(message, kind) {
  const node = document.getElementById("status");
  if (!node) {
    return;
  }
  node.textContent = message;
  node.className = kind ? `status ${kind}` : "status";
}

// Pull the current price from the worker (single source of truth) so the price
// card always matches what checkout charges. On any failure the hardcoded
// prices in index.html stay as a fallback.
async function loadPricing() {
  try {
    const res = await fetch(`${API_BASE}/api/pricing`);
    if (!res.ok) {
      return;
    }
    const {usd, inr} = await res.json();
    if (inr) {
      const inrInt = String(inr).replace(/\.00$/, "");
      document.querySelectorAll(".price-card__amount--inr").forEach((el) => {
        el.textContent = `₹${inrInt}`;
      });
    }
    if (usd) {
      document.querySelectorAll(".price-block--intl .price-card__amount").forEach((el) => {
        el.textContent = `$${usd}`;
      });
    }
  } catch (_) {
    // leave hardcoded HTML values as fallback
  }
}

async function postJson(path, payload) {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload)
  });

  const text = await response.text();
  let data = null;
  if (text && text.length > 0) {
    data = JSON.parse(text);
  }

  if (!response.ok) {
    const message = data && data.error ? data.error : `Request failed (${response.status})`;
    throw new Error(message);
  }

  return data;
}
