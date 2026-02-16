const API_BASE = "http://127.0.0.1:8000";
const sections = ["home", "profile", "contests", "reminders"];
let timezoneOptions = [];

const state = {
  userId: localStorage.getItem("cf_user_id") || null,
  contests: [],
};

const qs = (sel) => document.querySelector(sel);
const qsa = (sel) => Array.from(document.querySelectorAll(sel));

function setText(id, text) {
  const el = typeof id === "string" ? qs(id) : id;
  if (el) el.textContent = text;
}

function showStatus(el, text) {
  if (el) {
    el.textContent = text;
    setTimeout(() => {
      if (el.textContent === text) el.textContent = "";
    }, 4000);
  }
}

async function api(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || res.statusText);
  }
  return res.json();
}

function switchSection(target) {
  sections.forEach((id) => {
    const el = qs(`#section-${id}`);
    if (el) {
      el.hidden = id !== target;
    }
  });
  // Close mobile nav if open
  const nav = document.querySelector(".navbar-collapse");
  if (nav && nav.classList.contains("show")) {
    new bootstrap.Collapse(nav).hide();
  }
}

function wireNav() {
  document.querySelectorAll("[data-section]").forEach((el) => {
    el.addEventListener("click", (e) => {
      e.preventDefault();
      const target = el.getAttribute("data-section");
      if (sections.includes(target)) {
        switchSection(target);
        if (target === "contests") loadContests();
        if (target === "reminders") loadPreview();
      }
    });
  });
}

function buildContestCard(contest) {
  const startLocal = contest.start_time_local_formatted || contest.start_time_utc;
  return `<div class="col-md-6">
    <div class="card contest-card h-100">
      <div class="card-body">
        <div class="d-flex justify-content-between align-items-start mb-2">
          <div>
            <h5 class="card-title mb-1">${contest.name}</h5>
            <span class="badge badge-soft">ID: ${contest.id}</span>
          </div>
          <div class="form-check">
            <input class="form-check-input contest-check" type="checkbox" value="${contest.id}" />
          </div>
        </div>
        <p class="text-faded mb-1">Starts: ${startLocal || "TBD"}</p>
        <p class="text-faded mb-0">Duration: ${contest.duration_seconds ? Math.round(contest.duration_seconds / 60) + " min" : "TBD"}</p>
      </div>
    </div>
  </div>`;
}

function getSelectedContestIds() {
  return qsa(".contest-check:checked").map((el) => Number(el.value));
}

async function loadContests() {
  setText("#contest-status", "Loading contests...");
  const tz = qs("#contest-timezone").value.trim();
  const tzParam = tz ? `?timezone=${encodeURIComponent(tz)}` : "";
  try {
    const data = await api(`/contests${tzParam}`);
    state.contests = data;
    const list = qs("#contests-list");
    list.innerHTML = data.map(buildContestCard).join("");
    await precheckSubscriptions();
    showStatus(qs("#contest-status"), `Loaded ${data.length} upcoming contests`);
  } catch (err) {
    showStatus(qs("#contest-status"), `Error: ${err.message}`);
  }
}

async function precheckSubscriptions() {
  if (!state.userId) return;
  try {
    const subs = await api(`/users/${state.userId}/subscriptions`);
    const subIds = new Set(subs.map((s) => s.contest_id));
    qsa(".contest-check").forEach((el) => {
      el.checked = subIds.has(Number(el.value));
    });
  } catch (err) {
    showStatus(qs("#contest-status"), `Sub load failed: ${err.message}`);
  }
}

async function saveUser(e) {
  e.preventDefault();
  const form = e.target;
  const payload = Object.fromEntries(new FormData(form).entries());
  payload.reminder_count = Number(payload.reminder_count);
  payload.reminder_start_minutes = Number(payload.reminder_start_minutes);
  payload.reminder_interval_minutes = Number(payload.reminder_interval_minutes);
  try {
    const user = await api("/users", { method: "POST", body: JSON.stringify(payload) });
    state.userId = user.id;
    localStorage.setItem("cf_user_id", user.id);
    showStatus(qs("#user-status"), `Saved user #${user.id}`);
    await loadContests();
    await loadPreview();
  } catch (err) {
    showStatus(qs("#user-status"), `Error: ${err.message}`);
  }
}

async function loadExistingUser() {
  if (!state.userId) {
    showStatus(qs("#user-status"), "No user saved yet");
    return;
  }
  try {
    const user = await api(`/users/${state.userId}`);
    const form = qs("#user-form");
    form.email.value = user.email;
    form.timezone.value = user.timezone;
    form.reminder_count.value = user.reminder_count;
    form.reminder_start_minutes.value = user.reminder_start_minutes;
    form.reminder_interval_minutes.value = user.reminder_interval_minutes;
    showStatus(qs("#user-status"), `Loaded user #${user.id}`);
  } catch (err) {
    showStatus(qs("#user-status"), `Error: ${err.message}`);
  }
}

