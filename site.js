/* VulcanBench — terminal run animation + scroll reveals. No dependencies. */
(function () {
  "use strict";

  var reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ---- scroll reveal ---- */
  var revealed = document.querySelectorAll(".reveal");
  function vh() { return window.innerHeight || document.documentElement.clientHeight; }
  function nearViewport(el) {
    var r = el.getBoundingClientRect();
    return r.top < vh() * 0.92 && r.bottom > 0;
  }
  function show(el) { el.classList.add("in-view"); }

  if ("IntersectionObserver" in window && !reducedMotion) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) { show(e.target); io.unobserve(e.target); }
      });
    }, { threshold: 0.15, rootMargin: "0px 0px -40px 0px" });
    revealed.forEach(function (el) {
      // Reveal anything already on screen at load; observe the rest. This keeps
      // above-the-fold content visible even if the observer is slow to fire.
      if (nearViewport(el)) { show(el); } else { io.observe(el); }
    });
  } else {
    revealed.forEach(show);
  }

  /* ---- terminal run playback ---- */
  var term = document.getElementById("term");
  if (!term) return;

  var CMD = "vulcanbench run --suite v1-micro --model anthropic:claude-sonnet-5 --effort low --no-judges";
  var SPIN = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"];
  var N = 26;
  var NAME_W = 26;

  /* [name, pass, time, cost] — real v1-micro run, Sonnet 5 (low), 2026-07-03:
     25/26 pass, $0.82, pass@1 0.9615. Harvested from the run summary.json files. */
  var TASKS = [
    ["go-stack-pop-bug",        true,  "1m02s", "$0.02"],
    ["go-csv-quoting",          true,  "1m23s", "$0.03"],
    ["go-money-allocate",       true,  "1m08s", "$0.02"],
    ["go-lru-cache",            true,  "1m34s", "$0.05"],
    ["go-worker-pool",          true,  "1m56s", "$0.01"],
    ["oss-go-m2-01",            true,  "1m03s", "$0.02"],
    ["oss-go-m3-04",            true,  "1m02s", "$0.02"],
    ["oss-inflection-titleize", true,  "0m31s", "$0.04"],
    ["oss-py-m2-00",            true,  "0m14s", "$0.01"],
    ["oss-py-m3-00",            true,  "0m13s", "$0.01"],
    ["oss-ty-m2-02",            true,  "0m21s", "$0.02"],
    ["oss-ty-m3-05",            true,  "0m18s", "$0.02"],
    ["py-csv-export-feature",   true,  "0m29s", "$0.04"],
    ["py-jsonpointer",          true,  "0m29s", "$0.04"],
    ["py-retry-refactor",       true,  "0m27s", "$0.05"],
    ["py-topo-sort-cycle",      true,  "0m21s", "$0.03"],
    ["py-ttl-cache-expiry",     true,  "0m16s", "$0.02"],
    ["rs-borrow-split",         false, "1m02s", "$0.10"],
    ["rs-feature-gate",         true,  "0m21s", "$0.01"],
    ["ts-debounce",             true,  "1m57s", "$0.07"],
    ["ts-deep-merge",           true,  "0m32s", "$0.05"],
    ["ts-event-emitter",        true,  "0m30s", "$0.03"],
    ["ts-querystring-bug",      true,  "0m25s", "$0.03"],
    ["ts-schema-validate",      true,  "0m21s", "$0.02"],
    ["py-expr-eval",            true,  "0m35s", "$0.07"],
    ["go-parallel-map",         true,  "1m12s", "$0.03"]
  ];

  function esc(s) {
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }
  function pad2(n) { return (n < 10 ? "0" : "") + n; }
  function leader(name) {
    var dots = Math.max(2, NAME_W - name.length);
    return esc(name) + ' <span class="dim">' + new Array(dots + 1).join("·") + "</span>";
  }
  function taskHTML(i, t, state, frame) {
    var idx = '<span class="dim">' + pad2(i + 1) + "/" + N + "</span>  ";
    if (state === "run") {
      return '<span class="run">' + SPIN[frame % SPIN.length] + "</span> " + idx + leader(t[0]) +
        ' <span class="dim">running</span>';
    }
    var mark = t[1] ? '<span class="ok">✓</span>' : '<span class="bad">✗</span>';
    var verdict = t[1] ? '<span class="ok">pass</span>' : '<span class="bad">fail</span>';
    return mark + " " + idx + leader(t[0]) + " " + verdict +
      '  <span class="dim">' + t[2] + "</span>  " + t[3];
  }
  function headerHTML() {
    return [
      '<span class="dim">vulcanbench 0.5.1 · suite v1-micro · ' + N + ' tasks · deterministic hidden tests · no judges</span>',
      '<span class="dim">sandboxes ready</span> <span class="ok">✓</span> <span class="dim">' + N + '/' + N + ' docker images · network off · fail→pass validated</span>'
    ];
  }
  function summaryHTML() {
    return [
      '<span class="dim">' + new Array(58).join("─") + "</span>",
      'suite complete   <span class="ok">25/26 pass</span> · pass@1 <span class="em">0.9615</span> · <span class="em">$0.82</span> · 4-way parallel',
      '<span class="dim">leaderboard →</span> <span class="em">anthropic:claude-sonnet-5 (low)</span>'
    ];
  }

  function line(html) {
    var el = document.createElement("span");
    el.className = "tl";
    el.innerHTML = html;
    term.appendChild(el);
    term.scrollTop = term.scrollHeight;
    return el;
  }

  /* static transcript for reduced motion */
  if (reducedMotion) {
    line('<span class="prompt">$</span> <span class="cmd">' + esc(CMD) + "</span>");
    headerHTML().forEach(line);
    TASKS.forEach(function (t, i) { line(taskHTML(i, t, "done")); });
    summaryHTML().forEach(line);
    return;
  }

  var timers = [];
  function later(fn, ms) { timers.push(setTimeout(fn, ms)); }

  function play() {
    timers.forEach(clearTimeout);
    timers = [];
    term.innerHTML = "";

    var cmdLine = line('<span class="prompt">$</span> <span class="cmd"></span><span class="cursor"></span>');
    var cmdSpan = cmdLine.querySelector(".cmd");
    var ci = 0;

    function typeCmd() {
      if (ci <= CMD.length) {
        cmdSpan.textContent = CMD.slice(0, ci);
        ci++;
        later(typeCmd, 14 + Math.random() * 22);
        return;
      }
      cmdLine.querySelector(".cursor").remove();
      later(function () {
        var h = headerHTML();
        line(h[0]);
        later(function () { line(h[1]); later(runTasks, 420); }, 380);
      }, 260);
    }

    function runTasks() {
      var started = 0, finished = 0, active = [];

      function tick() {
        active.forEach(function (a) {
          a.frame++;
          a.el.innerHTML = taskHTML(a.i, TASKS[a.i], "run", a.frame);
        });
        if (finished < TASKS.length) later(tick, 90);
      }

      function startNext() {
        if (started >= TASKS.length) return;
        var i = started++;
        var a = { i: i, frame: 0, el: line(taskHTML(i, TASKS[i], "run", 0)) };
        active.push(a);
        later(function () {
          a.el.innerHTML = taskHTML(a.i, TASKS[a.i], "done");
          active.splice(active.indexOf(a), 1);
          finished++;
          if (finished === TASKS.length) later(showSummary, 500);
        }, 600 + Math.random() * 900);
        if (started < TASKS.length) later(startNext, 240 + Math.random() * 260);
      }

      tick();
      startNext();
    }

    function showSummary() {
      var s = summaryHTML();
      line(s[0]);
      later(function () {
        line(s[1]);
        later(function () {
          line(s[2]);
          later(function () {
            line('<span class="prompt">$</span> <span class="cursor"></span>');
            later(play, 6000);
          }, 700);
        }, 350);
      }, 250);
    }

    typeCmd();
  }

  /* start immediately if the terminal is already on screen (the usual case for
     a hero); otherwise wait until it scrolls into view. */
  var started = false;
  function start() { if (!started) { started = true; play(); } }
  function inViewport(el) {
    var r = el.getBoundingClientRect();
    var vh = window.innerHeight || document.documentElement.clientHeight;
    return r.top < vh * 0.85 && r.bottom > 0;
  }

  if (inViewport(term)) {
    start();
  } else if ("IntersectionObserver" in window) {
    var tio = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) { start(); tio.disconnect(); }
      });
    }, { threshold: 0.2 });
    tio.observe(term);
    window.addEventListener("scroll", function onScroll() {
      if (inViewport(term)) { start(); window.removeEventListener("scroll", onScroll); }
    }, { passive: true });
  } else {
    start();
  }
})();
