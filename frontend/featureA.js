/* =====================================================================
   featureA.js: Student Timetable
   ---------------------------------------------------------------------
   Requires app.js (API_BASE, $, esc, iso, fmtDay, dublinDate).
   Set USE_MOCK_* = true to use illustrative data instead of the backend.
   apiGetProgrammes, apiGetAnalysisOptions, apiGetWeeks, apiGetTimetable
   and apiAnalyze are the ONLY functions that talk to the backend.
   ===================================================================== */
const USE_MOCK_TIMETABLE = false;   // false = use the real /api/weekly/timetable
const USE_MOCK_ANALYZE = false;     // false = use the real analyze endpoint
const USE_MOCK_PROGRAMMES = false;  // false = load the real list from /api/weekly/programmes

// Group event types into the three colour classes used by the page.
const kindOf = t => {
  const x = (t || "").toLowerCase();
  if (x.includes("lab") || x.includes("practical")) return "lab";
  if (x.includes("tutorial")) return "tutorial";
  return "lecture";
};

// Loaded from GET /api/weekly/programmes. Each item looks like:
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
  const res = await fetch(`/api/weekly/programmes`, { headers: { accept: "application/json" } });
  if (!res.ok) throw new Error("Could not load courses (" + res.status + ")");
  return res.json();
}

// Loaded from GET /api/weekly/analysis/options. Each item looks like:
//   { value: "week_balance", label: "How is my week balanced?" }
// One button is shown per option; `value` is sent to the analyze call.
let ANALYSIS_OPTIONS = [];

async function apiGetAnalysisOptions() {
  const res = await fetch(`/api/weekly/analysis/options`, { headers: { accept: "application/json" } });
  if (!res.ok) throw new Error("Could not load analysis options (" + res.status + ")");
  return res.json();
}

// Loaded from GET /api/weeks. Each item looks like:
//   { label: "Monday, 07 September 2026", start: "2026-09-07T00:00:00Z", end: "2026-09-11T23:59:59Z" }
let WEEKS = [];
const weekKey = w => w.start.slice(0, 10);   // "2026-09-07", used as the dropdown value

