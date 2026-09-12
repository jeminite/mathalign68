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
      students.push({ section: sec, resp: resp });
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
             headerRow: head.row + 1, warnings: warn };
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
      constructed: items.filter(function (i) { return i.type === "cr"; })
                        .sort(function (a, b) { return b.zeroCredit - a.zeroCredit; }),
      omissions: items.filter(function (i) { return i.omitted > 0; })
                      .sort(function (a, b) { return b.omitted - a.omitted; }),
      warnings: parsed.warnings || []
    };
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
              findClassColumn: findClassColumn, identifyTest: identifyTest,
              analyse: analyse, assertNoIdentity: assertNoIdentity, run: run };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.ClassEngine = api;
})(this);
