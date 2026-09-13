/* Class results engine -- parsing and analysis, no DOM.
 *
 * The same file runs in Node (for the test harness) and in the browser (where
 * the page loads it with a <script> tag). It never touches the network and
 * never writes anything: the caller hands it a parsed workbook and the
 * published payload, and gets back a report object.
 *
 * WHAT IT READS
 * A NYSED ISA export: one header row of "Q<n> (<standard>)" cells, then one row
 * per student. A multiple-choice cell holds the letter that student chose; a
 * constructed-response cell holds points earned. See provenance/isa_format.md
 * for the layout and for how it differs from the ATS REDS export that
 * RegentsAlign's analyzer reads.
 *
 * WHY IT DETECTS STRUCTURE RATHER THAN TRUSTING POSITIONS
 * The one export in hand puts its header on row 1, but RegentsAlign saw two
 * exports from the same school a year apart put theirs on different rows, and
 * deleting the identity columns shifts everything left. Anchoring on "the row
 * that contains the Q(standard) headers" survives both.
 *
 * WHAT IT NEVER READS
 * Identity columns. The question grid is located first and only those columns
 * are ever touched, so a name or an OSIS number cannot reach the report even if
 * the teacher forgets to delete them. The single exception is a column headed
 * exactly "Class", which is read for section codes and is guarded three ways --
 * see findClassColumn. Column 0 is never read whatever it is headed.
 */
