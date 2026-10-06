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
  var zoom = "all", ZOOM_MIN = 80;  // "top" keeps the y axis to 80 and up, where most levels crowd together
  try { var z = localStorage.getItem("vb_v4_zoom"); if (z === "top") zoom = z; } catch (e) {}
  var pinned = {}, hoverKey = null;  // models picked out in the key, and the one under the pointer

  function past(cols, cap) {
    // Columns past the cap, grouped by model: pointer text, caption text and the cheapest such level (where the line leaves the view).
    var out = [];
    MODELS.forEach(function (m) {
      var all = cols.filter(function (r) { return r.key === m.key; });
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

  function ymin() { return zoom === "top" ? ZOOM_MIN : Math.max(0, Math.floor((Math.min.apply(null, plotted().map(function (r) { return r.combined; })) - 4) / 10) * 10); }
  function shown() { var lo = ymin(); return plotted().filter(function (r) { return r.combined >= lo; }); }  // levels inside the y range
  function hidden() { var s = shown(); return MODELS.filter(function (m) { return plotted().some(function (r) { return r.key === m.key; }) && !s.some(function (r) { return r.key === m.key; }); }); }

  function chart() {
    // $0 on the left. The y axis is pinned; the plot scrolls sideways when the cost axis runs past CAP, so $0 to CAP keeps the full width.
    var size = window.VB_V4_SIZE || {}, W = size.W || 960, H = size.H || 600, L = 56, T = 40, B = 56, P = 12, ax = AXES[xKey];
    var all = plotted(), cols = shown(), lo = ymin(), hi = zoom === "top" ? Math.min(100, Math.ceil((Math.max.apply(null, cols.map(function (r) { return r.combined; })) + 1) / 2) * 2) : 100, ystep = zoom === "top" ? 2 : 10;
    var xs = cols.map(function (r) { return r[xKey]; });
    var top = Math.max.apply(null, xs), cap = xKey === "usd" && top > CAP ? CAP : 0;
    var step = niceStep(cap || top);
    var xmax = Math.ceil(top * 1.04 / step) * step;
    var R = cap ? 24 : 150;  // room right of the plot: model names when everything fits, a margin after the last tick when it scrolls
    var VIEW = W - L, room = cap ? 64 : R;  // the visible plot width, and how much of it stays clear of the axis at the right edge
    var per = (VIEW - P - room) / (cap || xmax), PW = cap ? Math.ceil(P + xmax * per + R) : VIEW;
    function X(v) { return P + v * per; }
    function Y(v) { return T + (1 - (v - lo) / (hi - lo)) * (H - T - B); }
    var INK = "#1c1a17", SOFT = "#6f6a62", GRID = "#1c1a17", BG = "#ffffff";
    var yaxis = '<rect x="0" y="0" width="' + L + '" height="' + H + '" fill="' + BG + '"/>';
    var g = '<defs><clipPath id="v4clip"><rect x="0" y="' + (T - 10) + '" width="' + PW + '" height="' + (H - T - B + 16) + '"/></clipPath></defs>' +
      '<rect x="0" y="0" width="' + PW + '" height="' + H + '" fill="' + BG + '"/>';
    for (var y = lo; y <= hi; y += ystep) {
      g += '<line x1="0" y1="' + Y(y).toFixed(1) + '" x2="' + (PW - R + 8) + '" y2="' + Y(y).toFixed(1) + '" stroke="' + GRID + '" stroke-opacity="' + (y === lo ? 0.35 : 0.08) + '"/>';
      yaxis += '<text x="' + (L - 10) + '" y="' + (Y(y) + 4).toFixed(1) + '" text-anchor="end" font-size="12" fill="' + SOFT + '">' + y + "</text>";
    }
    for (var t = 0; t <= xmax + 1e-9; t += step) {
      g += '<line x1="' + X(t).toFixed(1) + '" y1="' + T + '" x2="' + X(t).toFixed(1) + '" y2="' + (H - B) + '" stroke="' + GRID + '" stroke-opacity="' + (t === 0 ? 0.35 : 0.08) + '"/>';
      g += '<text x="' + X(t).toFixed(1) + '" y="' + (H - B + 20) + '" text-anchor="' + (t === 0 ? "start" : "middle") + '" font-size="12" fill="' + SOFT + '">' + ax.fmt(t) + "</text>";
    }
    g += '<text x="' + P + '" y="' + (T - 14) + '" font-size="13" font-weight="600" fill="' + INK + '">VulcanBench Frontier v4 score' + (zoom === "top" ? ", " + lo + " and up" : "") + "</text>";
    g += '<text x="' + ((VIEW - room) / 2).toFixed(1) + '" y="' + (H - 10) + '" text-anchor="middle" font-size="12.5" fill="#3d3a35">' + esc(ax.label) + "</text>";

    var boxes = [], edge = cap ? VIEW - 4 : PW;  // labels stay inside the first view
    function hits(b, set) { return b.x < 0 || b.x + b.w > edge || b.y < T - 12 || b.y + b.h > H - B + 4 || set.some(function (q) { return b.x < q.x + q.w && b.x + b.w > q.x && b.y < q.y + q.h && b.y + b.h > q.y; }); }
    function place(x, y, text, size, tries, anchor, set, force) {
      // The first free spot from tries; null when every spot collides, unless force (then the first try).
      var w = text.length * size * 0.62, h = size + 2;
      for (var i = 0; i < tries.length; i++) {
        var left = anchor === "start" ? x + tries[i][0] : x + tries[i][0] - w / 2;
        var b = { x: left, y: y + tries[i][1] - size, w: w, h: h };
        if (!hits(b, set)) { set.push(b); return { x: x + tries[i][0], y: y + tries[i][1], box: b }; }
      }
      return force ? { x: x + tries[0][0], y: y + tries[0][1], box: null } : null;
    }
    function dotBox(r) { return { x: X(r[xKey]) - 7, y: Y(r.combined) - 7, w: 14, h: 14 }; }
    function lineBoxes(pts) {
      var out = [];
      for (var i = 1; i < pts.length; i++) {
        var x0 = X(pts[i - 1][xKey]), y0 = Y(pts[i - 1].combined), x1 = X(pts[i][xKey]), y1 = Y(pts[i].combined);
        var n = Math.ceil(Math.hypot(x1 - x0, y1 - y0) / 4);
        for (var j = 0; j <= n; j++) out.push({ x: x0 + (x1 - x0) * j / n - 2, y: y0 + (y1 - y0) * j / n - 2, w: 4, h: 4 });
      }
      return out;
    }
    function series(m) { return all.filter(function (r) { return r.key === m.key; }).sort(function (a, b) { return EFFORTS.indexOf(a.effort) - EFFORTS.indexOf(b.effort); }); }

    var groups = {}, names = [], effort = {};
    MODELS.forEach(function (m) {
      var pts = series(m), vis = pts.filter(function (r) { return r.combined >= lo; });
      if (!vis.length) return;
      var col = COLORS[m.key] || INK;
      vis.forEach(function (r) { boxes.push(dotBox(r)); });
      boxes = boxes.concat(lineBoxes(pts));  // keep labels off the lines too
      var s = '<g clip-path="url(#v4clip)">';
      if (pts.length > 1) s += '<polyline fill="none" stroke="' + col + '" stroke-width="2.2" stroke-linejoin="round" stroke-linecap="round" points="' + pts.map(function (r) { return X(r[xKey]).toFixed(1) + "," + Y(r.combined).toFixed(1); }).join(" ") + '"/>';
      vis.forEach(function (r) {
        var cx = X(r[xKey]).toFixed(1), cy = Y(r.combined).toFixed(1);
        s += '<circle cx="' + cx + '" cy="' + cy + '" r="5" fill="' + col + '" stroke="' + BG + '" stroke-width="2"/>' +
          '<circle class="v4hit" cx="' + cx + '" cy="' + cy + '" r="11" fill="transparent" data-tip="' + esc(r.model + " " + LABEL[r.effort] + "|" + r.combined.toFixed(1) + " score|" + ax.tip(r)) + '"/>';
      });
      groups[m.key] = { body: s + "</g>", col: col, label: "" };
      // The name sits beside the line's costliest level that is on screen before any scrolling.
      // A line wholly past the cap is named beside its cheapest level instead, out in the scrolled part.
      var seen = vis.filter(function (r) { return !cap || r[xKey] <= cap; }), far = !seen.length;
      var end = far ? vis.reduce(function (a, b) { return b[xKey] < a[xKey] ? b : a; }) : seen.reduce(function (a, b) { return b[xKey] > a[xKey] ? b : a; });
      names.push({ key: m.key, x: X(end[xKey]), y: Y(end.combined), text: m.name, col: col, far: far });
      effort[m.key] = vis;
    });

    var beyond = cap ? past(cols, cap) : [];
    var cues = {};
    beyond.forEach(function (b) {  // one pointer per model at the right edge of the first view, toward its levels past the cap
      var cue = b.text + " →", w = cue.length * 11 * 0.62;
      var at = place(VIEW - 8 - w, Y(b.first.combined), cue, 11, [[0, 18], [0, -10], [0, 30], [0, -22], [0, 42], [0, -34], [0, 54], [0, -46]], "start", boxes, true);
      cues[b.key] = '<text x="' + at.x.toFixed(1) + '" y="' + at.y.toFixed(1) + '" font-size="11" font-weight="500" fill="' + INK + '"><tspan fill="' + (COLORS[b.key] || INK) + '">●</tspan> ' + esc(cue) + "</text>";
    });

    // Model names: the nearest free spot, walking out from the line's end; past a short hop a leader line ties the name back to its dot.
    var nameBoxes = [];
    names.sort(function (a, b) { return a.y - b.y; }).forEach(function (n) {
      var w = n.text.length * 13 * 0.62, tries = [];
      [0, -16, 16, -32, 32, -48, 48, -66, 66, -86, 86, -108, 108].forEach(function (dy) { tries.push([12, dy + 4], [-w - 12, dy + 4]); });
      [40, 72].forEach(function (dx) { [-24, 24, -48, 48, -72, 72].forEach(function (dy) { tries.push([dx, dy + 4], [-w - dx, dy + 4]); }); });
      edge = n.far ? PW : cap ? VIEW - 4 : PW;
      var at = place(n.x, n.y, n.text, 13, tries, "start", boxes, true);
      var s = "";
      if (at.box && (Math.abs(at.y - 4 - n.y) > 10 || at.x - n.x > 14 || n.x - (at.x + w) > 14)) {
        var bx = Math.max(at.box.x, Math.min(n.x, at.box.x + at.box.w)), by = Math.max(at.box.y, Math.min(n.y, at.box.y + at.box.h));
        var d = Math.hypot(bx - n.x, by - n.y) || 1, sx = n.x + (bx - n.x) * 7 / d, sy = n.y + (by - n.y) * 7 / d;
        s += '<line x1="' + sx.toFixed(1) + '" y1="' + sy.toFixed(1) + '" x2="' + bx.toFixed(1) + '" y2="' + by.toFixed(1) + '" stroke="' + n.col + '" stroke-width="1" stroke-opacity="0.7"/>';
      }
      s += '<text x="' + at.x.toFixed(1) + '" y="' + at.y.toFixed(1) + '" font-size="13" font-weight="600" fill="' + INK + '" paint-order="stroke" stroke="' + BG + '" stroke-width="3">' + esc(n.text) + "</text>";
      groups[n.key].label = s + (cues[n.key] || "");
      if (at.box) nameBoxes.push(at.box);
    });
    edge = cap ? VIEW - 4 : PW;

    // Effort labels. With nothing picked out, a level is labelled only where its label fits clear of everything else.
    // Picking a model out shows every one of its labels, kept clear of every dot and of the other models' picked-out labels,
    // so any mix of picked-out lines reads cleanly; a label pushed out past its dot gets a short leader.
    var ETRY = [[0, -10], [0, 19], [12, -9], [-12, -9], [12, 17], [-12, 17], [20, 4], [-20, 4], [0, -22], [0, 31]];
    var FAR = ETRY.concat([[28, -20], [-28, -20], [28, 28], [-28, 28], [0, -36], [0, 45], [36, 4], [-36, 4], [40, -34], [-40, -34], [40, 42], [-40, 42], [0, -50], [0, 59]]);
    var auto = "", lit = {}, taken = cols.map(dotBox).concat(nameBoxes);
    MODELS.forEach(function (m) {
      if (!effort[m.key]) return;
      var col = COLORS[m.key] || INK;
      effort[m.key].slice().sort(function (a, b) { return a[xKey] - b[xKey]; }).forEach(function (r) {
        var at = place(X(r[xKey]), Y(r.combined), SHORT_EFFORT[r.effort], 10, ETRY, "middle", boxes, false);
        if (at) auto += '<text data-m="' + m.key + '" x="' + at.x.toFixed(1) + '" y="' + at.y.toFixed(1) + '" text-anchor="middle" font-size="10" fill="' + SOFT + '">' + SHORT_EFFORT[r.effort] + "</text>";
      });
      var mine = taken.concat(lineBoxes(series(m))), s = "";
      effort[m.key].slice().sort(function (a, b) { return b.combined - a.combined; }).forEach(function (r) {  // top first, so a higher dot takes the spot above
        var x = X(r[xKey]), y = Y(r.combined), at = place(x, y, SHORT_EFFORT[r.effort], 11, FAR, "middle", mine, true);
        if (at.box) {
          taken.push(at.box);
          if (Math.abs(at.x - x) > 14 || at.y - y > 32 || at.y - y < -24) {
            var bx = Math.max(at.box.x, Math.min(x, at.box.x + at.box.w)), by = Math.max(at.box.y, Math.min(y, at.box.y + at.box.h)), d = Math.hypot(bx - x, by - y) || 1;
            s += '<line x1="' + (x + (bx - x) * 7 / d).toFixed(1) + '" y1="' + (y + (by - y) * 7 / d).toFixed(1) + '" x2="' + bx.toFixed(1) + '" y2="' + by.toFixed(1) + '" stroke="' + col + '" stroke-width="1"/>';
          }
        }
        s += '<text x="' + at.x.toFixed(1) + '" y="' + at.y.toFixed(1) + '" text-anchor="middle" font-size="11" font-weight="600" fill="' + INK + '" paint-order="stroke" stroke="' + BG + '" stroke-width="3">' + SHORT_EFFORT[r.effort] + "</text>";
      });
      lit[m.key] = s;
    });

    MODELS.forEach(function (m) {
      var gr = groups[m.key];
      if (gr) g += '<g class="v4m" data-m="' + m.key + '">' + gr.body + gr.label + '<g class="v4eff">' + lit[m.key] + "</g></g>";
    });
    g += '<g class="v4auto">' + auto + "</g>";

    var label = "VulcanBench Frontier v4 score against " + ax.label.toLowerCase() + ", $0 on the left, one line per model across its effort levels";
    return {
      beyond: beyond,
      html: '<div class="v4frame">' +
        '<svg class="v4yaxis" viewBox="0 0 ' + L + " " + H + '" style="width:' + (100 * L / W).toFixed(3) + '%" aria-hidden="true" font-family="IBM Plex Mono, SF Mono, monospace">' + yaxis + "</svg>" +
        '<div class="v4scroll" style="width:' + (100 * VIEW / W).toFixed(3) + '%"' + (cap ? ' tabindex="0" role="region" aria-label="Chart, scrolls sideways past ' + ax.fmt(cap) + '"' : "") + ">" +
        '<svg class="v4plot" viewBox="0 0 ' + PW + " " + H + '" style="width:' + (100 * PW / VIEW).toFixed(3) + '%" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="' + esc(label) + '" font-family="IBM Plex Mono, SF Mono, monospace">' + g + "</svg></div></div>"
    };
  }

  function legend() {
    var on = plotted(), gone = hidden().map(function (m) { return m.key; }), any = Object.keys(pinned).length;
    return '<div class="v4legend" role="group" aria-label="Pick out a model">' + MODELS.map(function (m) {
      var off = !on.some(function (r) { return r.key === m.key; }) || gone.indexOf(m.key) >= 0;
      return '<button type="button" class="v4key' + (pinned[m.key] ? " on" : "") + '" data-m="' + m.key + '" aria-pressed="' + (pinned[m.key] ? "true" : "false") + '"' + (off ? " disabled" : "") + '><span class="v4dot" style="background:' + (COLORS[m.key] || "#1c1a17") + '"></span>' + esc(m.name) + "</button>";
    }).join("") + (any ? '<button type="button" class="v4key v4clear" data-clear="1">Show all</button>' : "") + "</div>";
  }

  function focus() {
    // Fade every line but the picked-out ones (and the one under the pointer), bring those to the front and show their effort labels.
    var svg = app.querySelector(".v4plot");
    if (!svg) return;
    var keys = Object.keys(pinned);
    if (hoverKey && keys.indexOf(hoverKey) < 0) keys.push(hoverKey);
    svg.classList.toggle("focus", keys.length > 0);
    Array.prototype.forEach.call(svg.querySelectorAll(".v4m"), function (el) {
      var lit = keys.indexOf(el.getAttribute("data-m")) >= 0, was = el.classList.contains("on");
      el.classList.toggle("on", lit);
      if (lit && !was) el.parentNode.insertBefore(el, svg.querySelector(".v4auto"));
    });
  }

  function render() {
    var tabs = [["usd", "Cost"], ["output_tokens_median", "Tokens"], ["minutes", "Minutes"]].map(function (t) {
      return '<button type="button" role="tab" class="' + (xKey === t[0] ? "active" : "") + '" aria-selected="' + (xKey === t[0] ? "true" : "false") + '" data-x="' + t[0] + '">' + t[1] + "</button>";
    }).join("");
    var zooms = [["all", "All scores"], ["top", ZOOM_MIN + " and up"]].map(function (t) {
      return '<button type="button" class="' + (zoom === t[0] ? "active" : "") + '" aria-pressed="' + (zoom === t[0] ? "true" : "false") + '" data-zoom="' + t[0] + '">' + t[1] + "</button>";
    }).join("");
    var c = chart(), gone = hidden();
    app.innerHTML = '<div class="v4controls"><div class="v4group"><span class="v4label">X axis</span><div class="lb-toggle chart-toggle on v4modes" role="tablist" aria-label="Chart x axis">' + tabs + "</div></div>" +
      '<div class="v4group"><span class="v4label">Y axis</span><div class="lb-toggle chart-toggle on v4modes" role="group" aria-label="Chart y axis range">' + zooms + "</div></div></div>" +
      '<figure class="v4card v4chart">' + legend() + '<div class="v4plotwrap">' + c.html + '<div class="v4tip" hidden></div></div><figcaption><span>Each line is one model through its reasoning-effort levels. The x axis starts at zero on the left, so cheaper levels sit toward the left of each line. Hover or tap a model in the key to pick out its line with every effort level labelled; hover a dot for the exact numbers.' +
      (c.beyond.length ? " The cost axis shows up to " + AXES.usd.fmt(CAP) + " per task; scroll the chart right for " + c.beyond.map(function (b) { return b.caption; }).join(" and ") + "." : "") +
      (gone.length ? " " + gone.map(function (m) { return m.name; }).join(" and ") + (gone.length > 1 ? " have" : " has") + " no level at " + ZOOM_MIN + " or above, so " + (gone.length > 1 ? "they sit" : "it sits") + " out of this view; choose All scores to see " + (gone.length > 1 ? "them" : "it") + "." : "") +
      (unplotted().length ? " " + unplotted().map(function (m) { return m.name; }).join(" and ") + " has no list price, so it is not on the cost view; choose Tokens or Minutes to see it." : "") + "</span></figcaption></figure>";
    focus();
    try { localStorage.setItem("vb_v4_axis", xKey); localStorage.setItem("vb_v4_zoom", zoom); } catch (e) {}
  }

  function tip(el, e) {
    var box = app.querySelector(".v4tip"), wrap = app.querySelector(".v4plotwrap");
    if (!box || !wrap) return;
    if (!el) { box.hidden = true; return; }
    var parts = el.getAttribute("data-tip").split("|"), a = wrap.getBoundingClientRect(), d = el.getBoundingClientRect();
    box.innerHTML = "<b>" + esc(parts[0]) + "</b><span>" + esc(parts[1]) + "</span><span>" + esc(parts[2]) + "</span>";
    box.hidden = false;
    var x = d.left + d.width / 2 - a.left, y = d.top - a.top;
    box.style.left = Math.max(0, Math.min(x - box.offsetWidth / 2, a.width - box.offsetWidth)) + "px";
    box.style.top = (y - box.offsetHeight - 4 < 0 ? y + d.height + 4 : y - box.offsetHeight - 4) + "px";
  }

  app.addEventListener("click", function (e) {
    var el = e.target.closest ? e.target.closest("button[data-x], button[data-zoom], button[data-m], button[data-clear]") : null;
    if (!el) {
      var line = e.target.closest ? e.target.closest(".v4m") : null;  // tapping a line picks it out too
      if (!line) return;
      el = { getAttribute: function (k) { return k === "data-m" ? line.getAttribute("data-m") : null; } };
    }
    if (el.getAttribute("data-x")) xKey = el.getAttribute("data-x");
    else if (el.getAttribute("data-zoom")) zoom = el.getAttribute("data-zoom");
    else if (el.getAttribute("data-clear")) pinned = {};
    else { var k = el.getAttribute("data-m"); if (pinned[k]) delete pinned[k]; else pinned[k] = true; hoverKey = null; }
    render();
  });
  app.addEventListener("mouseover", function (e) {
    var key = e.target.closest ? e.target.closest("button[data-m], .v4m") : null, hit = e.target.closest ? e.target.closest(".v4hit") : null;
    var k = key ? key.getAttribute("data-m") : null;
    if (k !== hoverKey) { hoverKey = k; focus(); }
    tip(hit, e);
  });
  app.addEventListener("mouseleave", function () { hoverKey = null; focus(); tip(null); });
  app.addEventListener("focusin", function (e) {
    var key = e.target.closest ? e.target.closest("button[data-m]") : null;
    hoverKey = key ? key.getAttribute("data-m") : null;
    focus();
  });
  render();
})();
