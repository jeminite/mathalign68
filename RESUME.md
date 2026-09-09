# Where this is up to

## Status

**Phase 0 complete.** Phase 1 (the item map) is next.

| Phase | State | Blocked by |
|---|---|---|
| 0 — foundations, sources, standards registry, blueprint | done | — |
| 1 — item map extractor, site, preflight, deploy | next | — |
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

1. **`expectedReleasedItems` is null for all 12 tests** in `blueprint.json`, deliberately. Fill
   each from the extractor's own count at ingest, then confirm against the PDF. Do not use the
   rough counts from early exploration — they ran 3–4 high per test because secondary-standard
   citations look like item rows.
2. **P-value population is undefined.** The guide does not say whether the published P-values
   exclude embedded field-test takers, or what the denominator is. Read the guide again before
   writing the site copy, and if it stays unclear, say so on the page rather than implying a
   like-for-like comparison with one class.
3. **`statement` is null for all 146 standards.** The educator guide gives cluster descriptions,
   not per-standard wording. Sourcing the actual statements means a different NYSED document.
   Until then the site shows `clusterText` and must label it as the cluster, not the standard.
4. **Which results export will colleagues actually have?** Unknown, which is why the analyzer is
   specified as a sniffing cascade with a fill-in template fallback. Worth simply asking a
   colleague before building Phase 2 rather than guessing at four layouts.
5. **Imagine IM New York 6–8 course guides** are not in `sources/` yet. Phase 3b is blocked on
   them; Phase 3a's public national tables are the unblocked fallback.