(function (root) {
  "use strict";

  var HEADER = /^Q\s*(\d+)\s*\(\s*([0-9]+(?:\.[A-Za-z0-9]+)+)\s*\)$/;

  function cell(v) {
    return (v === null || v === undefined) ? "" : String(v).trim();
  }

  /* ------------------------------------------------------------------ parse */

  // The header row is the first row holding several Q(standard) cells. Ten is
  // well above anything that could appear by accident and well below the 39
  // this export carries, so a test with many withheld items still parses.
  function findHeaderRow(grid) {
    for (var r = 0; r < Math.min(grid.length, 40); r++) {
      if (!grid[r]) continue;
      var cols = {}, std = {}, seen = 0;
      for (var c = 0; c < grid[r].length; c++) {
        var m = HEADER.exec(cell(grid[r][c]));
        if (!m) continue;
        var q = parseInt(m[1], 10);
        if (q in cols) continue;              // a duplicated header, keep the first
        cols[q] = c;
        // The ISA writes standards bare. The payload writes them NY-prefixed,
        // and that prefix is the documented boundary between this project's
        // codes and RegentsAlign's.
        std[q] = "NY-" + m[2];
        seen++;
      }
      if (seen >= 10) return { row: r, cols: cols, std: std, count: seen };
    }
    return null;
  }

  // Anything alphabetic in a column left of the question grid looks like a
  // name. We do not read those columns; this only powers a notice.
  //
  // Distinct values, not hits. A roster is 78 different people; a column
  // holding one word 78 times is a placeholder. The real export this format
  // was read from has every name replaced by the literal string "name", and
  // counting hits warned about it on every load -- a warning that cries wolf
  // when nothing is wrong is a warning people learn to click past, which
  // costs exactly the case it exists for.
  function looksLikeIdentity(grid, headerRow, firstQCol) {
    var seen = {}, distinct = 0;
    for (var r = headerRow + 1; r < Math.min(grid.length, headerRow + 40); r++) {
      if (!grid[r]) continue;
      for (var c = 0; c < Math.min(firstQCol, 3); c++) {
        var v = grid[r][c];
        // "DOE, JANE" -- the comma matters, it is how ATS writes names.
        if (typeof v !== "string") continue;
        var t = v.trim();
        if (!/^[A-Za-z][A-Za-z', .-]{3,}$/.test(t)) continue;
        if (!seen[t]) { seen[t] = 1; distinct++; }
      }
    }
    return distinct >= 3;
  }

  // The one column left of the grid we are allowed to read, and only this one.
  //
  // Three guards, each for its own reason. The header must be exactly "Class",
  // so the rule is mechanical rather than a judgement about which column looks
  // section-shaped. The index must not be 0, because column 0 is where the name
  // lives and no header spelling should be able to unlock it. And the values
  // must look like codes -- short, no comma, not name-shaped -- before a single
  // one is kept.
  function findClassColumn(grid, headerRow, firstQCol) {
    if (!grid[headerRow]) return -1;
    for (var c = 1; c < firstQCol; c++) {
      if (cell(grid[headerRow][c]).toLowerCase() !== "class") continue;
      for (var r = headerRow + 1; r < Math.min(grid.length, headerRow + 40); r++) {
        var v = cell(grid[r] && grid[r][c]);
        if (!v) continue;
        if (v.length > 8 || v.indexOf(",") >= 0 || /^[A-Za-z][A-Za-z', .-]{3,}$/.test(v)) {
          return -1;
        }
      }
      return c;
    }
    return -1;
  }

  // The proficiency-level column, and the second exception to "never read left
  // of the grid". It is read for exactly two aggregate purposes -- recovering
  // the raw-to-PL curve, which is a property of the TEST, and banding students
  // so the report can say which standards gate which threshold. No individual
  // PL ever reaches the report; assertNoIdentity enforces that with a banned
  // key list rather than trusting this comment.
  //
  // Guarded the same mechanical way as the Class column: the header must be
  // exactly "NYS Math", the index must not be 0, and every value must parse as
  // a number inside the level scale. A column of anything else is refused
  // whole rather than read partially.
  function findPlColumn(grid, headerRow, firstQCol) {
    if (!grid[headerRow]) return -1;
    for (var c = 1; c < firstQCol; c++) {
      if (cell(grid[headerRow][c]).toLowerCase() !== "nys math") continue;
      var seen = 0;
      for (var r = headerRow + 1; r < Math.min(grid.length, headerRow + 400); r++) {
        var v = cell(grid[r] && grid[r][c]);
        if (!v) continue;
        var n = parseFloat(v);
        // 1.0 to 4.6: the NYS level scale with headroom. A percentage, a scale
        // score in the hundreds, or a letter grade all fall outside it.
        if (isNaN(n) || n < 1 || n > 4.6) return -1;
        seen++;
      }
      return seen ? c : -1;
    }
    return -1;
  }

  function parseGrid(grid) {
    var warn = [];
    if (!grid || !grid.length) {
      return { error: "That sheet is empty." };
    }
    var head = findHeaderRow(grid);
    if (!head) {
      return { error: "No row of question headers was found. The analyser expects a NYSED " +
                      "ISA export, whose header row reads like “Q1 (6.RP.2)” — the " +
                      "question number and the standard it assesses, one column per question." };
    }

    var qs = Object.keys(head.cols).map(Number).sort(function (a, b) { return a - b; });
    var firstQCol = head.cols[qs[0]];
    if (looksLikeIdentity(grid, head.row, firstQCol)) {
      warn.push("This file still has student names or ID numbers in its first columns. " +
                "They were not read and appear nowhere in this report, but you may want " +
                "to delete them before saving or sharing the file itself.");
    }

    var classCol = findClassColumn(grid, head.row, firstQCol);
    var plCol = findPlColumn(grid, head.row, firstQCol);
    var students = [], sections = {};
    for (var r = head.row + 1; r < grid.length; r++) {
      if (!grid[r]) continue;
      var resp = {}, any = false;
      for (var i = 0; i < qs.length; i++) {
        var v = cell(grid[r][head.cols[qs[i]]]);
        resp[qs[i]] = v === "" ? null : v;
        if (v !== "") any = true;
      }
      if (!any) continue;                       // blank or spacer row
      var sec = classCol >= 0 ? (cell(grid[r][classCol]) || null) : null;
      if (sec) sections[sec] = (sections[sec] || 0) + 1;
      var pl = null;
      if (plCol >= 0) {
        var pv = parseFloat(cell(grid[r][plCol]));
        if (!isNaN(pv)) pl = pv;
      }
      students.push({ section: sec, resp: resp, pl: pl });
    }

    if (!students.length) {
      return { error: "No student rows were found beneath the question headers." };
    }

    // A class section holds several students. A code that appears once per row
    // is a per-student identifier, not a section -- one 2024 export RegentsAlign
    // saw used initials plus year (DC24, JF24) in that column, and reporting
    // those would have put an identifier in the output. If the codes are mostly
    // unique, discard them and record no sections at all.
    var codes = Object.keys(sections);
    var shared = codes.filter(function (k) { return sections[k] > 1; }).length;
    if (!codes.length || shared < codes.length / 2 || codes.length > students.length / 2) {
      sections = {};
      students.forEach(function (s) { s.section = null; });
    }

    return { questions: qs, std: head.std, students: students, sections: sections,
             hasPl: plCol >= 0, headerRow: head.row + 1, warnings: warn };
  }

  /* --------------------------------------------------------------- identify */

  // The ISA carries no answer key, so the exam cannot be fingerprinted the way
  // RegentsAlign does it. The headers carry something better: each question's
  // standard. Scoring those pairs against all twelve tests puts the right one
  // at 39 of 39 and the runner-up at 2, so this can demand a decisive winner
  // and refuse rather than join against the nearest neighbour.
  function identifyTest(parsed, data) {
    var byTest = {};
    data.items.forEach(function (it) {
      (byTest[it.testId] = byTest[it.testId] || {})[it.item] = it.standard;
    });
    var total = parsed.questions.length;
    var scores = Object.keys(byTest).map(function (testId) {
      var agree = 0;
      parsed.questions.forEach(function (q) {
        if (byTest[testId][q] && byTest[testId][q] === parsed.std[q]) agree++;
      });
      return { testId: testId, agree: agree };
    }).sort(function (a, b) { return b.agree - a.agree; });

    var best = scores[0], next = scores[1] || { agree: 0 };
    // Both halves matter. A high score alone could come from two tests that
    // share a blueprint; a wide margin alone could be two poor scores far
    // apart. The observed numbers clear this by a distance (39/39, 19.5x).
    if (!best || best.agree < total * 0.8 || best.agree < next.agree * 2) {
      return { testId: null, agree: best ? best.agree : 0, total: total,
               runnerUp: next.agree,
               error: "This file could not be matched to a published test. Its question " +
                      "headers agreed with the closest one on " + (best ? best.agree : 0) +
                      " of " + total + " standards, which is not a clear enough match to " +
                      "trust. MathAlign68 covers grades 6–8 for 2023–2026." };
    }
    return { testId: best.testId, agree: best.agree, total: total, runnerUp: next.agree };
  }

  /* --------------------------------------------------------------- pl curve */

  // Recover raw-credits -> proficiency level from the file's own PL column.
  //
  // It is a LOOKUP, not a fit. On the one real export in hand the PL is a
  // collision-free strictly-increasing function of raw credits: 35 distinct raw
  // values across 78 students, not one mapping to two PLs. So the conversion is
  // recovered rather than estimated, and a target can be stated in credits --
  // the only unit a student can act on.
  //
  // If it ever DOES collide, that assumption is broken for that file and every
  // downstream PL claim is suppressed. Averaging the colliding values would
  // produce a curve that looks fine and is wrong. See provenance/pl_curve.md.
  var PL_CUTS = [2, 3, 4];

  function plCurve(rawByStudent, pls, total) {
    var seen = {}, collisions = 0;
    for (var i = 0; i < pls.length; i++) {
      if (pls[i] === null || rawByStudent[i] === null) continue;
      var raw = rawByStudent[i];
      if (!(raw in seen)) { seen[raw] = pls[i]; continue; }
      if (Math.abs(seen[raw] - pls[i]) > 0.005) collisions++;
    }
    var points = Object.keys(seen).map(Number).sort(function (a, b) { return a - b; });
    if (points.length < 6) {
      return { usable: false, why: "too few distinct raw scores (" + points.length +
                                  ") to recover a curve", points: points.length };
    }
    for (var j = 0; j + 1 < points.length; j++) {
      if (seen[points[j + 1]] <= seen[points[j]]) collisions++;   // not monotonic
    }
    if (collisions) {
      return { usable: false, why: "the proficiency level is not a clean function of raw " +
                                   "credits in this file (" + collisions + " conflict(s)), so " +
                                   "no credit target can be trusted from it",
               collisions: collisions, points: points.length };
    }

    // Named `level`, not `pl`, so that `pl` stays reserved for per-student
    // data and assertNoIdentity's banned-key list needs no path exception.
    var table = points.map(function (r) { return { raw: r, level: seen[r] }; });

    // Which cut points landed on an OBSERVED raw score and which are bracketed
    // between two. On the real file Level 3 and Level 4 are exact and Level 2
    // is not, and presenting all three with equal confidence would be a lie.
    var cuts = PL_CUTS.map(function (cut) {
      var exact = points.filter(function (r) { return Math.abs(seen[r] - cut) < 0.005; });
      if (exact.length) {
        return { level: cut, raw: exact[0], exact: true,
                 pctOfTest: total ? Math.round(1000 * exact[0] / total) / 10 : null };
      }
      var below = points.filter(function (r) { return seen[r] < cut; });
      var above = points.filter(function (r) { return seen[r] > cut; });
      if (!below.length || !above.length) return { level: cut, raw: null, exact: false };
      var lo = below[below.length - 1], hi = above[0];
      return { level: cut, raw: hi, exact: false, between: [lo, hi],
               pctOfTest: total ? Math.round(1000 * hi / total) / 10 : null };
    });

    // PL gained per credit, between adjacent observed points, per level band.
    // The L2 band runs at roughly double the others: a student just below
    // proficient is the cheapest to move. That is a targeting fact and the page
    // presents it as one.
    var bands = [[1, 2, "L1"], [2, 3, "L2"], [3, 4, "L3"], [4, 9, "L4"]].map(function (b) {
      var rates = [];
      for (var k = 0; k + 1 < points.length; k++) {
        var a = points[k], c = points[k + 1];
        // BOTH endpoints inside the band. A segment that crosses a threshold
        // belongs to neither: raw 23->24 is the credit that carries a student
        // from 2.94 into proficiency, and counting it as an L2 rate pulled the
        // L2 figure down by half a point. Likewise raw 38 (3.97) is an L3
        // point, and including it in L4 understated L4.
        if (seen[a] >= b[0] && seen[a] < b[1] && seen[c] >= b[0] && seen[c] < b[1]) {
          rates.push((seen[c] - seen[a]) / (c - a));
        }
      }
      var mean = rates.length ? rates.reduce(function (x, y) { return x + y; }, 0) / rates.length : null;
      return { band: b[2], plPerCredit: mean === null ? null : Math.round(mean * 1000) / 1000,
               segments: rates.length };
    });

    function rawFor(pl) {
      var over = points.filter(function (r) { return seen[r] > pl; });
      return over.length ? over[0] : null;
    }
    function plFor(raw) {
      if (raw in seen) return seen[raw];
      var below = points.filter(function (r) { return r <= raw; });
      return below.length ? seen[below[below.length - 1]] : null;
    }

    return { usable: true, total: total, table: table, cuts: cuts, bands: bands,
             points: points.length, collisions: 0,
             // Raw scores nobody in this class earned. Anything between two
             // observed points is interpolation; the page says so.
             unobserved: (function () {
               var out = [];
               for (var r = points[0]; r <= total; r++) if (!(r in seen)) out.push(r);
               return out;
             })(),
             rawFor: rawFor, plFor: plFor };
  }

  // "From PL x, how many more credits to get above PL y?" -- the question the
  // whole curve exists to answer. A band-level answer would be wrong for almost
  // everyone in the band: 2.75-3.25 is 8 credits at the bottom and 1 at the top.
  function creditsToReach(curve, fromPl, targetPl) {
    if (!curve.usable) return null;
    var from = null;
    curve.table.forEach(function (t) { if (t.level <= fromPl) from = t.raw; });
    if (from === null) from = curve.table[0].raw;
    var to = curve.rawFor(targetPl);
    if (to === null) return null;
    return { fromRaw: from, toRaw: to, credits: Math.max(0, to - from) };
  }

  /* ---------------------------------------------------------------- analyse */

  function pct(x) { return x === null || x === undefined ? null : Math.round(x * 1000) / 1000; }

  function analyse(parsed, testId, data) {
    var byItem = {};
    data.items.forEach(function (it) { if (it.testId === testId) byItem[it.item] = it; });
    var test = (data.tests || []).filter(function (t) { return t.testId === testId; })[0] || {};
    var n = parsed.students.length;

    var items = [], unmatched = [];
    parsed.questions.forEach(function (q) {
      var meta = byItem[q];
      if (!meta) {
        // The ISA reported an item this project has no key or P-value for --
        // NYSED withheld it from release. Counted and named, never guessed at.
        unmatched.push({ item: q, standard: parsed.std[q] });
        return;
      }
      var mc = meta.type === "Multiple Choice";
      var credits = meta.credits || 1;
      var answered = 0, omitted = 0, earned = 0;
      var chose = {}, correct = 0, full = 0, zero = 0;

      parsed.students.forEach(function (s) {
        var v = s.resp[q];
        if (v === null) { omitted++; return; }
        answered++;
        if (mc) {
          // Unlike a REDS export, the ISA records the letter chosen whether it
          // was right or wrong, so the correct letter has to be kept out of
          // `chose` deliberately. RegentsAlign hit the mirror image of this bug
          // and put the RIGHT option at the top of its most-chosen-wrong column.
          if (meta.key && v.toUpperCase() === meta.key.toUpperCase()) {
            correct++; earned += credits;
          } else {
            var lab = v.toUpperCase();
            chose[lab] = (chose[lab] || 0) + 1;
          }
        } else {
          var pts = parseFloat(v);
          if (isNaN(pts)) { answered--; omitted++; return; }
          earned += pts;
          if (pts >= credits) full++;
          if (pts === 0) zero++;
        }
      });

      // Denominator is every student in the file, not every student who
      // answered. NYSED's P-value counts an omission as no credit, and a
      // different denominator would not be comparable to it. Omissions are
      // reported separately so they can still be seen.
      var classP = n ? earned / (credits * n) : null;
      // For a constructed-response item NYSED publishes average points earned,
      // so divide by credits to get the same 0-1 quantity. meta.pValueCaveat
      // is explicit that this is NOT the same quantity as a multiple-choice
      // percent correct, and the page keeps them off one axis.
      var stateP = mc ? meta.pValue
                      : (meta.avgPointsEarned === null || meta.avgPointsEarned === undefined
                         ? meta.pValue : meta.avgPointsEarned / credits);

      var top = Object.keys(chose).sort(function (a, b) { return chose[b] - chose[a]; })[0];
      var topText = null;
      if (top && meta.choiceList) {
        var ch = meta.choiceList.filter(function (x) { return x.label === top; })[0];
        // An empty string is not a missing value here. Where the choices ARE
        // the pictures -- 2026 grade 6 items 23 and 34 are number lines -- the
        // payload carries the labels with no text, on purpose. Normalise to
        // null so the page can say "that choice is a picture, look at it"
        // rather than printing nothing and looking broken.
        if (ch && ch.text) topText = ch.text;
      }

      // Name the domain from the standards registry, not from the item's
      // domainLabel. domainLabel is NYSED's reporting SUBSCORE, so the
      // grade 5 post-test item on NY-5.OA.3 carries "Expressions and
      // Equations" -- correct as a subscore, but it put two rows called
      // "Expressions and Equations" in the domain table. The registry also
      // has the clean name: the item maps yield "Number Sense", "Number
      // Systems" and "The Number Session System 2" for NS across the twelve
      // tests, and grouping on those would split one domain four ways.
      var reg = (data.standards || {})[meta.standard] || {};
      items.push({
        item: q, standard: meta.standard, domain: meta.domain,
        domainLabel: reg.domainName || meta.domainLabel,
        subscore: meta.subscore || null,
        type: mc ? "mc" : "cr", credits: credits,
        key: meta.key || null, postTest: !!meta.postTest,
        n: n, answered: answered, omitted: omitted,
        earned: Math.round(earned * 100) / 100,
        correct: correct, fullCredit: full, zeroCredit: zero,
        classP: pct(classP), stateP: pct(stateP),
        gap: stateP === null || stateP === undefined ? null : pct(classP - stateP),
        chose: chose, topWrong: top || null,
        topWrongCount: top ? chose[top] : 0,
        topWrongText: topText,
        choiceList: meta.choiceList || null,
        choicesInImage: !!meta.choicesInImage,
        stemPlain: meta.stemPlain || null,
        sourceUrl: meta.sourceUrl || null,
        lesson: meta.lesson || null, lessonTitle: meta.lessonTitle || null,
        unit: meta.unit || null, unitTitle: meta.unitTitle || null,
        // Which grade's curriculum the placement sits in. A grade 8 item on a
        // grade 7 standard is judged into grade 7's course, and filing it under
        // a grade 8 unit would be wrong.
        course: meta.course || null,
        alignmentStatus: meta.alignmentStatus || null
      });
    });

    // A quarter of the class landing on the SAME wrong option is a specific
    // misconception rather than scattered difficulty. That threshold is what
    // separates a teachable pattern from noise.
    var dominant = items.filter(function (i) {
      return i.type === "mc" && i.topWrongCount >= n / 4;
    }).sort(function (a, b) { return b.topWrongCount - a.topWrongCount; });

    function rollup(keyOf, labelOf) {
      var groups = {};
      items.forEach(function (i) {
        var k = keyOf(i);
        if (!k) return;
        var g = groups[k] || (groups[k] = { key: k, label: labelOf(i), items: [],
                                            earned: 0, possible: 0, stateEarned: 0 });
        g.items.push(i.item);
        g.earned += i.earned;
        g.possible += i.credits * n;
        // The state's expectation on the same credits, so both sides of the
        // comparison are computed the same way. Within a rollup this blends
        // multiple-choice percent correct with constructed-response points per
        // credit; the page says so where it shows one.
        if (i.stateP !== null) g.stateEarned += i.stateP * i.credits * n;
      });
      return Object.keys(groups).map(function (k) {
        var g = groups[k];
        g.classP = pct(g.possible ? g.earned / g.possible : null);
        g.stateP = pct(g.possible ? g.stateEarned / g.possible : null);
        g.gap = g.classP === null || g.stateP === null ? null : pct(g.classP - g.stateP);
        return g;
      }).sort(function (a, b) { return (a.gap === null ? 1 : a.gap) - (b.gap === null ? 1 : b.gap); });
    }

    // Per-section figures, computed only when parseGrid kept the sections.
    var bySection = [];
    var secNames = Object.keys(parsed.sections).sort();
    if (secNames.length > 1) {
      bySection = secNames.map(function (name) {
        var roster = parsed.students.filter(function (s) { return s.section === name; });
        var earned = 0, possible = 0, perItem = {};
        items.forEach(function (i) {
          var meta = byItem[i.item], got = 0;
          roster.forEach(function (s) {
            var v = s.resp[i.item];
            if (v === null) return;
            if (i.type === "mc") {
              if (meta.key && v.toUpperCase() === meta.key.toUpperCase()) got += i.credits;
            } else {
              var p = parseFloat(v);
              if (!isNaN(p)) got += p;
            }
          });
          earned += got;
          possible += i.credits * roster.length;
          perItem[i.item] = roster.length ? pct(got / (i.credits * roster.length)) : null;
        });
        return { section: name, students: roster.length,
                 classP: pct(possible ? earned / possible : null), perItem: perItem };
      });
    }

    var earnedAll = 0, possibleAll = 0, stateAll = 0;
    items.forEach(function (i) {
      earnedAll += i.earned;
      possibleAll += i.credits * n;
      if (i.stateP !== null) stateAll += i.stateP * i.credits * n;
    });

    // Per-student raw credit totals, on the matched items only. These exist to
    // build the curve and to band students; they are NOT part of the report and
    // assertNoIdentity refuses a report that carries them.
    var totalCredits = items.reduce(function (a, i) { return a + i.credits; }, 0);
    var rawByStudent = parsed.students.map(function (s) {
      var raw = 0;
      items.forEach(function (i) {
        var meta = byItem[i.item], v = s.resp[i.item];
        if (v === null) return;
        if (meta.type === "Multiple Choice") {
          if (meta.key && v.toUpperCase() === meta.key.toUpperCase()) raw += meta.credits;
        } else {
          var pv = parseFloat(v);
          if (!isNaN(pv)) raw += pv;
        }
      });
      return raw;
    });
    var curve = parsed.hasPl
      ? plCurve(rawByStudent, parsed.students.map(function (s) { return s.pl; }), totalCredits)
      : { usable: false, why: "this file carries no proficiency-level column" };

    var gating = parsed.hasPl ? bandGating(parsed, items, byItem)
                              : { usable: false, why: "this file carries no proficiency-level column" };
    var focusRows = focus(items, data, test.grade);
    var lessonRows = focusByLesson(items, test.grade, focusRows);
    var place = placement(items, data, test.grade);
    place.focusRows = focusRows;
    var checks = checkpoints(items, data, gating, place, test.grade);

    // Gating credits per unit -- the finding that turned out to matter most on
    // the real file. The standards that gate proficiency concentrate in units
    // taught after the midpoint of the year, against a test in roughly week 30.
    var gatingByUnit = { units: [], distinctCredits: 0, doubleCounted: false };
    if (gating.usable) {
      var acc = {};
      gating.rows.filter(function (r) { return r.bucket === "gates-L2-L3"; }).forEach(function (r) {
        (place.byStandard[r.standard] || []).forEach(function (u) {
          var a = acc[u.unit] = acc[u.unit] ||
            { unit: u.unit, title: u.title, startWeek: u.startWeek, credits: 0, standards: [] };
          a.credits += r.credits;
          if (a.standards.indexOf(r.standard) < 0) a.standards.push(r.standard);
        });
      });
      gatingByUnit = Object.keys(acc).map(function (k) { return acc[k]; })
        .sort(function (a, b) { return b.credits - a.credits; });

      // A standard taught in several units is counted in each, so the per-unit
      // figures deliberately do NOT sum to the gating total -- NY-6.RP.3c alone
      // appears in units 3, 6 and 9. Publish the true distinct total beside them
      // so the page can say so rather than implying a partition.
      var distinct = gating.rows.filter(function (r) { return r.bucket === "gates-L2-L3"; })
        .reduce(function (a, r) { return a + r.credits; }, 0);
      gatingByUnit.distinctCredits = distinct;
      gatingByUnit = { units: gatingByUnit, distinctCredits: distinct,
                       doubleCounted: gatingByUnit.reduce(function (a, u) {
                         return a + u.credits; }, 0) !== distinct };
    }

    return {
      testId: testId, grade: test.grade || null, year: test.year || null,
      label: test.label || testId,
      students: n, sections: parsed.sections,
      matched: items.length, unmatched: unmatched,
      overall: { classP: pct(possibleAll ? earnedAll / possibleAll : null),
                 stateP: pct(possibleAll ? stateAll / possibleAll : null),
                 gap: pct(possibleAll ? (earnedAll - stateAll) / possibleAll : null),
                 earned: Math.round(earnedAll * 10) / 10, possible: possibleAll },
      items: items,
      byGap: items.slice().sort(function (a, b) {
        return (a.gap === null ? 1 : a.gap) - (b.gap === null ? 1 : b.gap);
      }),
      dominant: dominant,
      byStandard: rollup(function (i) { return i.standard; },
                         function (i) { return i.standard; }),
      byDomain: rollup(function (i) { return i.domain; },
                       function (i) { return i.domainLabel; }),
      bySection: bySection,
      totalCredits: totalCredits,
      curve: curve, gating: gating, focus: focusRows, focusByLesson: lessonRows,
      placement: place, gatingByUnit: gatingByUnit, checkpoints: checks,
      constructed: items.filter(function (i) { return i.type === "cr"; })
                        .sort(function (a, b) { return b.zeroCredit - a.zeroCredit; }),
      omissions: items.filter(function (i) { return i.omitted > 0; })
                      .sort(function (a, b) { return b.omitted - a.omitted; }),
      warnings: parsed.warnings || []
    };
  }

  /* ------------------------------------------------------ focus and gating */

  // Expected credits lost per student per year, per standard.
  //
  // Ranking by gap alone is wrong, and the real file shows exactly why:
  // NY-6.EE.8 and NY-6.G.1 share a -17.8% gap, but G.1 is worth 2.5 credits a
  // year and EE.8 is worth 1. Sorting by gap puts them level. Multiplying the
  // gap by how many credits the standard actually carries -- averaged over
  // every same-grade test in the payload -- puts G.1 first, which is where it
  // belongs.
  function focus(items, data, grade) {
    var years = {}, weight = {};
    data.items.forEach(function (it) {
      if (it.grade !== grade) return;
      years[it.year] = 1;
      (weight[it.standard] = weight[it.standard] || {})[it.year] =
        ((weight[it.standard] || {})[it.year] || 0) + it.credits;
    });
    var yrs = Object.keys(years).map(Number).sort();
    if (!yrs.length) return [];

    var byStd = {};
    items.forEach(function (i) {
      var g = byStd[i.standard] = byStd[i.standard] ||
        { standard: i.standard, domain: i.domain, domainLabel: i.domainLabel,
          items: [], earned: 0, possible: 0, stateEarned: 0 };
      g.items.push(i.item);
      g.earned += i.earned;
      g.possible += i.credits * i.n;
      if (i.stateP !== null) g.stateEarned += i.stateP * i.credits * i.n;
    });

    return Object.keys(byStd).map(function (k) {
      var g = byStd[k], w = weight[k] || {};
      var classP = g.possible ? g.earned / g.possible : null;
      var stateP = g.possible ? g.stateEarned / g.possible : null;
      var gap = (classP === null || stateP === null) ? null : classP - stateP;
      var mean = yrs.reduce(function (a, y) { return a + (w[y] || 0); }, 0) / yrs.length;
      var recurs = yrs.filter(function (y) { return w[y]; }).length;
      return { standard: k, domain: g.domain, domainLabel: g.domainLabel,
               items: g.items, classP: pct(classP), stateP: pct(stateP), gap: pct(gap),
               creditsPerYear: Math.round(mean * 100) / 100,
               recurs: recurs, ofYears: yrs.length,
               // Negative gap only: a standard the class beat the state on is
               // not an area of focus, and signing it would sort it into the
               // middle rather than out of the way.
               creditsLost: gap === null || gap >= 0 ? 0 : Math.round(-gap * mean * 100) / 100 };
    }).sort(function (a, b) { return b.creditsLost - a.creditsLost; });
  }

  // The same question asked of LESSONS instead of standards.
  //
  // focus() answers "which standard is costing you credits", which is the
  // question the data could answer before the alignment existed. A standard is
  // not a thing a teacher can reteach on a Tuesday; a lesson is. Every item now
  // carries a judged lesson, so the credits a class is losing can be attributed
  // to the lesson whose activities ask that item's question -- "reteach Unit 3
  // Lesson 7" rather than "focus on NY-6.RP.3b".
  //
  // Deliberately reuses focus()'s credit weighting rather than recomputing it:
  // creditsPerYear is how often this content has actually recurred across the
  // released tests, and a lesson inherits it from the items on it. Two figures
  // that ought to agree and are computed twice will eventually disagree.
  //
  // Items without a judged lesson in this grade's own curriculum are skipped,
  // not bucketed into an "unknown" row. A lesson report whose largest row is
  // "unknown" teaches nobody anything.
  function focusByLesson(items, grade, focusRows) {
    var perStandard = {};
    (focusRows || []).forEach(function (r) { perStandard[r.standard] = r; });

    var acc = {};
    items.forEach(function (i) {
      if (i.lesson === null || i.lesson === undefined) return;
      if (i.unit === null || i.unit === undefined) return;
      var m = /Grade\s+(\d)/.exec(i.course || "");
      if (!m || m[1] !== String(grade)) return;

      var key = i.unit + "." + i.lesson;
      var a = acc[key] = acc[key] ||
        { unit: i.unit, unitTitle: i.unitTitle || null,
          lesson: i.lesson, lessonTitle: i.lessonTitle || null,
          items: [], standards: [], earned: 0, possible: 0, stateEarned: 0,
          creditsPerYear: 0 };
      a.items.push(i.item);
      if (a.standards.indexOf(i.standard) < 0) {
        a.standards.push(i.standard);
        // A standard's whole per-year credit weight is attributed to each lesson
        // its items land on. Two lessons sharing a standard therefore both show
        // its weight, which overstates the total ACROSS rows -- the same
        // double-count gatingByUnit already carries and reports rather than
        // hides. Per row the figure is right, and the rows are what a teacher
        // reads.
        var f = perStandard[i.standard];
        if (f) a.creditsPerYear += f.creditsPerYear;
      }
      a.earned += i.earned;
      a.possible += i.credits * i.n;
      if (i.stateP !== null && i.stateP !== undefined) {
        a.stateEarned += i.stateP * i.credits * i.n;
      }
    });

    return Object.keys(acc).map(function (k) {
      var a = acc[k];
      var classP = a.possible ? a.earned / a.possible : null;
      var stateP = a.possible ? a.stateEarned / a.possible : null;
      var gap = (classP === null || stateP === null) ? null : classP - stateP;
      a.classP = pct(classP);
      a.stateP = pct(stateP);
      a.gap = pct(gap);
      a.creditsPerYear = Math.round(a.creditsPerYear * 100) / 100;
      // Same rule as focus(): a lesson the class beat the state on is not an
      // area of focus, and signing it would sort it into the middle rather than
      // out of the way.
      a.creditsLost = (gap === null || gap >= 0)
        ? 0 : Math.round(-gap * a.creditsPerYear * 100) / 100;
      return a;
    }).sort(function (a, b) { return b.creditsLost - a.creditsLost; });
  }

  // Which threshold does each standard gate?
  //
  // Borrowed from AlgebraTeaching's Performance_Band_Analysis, which buckets
  // standards by which score band they block rather than by raw difficulty.
  // That report calls its own thresholds "a heuristic, not a fitted model";
  // this one is grounded in the student's own published PL instead.
  //
  // 0.60 of available credits is the line for "this band handles it". It is a
  // judgement, so it is named, reported on the page, and kept in one place.
  var GATING_THRESHOLD = 0.6;
  // Below this a band's percentage is noise. AlgebraTeaching scoped this whole
  // analysis down because its bands held 4-10 students; refusing is better than
  // publishing a number that cannot bear weight.
  var MIN_BAND = 5;

  function bandGating(parsed, items, byItem) {
    var withPl = parsed.students.filter(function (s) { return s.pl !== null; });
    if (withPl.length < 4 * MIN_BAND) {
      return { usable: false, why: "not enough students with a proficiency level to band" };
    }
    var NAMES = ["L1", "L2", "L3", "L4"];
    function bandOf(pl) { return pl < 2 ? "L1" : (pl < 3 ? "L2" : (pl < 4 ? "L3" : "L4")); }
    var groups = {}, sizes = {};
    NAMES.forEach(function (b) { groups[b] = []; sizes[b] = 0; });
    withPl.forEach(function (s) { var b = bandOf(s.pl); groups[b].push(s); sizes[b]++; });

    var small = NAMES.filter(function (b) { return sizes[b] < MIN_BAND; });
    if (small.length) {
      return { usable: false, sizes: sizes,
               why: "band" + (small.length === 1 ? " " : "s ") + small.join(", ") +
                    " " + (small.length === 1 ? "holds" : "hold") + " fewer than " +
                    MIN_BAND + " students, too few to report a percentage for" };
    }

    var byStd = {};
    items.forEach(function (i) {
      (byStd[i.standard] = byStd[i.standard] || []).push(i.item);
    });

    var rows = Object.keys(byStd).map(function (std) {
      var qs = byStd[std];
      var credits = qs.reduce(function (a, q) { return a + (byItem[q].credits || 1); }, 0);
      var per = {};
      NAMES.forEach(function (b) {
        var roster = groups[b], got = 0;
        roster.forEach(function (s) {
          qs.forEach(function (q) {
            var meta = byItem[q], v = s.resp[q];
            if (v === null) return;
            if (meta.type === "Multiple Choice") {
              if (meta.key && v.toUpperCase() === meta.key.toUpperCase()) got += meta.credits;
            } else {
              var n = parseFloat(v);
              if (!isNaN(n)) got += n;
            }
          });
        });
        per[b] = roster.length ? pct(got / (credits * roster.length)) : null;
      });

      var T = GATING_THRESHOLD;
      var bucket;
      if (NAMES.every(function (b) { return per[b] >= T; })) bucket = "solid";
      else if (NAMES.every(function (b) { return per[b] < T; })) bucket = "weak-for-all";
      else if (per.L2 >= T && per.L1 < T) bucket = "gates-L1-L2";
      else if (per.L3 >= T && per.L2 < T) bucket = "gates-L2-L3";
      else if (per.L4 >= T && per.L3 < T) bucket = "gates-L3-L4";
      else bucket = "mixed";
      return { standard: std, credits: credits, items: qs, byBand: per, bucket: bucket };
    });

    var ORDER = ["gates-L2-L3", "gates-L1-L2", "gates-L3-L4", "weak-for-all", "mixed", "solid"];
    rows.sort(function (a, b) {
      var d = ORDER.indexOf(a.bucket) - ORDER.indexOf(b.bucket);
      return d || b.credits - a.credits;
    });
    return { usable: true, threshold: GATING_THRESHOLD, minBand: MIN_BAND, sizes: sizes,
             students: withPl.length, rows: rows };
  }

  // Where a standard is taught, and when.
  //
  // THE JUDGED PLACEMENT FIRST. This used to read the publisher's
  // standard-to-lesson table and nothing else, which
  // provenance/alignment_baseline_measurement.md measures at 96.4% for the unit
  // and 77.8% for the lesson. That was the only source available when this was
  // written. 385 of 396 items now carry a placement judged by reading the
  // lessons, so the table is the fallback and the judgement is the answer.
  //
  // It matters more here than on the main site, because three of this report's
  // claims hang off it: which unit to focus on, when that unit is taught, and
  // when to run a checkpoint. Those were all being answered by a table the rest
  // of the project exists to improve on.
  //
  // byStandard is keyed by UNIT and stays that way, because every consumer of it
  // schedules against the pacing calendar and pacing is per unit -- startWeek and
  // the mid-unit assessment flag exist nowhere else, and there is no per-lesson
  // week published anywhere. The judged LESSONS now ride INSIDE each unit record
  // rather than replacing it: MS343Teaching's per-student plans have to name a
  // lesson a teacher can reteach on a Tuesday and need the week attached to it,
  // so handing back two structures to re-join would only move the join outwards.
  // byLesson still carries the class-performance answer for the focus report.
  function placement(items, data, grade) {
    var cur = ((data.curriculum || {}).grades || {})[String(grade)] || {};
    var s2l = cur.standardToLessons || {};
    // Pacing is already folded into each published unit by build/payload.py --
    // startWeek, the day range and the mid-unit assessment flag all live there.
    // Reading it from the unit rather than republishing a pacing block keeps one
    // copy of the 35-week table on the site.
    var units = cur.units || {};
    var out = {}, unplaced = [], priorGrade = [], judged = {}, derivedStds = {};
    var unjudged = {};

    // Resolve a lesson's title from the curriculum index, the same way
    // unitRecord resolves a unit's, so the site keeps one copy of the titles.
    // The fallback is the title the ALIGNMENT recorded: a judged lesson the
    // index does not hold would otherwise publish as a bare number, and
    // "Lesson 12" with nothing to look up is not a thing anyone can go and read.
    //
    // The key is lessonTitle and NOT title, deliberately. assertNoIdentity's
    // SKIP list exempts lessonTitle and unitTitle from the SURNAME, FORENAME
    // sweep because the publisher's own prose trips it -- "Triangle ABC is
    // similar to triangles DEF, GHI, and JKL" is a real curriculum sentence, and
    // CLAUDE.md's rule is to change the content rather than the scan. A field
    // called title inside this record would be swept instead of skipped, and
    // would throw on a geometry lesson the first time one came through.
    function lessonRecord(u, n, fallbackTitle, itemNumbers) {
      var ls = ((units[u] || {}).lessons || {})[String(n)] || {};
      return { lesson: Number(n),
               lessonTitle: ls.title || fallbackTitle || null,
               items: itemNumbers };
    }

    function unitRecord(u, judgedInUnit) {
      var p = units[u] || {};
      var jl = judgedInUnit || { lessons: {}, noLesson: 0 };
      var nums = Object.keys(jl.lessons).sort(function (a, b) { return a - b; });
      return { unit: Number(u), title: p.title || null, startWeek: p.startWeek || null,
               days: p.days || null, midUnitAssessment: !!p.midUnitAssessment,
               // Empty for a unit that came from the table rather than a
               // judgement, so a consumer can tell "no lesson was judged" from
               // "no lesson was asked for". The table is 77.8% right on the
               // lesson against 96.4% on the unit, so its lesson codes must not
               // arrive here dressed as judgements.
               lessons: nums.map(function (n) {
                 return lessonRecord(u, n, jl.lessons[n].title, jl.lessons[n].items);
               }),
               // An item judged into this unit but not to a lesson within it.
               // Zero today, because the 9 candidates-only alignments are all
               // drafted and build/payload.py drops a drafted entry's unit along
               // with its lesson. Carried anyway: it is what makes the "every
               // judged item is accounted for" invariant checkable, and it is
               // the shape the report needs the day a unit-only placement is
               // reviewed and published.
               itemsWithoutLesson: jl.noLesson };
    }

    // A placement counts for THIS grade only when it was judged into this
    // grade's curriculum. A grade 8 item on a grade 7 standard is judged into
    // grade 7 Unit 8, and filing it under grade 8's Unit 8 -- a different unit
    // about a different topic -- is exactly the kind of error the edition swap
    // already makes easy.
    function judgedUnitFor(i) {
      if (i.unit === null || i.unit === undefined) return null;
      var m = /Grade\s+(\d)/.exec(i.course || "");
      return (m && m[1] === String(grade)) ? String(i.unit) : null;
    }

    items.forEach(function (i) {
      var ju = judgedUnitFor(i);
      if (ju === null) {
        // An item with no judged placement at all. Recorded per standard rather
        // than discarded: a standard whose OTHER items are judged answers from
        // those, and this one then becomes invisible -- a plan would list two
        // lessons for a three-item standard and read as if it had covered it.
        (unjudged[i.standard] = unjudged[i.standard] || []).push(i.item);
        return;
      }
      var perStd = judged[i.standard] = judged[i.standard] || {};
      var perUnit = perStd[ju] = perStd[ju] || { lessons: {}, noLesson: 0 };
      if (i.lesson === null || i.lesson === undefined) { perUnit.noLesson++; return; }
      var key = String(i.lesson);
      var l = perUnit.lessons[key] = perUnit.lessons[key] ||
        { title: i.lessonTitle || null, items: [] };
      if (l.items.indexOf(i.item) < 0) l.items.push(i.item);
    });

    items.forEach(function (i) {
      // Judged wins. Several items on one standard can be judged into different
      // units -- alignment is per item, not per standard -- so the answer for a
      // standard is the set its own items actually landed in.
      if (judged[i.standard]) {
        out[i.standard] = Object.keys(judged[i.standard])
          .sort(function (a, b) { return a - b; })
          .map(function (u) { return unitRecord(u, judged[i.standard][u]); });
        return;
      }
      var codes = s2l[i.standard] || [];
      if (!codes.length) {
        // A prior-grade post-test standard is not IN this grade's curriculum and
        // never will be, so it is not a gap in the index -- it is the test
        // assessing something taught a year earlier. Kept separate, because
        // reporting NY-5.OA.3 next to NY-6.G.5 as the same kind of problem
        // would send someone looking for a grade 6 lesson that cannot exist.
        var list = (i.postTest || i.standard.indexOf("NY-" + grade + ".") !== 0)
          ? priorGrade : unplaced;
        if (list.indexOf(i.standard) < 0) list.push(i.standard);
        return;
      }
      var seenUnits = {};
      codes.forEach(function (c) {
        var parts = String(c).split(".");
        if (parts.length >= 2) seenUnits[parts[1]] = 1;
      });
      derivedStds[i.standard] = 1;
      out[i.standard] = Object.keys(seenUnits).sort(function (a, b) { return a - b; })
        .map(function (u) { return unitRecord(u, null); });
    });
    // Only for a standard that DOES answer from judged placements. A standard
    // with no judged item at all is already reported, and better, by priorGrade
    // (taught a year earlier, so there is no lesson in this grade to find) or by
    // unplaced (a genuine hole in the index). Listing it here as well would tell
    // a teacher to go looking for the grade 6 lesson behind NY-5.OA.3.
    Object.keys(unjudged).forEach(function (st) {
      if (!judged[st]) delete unjudged[st];
    });

    return { byStandard: out, unplaced: unplaced, priorGrade: priorGrade,
             // Item numbers on a standard that names lessons but does not name
             // one for these, so a consumer can say what it is NOT naming. A
             // plan listing two lessons for a three-item standard otherwise
             // reads as though it had covered the standard.
             unjudgedItems: unjudged,
             judgedStandards: Object.keys(judged).length,
             derivedStandards: Object.keys(derivedStds).length,
             // The TABLE's accuracy against NYCPS's independent citations. This
             // is the FALLBACK's quality, measured in
             // provenance/alignment_baseline_measurement.md.
             unitAccuracy: 0.964, lessonAccuracy: 0.778,
             // The JUDGED placement's own agreement, which is what a consumer of
             // `lessons` is actually leaning on. Grade 7's 129 evidenced items
             // were re-derived blind by a reader who could not see the first
             // pass: 85 chose the same lesson, 112 the same unit.
             // provenance/alignment_second_pass_g7.md.
             //
             // ONE measurement, not a per-grade figure. Grade 6 was never
             // second-passed, and grade 8's 55.6% is not comparable -- a blind
             // re-test chose the second reading 18 times out of 18, so that
             // number measured one bad reading rather than irreducible
             // judgement. Quoting the honest ceiling everywhere beats quoting a
             // flattering per-grade number three different ways.
             lessonAgreement: 0.659, unitAgreement: 0.868 };
  }

  /* ---------------------------------------------------------- checkpoints */

  // Real released questions to check the gating standards with, placed on the
  // pacing calendar.
  //
  // The rest of this report says what happened, what to focus on and when it is
  // taught. It stopped short of what to ASK, which left a teacher with a date and
  // no instrument. Every item here is a real released NYSED question with its own
  // published answer; nothing is generated.
  //
  // AlgebraTeaching's Snorkl calendar is the model, including the placement rule:
  // check a standard just after it is first taught, not at the end of the year.
  var CHECKPOINT_CAP = 6;

  function checkpoints(items, data, gating, place, grade) {
    if (!gating.usable) return { usable: false, why: gating.why };

    var lost = {};
    (place.focusRows || []).forEach(function (f) { lost[f.standard] = f.creditsLost; });

    var gates = gating.rows.filter(function (r) { return r.bucket === "gates-L2-L3"; });
    if (!gates.length) return { usable: false, why: "no standard gated proficiency cleanly" };

    // A standard taught in several units is checked in the EARLIEST of them. A
    // checkpoint after the third teaching is not a checkpoint, it is a post-mortem.
    var byUnit = {}, unschedulable = [];
    gates.forEach(function (r) {
      var us = (place.byStandard[r.standard] || []).slice()
        .sort(function (a, b) { return (a.startWeek || 99) - (b.startWeek || 99); });
      if (!us.length) { unschedulable.push(r.standard); return; }
      var u = us[0];
      var g = byUnit[u.unit] = byUnit[u.unit] ||
        { unit: u.unit, title: u.title, startWeek: u.startWeek,
          midUnitAssessment: u.midUnitAssessment, standards: [] };
      g.standards.push(r);
    });

    // The class's own result per standard, to choose between items on it.
    var classOn = {};
    items.forEach(function (i) {
      var c = classOn[i.standard] = classOn[i.standard] || { cr: [], all: [] };
      c.all.push(i);
      if (i.type === "cr") c.cr.push(i);
    });

    // Everything released on this grade, transcribed, with an answer to mark
    // against. An item with no answer cannot be a checkpoint.
    var pool = data.items.filter(function (it) {
      if (it.grade !== grade || !it.transcribed) return false;
      return it.type === "Multiple Choice" ? !!it.key : !!((it.cr || {}).answer);
    });

    var used = {}, thinSupply = [];

    function pick(std, want) {
      var avail = pool.filter(function (it) { return it.standard === std && !used[it.id]; });
      // Constructed response first where the class lost most ground on this
      // standard's CR items -- that is where a wrong answer is most legible.
      var weakCr = (classOn[std] && classOn[std].cr.length)
        ? classOn[std].cr.some(function (i) { return i.gap !== null && i.gap < -0.05; })
        : false;
      avail.sort(function (a, b) {
        if (weakCr && (a.type === "Multiple Choice") !== (b.type === "Multiple Choice")) {
          return a.type === "Multiple Choice" ? 1 : -1;
        }
        // Then the item the state found hardest: a checkpoint that everyone
        // passes has told the teacher nothing.
        var pa = a.pValue === null ? 1 : a.pValue, pb = b.pValue === null ? 1 : b.pValue;
        if (pa !== pb) return pa - pb;
        return b.year - a.year;
      });
      var out = avail.slice(0, want);
      out.forEach(function (it) { used[it.id] = 1; });
      if (out.length < want) thinSupply.push({ standard: std, wanted: want, got: out.length });
      return out.map(function (it) {
        return { id: it.id, year: it.year, item: it.item, type: it.type,
                 credits: it.credits, standard: it.standard, key: it.key || null,
                 stem: it.stem || null, stemAfter: it.stemAfter || null,
                 stemPlain: it.stemPlain || null, instructions: it.instructions || null,
                 choiceList: it.choiceList || null, choicesInImage: !!it.choicesInImage,
                 figures: it.figures || [], answer: (it.cr || {}).answer || null,
                 pValue: it.pValue, sourceUrl: it.sourceUrl || null };
      });
    }

    // One item per gating standard; a second for the standards costing the most
    // credits. Unbounded, this gave one unit ten items -- that is an exam, not a
    // checkpoint, and an exam does not get used as one.
    var ranked = gates.slice().sort(function (a, b) {
      return (lost[b.standard] || 0) - (lost[a.standard] || 0);
    });
    var doubled = {};
    ranked.slice(0, Math.max(1, Math.ceil(ranked.length / 3))).forEach(function (r) {
      doubled[r.standard] = 1;
    });

    var units = Object.keys(byUnit).map(function (k) { return byUnit[k]; })
      .sort(function (a, b) { return (a.startWeek || 99) - (b.startWeek || 99); });

    units.forEach(function (u) {
      var picked = [];
      u.standards.sort(function (a, b) {
        return (lost[b.standard] || 0) - (lost[a.standard] || 0);
      }).forEach(function (r) {
        if (picked.length >= CHECKPOINT_CAP) return;
        var want = doubled[r.standard] ? 2 : 1;
        want = Math.min(want, CHECKPOINT_CAP - picked.length);
        picked = picked.concat(pick(r.standard, want));
      });
      u.items = picked;
      u.gatingCredits = u.standards.reduce(function (a, r) { return a + r.credits; }, 0);
      // Split across the mid-unit assessment and the unit assessment where there
      // is one. Where there is not, the unit gives a single reading at the end --
      // which for a unit carrying real gating weight close to the test is worth
      // saying out loud.
      if (u.midUnitAssessment && picked.length > 1) {
        var half = Math.ceil(picked.length / 2);
        u.sets = [{ when: "mid-unit assessment", items: picked.slice(0, half) },
                  { when: "unit assessment", items: picked.slice(half) }];
      } else {
        u.sets = [{ when: "unit assessment", items: picked }];
      }
    });

    var lateNoMid = units.filter(function (u) {
      return !u.midUnitAssessment && u.gatingCredits >= 4 && u.startWeek >= 21;
    });

    return { usable: true, cap: CHECKPOINT_CAP, units: units,
             totalItems: units.reduce(function (a, u) { return a + u.items.length; }, 0),
             thinSupply: thinSupply, unschedulable: unschedulable,
             lateWithoutMidUnit: lateNoMid.map(function (u) {
               return { unit: u.unit, title: u.title, startWeek: u.startWeek,
                        gatingCredits: u.gatingCredits };
             }) };
  }

  /* -------------------------------------------------------------- the guard */

  // Walk the finished report and refuse to hand back anything identity-shaped.
  // Everything above is written so this cannot fire; it exists because the day
  // it does fire is the day it matters, and because a future edit that widens
  // what gets read should fail loudly here rather than quietly ship.
  //
  // The patterns are preflight.py's, deliberately: one definition of what an
  // identifier looks like, checked both in the browser and at the deploy gate.
  function assertNoIdentity(report) {
    var OSIS = /\b\d{9}\b/;
    var NAME = /\b[A-Z]{2,}, ?[A-Z]{2,}\b/;
    var seen = [];

    // A proficiency level is not name-shaped and not OSIS-shaped, so the two
    // patterns above would never catch one. The PL column IS student data: it
    // is read to recover the curve and to band students, both aggregate, and an
    // individual PL must not survive into the report. Mechanical list rather
    // than a convention, because the next person to add a field will not read
    // this comment.
    var BANNED_KEYS = ["pl", "plByStudent", "rawByStudent", "perStudent",
                       "students_", "roster", "osis", "studentName"];
    (function walkKeys(node, path) {
      if (!node || typeof node !== "object") return;
      if (seen.indexOf(node) >= 0) return;
      seen.push(node);
      if (Array.isArray(node)) {
        node.forEach(function (v, i) { walkKeys(v, path + "[" + i + "]"); });
        return;
      }
      Object.keys(node).forEach(function (k) {
        if (BANNED_KEYS.indexOf(k) >= 0) {
          throw new Error("assertNoIdentity: student-level key '" + k + "' at " + path);
        }
        walkKeys(node[k], path + "." + k);
      });
    })(report, "");
    seen = [];

    // Item stems and answer choices come from the published payload, which is
    // NYSED's own text and contains no student data by construction. Walking
    // them would only invite a false positive on a word problem's characters.
    var SKIP = { stemPlain: 1, topWrongText: 1, choiceList: 1, label: 1,
                 lessonTitle: 1, unitTitle: 1, sourceUrl: 1, domainLabel: 1 };

    function walk(node, path) {
      if (node === null || node === undefined) return;
      if (typeof node === "string") {
        if (OSIS.test(node)) throw new Error("assertNoIdentity: OSIS-shaped value at " + path);
        if (NAME.test(node)) throw new Error("assertNoIdentity: name-shaped value at " + path);
        return;
      }
      if (typeof node !== "object") return;
      if (seen.indexOf(node) >= 0) return;
      seen.push(node);
      if (Array.isArray(node)) {
        node.forEach(function (v, i) { walk(v, path + "[" + i + "]"); });
        return;
      }
      Object.keys(node).forEach(function (k) {
        if (SKIP[k]) return;
        // A section code is a code. Anything longer is not one, whatever the
        // uniqueness guard thought.
        if (path === ".sections" && k.length > 8) {
          throw new Error("assertNoIdentity: over-long section code at .sections");
        }
        walk(node[k], path + "." + k);
      });
    }

    walk(report, "");
    return report;
  }

  /* -------------------------------------------------------------------- run */

  // The whole pipeline, so the page and the test harness cannot drift apart.
  function run(grid, data) {
    var parsed = parseGrid(grid);
    if (parsed.error) return { error: parsed.error };
    var id = identifyTest(parsed, data);
    if (!id.testId) return { error: id.error, identify: id };
    var report = analyse(parsed, id.testId, data);
    report.identify = id;
    return assertNoIdentity(report);
  }

  var api = { parseGrid: parseGrid, findHeaderRow: findHeaderRow,
              findClassColumn: findClassColumn, findPlColumn: findPlColumn,
              identifyTest: identifyTest, plCurve: plCurve,
              creditsToReach: creditsToReach, focus: focus,
              bandGating: bandGating, placement: placement,
              checkpoints: checkpoints,
              analyse: analyse, assertNoIdentity: assertNoIdentity, run: run };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.ClassEngine = api;
})(this);
