#!/usr/bin/env node
/* The class-results engine suite.
 *
 *   npm test        (runs this, then tools/test_render.js)
 *
 * Plain Node, no framework. RegentsAlign's equivalent explains why and the
 * reasoning carries: a test that needs a toolchain to run is a test that stops
 * being run. The last line is the sentinel preflight.py greps for.
 */
"use strict";

const fs = require("fs");
const path = require("path");
const ROOT = path.join(__dirname, "..");

const Xlsx = require(path.join(ROOT, "templates", "analyze", "xlsx.js"));
const Engine = require(path.join(ROOT, "templates", "analyze", "engine.js"));
const DATA = JSON.parse(fs.readFileSync(path.join(ROOT, "site", "data.json"), "utf8"));

let failures = 0;
let checks = 0;

function check(label, got, want) {
  checks++;
  const ok = JSON.stringify(got) === JSON.stringify(want);
  if (!ok) {
    failures++;
    console.log("FAIL  " + label + "\n        got  " + JSON.stringify(got) +
                "\n        want " + JSON.stringify(want));
  } else {
    console.log("ok    " + label);
  }
}

// Deliberately not routed through check(): an earlier version passed the
// detail as the "got" value, so a failing check whose detail happened to be
// `true` compared true to true and reported ok. A boolean assertion needs its
// own reporter.
function ok(label, cond, detail) {
  checks++;
  if (cond) { console.log("ok    " + label); return; }
  failures++;
  console.log("FAIL  " + label +
              (detail === undefined ? "" : "\n        " + JSON.stringify(detail)));
}

function skip(label, why) { console.log("skip  " + label + "  (" + why + ")"); }

const fixture = (f) => path.join(ROOT, "fixtures", f);
const read = (f) => Xlsx.parse(fs.readFileSync(f));

