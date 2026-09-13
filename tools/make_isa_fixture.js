#!/usr/bin/env node
/* Generate the synthetic ISA fixtures the engine suite runs against.
 *
 *   node tools/make_isa_fixture.js
 *
 * Writes fixtures/isa_g6_2026_synthetic.xlsx and fixtures/isa_identity_left_in.xlsx.
 *
 * WHY SYNTHETIC
 * The real export this format was reverse-engineered from holds 78 real
 * students' real response patterns. Its name column had already been redacted
 * before it reached the project, so no name was ever at risk -- but pseudonymous
 * real results are still student data, and this repository contains none and
 * never will. A fixture only needs the shape.
 *
 * Deterministic: same seed, same bytes, so a regenerated fixture is a no-op in
 * git unless the generator actually changed.
 */
"use strict";

const fs = require("fs");
const path = require("path");
const XLSX = require("xlsx");

const ROOT = path.join(__dirname, "..");
const DATA = JSON.parse(fs.readFileSync(path.join(ROOT, "site", "data.json"), "utf8"));
const TEST_ID = "g6-2026";

// A tiny LCG. Math.random() would make the fixture different on every run and
// the suite's expected numbers unwriteable.
function lcg(seed) {
  let s = seed >>> 0;
  return function () { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; };
}

function build(opts) {
  const rand = lcg(opts.seed);
  const items = DATA.items
    .filter((i) => i.testId === TEST_ID)
    .sort((a, b) => a.item - b.item);

  const header = ["Student Name", "Class", "MC%", "CR%", "NYS Math", "Math Lv"]
    .concat(items.map((i) => "Q" + i.item + " (" + i.standard.replace(/^NY-/, "") + ")"));
  const rows = [header];

  const sections = opts.sections;
  for (let s = 0; s < opts.students; s++) {
    const section = sections[s % sections.length];
    // Per-student ability, shifted per section so the by-class view has
    // something real to find. The spread is deliberately wide enough to put at
    // least five students in each of the four proficiency bands, because the
    // band-gating analysis refuses to report a band with fewer -- and a fixture
    // that trips that refusal would leave the gating path untested. The refusal
    // itself is covered by a unit case in the suite instead.
    const ability = (rand() - 0.5) * 1.15 + (sections.indexOf(section) - 1.5) * 0.07;
    const row = [opts.name(s), section, "", "", null, ""];   // PL filled in below

    items.forEach((it) => {
      const credits = it.credits || 1;
      if (it.type === "Multiple Choice") {
        const p = Math.max(0.05, Math.min(0.97, (it.pValue || 0.5) + ability));
        if (rand() < p) { row.push(it.key); return; }
        const wrong = (it.choiceList || [])
          .map((c) => c.label).filter((l) => l !== it.key);
        if (!wrong.length) { row.push(it.key); return; }
        // Bias every item's wrong answers towards its first distractor, so some
        // items cross the "a quarter of the class chose the same wrong option"
        // threshold and the dominant-distractor section has something to show.
        const pick = rand() < 0.55 ? wrong[0] : wrong[Math.floor(rand() * wrong.length)];
        row.push(pick);
      } else {
        const target = it.avgPointsEarned === null || it.avgPointsEarned === undefined
          ? (it.pValue || 0.4) * credits : it.avgPointsEarned;
        const p = Math.max(0.02, Math.min(0.98, target / credits + ability));
        let pts = 0;
        for (let c = 0; c < credits; c++) if (rand() < p) pts++;
        row.push(pts);
      }
    });
    rows.push(row);
  }

  // One student leaves the last two questions blank, so "Left blank" is
  // exercised and omissions stay visibly distinct from wrong answers. This has
  // to happen BEFORE the proficiency level is computed: doing it after left that
  // student with a PL for a raw score they no longer had, which showed up as the
  // curve colliding at one raw value.
  const last = rows[rows.length - 1];
  last[last.length - 1] = null;
  last[last.length - 2] = null;

  // Fill the "NYS Math" column with a proficiency level that is a strict
  // function of raw credits, because that is the property the real export has
  // and the property plCurve depends on. The shape is synthetic -- piecewise
  // linear through the three thresholds -- rather than a copy of any real
  // conversion chart, so the fixture exercises the code path without asserting
  // anything about a particular test's curve. The real curve's own figures are
  // checked in the suite against the table in provenance/pl_curve.md.
  const total = items.reduce((a, i) => a + (i.credits || 1), 0);
  const PL_COL = 4;
  function levelFor(raw) {
    const pts = [[0, 1.0], [Math.round(total * 0.33), 2.0],
                 [Math.round(total * 0.52), 3.0], [Math.round(total * 0.85), 4.0],
                 [total, 4.5]];
    for (let i = 0; i + 1 < pts.length; i++) {
      const [r0, p0] = pts[i], [r1, p1] = pts[i + 1];
      if (raw <= r1) return p0 + (p1 - p0) * ((raw - r0) / Math.max(1, r1 - r0));
    }
    return 4.5;
  }
  for (let i = 1; i < rows.length; i++) {
    let raw = 0;
    items.forEach((it, k) => {
      const v = rows[i][6 + k];
      if (v === null || v === undefined || v === "") return;
      if (it.type === "Multiple Choice") { if (v === it.key) raw += it.credits; }
      else raw += Number(v);
    });
    rows[i][PL_COL] = Math.round(levelFor(raw) * 100) / 100;
    rows[i][5] = "L" + Math.max(1, Math.min(4, Math.floor(rows[i][PL_COL])));
  }

  return rows;
}

function write(rows, file) {
  const ws = XLSX.utils.aoa_to_sheet(rows);
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, "Sheet1");
  const out = path.join(ROOT, "fixtures", file);
  XLSX.writeFile(wb, out, { compression: true });
  console.log("wrote fixtures/" + file + "  (" + (rows.length - 1) + " students)");
}

// The ordinary case. Column A holds no names at all, which is also how the one
// real export arrived.
write(build({
  seed: 20260912, students: 78, sections: ["6A1", "6A2", "6A3", "6A4"],
  name: () => "",
}), "isa_g6_2026_synthetic.xlsx");

// The case that matters: a teacher who did not delete the name column. The
// names are the classic fictional placeholders, written the way ATS writes
// them -- SURNAME, FORENAME -- because the comma is what the guard keys on.
write(build({
  seed: 4711, students: 24, sections: ["6A1", "6A2"],
  name: (s) => ["DOE, JANE", "ROE, RICHARD", "POE, PATRICIA"][s % 3],
}), "isa_identity_left_in.xlsx");
