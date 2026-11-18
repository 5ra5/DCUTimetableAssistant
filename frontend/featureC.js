/* =====================================================================
   featureC.js: Lecturer Finder
   ---------------------------------------------------------------------
   Requires app.js ($, esc, iso, dublinDate, API_BASE, makeWheel, makePicker). UI lives in #panel-C.
   Wrapped in an IIFE so its names never clash with other feature files.
   Backend routes (JSON bodies, no query parameters):
     POST /api/lecturers/search    { lecturer_name }
     POST /api/lecturers/schedule  { lecturer_name: "<numeric id>", date, time }
   Both return { status, summary, ai_note, facts, trace, options }.
   The frontend ignores `trace`.
   ===================================================================== */
(function () {
  let SELECTED = null;   // the lecturer chosen from the search results

  /* ---------- API ---------- */
  // FastAPI "detail" can be a string or a list of { msg, loc } objects.
  function formatDetail(detail) {
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) return detail.map(d => (d && d.msg) || "").filter(Boolean).join("; ");
    return "";
  }

  async function post(url, body, messages) {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", accept: "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      let detail = "";
      try { detail = formatDetail((await res.json()).detail); } catch (_) {}
      const msg = Object.assign({
        422: "Please check your input.",
        503: "The timetable database is unavailable right now. Please try again later.",
      }, messages)[res.status] || "The request failed (" + res.status + ").";
      throw new Error(detail && res.status !== 503 ? msg + " " + detail : msg);
    }
    return res.json();
  }

  const apiSearchLecturers = lecturerName =>
    post(`/api/lecturers/search`, { lecturer_name: lecturerName }, { 404: "No lecturer could be found." });

  const apiLecturerSchedule = (id, date, time) =>
    post(`/api/lecturers/schedule`, { lecturer_name: String(id), date, time }, { 404: "That lecturer could not be found." });

  /* ---------- Helpers ---------- */
  const fmtDate = s => {
    const [y, m, d] = s.split("-").map(Number);
    return new Date(y, m - 1, d).toLocaleDateString("en-IE", { weekday: "short", day: "numeric", month: "short" });
  };
  // Backend times are UTC ("...Z"); show them in Irish local time.
  const fmtTime = s => new Date(s).toLocaleTimeString("en-IE", { hour: "2-digit", minute: "2-digit", hour12: false, timeZone: "Europe/Dublin" });
  const fmtDateTime = s => fmtDate(dublinDate(s)) + ", " + fmtTime(s);

  const setHint = (id, msg, isError) => {
    $(id).textContent = msg || "";
    $(id).classList.toggle("error", !!isError);
  };

  // Notes and non-ok messages shared by both calls.
  const optionsList = data => Array.isArray(data.options) && data.options.length
    ? `<ul>${data.options.map(o => `<li>${esc(typeof o === "string" ? o : JSON.stringify(o))}</li>`).join("")}</ul>`
    : "";
  const statusBox = (data, fallback) =>
    `<div class="status-msg" style="white-space:pre-line">${esc(data.summary || fallback)}${optionsList(data)}</div>`;
  const aiNote = data => data.ai_note ? `<div class="ai-note"><strong>AI note:</strong> ${esc(data.ai_note)}</div>` : "";

  /* ---------- Phone-style time wheels (same picker as Room Locator) ---------- */
  // The hidden input holds the confirmed HH:MM; minutes go in 5-minute steps.
  const timeInput = $("lectTime");
  const hourWheel = makeWheel($("lectHour"), () => {});
  const minuteWheel = makeWheel($("lectMinute"), () => {});
  hourWheel.set(Array.from({ length: 24 }, (_, i) => String(i).padStart(2, "0")));
  minuteWheel.set(Array.from({ length: 12 }, (_, i) => String(i * 5).padStart(2, "0")));
  const timePicker = makePicker({
    box: $("lectTimePicker"), btn: $("lectTimeBtn"), text: $("lectTimeText"),
    panel: $("lectTimePanel"), done: $("lectTimeDone"), input: timeInput, focusEl: $("lectHour"),
    empty: "--:--", display: v => v,
    reset: v => { const [h, m] = v.split(":"); hourWheel.select(h); minuteWheel.select(m); },
    read: () => hourWheel.value() + ":" + minuteWheel.value(),
  });

  function setTime(hhmm) {
    let [h, m] = hhmm.split(":").map(Number);
    m = Math.min(55, Math.round(m / 5) * 5);   // snap to the 5-minute grid
    timeInput.value = String(h).padStart(2, "0") + ":" + String(m).padStart(2, "0");
    hourWheel.select(String(h).padStart(2, "0"));
    minuteWheel.select(String(m).padStart(2, "0"));
    timePicker.show();
  }
  setTime("09:00");

  /* ---------- Step 1: search ---------- */
  // The result can be one lecturer or a list of candidates, so accept both shapes.
  function readCandidates(data) {
    const d = ((data.facts || {}).search_lecturer || {}).data;
    if (!d) return [];
    if (Array.isArray(d)) return d;
    const list = d.candidates || d.lecturers || d.matches || d.results;
    if (Array.isArray(list)) return list;
    return d.id !== undefined ? [d] : [];
  }

  function resetBelow() {
    SELECTED = null;
    $("lectResultsCard").classList.add("hidden");
    $("lectScheduleCard").classList.add("hidden");
    $("lectScheduleResultCard").classList.add("hidden");
    setHint("lectScheduleHint", "");
  }

  async function runSearch() {
    const name = $("lectName").value.trim();
    resetBelow();
    if (!name) { setHint("lectHint", "Please enter a lecturer name.", true); return; }
    setHint("lectHint", "");

    $("lectResultsCard").classList.remove("hidden");
    $("lectResultsSub").textContent = "";
    $("lectResultsBody").innerHTML = `<div class="loading"><div class="spinner"></div>Searching for lecturers…</div>`;
    $("lectSearchBtn").disabled = true;
    try {
      renderCandidates(await apiSearchLecturers(name), name);
    } catch (e) {
      $("lectResultsBody").innerHTML = `<p class="error">${esc(e.message)}</p>`;
    } finally {
      $("lectSearchBtn").disabled = false;
    }
  }

  function lecturerCard(l) {
    const label = l.full_name || l.redbrick_identifier || "Lecturer " + l.id;
    const id = l.redbrick_identifier && l.full_name ? `<div class="lect-id">${esc(l.redbrick_identifier)}</div>` : "";
    const mods = l.modules ? `<div class="lect-modules">${esc(l.modules)}</div>` : "";
    return `<button type="button" class="lect" data-id="${esc(l.id)}"><div class="lect-name">${esc(label)}</div>${id}${mods}</button>`;
  }

  function renderCandidates(data, query) {
    $("lectResultsSub").textContent = `Results for “${query}”`;
    const status = data.status || "ok";
    const list = status === "ok" ? readCandidates(data).filter(l => l && l.id !== undefined && l.id !== null) : [];

    // none / ambiguous / error: show the backend's message only
    if (status !== "ok" || !list.length) {
      $("lectResultsBody").innerHTML = statusBox(data, "No lecturers were found for that search.");
      return;
    }

    let html = `<p class="lect-summary">${esc(data.summary || "")}</p>`;
    html += `<p class="sub">${list.length === 1 ? "Select the lecturer to check their schedule." : "Select a lecturer to check their schedule."}</p>`;
    html += `<div class="lect-list">${list.map(lecturerCard).join("")}</div>`;
    html += aiNote(data);
    $("lectResultsBody").innerHTML = html;

    const byId = new Map(list.map(l => [String(l.id), l]));
    $("lectResultsBody").querySelectorAll(".lect").forEach(btn =>
      btn.addEventListener("click", () => selectLecturer(byId.get(btn.dataset.id), btn)));

    // A single match is selected for the person straight away.
    if (list.length === 1) selectLecturer(list[0], $("lectResultsBody").querySelector(".lect"));
  }

  /* ---------- Step 3: schedule form ---------- */
  function selectLecturer(l, btn) {
    SELECTED = l;
    document.querySelectorAll("#lectResultsBody .lect").forEach(b => b.classList.toggle("active", b === btn));
    $("lectScheduleResultCard").classList.add("hidden");
    setHint("lectScheduleHint", "");
    $("lectScheduleSub").textContent = "Choose a date and time to see where " + (l.full_name || l.redbrick_identifier || "this lecturer") + " is.";
    if (!$("lectDate").value) $("lectDate").value = iso(new Date());
    $("lectScheduleCard").classList.remove("hidden");
  }

  /* ---------- Step 4: schedule ---------- */
  async function runSchedule() {
    if (!SELECTED) { setHint("lectScheduleHint", "Please select a lecturer first.", true); return; }
    const date = $("lectDate").value, time = $("lectTime").value;
    $("lectScheduleResultCard").classList.add("hidden");
    if (!date) { setHint("lectScheduleHint", "Please choose a date.", true); return; }
    if (!time) { setHint("lectScheduleHint", "Please choose a time.", true); return; }
    setHint("lectScheduleHint", "");

    $("lectScheduleResultCard").classList.remove("hidden");
    $("lectScheduleResultSub").textContent =
      `${SELECTED.full_name || SELECTED.redbrick_identifier} · ${fmtDate(date)}, ${time}`;
    $("lectScheduleResultBody").innerHTML = `<div class="loading"><div class="spinner"></div>Checking schedule…</div>`;
    $("lectScheduleBtn").disabled = true;
    try {
      renderSchedule(await apiLecturerSchedule(SELECTED.id, date, time));
    } catch (e) {
      $("lectScheduleResultBody").innerHTML = `<p class="error">${esc(e.message)}</p>`;
    } finally {
      $("lectScheduleBtn").disabled = false;
    }
  }

    function renderSchedule(data) {
        const status = data.status || "ok";
        const f = data.facts || {};
        const isObj = o => o && typeof o === "object";
        const current = (f.get_lecturer_schedule || {}).data;
        const next = (f.find_next_lecturer || {}).data;
        const s = isObj(current) ? current : (isObj(next) ? next : null);
        const isNext = !isObj(current) && !!s;

        // nothing at the requested time AND no next class: show the backend's message only
        if (status !== "ok" || !s) {
            $("lectScheduleResultBody").innerHTML = statusBox(data, "No class was found for this lecturer.");
            return;
        }

        const row = (label, value) => value ? `<div class="lect-row"><strong>${label}:</strong> ${esc(value)}</div>` : "";
        const when = s.start_time && s.end_time ? `${fmtDateTime(s.start_time)} to ${fmtTime(s.end_time)}` : "";
        let html = `<p class="lect-summary" style="white-space:pre-line">${esc(data.summary || "")}</p>`;
        html += `<div class="lect-detail">
      ${isNext ? `<div class="lect-row"><strong>Next class</strong></div>` : ""}
      <div class="lect-module">${esc(s.module_name || "Class")}</div>
      ${row("Room", s.room_name)}
      ${row("When", when)}
      ${row("Lecturer", s.staff_member)}
    </div>`;
        html += aiNote(data);
        html += `<p class="room-caveat">Times shown in Irish local time (Europe/Dublin).</p>`;
        $("lectScheduleResultBody").innerHTML = html;
    }

  /* ---------- Wire up ---------- */
  $("lectSearchBtn").addEventListener("click", runSearch);
  $("lectName").addEventListener("keydown", e => { if (e.key === "Enter") runSearch(); });
  $("lectName").addEventListener("input", () => { setHint("lectHint", ""); });
  ["lectDate", "lectTime"].forEach(id =>
    $(id).addEventListener("change", () => $("lectScheduleResultCard").classList.add("hidden")));
  $("lectScheduleBtn").addEventListener("click", runSchedule);
})();