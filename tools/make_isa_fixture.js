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
    // something real to find.
    const ability = (rand() - 0.5) * 0.5 + (sections.indexOf(section) - 1.5) * 0.06;
    const row = [opts.name(s), section, "", "", "", ""];

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
  // exercised and omissions stay visibly distinct from wrong answers.
  const last = rows[rows.length - 1];
  last[last.length - 1] = null;
  last[last.length - 2] = null;

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
