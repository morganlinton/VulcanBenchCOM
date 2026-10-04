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
  var CAP = 5;
  function plotted() { return COLS.filter(function (r) { return r[xKey] !== null && r[xKey] !== undefined; }); }  // unpriced columns sit out the cost view
  function unplotted() { return MODELS.filter(function (m) { return !plotted().some(function (r) { return r.key === m.key; }); }); }
  var SHORT_EFFORT = { low: "Low", medium: "Med", high: "High", "extra-high": "XHigh", max: "Max" };  // dollars per task shown before the cost chart scrolls
  var xKey = "usd";
  try { var saved = localStorage.getItem("vb_v4_axis"); if (saved && AXES[saved]) xKey = saved; } catch (e) {}

  function fmtTokens(v) { return v >= 1e6 ? (v / 1e6).toFixed(1) + "M" : v >= 1e3 ? Math.round(v / 1e3) + "k" : String(Math.round(v)); }
  function esc(s) { return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;"); }
  function niceStep(span) {
    var raw = span / 6, p = Math.pow(10, Math.floor(Math.log10(raw))), m = raw / p;
    return (m <= 1 ? 1 : m <= 2 ? 2 : m <= 2.5 ? 2.5 : m <= 5 ? 5 : 10) * p;
  }

  function past(cap) {
    // Columns past the cap, grouped by model: pointer text, caption text and the cheapest such level (where the line leaves the view).
    var out = [];
    MODELS.forEach(function (m) {
      var all = plotted().filter(function (r) { return r.key === m.key; });
      var off = all.filter(function (r) { return r.usd > cap; }).sort(function (a, b) { return a.usd - b.usd; });
      if (!off.length) return;
      var lo = "$" + off[0].usd.toFixed(2), hi = "$" + off[off.length - 1].usd.toFixed(2);
      var whole = off.length === all.length, one = off.length === 1;
      out.push({ key: m.key, first: off[0],
        text: m.name + " " + (one ? SHORT_EFFORT[off[0].effort] + " " + lo : (whole ? "" : off.length + " levels ") + lo + " to " + hi),
        caption: whole ? "every " + m.name + " level (" + lo + " to " + hi + ")" : off.map(function (r) { return m.name + " " + LABEL[r.effort] + " at $" + r.usd.toFixed(2); }).join(", ") });
    });
    return out;
  }

  function chart() {
    // $0 on the left. The y axis is pinned; the plot scrolls sideways when the cost axis runs past CAP, so $0 to CAP keeps the full width.
    var size = window.VB_V4_SIZE || {}, W = size.W || 960, H = size.H || 520, L = 56, T = 40, B = 56, P = 12, ax = AXES[xKey];
    var cols = plotted();
    var xs = cols.map(function (r) { return r[xKey]; }), ys = cols.map(function (r) { return r.combined; });
    var top = Math.max.apply(null, xs), cap = xKey === "usd" && top > CAP ? CAP : 0;
    var step = niceStep(cap || top);
    var xmax = Math.ceil(top * 1.04 / step) * step;
    var R = cap ? 24 : 150;  // room right of the plot: model names when everything fits, a margin after the last tick when it scrolls
    var VIEW = W - L, room = cap ? 64 : R;  // the visible plot width, and how much of it stays clear of the axis at the right edge
    var per = (VIEW - P - room) / (cap || xmax), PW = cap ? Math.ceil(P + xmax * per + R) : VIEW;
    var ymin = Math.max(0, Math.floor((Math.min.apply(null, ys) - 4) / 10) * 10), ymax = 100;
    function X(v) { return P + v * per; }
    function Y(v) { return T + (1 - (v - ymin) / (ymax - ymin)) * (H - T - B); }
    var yaxis = '<rect x="0" y="0" width="' + L + '" height="' + H + '" fill="#0e0e0c"/>';
    var g = '<defs><filter id="v4glow" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="3" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>' +
      '<rect x="0" y="0" width="' + PW + '" height="' + H + '" fill="#0e0e0c"/>';
    for (var y = ymin; y <= ymax; y += 10) {
      g += '<line x1="0" y1="' + Y(y).toFixed(1) + '" x2="' + (PW - R + 8) + '" y2="' + Y(y).toFixed(1) + '" stroke="#f7f4ee" stroke-opacity="0.12"/>';
      yaxis += '<text x="' + (L - 10) + '" y="' + (Y(y) + 4).toFixed(1) + '" text-anchor="end" font-size="12" fill="#a8a39a">' + y + "</text>";
    }
    for (var t = 0; t <= xmax + 1e-9; t += step) {
      g += '<line x1="' + X(t).toFixed(1) + '" y1="' + T + '" x2="' + X(t).toFixed(1) + '" y2="' + (H - B) + '" stroke="#f7f4ee" stroke-opacity="0.12"/>';
      g += '<text x="' + X(t).toFixed(1) + '" y="' + (H - B + 20) + '" text-anchor="' + (t === 0 ? "start" : "middle") + '" font-size="12" fill="#a8a39a">' + ax.fmt(t) + "</text>";
    }
    g += '<text x="' + P + '" y="' + (T - 14) + '" font-size="13" font-weight="600" fill="#f7f4ee">VulcanBench Frontier v4 score</text>';
    g += '<text x="' + ((VIEW - room) / 2).toFixed(1) + '" y="' + (H - 10) + '" text-anchor="middle" font-size="12.5" fill="#d8d3c8">' + esc(ax.label) + "</text>";
    var boxes = [], SHORT = { low: "Low", medium: "Med", high: "High", "extra-high": "XHigh", max: "Max" };
    var edge = cap ? VIEW - 4 : PW;  // labels stay inside the first view
    function free(b) { return b.x >= 0 && b.x + b.w <= edge && !boxes.some(function (q) { return b.x < q.x + q.w && b.x + b.w > q.x && b.y < q.y + q.h && b.y + b.h > q.y; }); }
    function place(x, y, text, size, tries, anchor) {
      var w = text.length * size * 0.62, h = size + 2;
      for (var i = 0; i < tries.length; i++) {
        var left = anchor === "start" ? x + tries[i][0] : x + tries[i][0] - w / 2;
        var b = { x: left, y: y + tries[i][1] - size, w: w, h: h };
        if (free(b)) { boxes.push(b); return [x + tries[i][0], y + tries[i][1]]; }
      }
      return [x + tries[0][0], y + tries[0][1]];
    }
    cols.forEach(function (r) { boxes.push({ x: X(r[xKey]) - 6, y: Y(r.combined) - 6, w: 12, h: 12 }); });  // keep labels off the dots
    var lines = [], names = [];
    MODELS.forEach(function (m) {
      var pts = cols.filter(function (r) { return r.key === m.key; }).sort(function (a, b) { return EFFORTS.indexOf(a.effort) - EFFORTS.indexOf(b.effort); });
      var col = COLORS[m.key] || "#f7f4ee";
      if (!pts.length) return;
      if (pts.length > 1) g += '<polyline fill="none" stroke="' + col + '" stroke-width="1.8" stroke-linejoin="round" stroke-linecap="round" filter="url(#v4glow)" points="' + pts.map(function (r) { return X(r[xKey]).toFixed(1) + "," + Y(r.combined).toFixed(1); }).join(" ") + '"/>';
      pts.forEach(function (r) {
        var tip = r.model + " " + LABEL[r.effort] + ": " + r.combined.toFixed(1) + ", " + ax.tip(r);
        g += '<circle cx="' + X(r[xKey]).toFixed(1) + '" cy="' + Y(r.combined).toFixed(1) + '" r="4.5" fill="' + col + '" stroke="#0e0e0c" stroke-width="1.5" filter="url(#v4glow)"><title>' + esc(tip) + "</title></circle>";
      });
      for (var i = 1; i < pts.length; i++) lines.push([X(pts[i - 1][xKey]), Y(pts[i - 1].combined), X(pts[i][xKey]), Y(pts[i].combined)]);
      // The name sits beside the line's costliest level that is on screen before any scrolling.
      // A line wholly past the cap is named beside its cheapest level instead, out in the scrolled part.
      var seen = pts.filter(function (r) { return !cap || r[xKey] <= cap; }), far = !seen.length;
      var end = far ? pts.reduce(function (a, b) { return b[xKey] < a[xKey] ? b : a; }) : seen.reduce(function (a, b) { return b[xKey] > a[xKey] ? b : a; });
      names.push({ x: X(end[xKey]), y: Y(end.combined), text: m.name, col: col, far: far });
    });
    lines.forEach(function (s) {  // keep the names off the lines too
      var n = Math.ceil(Math.hypot(s[2] - s[0], s[3] - s[1]) / 4);
      for (var i = 0; i <= n; i++) boxes.push({ x: s[0] + (s[2] - s[0]) * i / n - 2, y: s[1] + (s[3] - s[1]) * i / n - 2, w: 4, h: 4 });
    });
    var beyond = cap ? past(cap) : [];
    beyond.forEach(function (b) {  // one pointer per model at the right edge of the first view, toward its levels past the cap
      var cue = b.text + " →", w = cue.length * 11 * 0.62;
      var at = place(VIEW - 8 - w, Y(b.first.combined), cue, 11, [[0, 18], [0, -10], [0, 30], [0, -22], [0, 42], [0, -34]], "start");
      g += '<text x="' + at[0].toFixed(1) + '" y="' + at[1].toFixed(1) + '" font-size="11" fill="' + (COLORS[b.key] || "#f7f4ee") + '">' + esc(cue) + "</text>";
    });
    names.sort(function (a, b) { return a.y - b.y; }).forEach(function (n) {
      var w = n.text.length * 13 * 0.62, tries = [];
      [0, -14, 14, -28, 28, -42, 42].forEach(function (dy) { tries.push([12, dy], [-w - 12, dy]); });
      edge = n.far ? PW : cap ? VIEW - 4 : PW;
      var at = place(n.x, n.y + 4, n.text, 13, tries, "start");
      g += '<text x="' + at[0].toFixed(1) + '" y="' + at[1].toFixed(1) + '" font-size="13" font-weight="600" fill="' + n.col + '">' + esc(n.text) + "</text>";
    });
    edge = cap ? VIEW - 4 : PW;
    MODELS.forEach(function (m) {  // effort labels go last so they steer around the dots and the model names
      var col = COLORS[m.key] || "#f7f4ee";
      cols.filter(function (r) { return r.key === m.key; }).sort(function (a, b) { return a[xKey] - b[xKey]; }).forEach(function (r) {
        var at = place(X(r[xKey]), Y(r.combined), SHORT[r.effort], 10, [[0, -9], [0, 17], [11, -9], [-11, -9], [0, -21], [0, 29], [22, 4], [-22, 4]]);
        g += '<text x="' + at[0].toFixed(1) + '" y="' + at[1].toFixed(1) + '" text-anchor="middle" font-size="10" fill="' + col + '" fill-opacity="0.85">' + SHORT[r.effort] + "</text>";
      });
    });
    var label = "VulcanBench Frontier v4 score against " + ax.label.toLowerCase() + ", $0 on the left, one line per model across its effort levels";
    return {
      beyond: beyond,
      html: '<div class="v4frame">' +
        '<svg class="v4yaxis" viewBox="0 0 ' + L + " " + H + '" style="width:' + (100 * L / W).toFixed(3) + '%" aria-hidden="true" font-family="IBM Plex Mono, SF Mono, monospace">' + yaxis + "</svg>" +
        '<div class="v4scroll" style="width:' + (100 * VIEW / W).toFixed(3) + '%"' + (cap ? ' tabindex="0" role="region" aria-label="Chart, scrolls sideways past ' + ax.fmt(cap) + '"' : "") + ">" +
        '<svg viewBox="0 0 ' + PW + " " + H + '" style="width:' + (100 * PW / VIEW).toFixed(3) + '%" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="' + esc(label) + '" font-family="IBM Plex Mono, SF Mono, monospace">' + g + "</svg></div></div>"
    };
  }

  function render() {
    var tabs = [["usd", "Cost"], ["output_tokens_median", "Tokens"], ["minutes", "Minutes"]].map(function (t) {
      return '<button type="button" role="tab" class="' + (xKey === t[0] ? "active" : "") + '" aria-selected="' + (xKey === t[0] ? "true" : "false") + '" data-x="' + t[0] + '">' + t[1] + "</button>";
    }).join("");
    var c = chart();
    app.innerHTML = '<div class="v4group"><span class="v4label">X axis</span><div class="lb-toggle chart-toggle on v4modes" role="tablist" aria-label="Chart x axis">' + tabs + "</div></div>" +
      '<figure class="v4card v4chart">' + c.html + '<figcaption><span>Each line is one model through its reasoning-effort levels. The x axis starts at zero on the left, so cheaper levels sit toward the left of each line. Each dot is labelled with its effort level; hover for the exact numbers.' +
      (c.beyond.length ? " The cost axis shows up to " + AXES.usd.fmt(CAP) + " per task; scroll the chart right for " + c.beyond.map(function (b) { return b.caption; }).join(" and ") + "." : "") +
      (unplotted().length ? " " + unplotted().map(function (m) { return m.name; }).join(" and ") + " has no list price, so it is not on the cost view; choose Tokens or Minutes to see it." : "") + "</span></figcaption></figure>";
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
