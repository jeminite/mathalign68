# Where this is up to

## Status

**Phases 0 and 1 complete.** 396 items across 12 tests, a five-tab site, and a 53-check deploy
gate that passes. Not yet deployed to Netlify — that needs a site created and linked.

**The glyph decode works.** All 69 inline maths holes in 2026 grade 7 decode from vector geometry
with zero unknown glyphs, off 23 hand-labelled shapes. See "Showing the questions" below. Next
increments there are display-maths regions and figure crops.

Also outstanding: the class-results analyzer (the colleague-facing half, needs no curriculum data)
and the curriculum index now that the Teacher Course Guides are in `sources/`.

| Phase | State | Blocked by |
|---|---|---|
| 0 — foundations, sources, standards registry, blueprint | done | — |
| 1a — item map + page map + data/items.json | done | — |
| 1b — site, preflight | done | — |
| 1c — first Netlify deploy | ready | needs a Netlify site created |
| 2 — class-results analyzer | next | — |
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

## Done in Phase 1b

- `build/payload.py` — canonical data to published rows, and it owns two refusals: any
  student-derived field, and anything that would present item text. Both proven to fire.
- `build/render.py` + `templates/` — real HTML, CSS and JS files on disk rather than Python
  string constants, with a check that no placeholder survives into the built page.
- `publish.py` — ~90 lines. Writes `site/index.html` (384 KB, payload embedded) and
  `site/data.json` (481 KB, the public contract).
- Five tabs — Standards, Difficulty, Blueprint, Post-test standards, Items — with a grade 6/7/8
  switcher that carries its own accent colour, so a screenshot of one grade cannot be mistaken
  for another. Verified in a browser on all three grades with no console errors.
- `tools/preflight.py` — 53 checks, 13 sections, currently 53 passed / 0 failed / 3 skipped
  (the skips are Phase 2 and Phase 3 suites and say so).
- `tools/test_extractor.py` — 169 checks: goldens for all 14 extractions, property tests that
  consult no golden, and a test that deliberately breaks column assignment and requires the
  suite to notice.

Two bugs the gate found in itself, both fixed and both worth remembering:

- The regenerability check **rewrote** `data/standards.json` to compare it, which bumped its
  mtime past the site build and tripped the freshness check one section earlier. A verification
  step must not mutate what it verifies; `extract_standards.py --stdout` exists for that.
- Section 5's checks were named for the defect rather than the property, so a passing run
  printed `ok  multiple-choice key not in A-D`, which reads as though the defect were
  acceptable. Name a check for what is true when it passes.

## Showing the questions — the glyph decode

The stems in these PDFs are a **template with holes**: the prose is real text and extracts
exactly, and only the mathematics is missing. 2026 grade 7 yields 1,593 prose words verbatim with
~69 inline holes.

The holes are located by intersecting each prose line's y-band with the vector rectangles no text
span covers — not by whitespace heuristics, which miss a hole at a line wrap and a narrow variable
between two commas.

And the maths **decodes mechanically**. Every character is drawn as a vector path, so two
instances of one character have the same path geometry. `tools/glyphs.py` normalises a path's
points into its own bounding box and clusters by geometric distance; `tools/label_glyphs.py`
renders each cluster as a 10× tile so it can be labelled once. 2,478 glyph paths in 2026 grade 7
reduce to 178 clusters, of which **only 23 are needed for all 69 inline holes**.

Result: **69 of 69 holes decode, zero unknown glyphs.** Item 48 independently reproduces `$3.75`,
`$5.25` and `$30.00`, matching NYSED's own exemplary-response page for that item.

Why this rather than a vision pass over the page: a model reading a page can silently drop or
invent a term and the output gives no sign of it. A labelled glyph table either matches or reports
an unknown, which is a locatable failure. Vision is the *labeller* and the *reviewer* here, not the
transcriber.

### Traps found, all fixed

- **Reading order cannot key on `y0`.** A period sits on the baseline and a digit starts at cap
  height, so their `y0` differ by most of a glyph — every decimal point and operator sorted into a
  row of its own *after* the digits, turning `$540.00` into `$540 00 .` and `10%` into `%10`.
  Lines must be found by vertical *overlap*.
