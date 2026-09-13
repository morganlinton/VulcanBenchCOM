/* VulcanBench: share any benchmark table as a branded PNG card. Zero dependencies. */
(function () {
  "use strict";

  var PAPER   = "#f7f4ee";
  var INK     = "#1c1a17";
  var SOFT    = "#3a362f";
  var FAINT   = "#6f6a62";
  var EMBER   = "#b4490c";
  var LINE    = "#1c1a17";
  var EVEN_BG = "#f1eee8";

  var DISPLAY = '"Chakra Petch", "Avenir Next", sans-serif';
  var SERIF   = '"Iowan Old Style", "Palatino Linotype", Palatino, Georgia, serif';

  var DPR    = 2;
  var PAD    = 48;
  var ROW_H  = 46;
  var HDR_H  = 44;
  var CELL_PX = 18;
  var MIN_W  = 900;
  var ACCENT = 4;

  function pageTitle() {
    var h1 = document.querySelector(".article-head h1");
    return h1 ? h1.textContent.trim() : "";
  }
  function reportNo() {
    var el = document.querySelector(".article-head .rno");
    return el ? el.textContent.trim() : "";
  }
  function sectionHeading(table) {
    var sec = table.closest("section");
    if (!sec) return "";
    var h2 = sec.querySelector("h2");
    return h2 ? h2.textContent.trim() : "";
  }

  function parseTable(table) {
    var headers = [];
    table.querySelectorAll("thead th").forEach(function (th) {
      headers.push(th.textContent.trim());
    });
    var rows = [];
    table.querySelectorAll("tbody tr").forEach(function (tr) {
      var cells = [];
      tr.querySelectorAll("td").forEach(function (td) {
        cells.push({
          text: td.textContent.trim(),
          model: td.classList.contains("model"),
          win: td.classList.contains("win")
        });
      });
      rows.push(cells);
    });
    return { headers: headers, rows: rows };
  }

  function tw(ctx, text, font) { ctx.font = font; return ctx.measureText(text).width; }

  function renderCard(table) {
    var d       = parseTable(table);
    var title   = pageTitle();
    var rno     = reportNo();
    var heading = sectionHeading(table);
    var nC = d.headers.length, nR = d.rows.length;

    var canvas = document.createElement("canvas");
    var ctx    = canvas.getContext("2d");

    var fH   = "600 12px "        + DISPLAY;
    var fC   = "17px "            + SERIF;
    var fCI  = "italic 17px "     + SERIF;
    var fCB  = "700 17px "        + SERIF;
    var fCBI = "italic 700 17px " + SERIF;
    var fT   = "600 30px "  + DISPLAY;
    var fR   = "500 12px "  + DISPLAY;
    var fSH  = "600 20px "  + DISPLAY;
    var fU   = "500 13px "  + DISPLAY;
    var fBR  = "600 16px "  + DISPLAY;

    var colW = [];
    for (var c = 0; c < nC; c++) {
      var mx = tw(ctx, d.headers[c].toUpperCase(), fH);
      for (var r = 0; r < nR; r++) {
        var cl = d.rows[r][c];
        if (!cl) continue;
        var f = cl.win ? (cl.model ? fCBI : fCB) : (cl.model ? fCI : fC);
        var w = tw(ctx, cl.text, f);
        if (w > mx) mx = w;
      }
      colW.push(Math.ceil(mx) + CELL_PX * 2);
    }

    var tableW = 0;
    colW.forEach(function (w) { tableW += w; });
    var cardW = Math.max(MIN_W, tableW + PAD * 2);
    if (cardW > tableW + PAD * 2) {
      var extra = (cardW - PAD * 2 - tableW) / nC;
      for (var i = 0; i < nC; i++) colW[i] += extra;
      tableW = cardW - PAD * 2;
    }

    var y = ACCENT + PAD;
    y += 18;
    var titleY = y; y += 40;
    var headingY = 0;
    if (heading) { headingY = y; y += 32; }
    var tableY = y;
    y += HDR_H + nR * ROW_H + 40;
    var footerY = y; y += 20;
    var cardH = y + PAD;

    canvas.width  = cardW * DPR;
    canvas.height = cardH * DPR;
    ctx.scale(DPR, DPR);
    ctx.textBaseline = "alphabetic";

    ctx.fillStyle = PAPER;
    ctx.fillRect(0, 0, cardW, cardH);

    ctx.fillStyle = EMBER;
    ctx.fillRect(0, 0, cardW, ACCENT);

    ctx.strokeStyle = "rgba(28,26,23,0.12)";
    ctx.lineWidth = 1;
    ctx.strokeRect(0.5, ACCENT + 0.5, cardW - 1, cardH - ACCENT - 1);

    ctx.font = fR; ctx.fillStyle = EMBER; ctx.textAlign = "left";
    ctx.fillText(rno.toUpperCase(), PAD, ACCENT + PAD + 12);

    ctx.font = fT; ctx.fillStyle = INK;
    ctx.fillText(title, PAD, titleY + 28);

    if (heading) {
      ctx.font = fSH; ctx.fillStyle = SOFT;
      ctx.fillText(heading, PAD, headingY + 20);
    }

    var tx = PAD;

    ctx.strokeStyle = LINE; ctx.lineWidth = 2.5;
    ctx.beginPath(); ctx.moveTo(tx, tableY); ctx.lineTo(tx + tableW, tableY); ctx.stroke();
    ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(tx, tableY + HDR_H); ctx.lineTo(tx + tableW, tableY + HDR_H); ctx.stroke();

    var cx = tx;
    for (var h = 0; h < nC; h++) {
      ctx.font = fH; ctx.fillStyle = SOFT;
      ctx.textAlign = h === 0 ? "left" : "right";
      ctx.fillText(d.headers[h].toUpperCase(), h === 0 ? cx + CELL_PX : cx + colW[h] - CELL_PX, tableY + HDR_H - 14);
      cx += colW[h];
    }

    for (var r = 0; r < nR; r++) {
      var ry = tableY + HDR_H + r * ROW_H;
      if (r % 2 === 1) { ctx.fillStyle = EVEN_BG; ctx.fillRect(tx, ry, tableW, ROW_H); }
      cx = tx;
      for (var c = 0; c < nC; c++) {
        var cl = d.rows[r][c];
        if (!cl) { cx += colW[c]; continue; }
        ctx.fillStyle = cl.win ? EMBER : INK;
        ctx.font = cl.win ? (cl.model ? fCBI : fCB) : (cl.model ? fCI : fC);
        ctx.textAlign = c === 0 ? "left" : "right";
        ctx.fillText(cl.text, c === 0 ? cx + CELL_PX : cx + colW[c] - CELL_PX, ry + ROW_H - 15);
        cx += colW[c];
      }
    }

    ctx.strokeStyle = LINE; ctx.lineWidth = 2.5;
    var botY = tableY + HDR_H + nR * ROW_H;
    ctx.beginPath(); ctx.moveTo(tx, botY); ctx.lineTo(tx + tableW, botY); ctx.stroke();

    ctx.font = fBR; ctx.fillStyle = INK; ctx.textAlign = "left";
    ctx.fillText("VulcanBench", PAD, footerY + 14);
    ctx.font = fU; ctx.fillStyle = FAINT; ctx.textAlign = "right";
    ctx.fillText("vulcanbench.com", cardW - PAD, footerY + 14);

    return canvas;
  }

  function share(canvas, filename) {
    canvas.toBlob(function (blob) {
      if (!blob) return;
      if (navigator.canShare) {
        var file = new File([blob], filename, { type: "image/png" });
        if (navigator.canShare({ files: [file] })) {
          navigator.share({ files: [file], title: pageTitle() + " | VulcanBench" }).catch(function () {});
          return;
        }
      }
      var url = URL.createObjectURL(blob);
      var a = document.createElement("a"); a.href = url; a.download = filename;
      document.body.appendChild(a); a.click(); document.body.removeChild(a);
      setTimeout(function () { URL.revokeObjectURL(url); }, 10000);
    }, "image/png");
  }

  function init() {
    var tables = document.querySelectorAll("table.data");
    if (!tables.length) return;
    var slug = location.pathname.split("/").pop().replace(/\.html$/, "");

    tables.forEach(function (table, i) {
      var anchor = table.closest(".table-scroll") || table;
      var wrap = document.createElement("div");
      wrap.className = "table-share-wrap";
      var btn = document.createElement("button");
      btn.className = "table-share-btn";
      btn.type = "button";
      btn.setAttribute("aria-label", "Share this table as an image");
      btn.innerHTML =
        '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">' +
        '<path d="M4 12v8a2 2 0 002 2h12a2 2 0 002-2v-8"/><polyline points="16 6 12 2 8 6"/><line x1="12" y1="2" x2="12" y2="15"/></svg>' +
        '<span>Share table</span>';
      btn.addEventListener("click", function () {
        var suffix = tables.length > 1 ? "-t" + (i + 1) : "";
        share(renderCard(table), "vulcanbench-" + slug + suffix + ".png");
      });
      wrap.appendChild(btn);
      anchor.parentElement.insertBefore(wrap, anchor);
    });
  }

  if (document.fonts && document.fonts.ready) { document.fonts.ready.then(init); }
  else if (document.readyState === "loading") { document.addEventListener("DOMContentLoaded", init); }
  else { init(); }
})();
