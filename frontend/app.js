/* =====================================================================
   CONFIG: connect to your backend here
   ---------------------------------------------------------------------
   Set USE_MOCK = false once your backend is running. apiGetTimetable and
   apiAnalyze are the ONLY functions that talk to the backend. Adjust the
   URLs and payloads to match your API.
   ===================================================================== */
const USE_MOCK = false;
const API_BASE = "https://timetable.redbrick.dcu.ie/";   // e.g. "http://localhost:8000"

// The backend maps (course + year) to the Redbrick UUID, so the frontend
// only sends the course key and the year. Replace with your real courses.
const COURSES = [
  { key: "computer-science", label: "Computer Science" },
  { key: "data-science",     label: "Data Science" },
  { key: "electronic-eng",   label: "Electronic Engineering" },
  { key: "business",         label: "Business Studies" },
];

// The timetable snapshot covers 1 Sep to 20 Dec 2026, so only these weeks are offered.
const FIRST_MONDAY = new Date(2026, 7, 31);   // Mon 31 Aug 2026 (contains 1 Sep)
const NUM_WEEKS = 16;                          // up to the week of 14-20 Dec 2026


/* Timetable endpoint, expected response:
   { events: [ { module, type, start, end, room, building } ] }
   start/end are ISO strings (UTC with offset is fine; they are shown in Europe/Dublin). */
async function apiGetTimetable({ course, year, weekStart }) {
  if (USE_MOCK) return mockTimetable(weekStart);
  const res = await fetch(`${API_BASE}/api/v3/timetable?course=${course}&year=${year}&week_start=${weekStart}`);
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
async function apiAnalyze({ course, year, weekStart }) {
  if (USE_MOCK) return mockAnalyze(weekStart);
  const res = await fetch(`${API_BASE}/api/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ course, year, week_start: weekStart }),
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
COURSES.forEach(c => $("course").add(new Option(c.label, c.key)));

(function buildWeeks() {
  const today = iso(new Date());
  let defaultSet = false;
  for (let i = 0; i < NUM_WEEKS; i++) {
    const mon = new Date(FIRST_MONDAY); mon.setDate(mon.getDate() + i * 7);
    const sun = new Date(mon); sun.setDate(mon.getDate() + 6);
    const opt = new Option(`${fmtDay(mon)} to ${fmtDay(sun)}, ${sun.getFullYear()}`, iso(mon));
    if (!defaultSet && today >= iso(mon) && today <= iso(sun)) { opt.selected = true; defaultSet = true; }
    $("week").add(opt);
  }
})();

const selection = () => ({ course: $("course").value, year: $("year").value, weekStart: $("week").value });
let currentEvents = [];

function resetResults() {
  $("resultsCard").classList.add("hidden");
  $("highlightsCard").classList.add("hidden");
}
["course", "year", "week"].forEach(id => $(id).addEventListener("change", () => {
  $("timetableCard").classList.add("hidden");
  resetResults();
}));

/* ===================== Feature A: show timetable ===================== */
$("showBtn").addEventListener("click", async () => {
  const sel = selection();
  resetResults();
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
  const course = COURSES.find(c => c.key === sel.course).label;
  const [y, m, d] = sel.weekStart.split("-").map(Number);
  const mon = new Date(y, m - 1, d);
  $("timetableSub").textContent = `${course}, Year ${sel.year}`;

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

function mockAnalyze(weekStart) {
  return mockTimetable(weekStart).then(({ events }) => new Promise(resolve => {
    const byDay = {};
    let mins = 0, lectures = 0, labs = 0;
    events.forEach(e => {
      const s = new Date(e.start), en = new Date(e.end);
      mins += (en - s) / 60000;
      if (e.type === "Lecture") lectures++;
      if (e.type === "Lab") labs++;
      (byDay[iso(s)] = byDay[iso(s)] || []).push({ s, en });
    });
    let gaps = 0;
    Object.values(byDay).forEach(list => {
      list.sort((a, b) => a.s - b.s);
      for (let i = 1; i < list.length; i++) if (list[i].s - list[i - 1].en >= 30 * 60000) gaps++;
    });
    setTimeout(() => resolve({
      status: "ok",
      summary: "You have 4 lectures, 2 labs and 2 tutorials this week. Friday is free, and Thursday ends late with a 17:00 lecture.",
      ai_note: "Wednesday has a long gap between your morning tutorial and afternoon lab, which could suit a study session.",
      facts: { stats: { lectures, labs, class_hours: +(mins / 60).toFixed(1), gaps } },
      trace: {},
    }), 1400);
  }));
}
