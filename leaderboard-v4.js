/* VulcanBench-SWE v4 board: pick models and an effort level; charts, frontier and table follow. */
(function () {
  "use strict";
  var DATA = window.VB_V4;
  var app = document.getElementById("v4app");
  if (!DATA || !app) return;
  var COLORS = DATA.colors, EFFORTS = DATA.efforts, COLS = DATA.columns;
  var LABEL = { low: "Low", medium: "Medium", high: "High", "extra-high": "Extra-high", max: "Max" };
  var MODELS = [];
  COLS.forEach(function (c) { if (!MODELS.some(function (m) { return m.key === c.key; })) MODELS.push({ key: c.key, name: c.model, harness: c.harness, slug: c.slug }); });
  var state = { models: {}, mode: "best", metric: "combined" };
  MODELS.forEach(function (m) { state.models[m.key] = true; });
  try {
    var saved = JSON.parse(localStorage.getItem("vb_v4_board") || "null");
    if (saved && saved.models && saved.mode) { state.mode = saved.mode; MODELS.forEach(function (m) { if (m.key in saved.models) state.models[m.key] = !!saved.models[m.key]; }); }
  } catch (e) { /* storage unavailable */ }

  var METRICS = [
    { key: "combined", title: "Combined score", sub: "out of 100, higher is better", fmt: function (r) { return r.combined.toFixed(2); }, val: function (r) { return r.combined; }, max: 100, se: function (r) { return r.combined_se; } },
    { key: "code_quality", title: "Code quality", sub: "out of 100, judged by Muse Spark 1.3 and Grok 4.6", fmt: function (r) { return r.code_quality.toFixed(2); }, val: function (r) { return r.code_quality; }, max: 100 },
    { key: "passed", title: "Tasks passed", sub: "perfect functional score, share of the cell", fmt: function (r) { return r.passed + "/" + r.n; }, val: function (r) { return 100 * r.passed / r.n; }, max: 100 },
    { key: "minutes", title: "Runtime", sub: "minutes per task, lower is better", fmt: function (r) { return r.minutes.toFixed(1) + " min"; }, val: function (r) { return r.minutes; }, lower: true },
    { key: "usd", title: "API-equivalent cost", sub: "USD per task at list rates, lower is better", fmt: function (r) { return "$" + r.usd.toFixed(2); }, val: function (r) { return r.usd; }, lower: true }
  ];

  function esc(s) { return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;"); }
  function shade(key, effort) {
    if (state.mode !== "all") return COLORS[key];
    var i = EFFORTS.indexOf(effort), a = 0.45 + 0.55 * i / (EFFORTS.length - 1);
    return "color-mix(in srgb, " + COLORS[key] + " " + Math.round(a * 100) + "%, white)";
  }
  function selection() {
    return COLS.filter(function (c) {
      if (!state.models[c.key]) return false;
      if (state.mode === "best") return c.best;
      if (state.mode === "all") return true;
      return c.effort === state.mode;
    });
  }
  function save() {
    try { localStorage.setItem("vb_v4_board", JSON.stringify({ models: state.models, mode: state.mode })); } catch (e) { /* ignore */ }
  }

  function controls() {
    var chips = MODELS.map(function (m) {
      var on = state.models[m.key];
      return '<button type="button" class="v4chip' + (on ? " on" : "") + '" data-model="' + m.key + '" aria-pressed="' + (on ? "true" : "false") + '">' +
        '<span class="v4dot" style="background:' + COLORS[m.key] + '"></span>' + esc(m.name) + ' <span class="v4h">' + esc(m.harness) + "</span></button>";
    }).join("");
    var modes = [["best", "Best level per model"]].concat(EFFORTS.map(function (e) { return [e, LABEL[e]]; })).concat([["all", "All levels"]]);
    var tabs = modes.map(function (m) {
      return '<button type="button" role="tab" class="' + (state.mode === m[0] ? "active" : "") + '" aria-selected="' + (state.mode === m[0] ? "true" : "false") + '" data-mode="' + m[0] + '">' + m[1] + "</button>";
    }).join("");
    return '<div class="v4controls">' +
      '<div class="v4group"><span class="v4label">Models</span><div class="v4chips">' + chips +
      '<button type="button" class="v4chip v4all" data-act="all">All</button><button type="button" class="v4chip v4all" data-act="none">None</button></div></div>' +
      '<div class="v4group"><span class="v4label">Effort</span><div class="lb-toggle chart-toggle on v4modes" role="tablist" aria-label="Effort level">' + tabs + "</div></div>" +
      "</div>";
  }

  function labelFor(r) {
    var name = esc(r.model);
    if (state.mode === "best") return name + ' <span class="eff">&middot; ' + LABEL[r.effort] + "</span>";
    if (state.mode === "all") return name + ' <span class="eff">&middot; ' + LABEL[r.effort] + "</span>" + (r.best ? '<span class="bst">best</span>' : "");
    return name;
  }

  function barCard(metric, rows) {
    var sorted = rows.slice().sort(function (a, b) { return metric.lower ? metric.val(a) - metric.val(b) : metric.val(b) - metric.val(a); });
    var top = metric.max || Math.max.apply(null, sorted.map(metric.val)) * 1.08;
    var html = sorted.map(function (r) {
      var v = metric.val(r), w = Math.max(1.5, 100 * v / top);
      var se = metric.se ? metric.se(r) : 0;
      var whisker = se ? '<span class="v4se" style="left:' + (100 * (v - se) / top) + '%;width:' + (100 * 2 * se / top) + '%"></span>' : "";
      return '<div class="bc-row"><div class="bc-lab">' + labelFor(r) + '</div><div class="bc-track"><div class="v4barwrap"><div class="bc-bar" style="width:' + w.toFixed(2) + '%;background:' + shade(r.key, r.effort) + '"></div>' + whisker + '</div><span class="bc-val">' + metric.fmt(r) + "</span></div></div>";
    }).join("");
    return '<figure class="v4card"><figcaption><b>' + metric.title + "</b><span>" + metric.sub + (metric.se ? "; whiskers are one task standard error" : "") + "</span></figcaption>" +
      '<div class="bc-chart">' + html + "</div></figure>";
  }

  function scatter(rows, xKey, xLabel, log) {
    var W = 720, H = 400, L = 56, R = 24, T = 18, B = 48;
    var xs = rows.map(function (r) { return r[xKey]; }), ys = rows.map(function (r) { return r.combined; });
    var xmin = Math.min.apply(null, xs), xmax = Math.max.apply(null, xs);
    if (log) { xmin = Math.pow(10, Math.floor(Math.log10(xmin))); xmax = Math.pow(10, Math.ceil(Math.log10(xmax))); }
    else { xmin = 0; xmax = Math.ceil(xmax / 10) * 10; }
    var ymin = Math.max(0, Math.floor((Math.min.apply(null, ys) - 5) / 10) * 10), ymax = 100;
    function X(v) { var f = log ? (Math.log10(v) - Math.log10(xmin)) / (Math.log10(xmax) - Math.log10(xmin)) : (v - xmin) / (xmax - xmin); return L + f * (W - L - R); }
    function Y(v) { return T + (1 - (v - ymin) / (ymax - ymin)) * (H - T - B); }
    var g = "";
    for (var y = ymin; y <= ymax; y += 10) g += '<line x1="' + L + '" y1="' + Y(y).toFixed(1) + '" x2="' + (W - R) + '" y2="' + Y(y).toFixed(1) + '" stroke="#1c1a17" stroke-opacity="0.08"/><text x="' + (L - 8) + '" y="' + (Y(y) + 4).toFixed(1) + '" text-anchor="end" font-size="11" fill="#6f6a62">' + y + "</text>";
    var ticks = [];
    if (log) { for (var p = Math.log10(xmin); p <= Math.log10(xmax); p++) ticks.push(Math.pow(10, p)); }
    else { for (var t = xmin; t <= xmax; t += 10) ticks.push(t); }
    ticks.forEach(function (t) { g += '<line x1="' + X(t).toFixed(1) + '" y1="' + T + '" x2="' + X(t).toFixed(1) + '" y2="' + (H - B) + '" stroke="#1c1a17" stroke-opacity="0.06"/><text x="' + X(t).toFixed(1) + '" y="' + (H - B + 16) + '" text-anchor="middle" font-size="11" fill="#6f6a62">' + (xKey === "usd" ? "$" + (t < 1 ? t.toFixed(2) : t) : t) + "</text>"; });
    g += '<text x="' + ((L + W - R) / 2).toFixed(1) + '" y="' + (H - 8) + '" text-anchor="middle" font-size="12" fill="#3a362f">' + xLabel + "</text>";
    g += '<text transform="translate(14 ' + ((T + H - B) / 2).toFixed(1) + ') rotate(-90)" text-anchor="middle" font-size="12" fill="#3a362f">Combined score</text>';
    if (state.mode === "all") {
      MODELS.forEach(function (m) {
        var pts = rows.filter(function (r) { return r.key === m.key; }).sort(function (a, b) { return EFFORTS.indexOf(a.effort) - EFFORTS.indexOf(b.effort); });
        if (pts.length > 1) g += '<polyline fill="none" stroke="' + COLORS[m.key] + '" stroke-width="1.6" stroke-opacity="0.7" points="' + pts.map(function (r) { return X(r[xKey]).toFixed(1) + "," + Y(r.combined).toFixed(1); }).join(" ") + '"/>';
      });
    }
    var placed = [];
    rows.slice().sort(function (a, b) { return b.combined - a.combined; }).forEach(function (r) {
      var x = X(r[xKey]), y = Y(r.combined);
      var tip = esc(r.model) + " " + LABEL[r.effort] + ": " + r.combined.toFixed(2) + ", " + (xKey === "usd" ? "$" + r.usd.toFixed(2) : r.minutes.toFixed(1) + " min") + " per task";
      g += '<circle cx="' + x.toFixed(1) + '" cy="' + y.toFixed(1) + '" r="5.5" fill="' + shade(r.key, r.effort) + '" stroke="#1c1a17" stroke-width="0.8"><title>' + tip + "</title></circle>";
      if (state.mode === "all" && !r.best) return;  // one label per model on the ladder view; every point keeps its tooltip
      var text = state.mode === "best" || state.mode === "all" ? esc(r.model) : esc(r.model) + " " + LABEL[r.effort].toLowerCase();
      var ty = y - 9, tx = x;
      var anchor = x > W - 150 ? "end" : "start";
      if (anchor === "start") tx = x + 8; else tx = x - 8;
      while (placed.some(function (q) { return Math.abs(q[0] - tx) < 90 && Math.abs(q[1] - ty) < 12; })) ty += 12;
      placed.push([tx, ty]);
      g += '<text x="' + tx.toFixed(1) + '" y="' + ty.toFixed(1) + '" text-anchor="' + anchor + '" font-size="11" fill="#1c1a17">' + text + "</text>";
    });
    return '<svg viewBox="0 0 ' + W + " " + H + '" xmlns="http://www.w3.org/2000/svg" role="img" font-family="IBM Plex Mono, SF Mono, monospace"><title>Combined score against ' + xLabel + "</title>" + g + "</svg>";
  }

  function render() {
    var rows = selection();
    var head = controls();
    if (!rows.length) {
      app.innerHTML = head + '<div class="bc-empty">No models picked. Choose at least one model above.</div>';
    } else {
      var cards = METRICS.map(function (m) { return barCard(m, rows); }).join("");
      var lead = rows.slice().sort(function (a, b) { return b.combined - a.combined; })[0];
      var cheapest = rows.slice().sort(function (a, b) { return a.usd - b.usd; })[0];
      var fastest = rows.slice().sort(function (a, b) { return a.minutes - b.minutes; })[0];
      var strip = '<div class="v4strip">' +
        '<div><span class="v4k">Highest combined score</span><b>' + esc(lead.model) + " " + LABEL[lead.effort] + "</b><span>" + lead.combined.toFixed(2) + "</span></div>" +
        '<div><span class="v4k">Cheapest per task</span><b>' + esc(cheapest.model) + " " + LABEL[cheapest.effort] + "</b><span>$" + cheapest.usd.toFixed(2) + "</span></div>" +
        '<div><span class="v4k">Fastest per task</span><b>' + esc(fastest.model) + " " + LABEL[fastest.effort] + "</b><span>" + fastest.minutes.toFixed(1) + " min</span></div></div>";
      var plots = '<div class="v4plots">' +
        '<figure class="v4card v4wide"><figcaption><b>Score against cost</b><span>combined score against API-equivalent $ per task, log scale' + (state.mode === "all" ? "; a line joins each model’s effort ladder from Low to Max, the label sits on its best level, hover any point" : "") + "</span></figcaption>" + scatter(rows, "usd", "API-equivalent $ per task", true) + "</figure>" +
        '<figure class="v4card v4wide"><figcaption><b>Score against runtime</b><span>combined score against minutes per task' + (state.mode === "all" ? "; a line joins each model’s effort ladder from Low to Max, the label sits on its best level, hover any point" : "") + "</span></figcaption>" + scatter(rows, "minutes", "Minutes per task", false) + "</figure></div>";
      app.innerHTML = head + strip + '<div class="v4grid">' + cards + "</div>" + plots;
    }
    var shown = {};
    rows.forEach(function (r) { shown[r.key + "/" + r.effort] = true; });
    Array.prototype.forEach.call(document.querySelectorAll("#v4board tr.v4row"), function (tr) {
      tr.hidden = !shown[tr.getAttribute("data-model") + "/" + tr.getAttribute("data-effort")];
    });
    save();
  }

  app.addEventListener("click", function (e) {
    var el = e.target.closest ? e.target.closest("button") : null;
    if (!el) return;
    if (el.hasAttribute("data-model")) { var k = el.getAttribute("data-model"); state.models[k] = !state.models[k]; }
    else if (el.hasAttribute("data-act")) { var on = el.getAttribute("data-act") === "all"; MODELS.forEach(function (m) { state.models[m.key] = on; }); }
    else if (el.hasAttribute("data-mode")) { state.mode = el.getAttribute("data-mode"); }
    else return;
    render();
    if (typeof window.gtag === "function") window.gtag("event", "lb_v4_filter", { mode: state.mode, models: MODELS.filter(function (m) { return state.models[m.key]; }).length });
  });
  render();
})();
