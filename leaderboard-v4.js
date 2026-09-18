/* VulcanBench Frontier v4 board: pick models and an effort level; charts, frontier and table follow. */
(function () {
  "use strict";
  var DATA = window.VB_V4;
  var app = document.getElementById("v4app");
  if (!DATA || !app) return;
  var COLORS = DATA.colors, EFFORTS = DATA.efforts, COLS = DATA.columns;
  var LABEL = { low: "Low", medium: "Medium", high: "High", "extra-high": "Extra-high", max: "Max" };
  var MODELS = [];
  COLS.forEach(function (c) { if (!MODELS.some(function (m) { return m.key === c.key; })) MODELS.push({ key: c.key, name: c.model, harness: c.harness, slug: c.slug }); });
  var state = { models: {}, mode: "best", metric: "combined", tolerance: "routine" };
  var TOL = DATA.tolerances || { critical: 1, routine: 3, rough: 5 };
  var TOL_LABEL = { routine: "Routine tasks", critical: "Critical work", rough: "Rough passes" };
  MODELS.forEach(function (m) { state.models[m.key] = true; });
  try {
    var saved = JSON.parse(localStorage.getItem("vb_v4_board") || "null");
    if (saved && saved.models && saved.mode) { state.mode = saved.mode; if (saved.tolerance in TOL) state.tolerance = saved.tolerance; MODELS.forEach(function (m) { if (m.key in saved.models) state.models[m.key] = !!saved.models[m.key]; }); }
  } catch (e) { /* storage unavailable */ }

  var METRICS = [
    { key: "combined", title: "Combined score", sub: "out of 100, higher is better", fmt: function (r) { return r.combined.toFixed(2); }, val: function (r) { return r.combined; }, max: 100, se: function (r) { return r.combined_se; } },
    { key: "code_quality", title: "Code quality", sub: "out of 100, judged by Muse Spark 1.3 and Grok 4.6", fmt: function (r) { return r.code_quality.toFixed(2); }, val: function (r) { return r.code_quality; }, max: 100 },
    { key: "passed", title: "Tasks passed", sub: "perfect functional score, share of the cell", fmt: function (r) { return r.passed + "/" + r.n; }, val: function (r) { return 100 * r.passed / r.n; }, max: 100 },
    { key: "minutes", title: "Runtime", sub: "minutes per task, lower is better", fmt: function (r) { return r.minutes.toFixed(1) + " min"; }, val: function (r) { return r.minutes; }, lower: true },
    { key: "usd", title: "API-equivalent cost", sub: "USD per task at list rates, lower is better", fmt: function (r) { return "$" + r.usd.toFixed(2); }, val: function (r) { return r.usd; }, lower: true },
    { key: "tokens", title: "Completion tokens", sub: "median output tokens per task, reasoning included, lower is better", fmt: function (r) { return fmtTokens(r.output_tokens_median); }, val: function (r) { return r.output_tokens_median; }, lower: true }
  ];
  function fmtTokens(v) { return v >= 1e6 ? (v / 1e6).toFixed(2) + "M" : v >= 1e3 ? (v / 1e3).toFixed(1) + "k" : String(Math.round(v)); }
  function frontier(rows, xKey) {
    // Pareto frontier for "highest score at no more x": sort by x ascending, keep points that beat every cheaper one.
    var sorted = rows.slice().sort(function (a, b) { return a[xKey] - b[xKey] || b.combined - a.combined; });
    var best = -Infinity, out = [];
    sorted.forEach(function (r) { if (r.combined > best) { best = r.combined; out.push(r); } });
    return out;
  }

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
    try { localStorage.setItem("vb_v4_board", JSON.stringify({ models: state.models, mode: state.mode, tolerance: state.tolerance })); } catch (e) { /* ignore */ }
  }

  function controls() {
    var chips = MODELS.map(function (m) {
      var on = state.models[m.key];
      var shape = ladder(m.key).shape;
      return '<button type="button" class="v4chip' + (on ? " on" : "") + '" data-model="' + m.key + '" aria-pressed="' + (on ? "true" : "false") + '" title="' + (shape === "flat" ? "effort-flat: its best level is within 3 points of Low" : "effort-steep: Low trails its best level by more than 3 points") + '">' +
        '<span class="v4dot" style="background:' + COLORS[m.key] + '"></span>' + esc(m.name) + ' <span class="v4h">' + esc(m.harness) + '</span><span class="v4shape ' + shape + '">' + (shape === "flat" ? "effort-flat" : "effort-steep") + "</span></button>";
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

  function ladder(key) {
    var levels = COLS.filter(function (c) { return c.key === key; }).sort(function (a, b) { return EFFORTS.indexOf(a.effort) - EFFORTS.indexOf(b.effort); });
    var best = levels.reduce(function (a, b) { return b.combined > a.combined ? b : a; });
    var low = levels[0];
    return { levels: levels, best: best, low: low, spread: best.combined - low.combined, shape: best.combined - low.combined <= 3 ? "flat" : "steep" };
  }
  function suggest(key, tolerance) {
    var l = ladder(key), tol = TOL[tolerance];
    var ok = l.levels.filter(function (r) { return l.best.combined - r.combined <= tol; });
    var pick = ok.slice().sort(function (a, b) { return a.usd - b.usd || a.minutes - b.minutes; })[0];
    return { pick: pick, best: l.best, gap: l.best.combined - pick.combined, usdRatio: pick.usd / l.best.usd, minRatio: pick.minutes / l.best.minutes, ladder: l };
  }
  function pct(ratio) { return Math.round(ratio * 100) + "%"; }
  function ladderStrip(l, pickEffort) {
    // Dots on one scale: the model's Low score at the left edge, its best at the right edge, so a flat model bunches and a steep one spreads.
    var lo = Math.min.apply(null, l.levels.map(function (r) { return r.combined; })), hi = l.best.combined;
    var W = 100, span = Math.max(hi - lo, 0.001);
    var xs = l.levels.map(function (r) { return 4 + 92 * (r.combined - lo) / span; });
    var html = l.levels.map(function (r, i) {
      var x = xs[i];
      var picked = r.effort === pickEffort;
      // Labels drop to a second row when the previous label sits within 14% of this one, so flat ladders stay legible.
      var row = i > 0 && Math.abs(xs[i] - xs[i - 1]) < 14 && !(i > 1 && Math.abs(xs[i - 1] - xs[i - 2]) < 14 && i % 2 === 0) ? 1 : 0;
      return '<span class="v4lad-dot' + (picked ? " pick" : "") + '" style="left:' + x.toFixed(1) + '%;background:' + shade(r.key, r.effort) + '" title="' + LABEL[r.effort] + ": " + r.combined.toFixed(2) + '"></span>' +
        '<span class="v4lad-lab' + (picked ? " pick" : "") + (row ? " row2" : "") + '" style="left:' + x.toFixed(1) + '%">' + LABEL[r.effort] + "</span>";
    }).join("");
    return '<div class="v4lad"><div class="v4lad-line"></div>' + html + '</div><div class="v4lad-axis"><span>' + lo.toFixed(1) + "</span><span>" + hi.toFixed(1) + "</span></div>";
  }
  function suggestionSection() {
    var picked = MODELS.filter(function (m) { return state.models[m.key]; });
    var tabs = Object.keys(TOL).map(function (k) {
      return '<button type="button" role="tab" class="' + (state.tolerance === k ? "active" : "") + '" aria-selected="' + (state.tolerance === k ? "true" : "false") + '" data-tolerance="' + k + '">' + TOL_LABEL[k] + ' <span class="n">within ' + TOL[k] + (TOL[k] === 1 ? " pt" : " pts") + "</span></button>";
    }).join("");
    var cards = picked.map(function (m) {
      var sg = suggest(m.key, state.tolerance), p = sg.pick, l = sg.ladder;
      var saving = p.effort === sg.best.effort
        ? "No cheaper level stays within " + TOL[state.tolerance] + " points of its best: Low gives up " + l.spread.toFixed(1) + " points" + (l.levels.length > 2 ? " and " + LABEL[l.levels[l.levels.length - 2].effort] + " gives up " + (l.best.combined - l.levels[l.levels.length - 2].combined).toFixed(1) : "") + "."
        : pct(sg.usdRatio) + " of the cost and " + pct(sg.minRatio) + " of the time of " + LABEL[sg.best.effort] + ", for " + sg.gap.toFixed(1) + " points less.";
      var steps = l.levels.map(function (r, i) {
        if (!i) return "";
        var prev = l.levels[i - 1], dScore = r.combined - prev.combined, dUsd = r.usd - prev.usd;
        return '<div class="v4step"><span class="v4step-from">' + LABEL[prev.effort] + " &rarr; " + LABEL[r.effort] + "</span>" +
          '<span class="v4step-bar"><span style="width:' + Math.min(100, Math.abs(dScore) / 45 * 100).toFixed(1) + '%;background:' + (dScore >= 0 ? COLORS[r.key] : "#b4490c") + '"></span></span>' +
          '<span class="v4step-val">' + (dScore >= 0 ? "+" : "") + dScore.toFixed(1) + " pts for " + (dUsd >= 0 ? "+" : "&minus;") + "$" + Math.abs(dUsd).toFixed(2) + "</span></div>";
      }).join("");
      return '<div class="v4sug">' +
        '<div class="v4sug-head"><span class="v4dot" style="background:' + COLORS[m.key] + '"></span><b>' + esc(m.name) + '</b><span class="v4h">' + esc(m.harness) + '</span><span class="v4shape ' + l.shape + '">effort-' + l.shape + "</span></div>" +
        '<div class="v4sug-pick"><span class="v4k">Run it at</span><span class="v4sug-level">' + LABEL[p.effort] + "</span>" +
        '<span class="v4sug-meta">' + p.combined.toFixed(2) + " combined &middot; " + p.passed + "/" + p.n + " passed &middot; $" + p.usd.toFixed(2) + " &middot; " + p.minutes.toFixed(1) + " min per task</span></div>" +
        '<p class="v4sug-why">' + saving + "</p>" +
        ladderStrip(l, p.effort) +
        '<details class="v4steps"><summary>What each step up buys</summary>' + steps + "</details>" +
        "</div>";
    }).join("");
    return '<section class="v4need" aria-labelledby="v4need-heading">' +
      '<div class="v4need-head"><h3 id="v4need-heading">Suggested for routine tasks</h3>' +
      '<p>Sure, Max scores best. The question is how much better, and at what price. For each model this picks the cheapest effort level whose combined score sits within your tolerance of that model&rsquo;s best, and shows what it saves. The dot strip is the model&rsquo;s effort ladder on one scale, Low at the left, best at the right: bunched dots mean effort barely matters, spread dots mean it matters a lot.</p></div>' +
      '<div class="v4group"><span class="v4label">Tolerance</span><div class="lb-toggle chart-toggle on v4modes" role="tablist" aria-label="Score tolerance">' + tabs + "</div></div>" +
      '<div class="v4sugs">' + (cards || '<div class="bc-empty">No models picked.</div>') + "</div>" +
      '<p class="lb-context">These are 23 hard behavioural-reconstruction tasks. A model that is effort-flat here is flat on hard work; on routine edits the case for its lower levels is stronger still. Suggestions follow the chosen models and update with the tolerance; the effort selector above does not affect them.</p>' +
      "</section>";
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

  function scatter(rows, xKey, xLabel, log, withFrontier) {
    var W = 720, H = 400, L = 56, R = 24, T = 18, B = 48;
    function fx(t) { return xKey === "usd" ? "$" + (t < 1 ? t.toFixed(2) : t) : xKey === "output_tokens_median" ? fmtTokens(t) : t; }
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
    ticks.forEach(function (t) { g += '<line x1="' + X(t).toFixed(1) + '" y1="' + T + '" x2="' + X(t).toFixed(1) + '" y2="' + (H - B) + '" stroke="#1c1a17" stroke-opacity="0.06"/><text x="' + X(t).toFixed(1) + '" y="' + (H - B + 16) + '" text-anchor="middle" font-size="11" fill="#6f6a62">' + fx(t) + "</text>"; });
    g += '<text x="' + ((L + W - R) / 2).toFixed(1) + '" y="' + (H - 8) + '" text-anchor="middle" font-size="12" fill="#3a362f">' + xLabel + "</text>";
    g += '<text transform="translate(14 ' + ((T + H - B) / 2).toFixed(1) + ') rotate(-90)" text-anchor="middle" font-size="12" fill="#3a362f">Combined score</text>';
    if (state.mode === "all") {
      MODELS.forEach(function (m) {
        var pts = rows.filter(function (r) { return r.key === m.key; }).sort(function (a, b) { return EFFORTS.indexOf(a.effort) - EFFORTS.indexOf(b.effort); });
        if (pts.length > 1) g += '<polyline fill="none" stroke="' + COLORS[m.key] + '" stroke-width="1.6" stroke-opacity="0.7" points="' + pts.map(function (r) { return X(r[xKey]).toFixed(1) + "," + Y(r.combined).toFixed(1); }).join(" ") + '"/>';
      });
    }
    var onFrontier = {}, frontierEnd = {};
    if (withFrontier) {
      var f = frontier(rows, xKey);
      f.forEach(function (r) { onFrontier[r.key + "/" + r.effort] = true; });
      if (f.length) { frontierEnd[f[0].key + "/" + f[0].effort] = true; frontierEnd[f[f.length - 1].key + "/" + f[f.length - 1].effort] = true; }
      var d = "";
      f.forEach(function (r, i) {
        var x = X(r[xKey]).toFixed(1), y = Y(r.combined).toFixed(1);
        d += (i ? " H " + x + " V " + y : "M " + x + " " + y);  // step: hold the score until the next point that beats it
      });
      if (f.length) d += " H " + (W - R);
      g += '<path d="' + d + '" fill="none" stroke="#b4490c" stroke-width="1.4" stroke-dasharray="5 4" stroke-opacity="0.85"/>';
      g += '<text x="' + (W - R) + '" y="' + (T + 12) + '" text-anchor="end" font-size="11" fill="#b4490c">frontier: nothing to the left scores higher</text>';
    }
    var placed = [];
    rows.slice().sort(function (a, b) { return b.combined - a.combined; }).forEach(function (r) {
      var x = X(r[xKey]), y = Y(r.combined);
      var xv = xKey === "usd" ? "$" + r.usd.toFixed(2) : xKey === "output_tokens_median" ? fmtTokens(r.output_tokens_median) + " tokens" : r.minutes.toFixed(1) + " min";
      var here = onFrontier[r.key + "/" + r.effort];
      var tip = esc(r.model) + " " + LABEL[r.effort] + ": " + r.combined.toFixed(2) + ", " + xv + " per task" + (here ? " (on the frontier)" : "");
      var ring = here ? '<circle cx="' + x.toFixed(1) + '" cy="' + y.toFixed(1) + '" r="9" fill="none" stroke="#b4490c" stroke-width="1.4"/>' : "";
      g += ring + '<circle cx="' + x.toFixed(1) + '" cy="' + y.toFixed(1) + '" r="5.5" fill="' + shade(r.key, r.effort) + '" stroke="#1c1a17" stroke-width="0.8"><title>' + tip + "</title></circle>";
      if (state.mode === "all" && !r.best && !frontierEnd[r.key + "/" + r.effort]) return;  // ladder view: label best levels and the frontier's ends; every point keeps its tooltip
      var text = state.mode === "all" ? esc(r.model) + " " + LABEL[r.effort].toLowerCase() : state.mode === "best" ? esc(r.model) : esc(r.model) + " " + LABEL[r.effort].toLowerCase();
      var ty = y - 9, tx = x;
      var anchor = x > W - 150 ? "end" : "start";
      if (anchor === "start") tx = x + 8; else tx = x - 8;
      while (placed.some(function (q) { return Math.abs(q[0] - tx) < 130 && Math.abs(q[1] - ty) < 12; })) ty += 12;
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
        '<figure class="v4card v4wide"><figcaption><b>Score against completion tokens</b><span>combined score against median output tokens per task, reasoning included, log scale. The dashed line is the frontier: nothing that writes fewer tokens scores higher, and ringed points sit on it' + (state.mode === "all" ? "; thin lines join each model’s effort ladder from Low to Max, hover any point" : "") + "</span></figcaption>" + scatter(rows, "output_tokens_median", "Median completion tokens per task", true, true) + "</figure>" +
        '<figure class="v4card v4wide"><figcaption><b>Score against cost</b><span>combined score against API-equivalent $ per task, log scale; the dashed line is the cost frontier' + (state.mode === "all" ? "; thin lines join each model’s effort ladder from Low to Max, hover any point" : "") + "</span></figcaption>" + scatter(rows, "usd", "API-equivalent $ per task", true, true) + "</figure>" +
        '<figure class="v4card v4wide"><figcaption><b>Score against runtime</b><span>combined score against minutes per task' + (state.mode === "all" ? "; thin lines join each model’s effort ladder from Low to Max, hover any point" : "") + "</span></figcaption>" + scatter(rows, "minutes", "Minutes per task", false, false) + "</figure></div>";
      app.innerHTML = head + strip + suggestionSection() + '<h3 class="v4sub">Every model at the effort you picked</h3><div class="v4grid">' + cards + "</div>" + plots;
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
    else if (el.hasAttribute("data-tolerance")) { state.tolerance = el.getAttribute("data-tolerance"); }
    else return;
    render();
    if (typeof window.gtag === "function") window.gtag("event", "lb_v4_filter", { mode: state.mode, models: MODELS.filter(function (m) { return state.models[m.key]; }).length });
  });
  render();
})();
