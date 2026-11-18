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

/* ===================== Feature switcher ===================== */
document.querySelectorAll(".switcher button").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".switcher button").forEach(b => b.classList.toggle("active", b === btn));
    document.querySelectorAll(".panel").forEach(p => p.classList.remove("active"));
    $("panel-" + btn.dataset.feature).classList.add("active");
  });
});
