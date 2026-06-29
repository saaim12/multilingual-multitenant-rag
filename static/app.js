/* ═══════════════════════════════════════════════════════════════════
   app.js  —  Multilingual Multi-Tenant RAG Engine

   Storage keys in localStorage:
     rag_access   — short-lived access JWT
     rag_refresh  — long-lived refresh JWT

   Auth flow:
     login/register → save both tokens → enterApp()
     page load      → if access exists & not expired → enterApp()
                    → if expired → silently try refresh → enterApp() or login screen
     any 401        → try refresh once → retry request → or force logout
     logout         → clear both keys → show login screen
═══════════════════════════════════════════════════════════════════ */

const API_BASE = (window.RAG_API_BASE || "http://localhost:8000") + "/api";

/* ── localStorage token store ───────────────────────────────────── */
const tokens = {
  get access()  { return localStorage.getItem("rag_access");  },
  get refresh() { return localStorage.getItem("rag_refresh"); },

  save(access, refresh) {
    localStorage.setItem("rag_access", access);
    // refresh may be absent from a token-refresh response — don't overwrite with null
    if (refresh) localStorage.setItem("rag_refresh", refresh);
  },

  clear() {
    localStorage.removeItem("rag_access");
    localStorage.removeItem("rag_refresh");
  },
};

/* ── JWT decode for display claims ──────────────────────────────── */
// We never trust client-decoded claims for auth decisions — the server validates
// the signature. We only use decoded claims for UI display (tenant name, username).
function decodeJwt(token) {
  try {
    const b64 = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    return JSON.parse(atob(b64));
  } catch {
    return {};
  }
}

function isTokenExpired(token) {
  const { exp } = decodeJwt(token);
  return exp ? exp * 1000 < Date.now() : false;
}

/* ── Core API client ─────────────────────────────────────────────
   Injects Authorization header on every call.
   On 401: tries one silent token refresh, then retries.
   On second 401: clears storage and shows the login screen.
────────────────────────────────────────────────────────────────── */
async function apiCall(path, options = {}, _retried = false) {
  const headers = { ...(options.headers || {}) };

  if (tokens.access) headers["Authorization"] = `Bearer ${tokens.access}`;

  // Set JSON content-type for all non-multipart bodies
  if (options.body && !(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  const resp = await fetch(API_BASE + path, { ...options, headers });

  if (resp.status === 401 && !_retried) {
    const refreshed = await attemptRefresh();
    if (refreshed) return apiCall(path, options, true);
    // refresh failed — session is dead
    forceLogout("Your session expired. Please log in again.");
    return resp;
  }

  return resp;
}

async function attemptRefresh() {
  if (!tokens.refresh) return false;
  try {
    const resp = await fetch(API_BASE + "/auth/refresh/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh: tokens.refresh }),
    });
    if (!resp.ok) return false;
    const data = await resp.json();
    tokens.save(data.access, data.refresh || null);
    return true;
  } catch {
    return false;
  }
}

/* ── Screen routing ─────────────────────────────────────────────── */
function showScreen(name) {
  document.getElementById("auth-screen").classList.toggle("hidden", name !== "auth");
  document.getElementById("app-screen").classList.toggle("hidden", name !== "app");
}

function enterApp() {
  const claims = decodeJwt(tokens.access);
  document.getElementById("tenant-badge").textContent = claims.tenant_name || "tenant";
  document.getElementById("header-username").textContent = claims.sub || "";
  showScreen("app");
  loadUsage();
}

function logout() {
  tokens.clear();
  // Reset forms so the user isn't confused on re-login
  document.getElementById("login-form").reset();
  document.getElementById("register-form").reset();
  showScreen("auth");
}

function forceLogout(message) {
  tokens.clear();
  showScreen("auth");
  if (message) showToast(message, "warn");
}

/* ── Toast notification ─────────────────────────────────────────── */
function showToast(msg, type = "info") {
  let toast = document.getElementById("toast");
  if (!toast) {
    toast = document.createElement("div");
    toast.id = "toast";
    document.body.appendChild(toast);
  }
  toast.textContent = msg;
  toast.className = `toast toast-${type} show`;
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => toast.classList.remove("show"), 4000);
}

/* ── Auth tab switching ─────────────────────────────────────────── */
document.querySelectorAll(".tab").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
    btn.classList.add("active");
    const tab = btn.dataset.tab;
    document.getElementById("login-form").classList.toggle("hidden", tab !== "login");
    document.getElementById("register-form").classList.toggle("hidden", tab !== "register");
    // Clear error messages when switching tabs
    document.getElementById("login-error").textContent = "";
    document.getElementById("reg-error").textContent = "";
  });
});

