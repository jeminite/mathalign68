/* The analyse page -- file handling and rendering. All DOM, no analysis.
 *
 * The split matters: engine.js holds every number this page shows and is
 * testable in Node without a browser, so the render suite can stub the DOM and
 * still be a real test. Anything computed here rather than there is a number
 * nothing checks.
 */
(function () {
  "use strict";

  var DATA = null;
  var $ = function (id) { return document.getElementById(id); };

  function esc(s) {
    return String(s === null || s === undefined ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  // Choice text and stems arrive from data.json carrying this project's own
  // <span class="math"> markup, so they go in as HTML. Everything that came out
  // of the dropped file goes through esc() instead, without exception.
  function trusted(s) { return s === null || s === undefined ? "" : String(s); }

  function pc(x) { return x === null || x === undefined ? "—" : (Math.round(x * 1000) / 10).toFixed(1) + "%"; }
  function gapStr(g) {
    if (g === null || g === undefined) return "—";
    var v = (Math.round(g * 1000) / 10).toFixed(1);
    return (g > 0 ? "+" : "") + v;
  }
  function gapClass(g) {
    if (g === null || g === undefined) return "";
    if (g <= -0.15) return "g-bad";
    if (g <= -0.05) return "g-low";
    if (g >= 0.05) return "g-good";
    return "g-flat";
  }

  /* ------------------------------------------------------------------ intro */

  function itemLink(i) {
    if (!i.sourceUrl) return "Q" + i.item;
    return '<a href="' + esc(i.sourceUrl) + '" target="_blank" rel="noopener">Q' + i.item + "</a>";
  }

  function lessonCell(i) {
    // Grade 6 has no published alignment yet -- every entry is still draft, and
    // build/payload.py drops drafts before they reach the site. Say so rather
    // than rendering an empty cell that looks like a bug.
    if (i.lessonTitle) {
      return esc("Unit " + (i.unit || "?") + ", Lesson " + (i.lesson || "?") + " — " + i.lessonTitle);
    }
    return '<span class="muted">not yet placed</span>';
  }

  /* ----------------------------------------------------------------- render */

  function render(r) {
    var h = [];

    h.push('<div class="ident">');
    h.push("<h2>" + esc(r.label) + "</h2>");
    h.push("<p>Matched on <strong>" + r.identify.agree + " of " + r.identify.total +
           "</strong> question standards" +
           (r.identify.runnerUp !== undefined
             ? " (the next closest test matched " + r.identify.runnerUp + ")" : "") +
           ". <strong>" + r.students + "</strong> students, <strong>" + r.matched +
           "</strong> items scored.</p>");
    if (r.unmatched.length) {
      h.push('<p class="note">' + r.unmatched.length + " question" +
             (r.unmatched.length === 1 ? "" : "s") + " in your file " +
             (r.unmatched.length === 1 ? "is" : "are") +
             " not in the released set, so the State published no answer key or " +
             "difficulty for " + (r.unmatched.length === 1 ? "it" : "them") + ": " +
             r.unmatched.map(function (u) { return "Q" + u.item; }).join(", ") +
             ". They are left out of every figure below.</p>");
    }
    h.push("</div>");

    // The caution comes before any number, not after them. With a class this
    // size a single child moves a percentage by more than most of the gaps
    // below, and that is the first thing a reader needs in hand.
    var move = r.students ? Math.round(1000 / r.students) / 10 : 0;
    h.push('<div class="caution"><strong>Before reading anything below.</strong> ' +
           "One student moves any percentage here by about " + move +
           " points. Differences smaller than that are not findings. The State's " +
           "figure comes from every child in New York who sat the test; yours comes " +
           "from " + r.students + ". <strong>NYSED does not publish the population its " +
           "P-values are computed over</strong>, so treat the comparison as a signal " +
           "worth following up, not a like-for-like measurement.</div>");

    (r.warnings || []).forEach(function (w) {
      h.push('<div class="warn">' + esc(w) + "</div>");
    });

    h.push('<div class="overall"><div><span class="lbl">Your class</span><span class="big">' +
           pc(r.overall.classP) + '</span></div><div><span class="lbl">New York State</span>' +
           '<span class="big">' + pc(r.overall.stateP) + '</span></div>' +
           '<div><span class="lbl">Difference</span><span class="big ' +
           gapClass(r.overall.gap) + '">' + gapStr(r.overall.gap) + '</span></div></div>');
    h.push('<p class="note">Both figures are credits earned over credits possible, so ' +
           "they blend multiple-choice percent correct with constructed-response points " +
           "per credit. That is fine for a single comparison of like with like, but the " +
           "two are not the same quantity and are never plotted on one axis below.</p>");

    /* ---- dominant distractors, the headline ---- */
    h.push("<h3>Where one wrong answer dominated</h3>");
    if (!r.dominant.length) {
      h.push('<p class="muted">No wrong answer was chosen by a quarter of the class or ' +
             "more. Where this class struggled, it struggled in scattered ways rather " +
             "than on one shared misreading.</p>");
    } else {
      h.push('<p class="note">A quarter of the class or more landing on the <em>same</em> ' +
             "wrong answer is a specific misconception rather than general difficulty. " +
             "These are the ones worth a lesson.</p>");
      r.dominant.forEach(function (i) {
        h.push('<div class="dom">');
        h.push('<div class="dom-h">' + itemLink(i) + ' <span class="std">' +
               esc(i.standard) + "</span>" +
               '<span class="spacer"></span><span class="' + gapClass(i.gap) + '">you ' +
               pc(i.classP) + " · State " + pc(i.stateP) + " · " + gapStr(i.gap) +
               "</span></div>");
        if (i.stemPlain) h.push('<p class="stem">' + esc(i.stemPlain) + "</p>");
        h.push('<p class="pick"><strong>' + i.topWrongCount + " of " + i.n +
               "</strong> chose <strong>" + esc(i.topWrong) + "</strong>" +
               (i.topWrongText ? ": " + trusted(i.topWrongText)
                 : (i.choicesInImage
                    ? ' — <span class="muted">that choice is a picture; open the ' +
                      "question to see it</span>" : "")) +
               ". " + i.correct + " chose the correct answer, " + esc(i.key) + ".</p>");
        h.push('<p class="tally">' + tally(i) + "</p>");
        h.push("</div>");
      });
    }

    /* ---- every item against the State ---- */
    h.push("<h3>Every question, against the State</h3>");
    h.push('<p class="note">Sorted by the gap. A negative number is the amount by which ' +
           "this class fell below New York State on that item.</p>");
    h.push('<table class="grid"><thead><tr><th>Q</th><th>Standard</th><th>Type</th>' +
           "<th>Your class</th><th>State</th><th>Diff</th><th>Imagine IM</th></tr></thead><tbody>");
    r.byGap.forEach(function (i) {
      h.push("<tr><td>" + itemLink(i) + "</td><td>" + esc(i.standard) +
             (i.postTest ? ' <span class="post">post-test</span>' : "") +
             "</td><td>" + (i.type === "mc" ? "MC" : i.credits + "-credit CR") +
             "</td><td>" + pc(i.classP) + "</td><td>" + pc(i.stateP) +
             '</td><td class="' + gapClass(i.gap) + '">' + gapStr(i.gap) +
             "</td><td>" + lessonCell(i) + "</td></tr>");
    });
    h.push("</tbody></table>");

    /* ---- rollups ---- */
    h.push("<h3>By standard</h3>");
    h.push(rollupTable(r.byStandard, "Standard"));
    h.push("<h3>By domain</h3>");
    h.push(rollupTable(r.byDomain, "Domain"));

    /* ---- sections ---- */
    if (r.bySection.length > 1) {
      h.push("<h3>By class</h3>");
      h.push('<p class="note">Read across a row to see whether an item was hard for ' +
             "everyone or hard in one room. Your file’s <em>Class</em> column is the " +
             "only thing to the left of the question grid that was read; the name column " +
             "was not.</p>");
      h.push('<table class="grid"><thead><tr><th>Q</th><th>Standard</th><th>State</th>');
      r.bySection.forEach(function (s) {
        h.push("<th>" + esc(s.section) + "<br><span class=\"muted\">n=" + s.students + "</span></th>");
      });
      h.push("<th>Spread</th></tr></thead><tbody>");
      r.byGap.forEach(function (i) {
        var vals = r.bySection.map(function (s) { return s.perItem[i.item]; });
        var ok = vals.filter(function (v) { return v !== null; });
        var spread = ok.length ? Math.max.apply(null, ok) - Math.min.apply(null, ok) : null;
        h.push("<tr><td>" + itemLink(i) + "</td><td>" + esc(i.standard) +
               "</td><td>" + pc(i.stateP) + "</td>");
        vals.forEach(function (v) { h.push("<td>" + pc(v) + "</td>"); });
        h.push('<td class="' + (spread !== null && spread >= 0.3 ? "g-bad" : "") + '">' +
               (spread === null ? "—" : pc(spread)) + "</td></tr>");
      });
      h.push("</tbody></table>");
    }

    /* ---- constructed response ---- */
    if (r.constructed.length) {
      h.push("<h3>Constructed response</h3>");
      h.push('<p class="note">Most zeros first. The State figure is average points ' +
             "earned over points possible — not a percent correct, and not comparable " +
             "to the multiple-choice column above.</p>");
      h.push('<table class="grid"><thead><tr><th>Q</th><th>Standard</th><th>Credits</th>' +
             "<th>Zero</th><th>Full</th><th>Your class</th><th>State</th><th>Diff</th></tr></thead><tbody>");
      r.constructed.forEach(function (i) {
        h.push("<tr><td>" + itemLink(i) + "</td><td>" + esc(i.standard) + "</td><td>" +
               i.credits + "</td><td>" + i.zeroCredit + " of " + i.n + "</td><td>" +
               i.fullCredit + "</td><td>" + pc(i.classP) + "</td><td>" + pc(i.stateP) +
               '</td><td class="' + gapClass(i.gap) + '">' + gapStr(i.gap) + "</td></tr>");
      });
      h.push("</tbody></table>");
    }

    /* ---- omissions ---- */
    if (r.omissions.length) {
      h.push("<h3>Left blank</h3>");
      h.push('<p class="note">Kept separate because not answering is not the same as ' +
             "answering wrongly.</p><ul>");
      r.omissions.forEach(function (i) {
        h.push("<li>" + itemLink(i) + " " + esc(i.standard) + " — " + i.omitted +
               " left it blank</li>");
      });
      h.push("</ul>");
    }

    h.push('<div class="actions"><button type="button" id="print">Print or save as PDF</button>' +
           '<button type="button" id="again">Analyse another file</button></div>');

    $("out").innerHTML = h.join("");
    $("print").onclick = function () { window.print(); };
    $("again").onclick = reset;
  }

  function tally(i) {
    var out = [];
    (i.choiceList || []).forEach(function (c) {
      var count = c.label === i.key ? i.correct : (i.chose[c.label] || 0);
      out.push('<span class="t' + (c.label === i.key ? " t-ok" : "") + '">' +
               esc(c.label) + " " + count + "</span>");
    });
    return out.join(" ");
  }

  function rollupTable(rows, label) {
    var h = ['<table class="grid"><thead><tr><th>' + label +
             "</th><th>Items</th><th>Your class</th><th>State</th><th>Diff</th></tr></thead><tbody>"];
    rows.forEach(function (g) {
      h.push("<tr><td>" + esc(g.label || g.key) + "</td><td>" + g.items.length +
             "</td><td>" + pc(g.classP) + "</td><td>" + pc(g.stateP) +
             '</td><td class="' + gapClass(g.gap) + '">' + gapStr(g.gap) + "</td></tr>");
    });
    h.push("</tbody></table>");
    return h.join("");
  }

  /* ------------------------------------------------------------------- flow */

  function fail(msg) {
    $("out").innerHTML = '<div class="err">' + esc(msg) + "</div>" +
      '<div class="actions"><button type="button" id="again">Try another file</button></div>';
    $("again").onclick = reset;
    $("drop").hidden = true;
  }

  function reset() {
    $("out").innerHTML = "";
    $("drop").hidden = false;
    $("file").value = "";
  }

  function handle(file) {
    if (!file) return;
    $("out").innerHTML = '<p class="muted">Reading ' + esc(file.name) + "…</p>";
    $("drop").hidden = true;
    file.arrayBuffer().then(function (buf) {
      return XlsxLite.parse(buf);
    }).then(function (grid) {
      if (!DATA) throw new Error("The item data has not loaded yet. Reload the page and try again.");
      var r = ClassEngine.run(grid, DATA);
      if (r.error) { fail(r.error); return; }
      render(r);
    }).catch(function (err) {
      fail(err && err.message ? err.message : String(err));
    });
  }

  function init() {
    var drop = $("drop"), input = $("file");
    input.onchange = function () { handle(input.files[0]); };
    ["dragenter", "dragover"].forEach(function (e) {
      drop.addEventListener(e, function (ev) {
        ev.preventDefault(); drop.classList.add("over");
      });
    });
    ["dragleave", "drop"].forEach(function (e) {
      drop.addEventListener(e, function (ev) {
        ev.preventDefault(); drop.classList.remove("over");
      });
    });
    drop.addEventListener("drop", function (ev) {
      handle(ev.dataTransfer.files && ev.dataTransfer.files[0]);
    });

    // The only network request this page makes, and the only one it may make.
    fetch("../data.json").then(function (res) { return res.json(); })
      .then(function (d) { DATA = d; })
      .catch(function () {
        $("out").innerHTML = '<div class="err">Could not load the item data ' +
          "(../data.json). Reload the page.</div>";
      });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else { init(); }
})();
