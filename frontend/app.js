/* =====================================================================
   CONFIG: connect to your backend here
   ---------------------------------------------------------------------
   Set USE_MOCK = false once your backend is running. apiGetTimetable and
   apiAnalyze are the ONLY functions that talk to the backend. Adjust the
   URLs and payloads to match your API.
   ===================================================================== */
const USE_MOCK_TIMETABLE = false;   // false = use the real /api/weekly/timetable
const USE_MOCK_ANALYZE = true;      // analyze endpoint is still mocked
const USE_MOCK_PROGRAMMES = false;  // false = load the real list from /api/programmes
const API_BASE = "http://localhost:8080";

// Loaded from GET /api/programmes. Each item looks like:
//   { redbrick_name: "AC1 (Chem & Pharma Science-1)", redbrick_uuid: "8dc12a98-..." }
// The name already includes the year, and the UUID is the timetable code.
let PROGRAMMES = [];

async function apiGetProgrammes() {
  if (USE_MOCK_PROGRAMMES) {
    return [
      { redbrick_name: "CASE2 (Computer Applications-2)", redbrick_uuid: "mock-1" },
      { redbrick_name: "CASE3 (Computer Applications-3)", redbrick_uuid: "mock-2" },
    ];
  }
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

/* GET /api/weekly/timetable?programme_uuid=...&start=...&end=...
   Response: { events: [ { module_name1, module_name2, location, long_description,
                           short_description, start, end } ] }
   e.g. long_description = "Tutorial, On Campus", start = "2026-11-09T12:00:00Z".
   The selected week's exact start/end from /api/weeks are sent as the date range.
   Events are mapped to the shape the page renders:
   { module, type, room, building, description, start, end } */
async function apiGetTimetable({ programme, weekStart, start, end }) {
  if (USE_MOCK_TIMETABLE) return mockTimetable(weekStart);
  const qs = new URLSearchParams({ programme_uuid: programme, start, end });
  const res = await fetch(`${API_BASE}/api/weekly/timetable?${qs}`, { headers: { accept: "application/json" } });
  if (!res.ok) throw new Error("Could not load timetable (" + res.status + ")");
  const data = await res.json();
  return {
    events: (data.events || []).map(e => ({
      module: e.module_name1 || e.module_name2 || e.short_description || "Untitled event",
      type: (e.long_description || "").split(",")[0].trim() || "Event",
      room: e.location || "",
      building: "",
      description: e.short_description || "",
      start: e.start,
      end: e.end,
    })),
  };
}

/* Analyze endpoint, expected response (the shared agent response shape):
   { status: "ok" | "not_found" | "needs_choice" | "unsupported" (or similar),
     summary: "main answer built by Python",
     ai_note: null | "optional model note",
     facts: { stats: { lectures, labs, class_hours, gaps } },
     trace: {} }
   The frontend ignores `trace`. Adjust readStats() below if your facts are shaped differently. */
async function apiAnalyze({ programme, weekStart, start, end }) {
  if (USE_MOCK_ANALYZE) return mockAnalyze(currentEvents);
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
// Calendar date (YYYY-MM-DD) of a timestamp in Irish local time, so events land on the right day.
const dublinDate = s => new Date(s).toLocaleDateString("en-CA", { timeZone: "Europe/Dublin" });
// Group event types into the three colour classes used by the page.
const kindOf = t => {
  const x = (t || "").toLowerCase();
  if (x.includes("lab") || x.includes("practical")) return "lab";
  if (x.includes("tutorial")) return "tutorial";
  return "lecture";
};

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
      .filter(ev => dublinDate(ev.start) === iso(day))
      .sort((a, b) => new Date(a.start) - new Date(b.start));
    html += `<div class="day"><h3>${name}<span>${fmtDay(day)}</span></h3>`;
    if (!todays.length) html += `<div class="empty">No classes</div>`;
    todays.forEach(ev => {
      html += `<div class="event ${kindOf(ev.type)}"${ev.description ? ` title="${esc(ev.description)}"` : ""}>
        <div class="time">${time(ev.start)} to ${time(ev.end)}</div>
        <div class="name">${esc(ev.module)}</div>
        <div class="meta">${esc(ev.type || "Event")} · ${esc(ev.room || "Location TBC")}${ev.building ? ", " + esc(ev.building) : ""}</div>
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

/* ===================== Mock data (illustrative only) ===================== */
function mockTimetable(weekStart) {
  const [y, m, d] = weekStart.split("-").map(Number);
  const mk = (dayOffset, sh, sm, eh, em, module, type, room, building) => ({
    module, type, room, building,
    start: new Date(y, m - 1, d + dayOffset, sh, sm).toISOString(),
    end: new Date(y, m - 1, d + dayOffset, eh, em).toISOString(),
  });
  const events = [
    mk(0, 9, 0, 11, 0,  "Algorithms & Data Structures", "Lecture",  "L2.05", "Henry Grattan"),
    mk(0, 14, 0, 16, 0, "Databases",                      "Lab",      "LG25",  "Computer Science"),
    mk(1, 10, 0, 11, 0, "Operating Systems",              "Lecture",  "X104",  "Marconi"),
    mk(1, 15, 0, 16, 0, "Operating Systems",              "Tutorial", "C166",  "Henry Grattan"),
    mk(2, 9, 0, 10, 0,  "Algorithms & Data Structures",   "Tutorial", "L1.12", "Henry Grattan"),
    mk(2, 13, 0, 15, 0, "Software Engineering",           "Lab",      "LG26",  "Computer Science"),
    mk(3, 11, 0, 13, 0, "Databases",                      "Lecture",  "L2.05", "Henry Grattan"),
    mk(3, 17, 0, 18, 0, "Software Engineering",           "Lecture",  "X204",  "Marconi"),
  ];
  return new Promise(r => setTimeout(() => r({ events }), 500));
}

// Placeholder for the real analyze endpoint: computes the stats from the events
// currently shown on the page, so the numbers match the real timetable.
function mockAnalyze(events) {
  return new Promise(resolve => {
    const byDay = {};
    let mins = 0, lectures = 0, labs = 0;
    events.forEach(e => {
      const s = new Date(e.start), en = new Date(e.end);
      mins += (en - s) / 60000;
      const k = kindOf(e.type);
      if (k === "lecture") lectures++;
      if (k === "lab") labs++;
      (byDay[dublinDate(e.start)] = byDay[dublinDate(e.start)] || []).push({ s, en });
    });
    let gaps = 0;
    Object.values(byDay).forEach(list => {
      list.sort((a, b) => a.s - b.s);
      for (let i = 1; i < list.length; i++) if (list[i].s - list[i - 1].en >= 30 * 60000) gaps++;
    });
    const hours = +(mins / 60).toFixed(1);
    setTimeout(() => resolve({
      status: "ok",
      summary: `You have ${events.length} scheduled classes this week, totalling ${hours} hours across ${Object.keys(byDay).length} days.`,
      ai_note: null,
      facts: { stats: { lectures, labs, class_hours: hours, gaps } },
      trace: {},
    }), 800);
  });
}