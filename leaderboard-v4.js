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
    var g = "";
    for (var y = ymin; y <= ymax; y += 10) {
      g += '<line x1="' + L + '" y1="' + Y(y).toFixed(1) + '" x2="' + (W - R) + '" y2="' + Y(y).toFixed(1) + '" stroke="#1c1a17" stroke-opacity="0.1"/>';
      g += '<text x="' + (L - 10) + '" y="' + (Y(y) + 4).toFixed(1) + '" text-anchor="end" font-size="12" fill="#6f6a62">' + y + "</text>";
    }
    for (var t = 0; t <= xmax + 1e-9; t += step) {
      g += '<line x1="' + X(t).toFixed(1) + '" y1="' + T + '" x2="' + X(t).toFixed(1) + '" y2="' + (H - B) + '" stroke="#1c1a17" stroke-opacity="0.1"/>';
      g += '<text x="' + X(t).toFixed(1) + '" y="' + (H - B + 20) + '" text-anchor="middle" font-size="12" fill="#6f6a62">' + ax.fmt(t) + "</text>";
    }
    g += '<text x="' + L + '" y="' + (T - 14) + '" font-size="13" font-weight="600" fill="#1c1a17">VulcanBench Frontier v4 score</text>';
    g += '<text x="' + ((L + W - R) / 2).toFixed(1) + '" y="' + (H - 10) + '" text-anchor="middle" font-size="12.5" fill="#3a362f">' + esc(ax.label) + "</text>";
    var labels = [];
    MODELS.forEach(function (m) {
      var pts = COLS.filter(function (r) { return r.key === m.key; }).sort(function (a, b) { return EFFORTS.indexOf(a.effort) - EFFORTS.indexOf(b.effort); });
      var col = COLORS[m.key] || "#1c1a17";
      if (pts.length > 1) g += '<polyline fill="none" stroke="' + col + '" stroke-width="1.6" stroke-linejoin="round" points="' + pts.map(function (r) { return X(r[xKey]).toFixed(1) + "," + Y(r.combined).toFixed(1); }).join(" ") + '"/>';
      pts.forEach(function (r) {
        var tip = r.model + " " + LABEL[r.effort] + ": " + r.combined.toFixed(1) + ", " + ax.tip(r);
        g += '<circle cx="' + X(r[xKey]).toFixed(1) + '" cy="' + Y(r.combined).toFixed(1) + '" r="4.5" fill="' + col + '" stroke="#f7f4ee" stroke-width="1.2"><title>' + esc(tip) + "</title></circle>";
      });
      var end = pts.reduce(function (a, b) { return b[xKey] < a[xKey] ? b : a; });  // cheapest level sits at the right end of the line
      labels.push({ x: X(end[xKey]) + 10, y: Y(end.combined) + 4, text: m.name, col: col });
    });
    labels.sort(function (a, b) { return a.y - b.y; });
    for (var i = 1; i < labels.length; i++) if (labels[i].y - labels[i - 1].y < 15) labels[i].y = labels[i - 1].y + 15;
    labels.forEach(function (l) { g += '<text x="' + l.x.toFixed(1) + '" y="' + l.y.toFixed(1) + '" font-size="13" font-weight="600" fill="' + l.col + '">' + esc(l.text) + "</text>"; });
    return '<svg viewBox="0 0 ' + W + " " + H + '" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="VulcanBench Frontier v4 score against ' + esc(ax.label.toLowerCase()) + ', most expensive on the left, one line per model across its effort levels" font-family="IBM Plex Mono, SF Mono, monospace">' + g + "</svg>";
  }

  function render() {
    var tabs = [["usd", "Cost"], ["output_tokens_median", "Tokens"], ["minutes", "Minutes"]].map(function (t) {
      return '<button type="button" role="tab" class="' + (xKey === t[0] ? "active" : "") + '" aria-selected="' + (xKey === t[0] ? "true" : "false") + '" data-x="' + t[0] + '">' + t[1] + "</button>";
    }).join("");
    app.innerHTML = '<div class="v4group"><span class="v4label">X axis</span><div class="lb-toggle chart-toggle on v4modes" role="tablist" aria-label="Chart x axis">' + tabs + "</div></div>" +
      '<figure class="v4card v4chart">' + chart() + '<figcaption><span>Each line is one model through its reasoning-effort levels; cost runs from most expensive on the left to cheapest on the right, so Max sits at the left end of each line and Low at the right. Hover a point for the exact numbers.</span></figcaption></figure>';
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