/* ── Auth form helpers ──────────────────────────────────────────── */
function setSubmitting(btn, busy, label) {
  btn.disabled = busy;
  btn.textContent = busy ? "Please wait…" : label;
}

/* ── Login ──────────────────────────────────────────────────────── */
const loginForm = document.getElementById("login-form");
loginForm.addEventListener("submit", async e => {
  e.preventDefault();
  const errEl = document.getElementById("login-error");
  const btn   = loginForm.querySelector("button[type=submit]");
  errEl.textContent = "";
  setSubmitting(btn, true, "Sign in");

  const username = document.getElementById("login-username").value.trim();
  const password = document.getElementById("login-password").value;

  try {
    const resp = await fetch(API_BASE + "/auth/login/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    const data = await resp.json();
    if (!resp.ok) {
      errEl.textContent = data.detail || data.error || "Invalid credentials.";
      return;
    }
    tokens.save(data.access, data.refresh);
    enterApp();
  } catch {
    errEl.textContent = "Cannot reach the server. Is it running?";
  } finally {
    setSubmitting(btn, false, "Sign in");
  }
});

/* ── Register ───────────────────────────────────────────────────── */
const regForm = document.getElementById("register-form");
regForm.addEventListener("submit", async e => {
  e.preventDefault();
  const errEl = document.getElementById("reg-error");
  const btn   = regForm.querySelector("button[type=submit]");
  errEl.textContent = "";
  setSubmitting(btn, true, "Create account");

  const username = document.getElementById("reg-username").value.trim();
  const email    = document.getElementById("reg-email").value.trim();
  const password = document.getElementById("reg-password").value;

  try {
    const resp = await fetch(API_BASE + "/auth/register/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, email, password }),
    });
    const data = await resp.json();
    if (!resp.ok) {
      errEl.textContent = data.error || "Registration failed.";
      return;
    }
    tokens.save(data.access, data.refresh);
    showToast(`Welcome! You joined tenant "${data.tenant}".`, "info");
    enterApp();
  } catch {
    errEl.textContent = "Cannot reach the server. Is it running?";
  } finally {
    setSubmitting(btn, false, "Create account");
  }
});

/* ── Logout ─────────────────────────────────────────────────────── */
document.getElementById("logout-btn").addEventListener("click", logout);

/* ── Usage widget ───────────────────────────────────────────────── */
async function loadUsage() {
  const loadingEl = document.getElementById("usage-loading");
  const contentEl = document.getElementById("usage-content");
  loadingEl.classList.remove("hidden");
  contentEl.classList.add("hidden");

  try {
    const resp = await apiCall("/usage/");
    if (!resp.ok) return;
    const d = await resp.json();

    document.getElementById("usage-used").textContent      = d.requests_used.toLocaleString();
    document.getElementById("usage-quota").textContent     = d.api_quota.toLocaleString();
    document.getElementById("usage-remaining").textContent =
      `${d.remaining.toLocaleString()} request${d.remaining !== 1 ? "s" : ""} remaining`;

    const pct = d.api_quota > 0 ? Math.min(100, (d.requests_used / d.api_quota) * 100) : 0;
    const bar = document.getElementById("usage-bar");
    bar.style.width = pct + "%";
    // Turn the bar red when close to the limit
    bar.style.background = pct >= 90 ? "#dc2626" : pct >= 70 ? "#f59e0b" : "";

    loadingEl.classList.add("hidden");
    contentEl.classList.remove("hidden");
  } catch { /* silent — widget just stays loading */ }
}

/* ── File picker ────────────────────────────────────────────────── */
const csvInput   = document.getElementById("csv-file");
const uploadBtn  = document.getElementById("upload-btn");
const fileSummary = document.getElementById("file-summary");
const fileLabelSpan = document.getElementById("file-label").querySelector("span");

csvInput.addEventListener("change", () => {
  const file = csvInput.files[0];
  if (!file) {
    uploadBtn.disabled = true;
    fileSummary.classList.add("hidden");
    fileLabelSpan.textContent = "Choose file…";
    return;
  }
  const kb = (file.size / 1024).toFixed(1);
  fileSummary.textContent = `${file.name}  ·  ${kb} KB  ·  will replace existing chunks for this filename`;
  fileSummary.classList.remove("hidden");
  fileLabelSpan.textContent = file.name;
  uploadBtn.disabled = false;
});

