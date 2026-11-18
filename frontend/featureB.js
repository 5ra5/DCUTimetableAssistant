/* =====================================================================
   featureB.js: Room Locator
   ---------------------------------------------------------------------
   Requires app.js ($, esc, iso, API_BASE). UI lives in #panel-B.
   Wrapped in an IIFE so its names never clash with other feature files.
   Backend routes:
     GET  /api/rooms/options   populates the form (buildings, durations, limits)
     POST /api/rooms/search    { building_code, date, start_time,
                                 duration_minutes, search_preference }
   Nothing is hard-coded: buildings, preferences, durations, date limits and
   search hours all come from the options response.
   ===================================================================== */
(function () {
  let OPTIONS = null;

  /* ---------- API ---------- */
  // FastAPI "detail" can be a string or a list of { msg, loc } objects.
  function formatDetail(detail) {
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) return detail.map(d => (d && d.msg) || "").filter(Boolean).join("; ");
    return "";
  }

  async function apiGetRoomOptions() {
    const res = await fetch(`/api/rooms/options`, { headers: { accept: "application/json" } });
    if (!res.ok) throw new Error("Could not load room search options (" + res.status + ")");
    return res.json();
  }

  async function apiSearchRooms(body) {
    const res = await fetch(`/api/rooms/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json", accept: "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      let detail = "";
      try { detail = formatDetail((await res.json()).detail); } catch (_) {}
      const msg = {
        404: "That building could not be found or can't be searched.",
        422: "Please check your search.",
        503: "The timetable database is unavailable right now. Please try again later.",
      }[res.status] || "The search failed (" + res.status + ").";
      throw new Error(detail && res.status !== 503 ? msg + " " + detail : msg);
    }
    return res.json();
  }

  /* ---------- Helpers ---------- */
  const toMins = hhmm => { const [h, m] = hhmm.split(":").map(Number); return h * 60 + m; };
  const toHHMM = mins => String(Math.floor(mins / 60)).padStart(2, "0") + ":" + String(mins % 60).padStart(2, "0");
  const fmtDate = s => {
    const [y, m, d] = s.split("-").map(Number);
    return new Date(y, m - 1, d).toLocaleDateString("en-IE", { weekday: "short", day: "numeric", month: "short" });
  };
  const fmtDuration = n => {
    if (n < 60) return n + " minutes";
    const h = Math.floor(n / 60), m = n % 60;
    return (h === 1 ? "1 hour" : h + " hours") + (m ? " " + m + " min" : "");
  };
  const setHint = (msg, isError) => {
    $("roomHint").textContent = msg || "";
    $("roomHint").classList.toggle("error", !!isError);
  };

  /* ---------- Phone-style time wheels ---------- */
  const ROW = 40;   // must match .wheel .opt height in style.css
  function makeWheel(el, onPick) {
    let values = [], cur = null, timer;
    const index = () => Math.max(0, Math.min(values.length - 1, Math.round(el.scrollTop / ROW)));
    const mark = () => {
      const i = index();
      [...el.children].forEach((c, j) => { c.classList.toggle("sel", j === i); c.setAttribute("aria-selected", j === i); });
    };
    const goTo = (i, smooth) => el.scrollTo({ top: Math.max(0, Math.min(values.length - 1, i)) * ROW, behavior: smooth ? "smooth" : "auto" });
    el.addEventListener("scroll", () => {
      mark();
      clearTimeout(timer);
      timer = setTimeout(() => { cur = values[index()]; onPick(cur); }, 120);   // after the wheel settles
    });
    el.addEventListener("click", e => {
      const o = e.target.closest(".opt");
      if (o) goTo([...el.children].indexOf(o), true);
    });
    el.addEventListener("keydown", e => {
      if (e.key !== "ArrowDown" && e.key !== "ArrowUp") return;
      e.preventDefault();
      goTo(index() + (e.key === "ArrowDown" ? 1 : -1), true);
    });
    // The panel can be hidden (display:none) when the value is set; re-apply once it is shown.
    new ResizeObserver(() => { if (el.clientHeight && cur !== null) { goTo(values.indexOf(cur), false); mark(); } }).observe(el);
    return {
      cur: () => cur,
      value: () => values[index()],   // what the wheel is showing right now, even mid-settle
      set(list, label = v => v) {   // label() turns a value into the text shown on the wheel
        values = list;
        el.innerHTML = list.map(v => `<div class="opt" role="option">${label(v)}</div>`).join("");
        cur = list[0];
      },
      select(v) {
        cur = values.includes(v) ? v : values[0];
        goTo(values.indexOf(cur), false);
        mark();
      },
    };
  }

  // Collapsible picker: a compact box showing the confirmed value that expands in place
  // into scroll wheels with a Confirm button. Scrolling only previews a value; Confirm
  // commits it to the hidden input. Clicking elsewhere or pressing Escape closes the
  // wheels without changing anything.
  function makePicker({ box, btn, text, panel, done, input, focusEl, empty, display, reset, read }) {
    const show = () => { text.textContent = input.value ? display(input.value) : empty; };
    const open = () => {
      if (!input.value) return;                 // options not loaded yet
      panel.classList.remove("hidden");
      btn.setAttribute("aria-expanded", "true");
      reset(input.value);                       // start the wheels on the confirmed value
      focusEl.focus({ preventScroll: true });
    };
    const close = () => { panel.classList.add("hidden"); btn.setAttribute("aria-expanded", "false"); };
    const confirm = () => {
      const v = read();
      if (v !== input.value) { input.value = v; input.dispatchEvent(new Event("change")); }
      show(); close(); btn.focus();
    };
    btn.addEventListener("click", open);
    done.addEventListener("click", confirm);
    document.addEventListener("pointerdown", e => {
      if (!panel.classList.contains("hidden") && !box.contains(e.target)) close();
    });
    panel.addEventListener("keydown", e => {
      if (e.key === "Escape") { close(); btn.focus(); }
      else if (e.key === "Enter" && e.target !== done) { e.preventDefault(); confirm(); }
    });
    return { show };
  }

  // Start time (hidden input holds the confirmed HH:MM)
  const startInput = $("roomStart");
  const hourWheel = makeWheel($("roomHour"), () => {});
  const minuteWheel = makeWheel($("roomMinute"), () => {});
  minuteWheel.set(Array.from({ length: 12 }, (_, i) => String(i * 5).padStart(2, "0")));
  const startPicker = makePicker({
    box: $("roomTimePicker"), btn: $("roomTimeBtn"), text: $("roomTimeText"),
    panel: $("roomTimePanel"), done: $("roomTimeDone"), input: startInput, focusEl: $("roomHour"),
    empty: "--:--", display: v => v,
    reset: v => { const [h, m] = v.split(":"); hourWheel.select(h); minuteWheel.select(m); },
    read: () => hourWheel.value() + ":" + minuteWheel.value(),
  });

  function setTime(hhmm) {
    let [h, m] = hhmm.split(":").map(Number);
    m = Math.min(55, Math.round(m / 5) * 5);   // snap to the 5-minute grid
    startInput.value = String(h).padStart(2, "0") + ":" + String(m).padStart(2, "0");
    hourWheel.select(String(h).padStart(2, "0"));
    minuteWheel.select(String(m).padStart(2, "0"));
    startPicker.show();
  }

  // Duration: the wheel shows "1 hour 30 min" etc. but the hidden input holds minutes ("90")
  const durationInput = $("roomDuration");
  const durationWheel = makeWheel($("roomDurationWheel"), () => {});
  const durationPicker = makePicker({
    box: $("roomDurationPicker"), btn: $("roomDurationBtn"), text: $("roomDurationText"),
    panel: $("roomDurationPanel"), done: $("roomDurationDone"), input: durationInput, focusEl: $("roomDurationWheel"),
    empty: "--", display: v => fmtDuration(Number(v)),
    reset: v => durationWheel.select(v),
    read: () => durationWheel.value(),
  });

  /* ---------- Form setup ---------- */
  function fillForm(o) {
    const bSel = $("roomBuilding");
    bSel.innerHTML = "";
    bSel.add(new Option("Select a building…", ""));
    (o.buildings || []).forEach(b =>
      bSel.add(new Option(`${b.name} (${b.code}), ${b.room_count} room${b.room_count === 1 ? "" : "s"}`, b.code)));

    const durs = (o.durations_minutes || []).map(String);
    durationWheel.set(durs, v => fmtDuration(Number(v)));
    const startDur = durs.includes("60") ? "60" : (durs[0] || "");
    durationInput.value = startDur;
    durationWheel.select(startDur);
    durationPicker.show();

    const pSel = $("roomPreference");
    pSel.innerHTML = "";
    (o.search_preferences || []).forEach(p => pSel.add(new Option(p.label, p.value)));
    if ((o.search_preferences || []).some(p => p.value === "closest_buildings")) pSel.value = "closest_buildings";

    const date = $("roomDate");
    if (o.date_min) date.min = o.date_min;
    if (o.date_max) date.max = o.date_max;
    let today = iso(new Date());
    if (o.date_min && today < o.date_min) today = o.date_min;
    if (o.date_max && today > o.date_max) today = o.date_max;
    date.value = today;

    // Hours only cover the allowed search window; minutes go in 5-minute steps.
    const h0 = o.earliest_start ? parseInt(o.earliest_start, 10) : 0;
    const h1 = o.latest_finish ? parseInt(o.latest_finish, 10) : 23;
    hourWheel.set(Array.from({ length: h1 - h0 + 1 }, (_, i) => String(h0 + i).padStart(2, "0")));
    setTime(o.earliest_start || String(h0).padStart(2, "0") + ":00");

    const usable = (o.buildings || []).length > 0 && o.date_min && o.date_max;
    $("roomSearchBtn").disabled = !usable;
    if (!usable) setHint("No timetable coverage is available yet, so rooms can't be searched.", true);
  }

  async function loadRoomOptions() {
    $("roomBuilding").innerHTML = `<option value="">Loading buildings…</option>`;
    try {
      OPTIONS = await apiGetRoomOptions();
      fillForm(OPTIONS);
    } catch (e) {
      $("roomBuilding").innerHTML = `<option value="">Buildings unavailable</option>`;
      setHint(e.message + ". Is the backend running on " + API_BASE + "?", true);
    }
  }

  /* ---------- Validate and search ---------- */
  function readForm() {
    return {
      building_code: $("roomBuilding").value,
      date: $("roomDate").value,
      start_time: $("roomStart").value,
      duration_minutes: parseInt($("roomDuration").value, 10),
      search_preference: $("roomPreference").value,
    };
  }

  function validate(f) {
    if (!f.building_code) return "Please select a building.";
    if (!f.date) return "Please choose a date.";
    if (OPTIONS.date_min && f.date < OPTIONS.date_min || OPTIONS.date_max && f.date > OPTIONS.date_max)
      return `Please choose a date between ${fmtDate(OPTIONS.date_min)} and ${fmtDate(OPTIONS.date_max)}.`;
    if (!f.start_time) return "Please choose a start time.";
    if (!f.duration_minutes) return "Please choose a duration.";
    if (!f.search_preference) return "Please choose a search area.";
    const start = toMins(f.start_time), end = start + f.duration_minutes;
    if (OPTIONS.earliest_start && start < toMins(OPTIONS.earliest_start))
      return `Rooms can only be searched from ${OPTIONS.earliest_start}.`;
    if (OPTIONS.latest_finish && end > toMins(OPTIONS.latest_finish))
      return `Your slot must finish by ${OPTIONS.latest_finish}. Choose an earlier start or a shorter duration.`;
    return "";
  }

  async function runSearch() {
    if (!OPTIONS) return;
    const f = readForm();
    const problem = validate(f);
    $("roomResultsCard").classList.add("hidden");
    if (problem) { setHint(problem, true); return; }

    $("roomResultsCard").classList.remove("hidden");
    $("roomResultsSub").textContent = "";
    $("roomResultsBody").innerHTML = `<div class="loading"><div class="spinner"></div>Searching for rooms…</div>`;
    $("roomSearchBtn").disabled = true;
    try {
      renderResults(await apiSearchRooms(f), f);
    } catch (e) {
      $("roomResultsBody").innerHTML = `<p class="error">${esc(e.message)}</p>`;
    } finally {
      $("roomSearchBtn").disabled = false;
    }
  }

  /* ---------- Render ---------- */
  function roomCard(r) {
    const bits = [];
    bits.push(r.free_until ? "Free until " + esc(r.free_until) : "No later event recorded that day");
    if (typeof r.distance_metres === "number") bits.push(Math.round(r.distance_metres) + " m from your building");
    const stage = r.stage && r.stage !== "preferred" ? `<div><span class="room-badge">${esc(String(r.stage).replace(/_/g, " "))}</span></div>` : "";
    return `<div class="room"><div class="room-name">${esc(r.room_name)}</div><div class="room-meta">${bits.join(" · ")}</div>${stage}</div>`;
  }

  function renderResults(data, f) {
    const facts = data.facts || {};
    const main = facts.find_rooms_in_building || {};
    const nearby = facts.find_rooms_nearby || {};
    const end = main.end_time || toHHMM(toMins(f.start_time) + f.duration_minutes);
    const bName = main.building_name || (OPTIONS.buildings.find(b => b.code === f.building_code) || {}).name || f.building_code;
    $("roomResultsSub").textContent = `${bName} · ${fmtDate(f.date)}, ${f.start_time} to ${end}`;

    const summary = `<p class="room-summary">${esc(data.summary || "No result summary was returned.")}</p>`;
    const status = data.status || "ok";

    // none / unsupported: show the backend's message only
    if (status !== "ok") {
      $("roomResultsBody").innerHTML = `<div class="status-msg" style="white-space:pre-line">${esc(data.summary || "No rooms were found for this slot.")}</div>`;
      return;
    }

    // Group rooms by building: the chosen building first, then any nearby buildings.
    const groups = new Map();
    const add = (r, countFor) => {
      const key = r.building_code || "";
      if (!groups.has(key)) groups.set(key, { name: r.building_name || key, code: key, rooms: [], count: countFor });
      groups.get(key).rooms.push(r);
    };
    (main.rooms || []).forEach(r => add(r, main.count));
    (nearby.rooms || []).forEach(r => add(r));

    let html = summary;
    groups.forEach(g => {
      const shown = g.rooms.length;
      const more = typeof g.count === "number" && g.count > shown ? `showing ${shown} of ${g.count}` : `${shown} room${shown === 1 ? "" : "s"}`;
      html += `<div class="room-group"><h3>${esc(g.name)} (${esc(g.code)})<span>${more}</span></h3><div class="room-list">${g.rooms.map(roomCard).join("")}</div></div>`;
    });
    if (!groups.size) html += `<div class="status-msg">No rooms were returned for this slot.</div>`;

    if (data.ai_note) html += `<div class="ai-note"><strong>AI note:</strong> ${esc(data.ai_note)}</div>`;
    const asOf = main.data_as_of || OPTIONS.data_as_of;
    $("roomResultsBody").innerHTML = html;
  }

  /* ---------- Wire up ---------- */
  ["roomBuilding", "roomDate", "roomStart", "roomDuration", "roomPreference"].forEach(id =>
    $(id).addEventListener("change", () => $("roomResultsCard").classList.add("hidden")));
  $("roomSearchBtn").addEventListener("click", runSearch);
  loadRoomOptions();
})();