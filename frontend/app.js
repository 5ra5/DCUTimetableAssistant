/* =====================================================================
   CONFIG: connect to your backend here
   ---------------------------------------------------------------------
   Set USE_MOCK = false once your backend is running. apiGetTimetable and
   apiAnalyze are the ONLY functions that talk to the backend. Adjust the
   URLs and payloads to match your API.
   ===================================================================== */
const API_BASE = "http://localhost:8080";

// Loaded from GET /api/programmes. Each item looks like:
//   { redbrick_name: "AC1 (Chem & Pharma Science-1)", redbrick_uuid: "8dc12a98-..." }
// The name already includes the year, and the UUID is the timetable code.
let PROGRAMMES = [];

async function apiGetProgrammes() {
  const res = await fetch(`${API_BASE}/api/programmes`, { headers: { accept: "application/json" } });
  if (!res.ok) throw new Error("Could not load courses (" + res.status + ")");
  return res.json();
}

// Loaded from GET /api/weeks. Each item looks like:
//   { label: "Monday, 07 September 2026", start: "2026-09-07T00:00:00Z", end: "2026-09-11T23:59:59Z" }
let WEEKS = [];
const weekKey = w => w.start.slice(0, 10);   // "2026-09-07", used as the dropdown value

async function apiGetWeeks() {
  const res = await fetch(`${API_BASE}/api/weeks`, { headers: { accept: "application/json" } });
  if (!res.ok) throw new Error("Could not load weeks (" + res.status + ")");
  return res.json();
}

/* Timetable endpoint, expected response:
   { events: [ { module, type, start, end, room, building } ] }
   start/end are ISO strings (UTC with offset is fine; they are shown in Europe/Dublin).
   The selected week's exact start/end from /api/weeks are sent as the date range. */
async function apiGetTimetable({ programme, weekStart, start, end }) {
  const qs = new URLSearchParams({ programme, start, end });
  const res = await fetch(`${API_BASE}/api/timetable?${qs}`);
  if (!res.ok) throw new Error("Could not load timetable (" + res.status + ")");
  return res.json();
}

/* Analyze endpoint, expected response (the shared agent response shape):
   { status: "ok" | "not_found" | "needs_choice" | "unsupported" (or similar),
     summary: "main answer built by Python",
     ai_note: null | "optional model note",
     facts: { stats: { lectures, labs, class_hours, gaps } },
     trace: {} }
   The frontend ignores `trace`. Adjust readStats() below if your facts are shaped differently. */