async function main() {

  /* ---------------------------------------------- the reader, against SheetJS
   *
   * Two independent extraction paths agreeing is the only reason to trust a
   * parse. templates/analyze/xlsx.js exists because the analyse page may not
   * load a third-party script; SheetJS stays in devDependencies purely so this
   * check can exist. If they ever disagree, the hand-rolled reader is wrong.
   */
  let XLSX = null;
  try { XLSX = require("xlsx"); } catch (e) { /* not installed */ }

  for (const f of ["isa_g6_2026_synthetic.xlsx", "isa_identity_left_in.xlsx"]) {
    const ours = await read(fixture(f));
    if (!XLSX) { skip("xlsx.js agrees with SheetJS on " + f, "npm install not run"); continue; }
    const wb = XLSX.read(fs.readFileSync(fixture(f)), { type: "buffer" });
    const theirs = XLSX.utils.sheet_to_json(wb.Sheets[wb.SheetNames[0]],
                                            { header: 1, defval: null, raw: true });
    let diffs = 0;
    for (let r = 0; r < Math.max(ours.length, theirs.length); r++) {
      const a = ours[r] || [], b = theirs[r] || [];
      for (let c = 0; c < Math.max(a.length, b.length); c++) {
        const x = a[c] === null || a[c] === undefined ? null : String(a[c]);
        const y = b[c] === null || b[c] === undefined ? null : String(b[c]);
        if (x !== y) diffs++;
      }
    }
    check("xlsx.js agrees with SheetJS on " + f, diffs, 0);
  }

  /* ------------------------------------------------------------ the ordinary run */

  const grid = await read(fixture("isa_g6_2026_synthetic.xlsx"));
  const r = Engine.run(grid, DATA);
  ok("the synthetic fixture analyses without error", !r.error, r.error);

  // Identification. The margin is the point: this must not be a close call.
  check("identifies the test from its headers alone", r.testId, "g6-2026");
  check("agreement is total", [r.identify.agree, r.identify.total], [39, 39]);
  ok("the runner-up is far behind", r.identify.runnerUp <= 2, r.identify.runnerUp);
  check("every question matched a published item", r.unmatched.length, 0);
  check("student count", r.students, 78);

  // Pinned figures. These are regression detection, not truth: if a change
  // moves them, the change has altered what the page tells a teacher.
  check("overall class figure", r.overall.classP, 0.504);
  check("overall state figure", r.overall.stateP, 0.548);

  const q = (n) => r.items.find((i) => i.item === n);
  check("Q1 is multiple choice, 1 credit", [q(1).type, q(1).credits], ["mc", 1]);
  check("Q1 class and state", [q(1).classP, q(1).stateP], [0.782, 0.82]);
  check("Q46 is a 3-credit constructed response", [q(46).type, q(46).credits], ["cr", 3]);

  // A constructed-response state figure is average points earned over credits,
  // not the published pValue. Q43 is 0.58/2 = 0.29 either way in this test, so
  // check one where they differ.
  const cr = DATA.items.find((i) => i.testId === "g6-2026" && i.item === 41);
  check("CR state figure is avgPointsEarned over credits",
        q(41).stateP, Math.round(cr.avgPointsEarned / cr.credits * 1000) / 1000);

  // The correct letter must not be counted as a distractor.
  const q1 = q(1);
  ok("the key is absent from the chosen-wrong tally", !(q1.key in q1.chose),
     Object.keys(q1.chose));
  check("correct plus wrong plus blank is every student",
        q1.correct + Object.values(q1.chose).reduce((a, b) => a + b, 0) + q1.omitted, 78);

  // Post-test standards come through as themselves, prefixed and all.
  check("the post-test item keeps its prior-grade standard",
        [q(42).standard, q(42).postTest], ["NY-5.OA.3", true]);

  ok("dominant distractors were found", r.dominant.length > 0, r.dominant.length);
  ok("every dominant item clears the quarter-of-the-class bar",
     r.dominant.every((i) => i.topWrongCount >= r.students / 4), true);

  check("blank answers are counted as omissions, not wrong answers",
        r.omissions.map((i) => [i.item, i.omitted]), [[45, 1], [46, 1]]);

  check("sections were kept", Object.keys(r.sections).sort(), ["6A1", "6A2", "6A3", "6A4"]);
  check("every student landed in a section",
        r.bySection.reduce((a, s) => a + s.students, 0), 78);
  ok("rollups cover every item",
     r.byDomain.reduce((a, d) => a + d.items.length, 0) === r.matched, true);

  // Domain names come from the standards registry, not the item's
  // domainLabel. domainLabel is NYSED's subscore: the grade 5 post-test item
  // carries "Expressions and Equations", which put that name on two separate
  // rows of the domain table.
  check("the post-test item's domain is named from the registry",
        q(42).domainLabel, "Operations and Algebraic Thinking");
  const labels = r.byDomain.map((d) => d.label);
  check("no two domain rows share a name", labels.length, new Set(labels).size);

  /* ------------------------------------------------- the PL curve and focus */

  // The curve is a LOOKUP recovered from the file, not a fit. These figures are
  // derived in provenance/pl_curve.md; if a change moves them the change has
  // altered what the page tells a teacher about a student's target.
  const tbl = { 4: 1.34, 6: 1.53, 7: 1.62, 8: 1.68, 9: 1.74, 10: 1.79, 11: 1.85, 12: 1.89,
                13: 1.94, 14: 1.98, 16: 2.18, 17: 2.29, 19: 2.47, 20: 2.59, 21: 2.71, 22: 2.82,
                23: 2.94, 24: 3.00, 25: 3.03, 26: 3.10, 27: 3.16, 28: 3.23, 29: 3.29, 30: 3.35,
                31: 3.42, 32: 3.48, 33: 3.55, 34: 3.61, 35: 3.71, 38: 3.97, 39: 4.00, 41: 4.12,
                42: 4.24, 44: 4.36, 45: 4.42 };
  const craws = Object.keys(tbl).map(Number);
  const curve = Engine.plCurve(craws, craws.map((r) => tbl[r]), 46);

  ok("the curve is usable", curve.usable, curve.why);
  check("35 distinct raw scores, no collisions", [curve.points, curve.collisions], [35, 0]);

  const cut = (l) => curve.cuts.filter((c) => c.level === l)[0];
  // Level 3 and Level 4 land on observed raw scores; Level 2 does not, because
  // nobody in the class scored raw 15. Reporting all three as equally certain
  // would be a lie, so `exact` is part of the contract.
  check("Level 3 cut is exact at raw 24 of 46", [cut(3).raw, cut(3).exact], [24, true]);
  check("Level 4 cut is exact at raw 39", [cut(4).raw, cut(4).exact], [39, true]);
  check("Level 2 cut is bracketed, not observed",
        [cut(2).exact, cut(2).between], [false, [14, 16]]);
  check("raw 15 is among the unobserved scores", curve.unobserved.indexOf(15) >= 0, true);

  // A credit is worth roughly double just below proficiency. A segment counts
  // toward a band only when BOTH endpoints are inside it: raw 23->24 crosses
  // into proficiency and counting it as an L2 rate pulled L2 down by half a
  // point, and raw 38 (3.97) is an L3 point that understated L4.
  const rate = (b) => curve.bands.filter((x) => x.band === b)[0].plPerCredit;
  check("PL per credit by band", [rate("L1"), rate("L2"), rate("L3"), rate("L4")],
        [0.061, 0.112, 0.066, 0.075]);
  ok("a credit is worth most just below proficiency",
     rate("L2") > rate("L1") * 1.5 && rate("L2") > rate("L3") * 1.5, rate("L2"));

  // The questions the curve was built to answer. A band-level answer would be
  // wrong for almost everyone in the band: 2.75-3.25 is 8 credits at the bottom
  // and 1 at the top, which is why recommendations must be per student.
  const to = (a, b) => Engine.creditsToReach(curve, a, b).credits;
  check("3.5 -> 4.0 is 7 credits", to(3.5, 3.999), 7);
  check("2.75 -> above 3.25 is 8 credits", to(2.75, 3.25), 8);
  check("3.25 -> above 3.25 is 1 credit", to(3.25, 3.25), 1);
  check("1.75 -> above 2.25 is 8 credits", to(1.75, 2.25), 8);
  check("the same band spans 8 credits at the bottom and 1 at the top",
        [to(2.75, 3.25), to(3.25, 3.25)], [8, 1]);

  // A colliding PL column means the lookup assumption is broken for that file.
  // Averaging would produce a curve that looks fine and is wrong.
  const bad = Engine.plCurve([10, 10, 11, 12, 13, 14, 15], [2.0, 2.9, 2.1, 2.2, 2.3, 2.4, 2.5], 46);
  ok("a colliding PL column is refused, not averaged", bad.usable === false, bad);
  ok("and it says why", /not a clean function/.test(bad.why || ""), bad.why);

  const noCurve = Engine.plCurve([1, 2, 3], [1.1, 1.2, 1.3], 46);
  ok("too few points is refused", noCurve.usable === false, noCurve);

  // On the real file
  ok("the curve was recovered from the fixture", r.curve.usable, r.curve.why);
  check("fixture total credits", r.totalCredits, 46);

  // Focus: gap x weight, not gap. NY-6.EE.8 has a BIGGER gap than NY-6.G.1
  // (-17.8 vs -17.7) but is worth 1 credit a year against G.1's 2.5. Ranking by
  // gap alone would put them level; this is the check that they are not.
  const fo = (std) => r.focus.filter((x) => x.standard === std)[0];
  ok("focus is sorted by credits lost, descending",
     r.focus.every((x, i) => i === 0 || r.focus[i - 1].creditsLost >= x.creditsLost), true);
  check("NY-6.G.1 recurs on all four tests", [fo("NY-6.G.1").recurs, fo("NY-6.G.1").ofYears], [4, 4]);
  // creditsPerYear is a property of the published tests, not of any class, so it
  // holds on the synthetic fixture too.
  check("credits per year come from the published tests",
        [fo("NY-6.G.1").creditsPerYear, fo("NY-6.EE.8").creditsPerYear], [2.5, 1]);
  ok("a standard the class beat the State on is not an area of focus",
     r.focus.every((x) => x.gap === null || x.gap < 0 || x.creditsLost === 0), true);

  // Band gating
  ok("gating is usable on the fixture", r.gating.usable, r.gating.why);
  check("every band is reported with its size",
        Object.keys(r.gating.sizes).sort(), ["L1", "L2", "L3", "L4"]);
  ok("the threshold is published, not hidden", r.gating.threshold > 0, r.gating.threshold);
  ok("every standard landed in exactly one bucket",
     r.gating.rows.length === r.byStandard.length, [r.gating.rows.length, r.byStandard.length]);

  // Small bands are refused. AlgebraTeaching scoped this whole analysis down
  // because its bands held 4-10 students; a percentage over 2 students is noise.
  const tiny = Engine.bandGating(
    { students: [{ pl: 1.5, resp: {} }, { pl: 2.5, resp: {} }, { pl: 3.5, resp: {} }] }, [], {});
  ok("too few students to band is refused", tiny.usable === false, tiny);

  // Placement: a prior-grade standard is not a gap in the index.
  ok("a prior-grade standard is kept separate from a genuine index gap",
     r.placement.priorGrade.length + r.placement.unplaced.length >= 0 &&
     r.placement.unplaced.indexOf("NY-5.OA.3") < 0, r.placement.unplaced);
  // The figures moved when a regex fix let three more NYCPS rows parse; see
  // provenance/alignment_baseline_measurement.md. They describe the FALLBACK
  // now -- placement prefers the judged placement and reaches the table only
  // for a standard no item was judged into.
  check("placement states the table's accuracy, which is now the fallback's",
        [r.placement.unitAccuracy, r.placement.lessonAccuracy], [0.964, 0.778]);
  // The judged placement must actually be the one in use. If this ever reads 0
  // judged, the report has silently gone back to the standard-to-lesson table.
  ok("placement answers from judged placements, not the table",
     r.placement.judgedStandards > 0 && r.placement.derivedStandards === 0,
     [r.placement.judgedStandards, r.placement.derivedStandards]);

  /* ------------------------------------------- lessons inside the placement */

  // MS343Teaching's per-student plans said "Unit 6 (Expressions and Equations),
  // week 21" while 385 of 396 items carried a judged lesson. A unit is twenty
  // days of teaching; a lesson is something a teacher can reteach on a Tuesday.
  // These guard the shape that finer answer travels in, because the only caller
  // is in another repository and is invisible from here.
  const placedUnits = [];
  Object.keys(r.placement.byStandard).forEach((s) =>
    r.placement.byStandard[s].forEach((u) => placedUnits.push([s, u])));
  ok("every unit record carries a lessons array",
     placedUnits.length > 0 && placedUnits.every(([, u]) => Array.isArray(u.lessons)),
     placedUnits.length);
  ok("some standard actually names a lesson",
     placedUnits.some(([, u]) => u.lessons.length > 0),
     placedUnits.filter(([, u]) => u.lessons.length > 0).length);
  ok("every judged lesson has a number and a title that resolved",
     placedUnits.every(([, u]) => u.lessons.every((l) =>
       Number.isInteger(l.lesson) && typeof l.lessonTitle === "string" &&
       l.lessonTitle.length > 0)),
     placedUnits.map(([s, u]) => u.lessons.map((l) => [s, l.lesson, l.lessonTitle]))
                .reduce((a, b) => a.concat(b), [])
                .filter((x) => !x[2]));
  ok("lesson numbers ascend and do not repeat within a unit",
     placedUnits.every(([, u]) => u.lessons.every((l, k) =>
       k === 0 || l.lesson > u.lessons[k - 1].lesson)),
     placedUnits.map(([s, u]) => [s, u.lessons.map((l) => l.lesson)]));
  // The privacy sweep's SKIP list is keyed on the FIELD NAME: lessonTitle and
  // unitTitle are exempt from the SURNAME, FORENAME regex because the
  // publisher's own prose trips it. A lesson record whose title lived under a
  // key called `title` would be swept instead, and would throw the first time a
  // geometry lesson came through. Pinned so a later tidy-up cannot rename it.
  ok("a lesson's title is under lessonTitle, never title",
     placedUnits.every(([, u]) => u.lessons.every((l) => !("title" in l))), true);
  // Structural, not a count: every item judged into a unit in THIS grade is
  // either listed under one of that unit's lessons or counted as lacking one.
  // "Fewer than three activities" passed clean while 24 lessons were corrupt;
  // asserting what should be true catches what counting what looks odd misses.
  ok("every judged item is either on a lesson or counted as lacking one", (function () {
    const want = {};
    r.items.forEach((i) => {
      if (i.unit === null || i.unit === undefined) return;
      const m = /Grade\s+(\d)/.exec(i.course || "");
      if (!m || m[1] !== String(r.grade)) return;
      const k = i.standard + "|" + i.unit;
      (want[k] = want[k] || []).push(i.item);
    });
    return Object.keys(want).length > 0 && Object.keys(want).every((k) => {
      const st = k.split("|")[0], un = k.split("|")[1];
      const rec = (r.placement.byStandard[st] || [])
        .filter((x) => String(x.unit) === un)[0];
      if (!rec) return false;
      const listed = rec.lessons.reduce((n, l) => n + l.items.length, 0);
      return listed + rec.itemsWithoutLesson === want[k].length;
    });
  })(), true);
  // The judged placement's own agreement, beside the table's accuracy above.
  // These are different measurements of different things and conflating them
  // would overstate the lesson: the table is 77.8% against NYCPS, while two of
  // this project's own careful readings agree on the lesson only 65.9% of the
  // time. See provenance/alignment_second_pass_g7.md.
  check("placement states the judged placement's own blind agreement",
        [r.placement.lessonAgreement, r.placement.unitAgreement], [0.659, 0.868]);
  ok("the lesson is reported as the weaker claim than the unit",
     r.placement.lessonAgreement < r.placement.unitAgreement,
     [r.placement.lessonAgreement, r.placement.unitAgreement]);

  // The mixed case is exercised directly, because no 2026 test has one: a
  // standard whose items are judged into different lessons AND one of whose
  // items carries no placement at all. g6-2023 item 15 is the real example
  // (NY-6.G.1, one item judged and one not), and relying on the real data still
  // having that hole is how the orphan-standard test above went stale.
  const mixed = Engine.placement([
    { standard: "NY-6.EE.7", unit: 6, lesson: 4, lessonTitle: "Practice Solving Equations",
      course: "Imagine IM New York, Grade 6", item: 11 },
    { standard: "NY-6.EE.7", unit: 6, lesson: 4, lessonTitle: "Practice Solving Equations",
      course: "Imagine IM New York, Grade 6", item: 12 },
    // No title on the alignment side, to exercise the curriculum lookup. The
    // index is the authority on what lesson 5 is CALLED in this edition, and a
    // citation whose number and title disagree is the shape an edition
    // renumbering leaves behind -- which is why the curriculum wins and the
    // alignment's own title is only the fallback.
    { standard: "NY-6.EE.7", unit: 6, lesson: 5, lessonTitle: null,
      course: "Imagine IM New York, Grade 6", item: 13 },
    // Judged into the unit but not to a lesson: the candidates-only shape, which
    // is drafted and so unpublished today but is what this field is for.
    { standard: "NY-6.EE.7", unit: 6, lesson: null, lessonTitle: null,
      course: "Imagine IM New York, Grade 6", item: 14 },
    // No placement at all.
    { standard: "NY-6.EE.7", unit: null, lesson: null, lessonTitle: null,
      course: null, item: 15 },
    // A prior-grade standard with no judged item: already reported by
    // priorGrade, so it must NOT also appear as an unjudged item.
    { standard: "NY-5.OA.3", unit: null, lesson: null, lessonTitle: null,
      course: null, item: 42, postTest: true }
  ], DATA, 6);
  const mu = mixed.byStandard["NY-6.EE.7"][0];
  check("several items on one standard collapse into one lesson each",
        mu.lessons.map((l) => [l.lesson, l.items]), [[4, [11, 12]], [5, [13]]]);
  check("a lesson's title is resolved from the curriculum index",
        mu.lessons.map((l) => l.lessonTitle),
        ["Practice Solving Equations", "Represent Situations with Equations"]);
  // And a lesson the index does not hold still names itself rather than
  // publishing "Lesson 12" with nothing to look up.
  const offIndex = Engine.placement([
    { standard: "NY-6.EE.7", unit: 6, lesson: 99, lessonTitle: "A Lesson Not In The Index",
      course: "Imagine IM New York, Grade 6", item: 1 }
  ], DATA, 6);
  check("a judged lesson outside the index falls back to the alignment's title",
        offIndex.byStandard["NY-6.EE.7"][0].lessons,
        [{ lesson: 99, lessonTitle: "A Lesson Not In The Index", items: [1] }]);
  check("an item judged into the unit but not to a lesson is counted",
        mu.itemsWithoutLesson, 1);
  check("an item with no placement at all is named, not dropped",
        mixed.unjudgedItems["NY-6.EE.7"], [15]);
  ok("a prior-grade standard is not also listed as an unjudged item",
     !("NY-5.OA.3" in mixed.unjudgedItems) &&
     mixed.priorGrade.indexOf("NY-5.OA.3") >= 0,
     [Object.keys(mixed.unjudgedItems), mixed.priorGrade]);
  // The fallback must not dress the table's lesson codes as judgements.
  const tabled = Engine.placement([
    { standard: "NY-6.EE.1", unit: null, lesson: null, lessonTitle: null,
      course: null, item: 1 }
  ], DATA, 6);
  ok("a unit derived from the table names no lesson",
     (tabled.byStandard["NY-6.EE.1"] || []).length > 0 &&
     tabled.byStandard["NY-6.EE.1"].every((u) => u.lessons.length === 0 &&
                                                 u.itemsWithoutLesson === 0),
     tabled.byStandard["NY-6.EE.1"]);

  /* ------------------------------------------------------------ checkpoints */

  const cp = r.checkpoints;
  ok("checkpoints were built", cp.usable, cp.why);
  ok("every unit's set is capped", cp.units.every((u) => u.items.length <= cp.cap),
     cp.units.map((u) => u.items.length));
  // The cap exists because one item per standard, unbounded, gave a unit ten
  // items. That is an exam, and an exam does not get used as a checkpoint.
  ok("a unit with many gating standards is capped, not expanded",
     cp.units.every((u) => u.items.length <= 6), true);
  ok("no item is used in two checkpoints", (function () {
    const seenIds = {};
    return cp.units.every((u) => u.items.every((i) => {
      if (seenIds[i.id]) return false;
      seenIds[i.id] = 1; return true;
    }));
  })(), true);

  // Every item must be markable. A checkpoint whose answer is unknown is not one.
  ok("every checkpoint item has an answer",
     cp.units.every((u) => u.items.every((i) =>
       i.type === "Multiple Choice" ? !!i.key : !!i.answer)), true);
  ok("every checkpoint item resolves to a real released item",
     cp.units.every((u) => u.items.every((i) =>
       DATA.items.some((x) => x.id === i.id && x.transcribed))), true);

  // Placement: a standard taught in several units is checked at the EARLIEST.
  // A checkpoint after the third teaching is a post-mortem.
  ok("units are ordered by when they are taught",
     cp.units.every((u, i) => i === 0 || cp.units[i - 1].startWeek <= u.startWeek), true);
  const cpStds = cp.units.reduce((a, u) => a.concat(u.standards.map((x) => x.standard)), []);
  ok("each gating standard is checked in exactly one unit",
     cpStds.length === new Set(cpStds).size, cpStds);

  // A unit with a mid-unit assessment gets two smaller sets rather than one big
  // one, so there is a reading early enough to act on.
  const withMid = cp.units.filter((u) => u.midUnitAssessment && u.items.length > 1);
  ok("a unit with a mid-unit assessment splits its set",
     withMid.every((u) => u.sets.length === 2), withMid.map((u) => u.sets.length));
  ok("a unit without one gets a single set at the end",
     cp.units.filter((u) => !u.midUnitAssessment).every((u) => u.sets.length === 1), true);
  ok("the sets hold every picked item and no more",
     cp.units.every((u) => u.sets.reduce((a, st) => a + st.items.length, 0) === u.items.length),
     true);

  // Item text must come from the payload, never be reconstructed. stemAfter was
  // dropped at first, which silently lost the second half of any item whose text
  // wraps around its figure.
  ok("checkpoint items carry the payload's own stem markup",
     cp.units.every((u) => u.items.every((i) => {
       const src = DATA.items.filter((x) => x.id === i.id)[0];
       return i.stem === (src.stem || null) && i.stemAfter === (src.stemAfter || null);
     })), true);
  ok("instructions stay an array", cp.units.every((u) => u.items.every((i) =>
     i.instructions === null || Array.isArray(i.instructions))), true);

  // A standard that resolves to no unit at all must be REPORTED, never dropped
  // silently -- a checkpoint plan that quietly omits a gating standard is worse
  // than one that admits it cannot place it.
  //
  // This used to assert the property using NY-6.G.5, which the publisher's table
  // never cites. It no longer works as a fixture, and the reason is the change
  // worth having: NY-6.G.5's two items are now judged into Unit 1 Lesson 17, so
  // a standard that could not be scheduled at all can be. The property is now
  // exercised directly instead of relying on the real data still having a hole.
  const orphan = Engine.checkpoints(
    [], DATA,
    { usable: true, rows: [{ standard: "NY-6.ZZ.9", credits: 3, bucket: "gates-L2-L3" }] },
    { byStandard: {} }, 6);
  ok("a standard gating proficiency but in no unit is reported, not dropped",
     (orphan.unschedulable || []).indexOf("NY-6.ZZ.9") >= 0, orphan.unschedulable);
  ok("every gating standard in the real file can now be scheduled",
     cp.unschedulable.length === 0, cp.unschedulable);

  // Without a usable gating analysis there is nothing to check against, and the
  // refusal has to say so rather than produce an empty set.
  const noGate = Engine.checkpoints([], DATA, { usable: false, why: "no PL column" },
                                    { byStandard: {} }, 6);
  ok("no gating analysis means no checkpoints", noGate.usable === false, noGate);

  /* --------------------------------------------------------- names left in */

  const idGrid = await read(fixture("isa_identity_left_in.xlsx"));
  const idRep = Engine.run(idGrid, DATA);
  ok("a file with names still analyses", !idRep.error, idRep.error);
  check("it warns about the name column", idRep.warnings.length, 1);
  ok("the warning names the problem",
     /names or ID numbers/.test(idRep.warnings[0]), idRep.warnings[0]);
  // The one that matters. Not "was it warned about" but "did it get out".
  const blob = JSON.stringify(idRep);
  ok("no name from the file reached the report", !/DOE|ROE|POE/.test(blob), true);
  ok("no SURNAME, FORENAME pattern reached the report",
     !/\b[A-Z]{2,}, ?[A-Z]{2,}\b/.test(blob), true);

  // The other half of the warning: it must stay quiet when nothing is wrong.
  // A redacted export repeats one placeholder word down the name column, and
  // warning on that trains a teacher to click past the warning that matters.
  check("a clean file raises no warning", r.warnings.length, 0);
  const redacted = [
    ["Student Name", "Class", "Q1 (6.RP.2)", "Q2 (6.NS.5)", "Q3 (6.RP.3d)", "Q4 (6.EE.2c)",
     "Q5 (6.G.3)", "Q6 (6.EE.6)", "Q8 (6.NS.6a)", "Q9 (6.NS.1)", "Q10 (6.RP.3a)", "Q11 (6.G.2)"],
  ];
  for (let i = 0; i < 6; i++) {
    redacted.push(["name", "6A1", "A", "D", "A", "B", "C", "D", "A", "C", "D", "C"]);
  }
  check("one placeholder repeated down the name column is not a roster",
        Engine.parseGrid(redacted).warnings.length, 0);

  /* ------------------------------------------------------- the Class column */

  // Column 0 is never read, whatever it is headed. A file that labels its very
  // first column "Class" must not thereby unlock the column where the name
  // lives in every other file.
  const spoof = [["Class", "Q1 (6.RP.2)", "Q2 (6.NS.5)"]];
  check("a Class header on column 0 is refused",
        Engine.findClassColumn(spoof, 0, 1), -1);

  // Values that look like people, not sections.
  const namey = [["x", "Class", "Q1 (6.RP.2)"], ["", "Jane Doe", "A"], ["", "John Roe", "B"]];
  check("a Class column holding names is refused",
        Engine.findClassColumn(namey, 0, 2), -1);

  const codes = [["x", "Class", "Q1 (6.RP.2)"], ["", "6A1", "A"], ["", "6A2", "B"]];
  check("a Class column holding codes is accepted",
        Engine.findClassColumn(codes, 0, 2), 1);

  // The uniqueness guard, inherited from RegentsAlign: one 2024 export used
  // initials plus year (DC24, JF24) in the section column, and reporting those
  // would have put an identifier in the output.
  const unique = [
    ["Class", "Q1 (6.RP.2)", "Q2 (6.NS.5)", "Q3 (6.RP.3d)", "Q4 (6.EE.2c)", "Q5 (6.G.3)",
     "Q6 (6.EE.6)", "Q8 (6.NS.6a)", "Q9 (6.NS.1)", "Q10 (6.RP.3a)", "Q11 (6.G.2)"],
  ];
  for (const code of ["DC24", "JF24", "AB24", "CD24"]) {
    unique.push([code, "A", "D", "A", "B", "C", "D", "A", "C", "D", "C"]);
  }
  // Column 0 again, so this also re-proves the index guard on a real parse.
  const uniqueRep = Engine.parseGrid(unique);
  check("per-student codes in column 0 are never read as sections",
        uniqueRep.sections, {});

  /* --------------------------------------------------------- what it refuses */

  check("an empty sheet", Engine.parseGrid([]).error, "That sheet is empty.");
  ok("a sheet with no Q(standard) headers",
     /No row of question headers was found/.test(
       Engine.parseGrid([["Name", "Score"], ["a", 1]]).error), true);
  ok("headers but no students",
     /No student rows/.test(Engine.parseGrid([unique[0]]).error), true);

  // Standards that belong to no published test. The refusal has to be a
  // refusal: joining against the nearest neighbour would produce a confident,
  // wrong report.
  const alien = [["Q1 (9.XX.1)", "Q2 (9.XX.2)", "Q3 (9.XX.3)", "Q4 (9.XX.4)", "Q5 (9.XX.5)",
                  "Q6 (9.XX.6)", "Q7 (9.XX.7)", "Q8 (9.XX.8)", "Q9 (9.XX.9)", "Q10 (9.XX.10)"],
                 ["A", "B", "C", "D", "A", "B", "C", "D", "A", "B"]];
  const alienRep = Engine.run(alien, DATA);
  ok("standards from no published test are refused",
     /could not be matched to a published test/.test(alienRep.error), alienRep.error);
  check("and nothing was identified", alienRep.identify.testId, null);

  /* ------------------------------------------------------- the final guard */

  let threw = null;
  try {
    Engine.assertNoIdentity({ sections: { "6A1": 2 }, rows: [{ who: "SMITH, JOHN" }] });
  } catch (e) { threw = e.message; }
  ok("assertNoIdentity throws on a name-shaped value", /name-shaped/.test(threw || ""), threw);

  threw = null;
  try { Engine.assertNoIdentity({ items: [{ note: "123456789" }] }); }
  catch (e) { threw = e.message; }
  ok("assertNoIdentity throws on an OSIS-shaped value", /OSIS-shaped/.test(threw || ""), threw);

  // Item text comes from the published payload, which is NYSED's own wording.
  // A word problem about two children must not be mistaken for a roster.
  threw = null;
  try {
    Engine.assertNoIdentity({ items: [{ stemPlain: "ALVAREZ, MARIA sold 12 tickets." }] });
  } catch (e) { threw = e.message; }
  ok("assertNoIdentity does not fire on published item text", threw === null, threw);

  /* ------------------------------------------------- the real file, if present
   *
   * Not committed and never will be. Point MATHALIGN_ISA at a real export to
   * re-check the three figures provenance/isa_format.md records; without it
   * this skips, exactly as RegentsAlign's suite skips its private class files.
   */
  const real = process.env.MATHALIGN_ISA;
  if (!real || !fs.existsSync(real)) {
    skip("the real grade 6 2026 export reproduces its recorded figures",
         "set MATHALIGN_ISA to a real ISA file to run this");
  } else {
    const rr = Engine.run(await read(real), DATA);
    check("real file identifies as grade 6 2026", rr.testId, "g6-2026");
    check("real file matched every item", [rr.identify.agree, rr.unmatched.length], [39, 0]);
    const rq = (n) => rr.items.find((i) => i.item === n);
    check("Q43 against the State", [rq(43).classP, rq(43).stateP], [0.09, 0.29]);
    check("Q23 against the State", [rq(23).classP, rq(23).stateP], [0.462, 0.64]);
    check("Q9 against the State", [rq(9).classP, rq(9).stateP], [0.462, 0.6]);

    // The curve, recovered from the real file rather than from the table above.
    check("real curve: 35 points, no collisions", [rr.curve.points, rr.curve.collisions], [35, 0]);
    const rcut = (l) => rr.curve.cuts.filter((c) => c.level === l)[0];
    check("real Level 3 cut", [rcut(3).raw, rcut(3).exact, rr.totalCredits], [24, true, 46]);
    check("real Level 4 cut", [rcut(4).raw, rcut(4).exact], [39, true]);

    // Gap x weight, and the case that proves why weight matters: NY-6.EE.8 has
    // the BIGGER gap (-17.8 vs -17.7) but is worth 1 credit a year against
    // NY-6.G.1's 2.5, so it must rank lower.
    const rfo = (std) => rr.focus.filter((x) => x.standard === std)[0];
    check("NY-6.G.1 is the top area of focus",
          [rr.focus[0].standard, rr.focus[0].creditsLost], ["NY-6.G.1", 0.44]);
    ok("the bigger gap worth fewer credits ranks lower",
       rfo("NY-6.EE.8").gap < rfo("NY-6.G.1").gap &&
       rfo("NY-6.EE.8").creditsLost < rfo("NY-6.G.1").creditsLost,
       [rfo("NY-6.EE.8").gap, rfo("NY-6.G.1").gap]);

    check("real band sizes", rr.gating.sizes, { L1: 25, L2: 19, L3: 25, L4: 9 });
    const gates = rr.gating.rows.filter((x) => x.bucket === "gates-L2-L3");
    check("14 standards gate proficiency", gates.length, 14);
    check("NY-6.EE.7 leads them at 3 credits",
          [gates[0].standard, gates[0].credits], ["NY-6.EE.7", 3]);

    // The pacing finding: the gating content is taught late.
    const u6 = rr.gatingByUnit.units.filter((u) => u.unit === 6)[0];
    check("Unit 6 carries 11 gating credits from week 21",
          [u6.credits, u6.startWeek], [11, 21]);
    check("20 distinct gating credits", rr.gatingByUnit.distinctCredits, 20);
    const mid = rr.gatingByUnit.units
      .filter((u) => u.startWeek >= 21 && u.startWeek <= 29)
      .reduce((a, u) => a + u.credits, 0);
    check("17 gating credits fall in weeks 21-29", mid, 17);

    // The checkpoint findings on the real file.
    check("Unit 6's set is capped at six, not ten",
          rr.checkpoints.units.filter((u) => u.unit === 6)[0].items.length, 6);
    check("Unit 7 is flagged: gating weight, late, and no mid-unit assessment",
          rr.checkpoints.lateWithoutMidUnit.map((u) => u.unit), [7]);
    check("17 checkpoint items in total", rr.checkpoints.totalItems, 17);

    check("NY-5.OA.3 is a prior-grade standard, not an index gap",
          [rr.placement.priorGrade, rr.placement.unplaced],
          [["NY-5.OA.3"], ["NY-6.G.5"]]);
  }

  console.log("");
  if (failures) {
    console.log(failures + " of " + checks + " checks FAILED");
    process.exit(1);
  }
  console.log(checks + " checks, all checks passed");
}

main().catch((err) => { console.error(err); process.exit(1); });
