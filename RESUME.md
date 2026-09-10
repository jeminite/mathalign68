# Where this is up to

## Status

**Phase 0 complete. Phase 1 extraction complete** — 396 items across 12 tests, in
`data/items.json`. Next in Phase 1: the site (`build/` + `templates/` + `publish.py`) and
`tools/preflight.py`.

| Phase | State | Blocked by |
|---|---|---|
| 0 — foundations, sources, standards registry, blueprint | done | — |
| 1a — item map + page map + data/items.json | done | — |
| 1b — site, preflight, deploy | next | — |
| 2 — class-results analyzer, item picker | after 1 | — |
| 3a — national IM 6–8 alignment (public tables) | after 2 | — |
| 3b — Imagine IM New York 6–8 alignment | waiting | the district course guides |
| 3c — the per-standard judgement pass | after 3a/3b | — |
| 4 — scoring-materials exemplars, CCLS-era archive | later | — |

## Done in Phase 0

- `tools/fetch_sources.py` — 12 released-items PDFs + the educator guide, with
  `provenance/sources.json` recording URL, sha256, bytes, page count and fetch date for each.
- `tools/extract_standards.py` → `data/standards.json` — 146 standards for grades 5–8, with
  domain, cluster description, fluency notes and post-test flags.
- `data/blueprint.json` — hand-authored test design, per-grade domain percent ranges, session
  boundaries, calculator rules, known data defects.

## Done in Phase 1a

- `tools/extract_item_map.py` — geometry-based item map parser; all 12 Next Gen maps plus the
  two CCLS-era 2022 maps kept as regression coverage.
- `tools/build_pagemap.py` — item to PDF page, self-validating; 387 of 396 items carry a link.
- `tools/build_items.py` — assembles `data/items.json`, and `--check` rebuilds from
  `provenance/` and fails on any difference. Proven with a tamper test: hand-editing one
  P-value is caught.

**The corpus is 396 items, not the ~419 in the original plan.** The plan's figure came from
counting standard codes on the map page, which runs 3–4 high per test because a
secondary-standard citation looks like an item row. Real counts: grade 6 = 29/29/29/39,
grades 7 and 8 = 31/31/31/42, total 396 items and 489 credits. Confirmed twice by independent
methods (the geometry parser and a plain-text count of the type strings).

## Verified, and worth not re-deriving

- **All 420 standard citations across the 12 item maps resolve** against `standards.json`, and
  none is cited on a grade the registry says it is not assessed on. That is the strongest
  available check that the registry is complete and the post-test model is right.
- **Session boundaries**: grade 6 Session 1 = items 1–30, Session 2 = 31–46. Grades 7–8 Session 1
  = 1–32, Session 2 = 33–48. Confirmed against all twelve maps, not inferred from the blueprint.
- **2026 released substantially more items than 2023–2025** (roughly 39–41 per test against
  29–31). Any coverage or trend figure must be read per year; pooling without saying so would
  misrepresent it.
- **Post-test flags agree across both of the guide's own sources** — the chart's X column and the
  dedicated "Grade N Post-Test Standards Assessed in Grade N+1" tables. The extractor fails if
  they ever diverge.
- **Grade 8 is asymmetric**: it has X-marked post-test standards (`NY-8.EE.3`, `NY-8.EE.4`,
  `NY-8.EE.8a`, `NY-8.EE.8b`) but no next-grade table, because there is no grade 9 State
  mathematics test. Their `assessedOnGrades` is empty rather than pointing at a grade 9. An item
  map citing one of these would be a genuine anomaly worth investigating.
- **Real NYSED data defects found and handled**: 2024 grade 8 prints
  `NGLS.Math.Content.NY-NY-8.EE.6` (doubled prefix); some codes carry trailing whitespace
  (`NY-8.F.1 `). Both are in `blueprint.json.knownDataDefects` and both need regression tests in
  `tools/test_extractor.py`.

## Phase 1a findings

- **NYSED renamed a column in 2024.** The domain column is headed `Cluster` in 2023, 2025 and
  2026 and `Domain` in 2024. 2024's name is the accurate one: the values are domain names
  ("Expressions and Equations"), not cluster descriptions, in every year. The extractor accepts
  either header and the field is called `domainLabel`. A standard's real cluster description
  comes from `standards.json`.
- **Never publish a "% of the test released" figure.** NYSED promises "at least 75 percent of
  the test questions that counted toward students' scores" — the denominator is *scored* items,
  and `designedItems` includes embedded field-test questions whose number NYSED does not
  publish. Released ÷ designed gives 63–65% for 2023–2025, which reads as NYSED breaking its
  own promise and is simply the wrong denominator. There is a `doNotComputeReleaseShare` note in
  `blueprint.json` saying so.