function populateTimezoneList(filter = "") {
  const list = qs("#tz-options");
  if (!list) return;
  const needle = filter.toLowerCase();
  const top = timezoneOptions
    .filter((tz) => tz.toLowerCase().includes(needle))
    .sort((a, b) => a.localeCompare(b))
    .slice(0, 25)
    .map((tz) => `<option value="${tz}"></option>`) // eslint-disable-line no-useless-concat
    .join("");
  list.innerHTML = top;
}

function initTimezoneSuggestions() {
  // Use Intl.supportedValuesOf if available; fallback to a curated set.
  if (typeof Intl !== "undefined" && typeof Intl.supportedValuesOf === "function") {
    timezoneOptions = Intl.supportedValuesOf("timeZone");
    // Ensure popular Asia timezones are present even if the browser list is limited
    ["Asia/Kolkata", "Asia/Calcutta", "Asia/Dhaka", "Asia/Karachi"].forEach((tz) => {
      if (!timezoneOptions.includes(tz)) timezoneOptions.push(tz);
    });
  } else {
    timezoneOptions = [
      "UTC",
      "Europe/London",
      "Europe/Berlin",
      "Europe/Paris",
      "Asia/Kolkata",
      "Asia/Dubai",
      "Asia/Tokyo",
      "Asia/Singapore",
      "Asia/Shanghai",
      "America/New_York",
      "America/Chicago",
      "America/Denver",
      "America/Los_Angeles",
      "America/Sao_Paulo",
      "Africa/Johannesburg",
      "Australia/Sydney",
    ];
  }

  populateTimezoneList();

  ["input", "change"].forEach((evt) => {
    qs("[name=timezone]").addEventListener(evt, (e) => populateTimezoneList(e.target.value));
    qs("#contest-timezone").addEventListener(evt, (e) => populateTimezoneList(e.target.value));
  });
}

async function saveSubscriptions() {
  if (!state.userId) {
    showStatus(qs("#save-status"), "Save profile first");
    return;
  }
  const ids = getSelectedContestIds();
  if (!ids.length) {
    showStatus(qs("#save-status"), "Select at least one contest");
    return;
  }
  try {
    await api(`/users/${state.userId}/subscriptions`, {
      method: "POST",
      body: JSON.stringify({ contest_ids: ids }),
    });
    showStatus(qs("#save-status"), "Subscriptions saved");
    await loadPreview();
  } catch (err) {
    showStatus(qs("#save-status"), `Error: ${err.message}`);
  }
}

function renderPreview(previews) {
  const container = qs("#preview-list");
  if (!previews.length) {
    container.innerHTML = "<p class='text-faded mb-0'>No previews yet.</p>";
    return;
  }
  container.innerHTML = previews
    .map((p) => {
      const localTimes = p.reminders_local_formatted || [];
      const list = localTimes
        .map((t) => `<span class='badge bg-secondary me-2 mb-2'>${t}</span>`)
        .join("");
      return `<div class='mb-3'>
        <h6 class='mb-1 text-white'>${p.contest_name}</h6>
        <div class='text-faded mb-1'>Starts (UTC): ${p.start_time_utc || "TBD"}</div>
        <div>${list}</div>
      </div>`;
    })
    .join("");
}

async function loadPreview() {
  if (!state.userId) return;
  try {
    const previews = await api(`/users/${state.userId}/notification-preview`);
    renderPreview(previews);
  } catch (err) {
    showStatus(qs("#dispatch-status"), `Preview error: ${err.message}`);
  }
}

async function dispatchNotifications() {
  if (!state.userId) {
    showStatus(qs("#dispatch-status"), "Save profile first");
    return;
  }
  try {
    const res = await api(`/users/${state.userId}/notifications/dispatch`, { method: "POST" });
    const errorText = res.errors && res.errors.length ? ` Errors: ${res.errors.join("; ")}` : "";
    showStatus(qs("#dispatch-status"), `Sent ${res.sent_count} notifications.${errorText}`);
  } catch (err) {
    showStatus(qs("#dispatch-status"), `Dispatch error: ${err.message}`);
  }
}

function attachEvents() {
  qs("#user-form").addEventListener("submit", saveUser);
  qs("#load-profile").addEventListener("click", loadExistingUser);
  qs("#refresh-contests").addEventListener("click", loadContests);
  qs("#save-subscriptions").addEventListener("click", saveSubscriptions);
  qs("#dispatch").addEventListener("click", dispatchNotifications);
}

async function init() {
  attachEvents();
  wireNav();
  initTimezoneSuggestions();
  if (state.userId) {
    await loadExistingUser();
  }
  switchSection("home");
}

document.addEventListener("DOMContentLoaded", init);