async function apiGetWeeks() {
  const res = await fetch(`/api/weeks`, { headers: { accept: "application/json" } });
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
  const res = await fetch(`/api/weekly/timetable?${qs}`, { headers: { accept: "application/json" } });
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

/* POST /api/weekly/analysis   (URL assumed from the other /api/weekly/... routes; change if different)
   Body:     { programme_uuid, start, end, analysis_option }
   Response: { status: "ok" | ..., summary: "...", ai_note: "..." | null,
               facts: {...}, trace: {...}, options: ["..."] }
   The frontend ignores `trace`. `options` is shown when the status isn't "ok"
   (for example when the backend needs you to choose between matches).
   Adjust readStats() below if your facts are shaped differently. */
async function apiAnalyze({ programme, weekStart, start, end }, option) {
  if (USE_MOCK_ANALYZE) return mockAnalyze(currentEvents);
  const res = await fetch(`/api/weekly/analysis`, {
    method: "POST",
    headers: { "Content-Type": "application/json", accept: "application/json" },
    body: JSON.stringify({ programme_uuid: programme, start, end, analysis_option: option.value }),
  });
  if (!res.ok) {
    let detail = "";
    try { const j = await res.json(); detail = typeof j.detail === "string" ? ": " + j.detail : ""; } catch (_) {}
    throw new Error("Analysis failed (" + res.status + ")" + detail);
  }
  return res.json();
}

/* ===================== Setup ===================== */
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

/* ===================== Show timetable ===================== */
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
  setAnalysisEnabled(false);
  try {
    const data = await apiGetTimetable(sel);
    currentEvents = data.events || [];
    renderTimetable(sel, currentEvents);
    setAnalysisEnabled(currentEvents.length > 0);
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

/* ===================== Analyze ===================== */
// Pull the four mandatory stats out of the response. Adjust if your facts differ.
// Looks for the stats in facts (top level, or one level down, e.g. facts.stats or
// facts.weekly_stats). Any value not found is calculated from the events on screen.
function computeStats(events) {
  const byDay = {};
  let mins = 0, lectures = 0, labs = 0;
  events.forEach(e => {
    const s = new Date(e.start), en = new Date(e.end);
    mins += (en - s) / 60000;
    const k = kindOf(e.type);
    if (k === "lecture") lectures++;
    if (k === "lab") labs++;
    const day = dublinDate(e.start);
    (byDay[day] = byDay[day] || []).push({ s, en });
  });
  let gaps = 0;
  Object.values(byDay).forEach(list => {
    list.sort((a, b) => a.s - b.s);
    for (let i = 1; i < list.length; i++) if (list[i].s - list[i - 1].en >= 30 * 60000) gaps++;
  });
  return { lectures, labs, class_hours: +(mins / 60).toFixed(1), gaps, days: Object.keys(byDay).length };
}

function readStats(data) {
  const f = data.facts || {};
  const scopes = [f, f.stats, f.weekly_stats, f.statistics, f.mandatory_stats, data.stats]
    .concat(Object.values(f).filter(v => v && typeof v === "object" && !Array.isArray(v)))
    .filter(v => v && typeof v === "object");
  const pick = names => {
    for (const sc of scopes) for (const n of names) if (typeof sc[n] === "number" || typeof sc[n] === "string") return sc[n];
    return undefined;
  };
  const local = computeStats(currentEvents);
  return {
    lectures: pick(["lectures", "lecture_count", "num_lectures", "total_lectures"]) ?? local.lectures,
    labs: pick(["labs", "lab_count", "num_labs", "total_labs"]) ?? local.labs,
    hours: pick(["class_hours", "scheduled_hours", "total_hours", "total_class_hours", "scheduled_class_hours"]) ?? local.class_hours,
    gaps: pick(["gaps", "gap_count", "num_gaps", "total_gaps", "gaps_between_classes"]) ?? local.gaps,
  };
}

// Analysis option buttons (one per entry from /api/weekly/analysis/options)
function setAnalysisEnabled(enabled) {
  document.querySelectorAll(".option-btn").forEach(b => { b.disabled = !enabled; });
}

function renderAnalysisButtons() {
  const box = $("analysisOptions");
  box.innerHTML = "";
  ANALYSIS_OPTIONS.forEach(opt => {
    const b = document.createElement("button");
    b.className = "option-btn";
    b.type = "button";
    b.textContent = opt.label;
    b.dataset.value = opt.value;
    b.disabled = currentEvents.length === 0;
    b.addEventListener("click", () => runAnalysis(opt, b));
    box.appendChild(b);
  });
}

async function loadAnalysisOptions() {
  $("analysisOptions").innerHTML = `<div class="loading"><div class="spinner"></div>Loading options…</div>`;
  try {
    ANALYSIS_OPTIONS = await apiGetAnalysisOptions();
    renderAnalysisButtons();
  } catch (e) {
    $("analysisOptions").innerHTML = `<p class="error">${esc(e.message)}. Is the backend running on ${esc(API_BASE)}?</p>`;
  }
}
loadAnalysisOptions();

async function runAnalysis(opt, btn) {
  const sel = selection();
  document.querySelectorAll(".option-btn").forEach(b => b.classList.toggle("active", b === btn));
  setAnalysisEnabled(false);
  $("resultsCard").classList.remove("hidden");
  $("highlightsCard").classList.remove("hidden");
  $("highlightsSub").textContent = opt.label;
  $("statsBody").innerHTML = `<div class="loading"><div class="spinner"></div>Calculating statistics…</div>`;
  $("highlightsBody").innerHTML = `<div class="loading"><div class="spinner"></div>The AI is analysing your week…</div>`;
  try {
    const data = await apiAnalyze(sel, opt);
    renderAnalysis(data);
  } catch (e) {
    $("statsBody").innerHTML = `<p class="error">${esc(e.message)}</p>`;
    $("highlightsBody").innerHTML = "";
  } finally {
    setAnalysisEnabled(currentEvents.length > 0);
  }
}

function renderAnalysis(data) {
  const status = data.status || "ok";

  // Anything other than a successful result: show the backend's message, no stats.
  if (status !== "ok") {
    $("resultsCard").classList.add("hidden");
    let html = `<div class="status-msg">${esc(data.summary || "No analysis is available for this week.")}`;
    if (Array.isArray(data.options) && data.options.length) {
      html += `<ul>${data.options.map(o => `<li>${esc(o)}</li>`).join("")}</ul>`;
    }
    $("highlightsBody").innerHTML = html + `</div>`;
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
    const st = computeStats(events);
    setTimeout(() => resolve({
      status: "ok",
      summary: `You have ${events.length} scheduled classes this week, totalling ${st.class_hours} hours across ${st.days} days.`,
      ai_note: null,
      facts: { stats: { lectures: st.lectures, labs: st.labs, class_hours: st.class_hours, gaps: st.gaps } },
      trace: {},
    }), 800);
  });
}