- **A horizontal rule cannot be labelled as a character.** The same shape is a minus sign
  (`−10`), a fraction bar (`−2½`) and an answer blank. `g009` and `g063` are both 6.8–6.9 × 0.7pt
  and serve two different roles. They are labelled `@rule` and resolved by what sits above and
  below — RegentsAlign's `build_fractions()` rule, and for its reason: without it every stacked
  pair becomes a fraction, or every fraction becomes a subtraction.
- **Gap-inferred spacing breaks on narrow punctuation.** A period's side bearing exceeds the gap
  threshold, publishing `$11 .98` and `1 .5`. `.`, `,`, `)` and `%` never take a space before;
  `(` and `$` never after.
- **Exact hashing over-splits.** Rounded-coordinate hashes leave ~a quarter of fingerprints as
  singletons from sub-pixel placement — the dollar sign split across two keys on one page while
  every digit hashed consistently. Clustering is by distance with a tolerance, bucketed only for
  speed.
- **Not every glyph cluster is a character.** `g117` (×466) is a hatched grid cell, `g079` a
  dot-plot marker, `g084`/`g085`/`g118`/`g122` arrows. Size filters alone do not separate artwork
  from type.

### What is left

- **Display-maths regions** — items 41, 44 and 47 put their expressions on their own line, so
  there is no prose line to intersect. The glyphs are present and the fraction resolver handles
  them; the region just has to be passed as one group. A few more labels needed.
- **Figures** — item 46 is a graph plus a table, hundreds of glyphs. Those get cropped as images,
  not decoded. Transplant RegentsAlign's trick of growing the crop box to enclose every span
  stripped as furniture, or axis titles get sliced out of both the stem and the picture.
- The remaining 155 unlabelled clusters are mostly letters inside tables and graphs. They do not
  block anything, and decoding them is a cheap way to write accurate `longDescription` text —
  which is where RegentsAlign had a real error (its Aug 2025 Q22 description contradicted the
  PDF's own vector data).

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
- **282 answer keys agree across two independent code paths** — the geometry parser and a
  deliberately naive plain-reading-order re-read of the PDFs, which preflight runs on every
  deploy. This is the single strongest reason to trust the extraction.
- **Every domain's released credit share sits within 8 points of NYSED's published range**, on
  all twelve tests. Independent corroboration of both the extraction and the hand-authored
  blueprint.
- **New York places probability clusters in both grade 6 and grade 7.** `NY-6.SP.6`, `.7` and
  `.8a/8b` sit under "Investigate chance processes and develop, use, and evaluate probability
  models" — the same cluster wording as grade 7's `NY-7.SP.8a`. Identical cluster text on a
  grade 6 and a grade 7 standard is correct, not a mis-assignment. And since all of grade 6 SP
  is post-test, New York teaches probability in grade 6 and tests it in grade 7.
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
4. **The Imagine IM New York 6–8 course guides have arrived** (`ImagineIM_NY_{6,7,8}__TCG_*.pdf`,
   130 pages each, clean text layer), along with three NYCPS pacing workbooks and — fetched from
   links inside them — the NYCPS *NYS Exam IM Alignment* sheets in `sources/nycps/`. Phase 3 is
   unblocked. Three hazards are recorded in `sources/nycps/PROVENANCE.md` and the plan: grades 7
   and 8 **swap Units 7 and 8** between the New York and national editions; the NYCPS workbooks
   use *national* numbering on one sheet and *New York* numbering on its siblings; and grade 8's
   TCG contradicts itself on Unit 6 (11 lessons tabled, 9 everywhere else, because `8.SP.A.4` was
   removed under NGMLS and the table was not regenerated). Resolve lessons by title, never by
   number.
5. **The TCGs contain the full text of every standard**, so `statement` need not stay null for all
   146 entries in `data/standards.json`.
6. **Withheld constructed-response credits are the one inferred field in the dataset.** Which
   withheld CR item carries which credit value is derived from the blueprint's credit mix minus
   the released items, assigned in item order. NYSED does not publish it. Every such record
   carries a `basis` string saying so; do not let it leak into anything presented as fact.
