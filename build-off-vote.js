/* Build-off reader vote: wires up every <div class="bo-vote" data-build-off="..."> on the page.
 *
 * The buttons carry data-choice. A click posts the vote to /api/build-off-vote
 * and shows the tally; the tally stays hidden until the reader has voted, so
 * the running count does not steer the vote. The reader's choice is remembered
 * in localStorage only to redraw the box on a later visit: the server decides
 * what counts.
 */
(function () {
  "use strict";

  var API = "/api/build-off-vote";

  function remembered(key) {
    try {
      return window.localStorage.getItem(key);
    } catch (e) {
      return null;
    }
  }

  function remember(key, value) {
    try {
      window.localStorage.setItem(key, value);
    } catch (e) {
      /* private mode: the vote still counts, it just is not redrawn next visit */
    }
  }

  function setup(box) {
    var buildOff = box.getAttribute("data-build-off");
    var key = "vb.build-off-vote." + buildOff;
    var buttons = Array.prototype.slice.call(box.querySelectorAll("button[data-choice]"));
    var rows = Array.prototype.slice.call(box.querySelectorAll(".bo-vote-row"));
    var result = box.querySelector(".bo-vote-result");
    var status = box.querySelector(".bo-vote-status");
    var total = box.querySelector(".bo-vote-total");

    function say(text) {
      status.textContent = text;
    }

    function names(choice) {
      for (var i = 0; i < buttons.length; i++) {
        if (buttons[i].getAttribute("data-choice") === choice) return buttons[i].getAttribute("data-name");
      }
      return choice;
    }

    function draw(data, mine) {
      rows.forEach(function (row) {
        var choice = row.getAttribute("data-choice");
        var count = Number(data.counts[choice]) || 0;
        var share = data.total ? Math.round((count / data.total) * 100) : 0;
        row.querySelector(".bo-vote-fill").style.width = share + "%";
        row.querySelector(".bo-vote-num").textContent = count + (count === 1 ? " vote" : " votes") + " · " + share + "%";
        row.classList.toggle("mine", choice === mine);
      });
      buttons.forEach(function (button) {
        var chosen = button.getAttribute("data-choice") === mine;
        button.classList.toggle("primary", chosen);
        button.setAttribute("aria-pressed", chosen ? "true" : "false");
      });
      total.textContent = data.total + (data.total === 1 ? " vote so far." : " votes so far.");
      result.hidden = false;
      say("You voted for " + names(mine) + ". Pick the other one to change your vote.");
    }

    function busy(on) {
      buttons.forEach(function (button) {
        button.disabled = on;
      });
    }

    function fail() {
      say("Voting is not available right now. Please try again later.");
    }

    function vote(choice) {
      busy(true);
      say("Counting your vote…");
      fetch(API, {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ build_off: buildOff, choice: choice }),
      })
        .then(function (response) {
          return response.json();
        })
        .then(function (data) {
          if (!data || !data.ok) return fail();
          remember(key, choice);
          draw(data, choice);
        })
        .catch(fail)
        .then(function () {
          busy(false);
        });
    }

    buttons.forEach(function (button) {
      button.addEventListener("click", function () {
        vote(button.getAttribute("data-choice"));
      });
    });

    var earlier = remembered(key);
    if (earlier) {
      fetch(API + "?build_off=" + encodeURIComponent(buildOff), { headers: { Accept: "application/json" } })
        .then(function (response) {
          return response.json();
        })
        .then(function (data) {
          if (data && data.ok) draw(data, earlier);
        })
        .catch(function () {
          /* leave the buttons as they are */
        });
    }
  }

  Array.prototype.slice.call(document.querySelectorAll(".bo-vote[data-build-off]")).forEach(setup);
})();
