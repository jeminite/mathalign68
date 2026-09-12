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
  check("overall class figure", r.overall.classP, 0.53);
  check("overall state figure", r.overall.stateP, 0.548);

  const q = (n) => r.items.find((i) => i.item === n);
  check("Q1 is multiple choice, 1 credit", [q(1).type, q(1).credits], ["mc", 1]);
  check("Q1 class and state", [q(1).classP, q(1).stateP], [0.744, 0.82]);
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
  }

  console.log("");
  if (failures) {
    console.log(failures + " of " + checks + " checks FAILED");
    process.exit(1);
  }
  console.log(checks + " checks, all checks passed");
}

main().catch((err) => { console.error(err); process.exit(1); });
