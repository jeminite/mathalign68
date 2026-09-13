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

    /* ---- where to focus next year ---- */
    h.push("<h3>Where to focus next year</h3>");
    var f = r.focus.filter(function (x) { return x.creditsLost > 0; });
    if (!f.length) {
      h.push('<p class="muted">This class was at or above the State on every standard.</p>');
    } else {
      h.push('<p class="note">Ranked by <strong>expected credits lost per student per year</strong> ' +
             "\u2014 the gap multiplied by how many credits that standard actually carries, " +
             "averaged over every grade " + (r.grade || "") + " test published here. Two " +
             "standards with the same gap are not equally costly: one worth 2.5 credits a year " +
             "matters more than one worth 1.</p>");
      h.push('<table class="grid"><thead><tr><th>Standard</th><th>Your class</th><th>State</th>' +
             "<th>Diff</th><th>Credits/yr</th><th>On how many tests</th><th>Credits lost</th>" +
             "<th>Taught in</th></tr></thead><tbody>");
      f.forEach(function (x) {
        h.push("<tr><td>" + esc(x.standard) + "</td><td>" + pc(x.classP) + "</td><td>" +
               pc(x.stateP) + '</td><td class="' + gapClass(x.gap) + '">' + gapStr(x.gap) +
               "</td><td>" + x.creditsPerYear.toFixed(2) + "</td><td>" + x.recurs + " of " +
               x.ofYears + '</td><td><strong>' + x.creditsLost.toFixed(2) + "</strong></td><td>" +
               unitCell(r, x.standard) + "</td></tr>");
      });
      h.push("</tbody></table>");
      var lost = f.reduce(function (a, x) { return a + x.creditsLost; }, 0);
      h.push('<p class="note">Those add to about <strong>' + lost.toFixed(1) + " credits</strong> " +
             "per student per year." + plContext(r, lost) + "</p>");
    }

    /* ---- what gates proficiency ---- */
    h.push("<h3>What gates proficiency</h3>");
    if (!r.gating.usable) {
      h.push('<p class="muted">' + esc(r.gating.why) + ".</p>");
    } else {
      var g = r.gating, sz = g.sizes;
      h.push('<p class="note">Each standard\u2019s credits earned, split by the level each ' +
             "student actually reached on this test \u2014 Level 1 (" + sz.L1 + " students), " +
             "Level 2 (" + sz.L2 + "), Level 3 (" + sz.L3 + "), Level 4 (" + sz.L4 + "). " +
             "A standard \u201cgates\u201d a threshold when the band above handles it and the " +
             "band below does not. \u201cHandles it\u201d means earning at least " +
             Math.round(g.threshold * 100) + "% of its credits; that line is a judgement, and " +
             "moving it moves these lists.</p>");
      [["gates-L2-L3", "Gates Level 3 \u2014 proficiency", true],
       ["gates-L1-L2", "Gates Level 2", false],
       ["gates-L3-L4", "Gates Level 4", false],
       ["weak-for-all", "Weak for every band", false],
       ["mixed", "No clean threshold", false],
       ["solid", "Already solid everywhere", false]].forEach(function (b) {
        var rows = g.rows.filter(function (x) { return x.bucket === b[0]; });
        if (!rows.length) return;
        h.push("<h4>" + b[1] + " <span class=\"muted\">\u00b7 " + rows.length +
               " standard" + (rows.length === 1 ? "" : "s") + "</span></h4>");
        if (b[2]) {
          h.push('<p class="note">The highest-leverage list on this page. A credit is worth ' +
                 "roughly double here \u2014 see the note below \u2014 so these are the " +
                 "cheapest places to move a student across the proficiency line.</p>");
        }
        h.push('<table class="grid"><thead><tr><th>Standard</th><th>Credits</th>' +
               "<th>Level 1</th><th>Level 2</th><th>Level 3</th><th>Level 4</th>" +
               "<th>Taught in</th></tr></thead><tbody>");
        rows.forEach(function (x) {
          h.push("<tr><td>" + esc(x.standard) + "</td><td>" + x.credits + "</td>" +
                 ["L1", "L2", "L3", "L4"].map(function (k) {
                   var v = x.byBand[k];
                   var cls = v === null ? "" : (v >= g.threshold ? "g-good" : "g-bad");
                   return '<td class="' + cls + '">' + pc(v) + "</td>";
                 }).join("") + "<td>" + unitCell(r, x.standard) + "</td></tr>");
        });
        h.push("</tbody></table>");
      });
    }

    /* ---- when it is taught ---- */
    var G = r.gatingByUnit;
    if (G && G.units && G.units.length) {
      h.push("<h3>When the gating content is taught</h3>");
      h.push('<p class="note">The standards that gate proficiency, placed against the ' +
             "35-week Imagine IM pacing calendar. The unit a standard belongs to is taken from " +
             "the publisher\u2019s own standard-to-lesson table, which names the right " +
             "<em>unit</em> 96.3% of the time and the right lesson only 77.4%, so this is unit " +
             "level only.</p>");
      h.push('<table class="grid"><thead><tr><th>Unit</th><th>Starts</th>' +
             "<th>Gating credits</th><th>Standards</th></tr></thead><tbody>");
      G.units.forEach(function (u) {
        h.push("<tr><td>" + u.unit + " \u2014 " + esc(u.title || "?") + "</td><td>week " +
               (u.startWeek === null ? "?" : u.startWeek) + "</td><td>" + u.credits +
               "</td><td>" + u.standards.map(esc).join(", ") + "</td></tr>");
      });
      h.push("</tbody></table>");
      if (G.doubleCounted) {
        h.push('<p class="note">A standard taught in more than one unit is counted in each, so ' +
               "these do not sum to the " + G.distinctCredits + " distinct gating credits.</p>");
      }
      var late = G.units.filter(function (u) { return u.startWeek >= 21 && u.startWeek <= 29; });
      if (late.length) {
        var lateCr = late.reduce(function (a, u) { return a + u.credits; }, 0);
        h.push('<div class="caution"><strong>' + lateCr + " of the gating credits are taught " +
               "in weeks 21\u201329</strong> \u2014 " +
               late.map(function (u) { return "Unit " + u.unit + " (week " + u.startWeek + ")"; })
                 .join(" and ") + " \u2014 against a State test in roughly week 30. The content " +
               "that most decides whether a student reaches proficiency arrives last, with the " +
               "least room left to reteach it. That is a pacing decision rather than an " +
               "instructional one, and it is the most actionable thing on this page.</div>");
      }
    }

    if (r.placement && r.placement.unplaced.length) {
      h.push('<p class="note">Not found in the grade ' + (r.grade || "") +
             " standard-to-lesson table at all: " + r.placement.unplaced.map(esc).join(", ") +
             ". That is a gap in the published index, not a gap in your teaching.</p>");
    }
    if (r.placement && r.placement.priorGrade.length) {
      h.push('<p class="note">Assessed here but taught a year earlier, so they sit in no grade ' +
             (r.grade || "") + " unit: " + r.placement.priorGrade.map(esc).join(", ") + ".</p>");
    }

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

  // Which unit(s) a standard is taught in, and when. Unit level only.
  function unitCell(r, std) {
    var us = (r.placement && r.placement.byStandard[std]) || [];
    if (!us.length) return '<span class="muted">\u2014</span>';
    return us.map(function (u) {
      return "U" + u.unit + (u.startWeek === null ? "" : " (wk " + u.startWeek + ")");
    }).join(", ");
  }

  // Turn a credits figure into proficiency-level terms, and refuse to when the
  // curve could not be recovered. This is the sentence that keeps the whole page
  // honest: closing the State gap is worth far less than it sounds.
  function plContext(r, lostCredits) {
    var c = r.curve;
    if (!c || !c.usable) return "";
    var l2 = (c.bands.filter(function (b) { return b.band === "L2"; })[0] || {}).plPerCredit;
    if (!l2) return "";
    var cut = c.cuts.filter(function (x) { return x.level === 3; })[0] || {};
    var move = (lostCredits * l2).toFixed(2);
    return " On this test a credit was worth about " + l2.toFixed(3) + " of a proficiency " +
           "level just below the Level 3 line, so recovering all of them would move a student " +
           "there by roughly <strong>" + move + " of a level</strong>" +
           (cut.raw ? " \u2014 and Level 3 itself began at " + cut.raw + " of " +
            r.totalCredits + " credits" : "") +
           ". Closing the gap to the State average is worth real credits, but it is " +
           "<strong>not</strong> the same as moving a student up a level: that takes closer to " +
           "8 credits from mid-Level 2.";
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