/* ── Upload ─────────────────────────────────────────────────────── */
uploadBtn.addEventListener("click", async () => {
  const file = csvInput.files[0];
  if (!file) return;

  const statusEl = document.getElementById("upload-status");
  statusEl.className = "upload-status";
  statusEl.textContent = "Uploading and embedding…";
  setSubmitting(uploadBtn, true, "Upload");

  const form = new FormData();
  form.append("file", file);

  try {
    const resp = await apiCall("/ingest/", { method: "POST", body: form });
    const data = await resp.json();

    if (!resp.ok) {
      statusEl.textContent = "Error: " + (data.error || `HTTP ${resp.status}`);
      statusEl.className = "upload-status error-msg";
    } else {
      const skipped = data.rows_skipped ? `, ${data.rows_skipped} row(s) skipped` : "";
      statusEl.textContent = `✓ ${data.chunks_created} chunks created${skipped} for "${data.tenant}"`;
      statusEl.className = "upload-status success-msg";
      // Reset file picker
      csvInput.value = "";
      fileLabelSpan.textContent = "Choose file…";
      fileSummary.classList.add("hidden");
      uploadBtn.disabled = true;
      loadUsage();
    }
  } catch {
    statusEl.textContent = "Network error — upload failed.";
    statusEl.className = "upload-status error-msg";
  } finally {
    setSubmitting(uploadBtn, false, "Upload");
  }
});

/* ── Query ──────────────────────────────────────────────────────── */
document.getElementById("query-btn").addEventListener("click", runQuery);
document.getElementById("query-input").addEventListener("keydown", e => {
  // Ctrl+Enter / Cmd+Enter submits the query
  if ((e.ctrlKey || e.metaKey) && e.key === "Enter") runQuery();
});

async function runQuery() {
  const query    = document.getElementById("query-input").value.trim();
  if (!query) return;

  const template    = document.getElementById("template-select").value;
  const spinner     = document.getElementById("query-spinner");
  const errEl       = document.getElementById("query-error");
  const answerBlock = document.getElementById("answer-block");
  const queryBtn    = document.getElementById("query-btn");

  spinner.classList.remove("hidden");
  errEl.textContent = "";
  answerBlock.classList.add("hidden");
  setSubmitting(queryBtn, true, "Ask");

  try {
    const resp = await apiCall("/query/", {
      method: "POST",
      body: JSON.stringify({ query, template }),
    });
    const data = await resp.json();

    if (resp.status === 429) {
      errEl.textContent = data.error || "Monthly quota exceeded. Contact your admin.";
      return;
    }
    if (!resp.ok) {
      errEl.textContent = data.error || `Error ${resp.status}`;
      return;
    }
    if (data.error) {
      // Gemini-level error (rate limit after retries, etc.)
      errEl.textContent = data.error;
      return;
    }

    renderAnswer(data);
    loadUsage(); // refresh usage counter after a successful generation
  } catch {
    errEl.textContent = "Network error — please try again.";
  } finally {
    spinner.classList.add("hidden");
    setSubmitting(queryBtn, false, "Ask");
  }
}

function renderAnswer(data) {
  document.getElementById("answer-text").textContent = data.answer;

  const context = data.context || [];
  document.getElementById("source-count").textContent = context.length;

  const sourcesList = document.getElementById("sources-list");
  sourcesList.innerHTML = "";
  context.forEach(chunk => {
    const li = document.createElement("li");
    li.className = "source-item";
    const preview = chunk.content.length > 220
      ? chunk.content.slice(0, 220) + "…"
      : chunk.content;
    const similarity = ((1 - chunk.distance) * 100).toFixed(0);
    li.innerHTML =
      `<div class="source-preview">${escHtml(preview)}</div>
       <div class="source-meta">
         <span>📄 ${escHtml(chunk.source)}</span>
         ${chunk.category ? `<span>· ${escHtml(chunk.category)}</span>` : ""}
         <span>· ${similarity}% match</span>
       </div>`;
    sourcesList.appendChild(li);
  });

  document.getElementById("answer-block").classList.remove("hidden");
}

/* ── Helpers ────────────────────────────────────────────────────── */
function escHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

/* ── Boot sequence ──────────────────────────────────────────────────
   1. Check for an access token in localStorage.
   2. If present and not expired → go straight to the app (no round-trip).
   3. If expired but refresh token present → silently refresh → app or login.
   4. If no tokens → show the login/register screen.
────────────────────────────────────────────────────────────────── */
(async function boot() {
  if (!tokens.access) { showScreen("auth"); return; }

  if (!isTokenExpired(tokens.access)) {
    enterApp();
    return;
  }

  // Access token expired — try to restore the session via refresh token
  const ok = await attemptRefresh();
  if (ok) {
    enterApp();
  } else {
    tokens.clear();
    showScreen("auth");
  }
})();
