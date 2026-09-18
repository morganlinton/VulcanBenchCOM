/* VulcanBench Frontier v4 board: one chart, score against cost (or tokens, or minutes), one line per model across its effort levels. */
(function () {
  "use strict";
  var app = document.getElementById("v4app");
  if (!app || !window.VB_V4) return;
  var DATA = window.VB_V4, COLS = DATA.columns, COLORS = DATA.colors, EFFORTS = DATA.efforts;
  var LABEL = { low: "Low", medium: "Medium", high: "High", "extra-high": "Extra High", max: "Max" };
  var MODELS = [];
  COLS.forEach(function (c) { if (!MODELS.some(function (m) { return m.key === c.key; })) MODELS.push({ key: c.key, name: c.model, harness: c.harness }); });
  var AXES = {
    usd: { label: "Average cost per task (API-equivalent, list rates)", fmt: function (v) { return v === 0 ? "$0" : "$" + (v < 1 ? v.toFixed(2) : Number.isInteger(v) ? v : v.toFixed(1)); }, tip: function (r) { return "$" + r.usd.toFixed(2) + " per task"; } },
    output_tokens_median: { label: "Median completion tokens per task (reasoning included)", fmt: fmtTokens, tip: function (r) { return fmtTokens(r.output_tokens_median) + " tokens per task"; } },
    minutes: { label: "Minutes per task", fmt: function (v) { return String(Math.round(v)); }, tip: function (r) { return r.minutes.toFixed(1) + " min per task"; } }
  };
  var xKey = "usd";
  try { var saved = localStorage.getItem("vb_v4_axis"); if (saved && AXES[saved]) xKey = saved; } catch (e) {}

  function fmtTokens(v) { return v >= 1e6 ? (v / 1e6).toFixed(1) + "M" : v >= 1e3 ? Math.round(v / 1e3) + "k" : String(Math.round(v)); }
  function esc(s) { return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;"); }
  function niceStep(span) {
    var raw = span / 6, p = Math.pow(10, Math.floor(Math.log10(raw))), m = raw / p;
    return (m <= 1 ? 1 : m <= 2 ? 2 : m <= 2.5 ? 2.5 : m <= 5 ? 5 : 10) * p;
  }

  function chart() {
    // CursorBench layout: cost runs from most expensive on the left to $0 on the right, so every line ends at the far right.
    var size = window.VB_V4_SIZE || {}, W = size.W || 960, H = size.H || 520, L = 56, R = 176, T = 40, B = 56, ax = AXES[xKey];
    var xs = COLS.map(function (r) { return r[xKey]; }), ys = COLS.map(function (r) { return r.combined; });
    var step = niceStep(Math.max.apply(null, xs));
    var xmax = Math.ceil(Math.max.apply(null, xs) * 1.04 / step) * step;
    var ymin = Math.max(0, Math.floor((Math.min.apply(null, ys) - 4) / 10) * 10), ymax = 100;
    function X(v) { return L + (1 - v / xmax) * (W - L - R); }
    function Y(v) { return T + (1 - (v - ymin) / (ymax - ymin)) * (H - T - B); }
    var g = '<defs><filter id="v4glow" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="3" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>' +
      '<rect x="0" y="0" width="' + W + '" height="' + H + '" fill="#0e0e0c"/>';
    for (var y = ymin; y <= ymax; y += 10) {
      g += '<line x1="' + L + '" y1="' + Y(y).toFixed(1) + '" x2="' + (W - R) + '" y2="' + Y(y).toFixed(1) + '" stroke="#f7f4ee" stroke-opacity="0.12"/>';
      g += '<text x="' + (L - 10) + '" y="' + (Y(y) + 4).toFixed(1) + '" text-anchor="end" font-size="12" fill="#a8a39a">' + y + "</text>";
    }
    for (var t = 0; t <= xmax + 1e-9; t += step) {
      g += '<line x1="' + X(t).toFixed(1) + '" y1="' + T + '" x2="' + X(t).toFixed(1) + '" y2="' + (H - B) + '" stroke="#f7f4ee" stroke-opacity="0.12"/>';
      g += '<text x="' + X(t).toFixed(1) + '" y="' + (H - B + 20) + '" text-anchor="middle" font-size="12" fill="#a8a39a">' + ax.fmt(t) + "</text>";
    }
    g += '<text x="' + L + '" y="' + (T - 14) + '" font-size="13" font-weight="600" fill="#f7f4ee">VulcanBench Frontier v4 score</text>';
    g += '<text x="' + ((L + W - R) / 2).toFixed(1) + '" y="' + (H - 10) + '" text-anchor="middle" font-size="12.5" fill="#d8d3c8">' + esc(ax.label) + "</text>";
    var labels = [], boxes = [], SHORT = { low: "Low", medium: "Med", high: "High", "extra-high": "XHigh", max: "Max" };
    function free(b) { return !boxes.some(function (q) { return b.x < q.x + q.w && b.x + b.w > q.x && b.y < q.y + q.h && b.y + b.h > q.y; }); }
    function place(x, y, text, size) {
      var w = text.length * size * 0.62, h = size + 2;
      var tries = [[0, -9], [0, 17], [11, -9], [-11, -9], [0, -21], [0, 29], [22, 4], [-22, 4]];
      for (var i = 0; i < tries.length; i++) {
        var b = { x: x + tries[i][0] - w / 2, y: y + tries[i][1] - size, w: w, h: h };
        if (free(b)) { boxes.push(b); return [x + tries[i][0], y + tries[i][1]]; }
      }
      return [x, y - 9];
    }
    COLS.forEach(function (r) { boxes.push({ x: X(r[xKey]) - 6, y: Y(r.combined) - 6, w: 12, h: 12 }); });  // keep labels off the dots
    MODELS.forEach(function (m) {
      var pts = COLS.filter(function (r) { return r.key === m.key; }).sort(function (a, b) { return EFFORTS.indexOf(a.effort) - EFFORTS.indexOf(b.effort); });
      var col = COLORS[m.key] || "#f7f4ee";
      if (pts.length > 1) g += '<polyline fill="none" stroke="' + col + '" stroke-width="1.8" stroke-linejoin="round" stroke-linecap="round" filter="url(#v4glow)" points="' + pts.map(function (r) { return X(r[xKey]).toFixed(1) + "," + Y(r.combined).toFixed(1); }).join(" ") + '"/>';
      pts.forEach(function (r) {
        var tip = r.model + " " + LABEL[r.effort] + ": " + r.combined.toFixed(1) + ", " + ax.tip(r);
        g += '<circle cx="' + X(r[xKey]).toFixed(1) + '" cy="' + Y(r.combined).toFixed(1) + '" r="4.5" fill="' + col + '" stroke="#0e0e0c" stroke-width="1.5" filter="url(#v4glow)"><title>' + esc(tip) + "</title></circle>";
      });
      var end = pts.reduce(function (a, b) { return b[xKey] < a[xKey] ? b : a; });  // cheapest level sits at the right end of the line
      labels.push({ x: X(end[xKey]) + 12, y: Y(end.combined) + 4, text: m.name, col: col });
    });
    labels.sort(function (a, b) { return a.y - b.y; });
    for (var i = 1; i < labels.length; i++) if (labels[i].y - labels[i - 1].y < 15) labels[i].y = labels[i - 1].y + 15;
    labels.forEach(function (l) { boxes.push({ x: l.x, y: l.y - 12, w: l.text.length * 8, h: 14 }); });
    labels.forEach(function (l) { g += '<text x="' + l.x.toFixed(1) + '" y="' + l.y.toFixed(1) + '" font-size="13" font-weight="600" fill="' + l.col + '">' + esc(l.text) + "</text>"; });
    MODELS.forEach(function (m) {  // effort labels go last so they steer around the dots and the model names
      var col = COLORS[m.key] || "#f7f4ee";
      COLS.filter(function (r) { return r.key === m.key; }).sort(function (a, b) { return a[xKey] - b[xKey]; }).forEach(function (r) {
        var at = place(X(r[xKey]), Y(r.combined), SHORT[r.effort], 10);
        g += '<text x="' + at[0].toFixed(1) + '" y="' + at[1].toFixed(1) + '" text-anchor="middle" font-size="10" fill="' + col + '" fill-opacity="0.85">' + SHORT[r.effort] + "</text>";
      });
    });
    return '<svg viewBox="0 0 ' + W + " " + H + '" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="VulcanBench Frontier v4 score against ' + esc(ax.label.toLowerCase()) + ', most expensive on the left, one line per model across its effort levels" font-family="IBM Plex Mono, SF Mono, monospace">' + g + "</svg>";
  }

  function render() {
    var tabs = [["usd", "Cost"], ["output_tokens_median", "Tokens"], ["minutes", "Minutes"]].map(function (t) {
      return '<button type="button" role="tab" class="' + (xKey === t[0] ? "active" : "") + '" aria-selected="' + (xKey === t[0] ? "true" : "false") + '" data-x="' + t[0] + '">' + t[1] + "</button>";
    }).join("");
    app.innerHTML = '<div class="v4group"><span class="v4label">X axis</span><div class="lb-toggle chart-toggle on v4modes" role="tablist" aria-label="Chart x axis">' + tabs + "</div></div>" +
      '<figure class="v4card v4chart">' + chart() + '<figcaption><span>Each line is one model through its reasoning-effort levels; cost runs from most expensive on the left to cheapest on the right, so Max sits at the left end of each line and Low at the right. Each dot is labelled with its effort level; hover for the exact numbers.</span></figcaption></figure>';
    try { localStorage.setItem("vb_v4_axis", xKey); } catch (e) {}
  }

  app.addEventListener("click", function (e) {
    var el = e.target.closest ? e.target.closest("button[data-x]") : null;
    if (!el) return;
    xKey = el.getAttribute("data-x");
    render();
  });
  render();
})();