async function apiAnalyze({ programme, weekStart, start, end }) {
  const res = await fetch(`${API_BASE}/api/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ programme_uuid: programme, start, end }),
  });
  if (!res.ok) throw new Error("Analysis failed (" + res.status + ")");
  return res.json();
}

/* ===================== Helpers ===================== */
const $ = id => document.getElementById(id);
const fmtDay = d => d.toLocaleDateString("en-IE", { day: "numeric", month: "short" });
const iso = d => d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");
const esc = s => String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

/* ===================== Feature switcher ===================== */
document.querySelectorAll(".switcher button").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".switcher button").forEach(b => b.classList.toggle("active", b === btn));
    document.querySelectorAll(".panel").forEach(p => p.classList.remove("active"));
    $("panel-" + btn.dataset.feature).classList.add("active");
  });
});

/* ===================== Feature A: setup ===================== */
function fillCourseSelect() {
  const q = $("courseFilter").value.trim().toLowerCase();
  const prev = $("course").value;
  const matches = PROGRAMMES.filter(p => p.redbrick_name.toLowerCase().includes(q));
  const sel = $("course");
  sel.innerHTML = "";
  sel.add(new Option(matches.length ? "Select a course…" : "No matching courses", ""));
  matches.forEach(p => sel.add(new Option(p.redbrick_name, p.redbrick_uuid)));
  if (matches.some(p => p.redbrick_uuid === prev)) sel.value = prev;
  $("courseHint").textContent = `${matches.length} of ${PROGRAMMES.length} courses`;
  $("courseHint").classList.remove("error");
}

async function loadProgrammes() {
  $("course").innerHTML = `<option value="">Loading courses…</option>`;
  try {
    const list = await apiGetProgrammes();
    PROGRAMMES = list.slice().sort((a, b) => a.redbrick_name.localeCompare(b.redbrick_name));
    fillCourseSelect();
  } catch (e) {
    $("course").innerHTML = `<option value="">Courses unavailable</option>`;
    $("courseHint").textContent = e.message + ". Is the backend running on " + API_BASE + "?";
    $("courseHint").classList.add("error");
  }
}
$("courseFilter").addEventListener("input", fillCourseSelect);
loadProgrammes();

async function buildWeeks() {
  const sel = $("week");
  sel.innerHTML = `<option value="">Loading weeks…</option>`;
  try {
    const list = await apiGetWeeks();
    WEEKS = list.slice().sort((a, b) => a.start.localeCompare(b.start));
    sel.innerHTML = "";
    WEEKS.forEach(w => sel.add(new Option(w.label, weekKey(w))));
    // Default to the latest week that has already started (or the first week if none has).
    const today = iso(new Date());
    const current = WEEKS.filter(w => weekKey(w) <= today).pop() || WEEKS[0];
    if (current) sel.value = weekKey(current);
  } catch (e) {
    sel.innerHTML = `<option value="">Weeks unavailable</option>`;
    $("courseHint").textContent = e.message + ". Is the backend running on " + API_BASE + "?";
    $("courseHint").classList.add("error");
  }
}
buildWeeks();

const selection = () => {
  const week = WEEKS.find(w => weekKey(w) === $("week").value) || {};
  return { programme: $("course").value, weekStart: $("week").value, start: week.start, end: week.end };
};
const programmeName = uuid => (PROGRAMMES.find(p => p.redbrick_uuid === uuid) || {}).redbrick_name || "";
let currentEvents = [];

function resetResults() {
  $("resultsCard").classList.add("hidden");
  $("highlightsCard").classList.add("hidden");
}
["course", "week"].forEach(id => $(id).addEventListener("change", () => {
  $("timetableCard").classList.add("hidden");
  resetResults();
}));

/* ===================== Feature A: show timetable ===================== */
$("showBtn").addEventListener("click", async () => {
  const sel = selection();
  resetResults();
  if (!sel.programme || !sel.start) {
    $("timetableCard").classList.add("hidden");
    $("courseHint").textContent = sel.programme ? "Please select a week first." : "Please select a course first.";
    $("courseHint").classList.add("error");
    return;
  }
  $("timetableCard").classList.remove("hidden");
  $("timetableSub").textContent = "";
  $("timetableBody").innerHTML = `<div class="loading"><div class="spinner"></div>Loading timetable…</div>`;
  $("analyzeBtn").disabled = true;
  try {
    const data = await apiGetTimetable(sel);
    currentEvents = data.events || [];
    renderTimetable(sel, currentEvents);
    $("analyzeBtn").disabled = currentEvents.length === 0;
  } catch (e) {
    $("timetableBody").innerHTML = `<p class="error">${esc(e.message)}</p>`;
  }
});

function renderTimetable(sel, events) {
  const [y, m, d] = sel.weekStart.split("-").map(Number);
  const mon = new Date(y, m - 1, d);
  $("timetableSub").textContent = programmeName(sel.programme);

  if (!events.length) {
    $("timetableBody").innerHTML = `<div class="status-msg">No timetable data is available for this selection and week.</div>`;
    return;
  }

  const time = s => new Date(s).toLocaleTimeString("en-IE", { hour: "2-digit", minute: "2-digit", hour12: false, timeZone: "Europe/Dublin" });
  const names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];
  let html = `<div class="week">`;
  names.forEach((name, i) => {
    const day = new Date(mon); day.setDate(mon.getDate() + i);
    const todays = events
      .filter(ev => iso(new Date(ev.start)) === iso(day))
      .sort((a, b) => new Date(a.start) - new Date(b.start));
    html += `<div class="day"><h3>${name}<span>${fmtDay(day)}</span></h3>`;
    if (!todays.length) html += `<div class="empty">No classes</div>`;
    todays.forEach(ev => {
      html += `<div class="event ${esc((ev.type || "").toLowerCase())}">
        <div class="time">${time(ev.start)} to ${time(ev.end)}</div>
        <div class="name">${esc(ev.module)}</div>
        <div class="meta">${esc(ev.type || "Event")} · ${esc(ev.room || "TBC")}${ev.building ? ", " + esc(ev.building) : ""}</div>
      </div>`;
    });
    html += `</div>`;
  });
  html += `</div>`;
  $("timetableBody").innerHTML = html;
}

/* ===================== Feature A: analyze ===================== */
// Pull the four mandatory stats out of the response. Adjust if your facts differ.
function readStats(data) {
  const s = (data.facts && data.facts.stats) || data.stats || data.facts || {};
  return {
    lectures: s.lectures ?? "–",
    labs: s.labs ?? "–",
    hours: s.class_hours ?? s.scheduled_hours ?? "–",
    gaps: s.gaps ?? s.gap_count ?? "–",
  };
}

$("analyzeBtn").addEventListener("click", async () => {
  const sel = selection();
  $("analyzeBtn").disabled = true;
  $("resultsCard").classList.remove("hidden");
  $("highlightsCard").classList.remove("hidden");
  $("statsBody").innerHTML = `<div class="loading"><div class="spinner"></div>Calculating statistics…</div>`;
  $("highlightsBody").innerHTML = `<div class="loading"><div class="spinner"></div>The AI is analysing your week…</div>`;
  try {
    const data = await apiAnalyze(sel);
    renderAnalysis(data);
  } catch (e) {
    $("statsBody").innerHTML = `<p class="error">${esc(e.message)}</p>`;
    $("highlightsBody").innerHTML = "";
  } finally {
    $("analyzeBtn").disabled = false;
  }
});

function renderAnalysis(data) {
  const status = data.status || "ok";

  // Anything other than a successful result: show the backend's message, no stats.
  if (status !== "ok") {
    $("resultsCard").classList.add("hidden");
    $("highlightsBody").innerHTML = `<div class="status-msg">${esc(data.summary || "No analysis is available for this week.")}</div>`;
    return;
  }

  const s = readStats(data);
  const stat = (v, l) => `<div class="stat"><div class="value">${esc(v)}</div><div class="label">${l}</div></div>`;
  $("statsBody").innerHTML =
    stat(s.lectures, "Lectures") +
    stat(s.labs, "Labs") +
    stat(s.hours === "–" ? s.hours : s.hours + " h", "Scheduled class hours") +
    stat(s.gaps, "Gaps between classes");

  // The summary is the Python-built answer; ai_note is an optional model note.
  let html = Array.isArray(data.summary)
    ? `<ul>${data.summary.map(h => `<li>${esc(h)}</li>`).join("")}</ul>`
    : `<p>${esc(data.summary || "")}</p>`;
  if (data.ai_note) html += `<div class="ai-note"><strong>AI note:</strong> ${esc(data.ai_note)}</div>`;
  $("highlightsBody").innerHTML = html;
}