- **2026 broke the all-constructed-response promise.** 2023–2025 release all ten CR items
  (3 one-credit, 6 two-credit, 1 three-credit — the full design); 2026 releases only eight.
- **Some item numbers are vector artwork, inconsistently.** The 2023 grade 7 booklet prints
  items 13 and 16 as real glyphs at x=42 and items 1, 2, 17 and 18 as artwork on
  identically laid-out pages. So the page map is deliberately allowed to be partial: nothing
  interpolates a page, so an item is either located by its own printed number or gets no link.
  Nine items across 2023–2025 have no link. What *is* fatal is finding a margin number the item
  map does not list as released.
- **Detecting a multiple-choice page needs all four letters, not a column.** Counting bare A–D
  words fails (grade 8 2024 item 48 is a 3-credit CR about "Store A and Store B" — six of
  them). Requiring one left-aligned column of four fails too, because graphical choices are laid
  out 2x2 (grade 7 2025 item 2 puts A and B at x=75, C and D at x=310). Requiring all four
  distinct letters handles both.
- **The map's footnote had to be cut before row banding.** The last item's band extends past its
  anchor to catch a wrapped line, which swallowed "*This item map is intended..." — and that
  footnote contains the word "Constructed", so it parsed as part of item 48's type.

## Traps found the hard way in Phase 0

Each of these produced wrong output before it was fixed. They are all in the extractor now, but
they generalise to the item-map extractor in Phase 1.

- **Merged table cells are vertically centred over their contents**, so a Domain or Cluster cell
  can start *below* its own first code (grade 6: cluster at y=96.3, `NY-6.RP.1` at y=87.0) and end
  *above* its last (grade 7: cluster ends y=134.8, `NY-7.RP.3` at y=136.5). Assign by the midpoint
  boundary between adjacent cells. Nearest-start and nearest-anything each pick wrong.
- **Column bands cannot come from header positions alone.** "Standard(s)" is left-aligned at
  x=393 while its codes start at x=364 and cluster text above runs to x=330; the header midpoint
  therefore cut the tail off every wrapped cluster line, silently turning "real-world and
  mathematical problems" into "real-world mathematical problems". Derive the boundary from where
  the codes actually are.
- **A stray `X` sits at x=48 in the left margin of the standards charts.** Taking `min()` over
  every `X` to find the Post-Test column collapsed the Standard(s) band to nothing.
- **A gap alone cannot separate table cells.** Lines within a cell are ~14.4pt apart and the next
  cell can start only 17.3pt later (grade 5's two Operations and Algebraic Thinking clusters).
  The reliable extra signal is that cluster descriptions are complete sentences.
- **A code list can wrap mid-list, around an annotation.** Grade 7 prints
  `NY-7.EE.4a (Fluency),` and then `4b` alone on the next line. Lifting the parenthetical out
  before matching, and folding bare sub-letter lines into the line above, is what makes
  `NY-7.EE.4b` exist at all — and all four grade 7 maps cite it.
- **An annotation belongs to the one code it follows.** Carrying `(Fluency)` from `4a` to `4b`
  published a claim the guide does not make.

## Open questions

1. **P-value population is undefined.** The guide does not say whether the published P-values
   exclude embedded field-test takers, or what the denominator is. Read the guide again before
   writing the site copy, and if it stays unclear, say so on the page rather than implying a
   like-for-like comparison with one class.
2. **`statement` is null for all 146 standards.** The educator guide gives cluster descriptions,
   not per-standard wording. Sourcing the actual statements means a different NYSED document.
   Until then the site shows `clusterText` and must label it as the cluster, not the standard.
3. **Which results export will colleagues actually have?** Unknown, which is why the analyzer is
   specified as a sniffing cascade with a fill-in template fallback. Worth simply asking a
   colleague before building Phase 2 rather than guessing at four layouts.
4. **Imagine IM New York 6–8 course guides** are not in `sources/` yet. Phase 3b is blocked on
   them; Phase 3a's public national tables are the unblocked fallback.
5. **Withheld constructed-response credits are the one inferred field in the dataset.** Which
   withheld CR item carries which credit value is derived from the blueprint's credit mix minus
   the released items, assigned in item order. NYSED does not publish it. Every such record
   carries a `basis` string saying so; do not let it leak into anything presented as fact.
