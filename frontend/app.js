/* =====================================================================
   app.js: shared core
   ---------------------------------------------------------------------
   Loaded first. Holds config, helpers and the feature switcher that every
   feature file relies on. Each feature lives in its own file:
     featureA.js  Student Timetable
     featureB.js  Feature B (placeholder)
     featureC.js  Feature C (placeholder)
   ===================================================================== */
const API_BASE = "";

/* ===================== Helpers (shared by all features) ===================== */
const $ = id => document.getElementById(id);
const fmtDay = d => d.toLocaleDateString("en-IE", { day: "numeric", month: "short" });
const iso = d => d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");
const esc = s => String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
// Calendar date (YYYY-MM-DD) of a timestamp in Irish local time, so events land on the right day.
const dublinDate = s => new Date(s).toLocaleDateString("en-CA", { timeZone: "Europe/Dublin" });

/* ===================== Phone-style time wheels (shared by Feature B and C) ===================== */
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

/* ===================== Feature switcher ===================== */
document.querySelectorAll(".switcher button").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".switcher button").forEach(b => b.classList.toggle("active", b === btn));
    document.querySelectorAll(".panel").forEach(p => p.classList.remove("active"));
    $("panel-" + btn.dataset.feature).classList.add("active");
  });
});

// Buttons on the home page (data-goto="A" etc.) open the matching feature.
document.querySelectorAll("[data-goto]").forEach(el => {
  el.addEventListener("click", () => {
    const target = document.querySelector('.switcher button[data-feature="' + el.dataset.goto + '"]');
    if (target) target.click();
  });
});