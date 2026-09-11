# Where this is up to

## Status

**Phases 0 and 1 complete.** 396 items across 12 tests, a five-tab site, and a 53-check deploy
gate that passes. Not yet deployed to Netlify — that needs a site created and linked.

**Live and public at <https://mathalign68.netlify.app>.** 396 items across grades 6-8, 42 of them
(all of 2026 grade 7) showing the actual question, and an About & corrections tab with a working
feedback form -- verified end to end by submitting a correction and watching it arrive.

**The curriculum index is built and live** — a Curriculum tab per grade showing all 9 units, 427
lessons with their standards, the guide's own pacing, and which units are taught after the test
that could assess them. 71 gate checks plus a 23-check numbering gate of its own.

**Search, filter and sort are in**, modelled on RegentsAlign's sidebar: a derived "Taught in unit"
filter plus Standard, Question type, Year, four sort orders and a widened search on the Questions
tab; the same unit filter and a "Taught in" column on Items; and shift-click multi-level sort in
every table on the site.

**The whole of 2026 is published** — grade 6's 39 items, grade 7's 42 and grade 8's 42. 123 of 396
items carry the actual question, and the Questions tab is real for every grade.

Next: the per-item curriculum alignment (`data/alignment.json`, hand-owned), the class-results
analyzer, and then the 2023–2025 tests.

### Two Netlify settings that were wrong at first

Both are written up in README's publish section. A new project on this account inherits visitor
SSO for *all* contexts, so production answered 401 to everyone; RegentsAlign uses
`sso_login_context: non_production` and MathAlign68 now matches, which keeps draft URLs private
while production is public. And form detection is off by default
(`processing_settings.ignore_html_forms: true`), so the form deployed but collected nothing --
and the HTML is only re-scanned on a deploy, so enabling it needs a redeploy to take effect.

Also outstanding: the class-results analyzer (the colleague-facing half, needs no curriculum data)
and the curriculum index now that the Teacher Course Guides are in `sources/`.

| Phase | State | Blocked by |
|---|---|---|
| 0 — foundations, sources, standards registry, blueprint | done | — |
| 1a — item map + page map + data/items.json | done | — |
| 1b — site, preflight | done | — |
| 1c — first Netlify deploy | done | draft URL live |
| 2 — questions for 2026 grade 7 | done | 42 items published |
| 3 — curriculum index from the TCGs | next | — |
| 4 — questions for 2026 grades 6 and 8 | after 3 | — |
| 5 — class-results analyzer | later | — |
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

## Publishing the questions

`tools/extract_items.py` -> `provenance/content_g7-2026_raw.json` (a first pass) ->
`provenance/merge_g7-2026.json` (the reviewed spec) -> `tools/merge_content.py` ->
`data/content.json` -> `build/payload.py` joins it to `data/items.json` on item id.

**The ownership split is the load-bearing part.** `items.json` is script-owned and preflight
re-runs the extractors and fails if it differs from the source PDFs. Transcription is judgement
and cannot be regenerated, so it lives in `content.json` and nothing else. An item with no
content entry publishes exactly as it did before, so coverage grows test by test with nothing
half-broken in between.

### The gate, re-pointed

Phase 1 committed to publishing no item text. That was about never publishing *extraction
output* as if it were the question, and the replacement is stricter, not looser. Section 8 of
`preflight.py` is now 18 checks, of which two matter most and are complements:

- **Prose fidelity** - strip the markup and the decoded mathematics from a published stem and
  what remains must be character-identical to the PDF's own text layer. Proven to fail: changing
  "bowling alley" to "bowling centre" in item 48 was caught and named.
- **Hole completeness** - every hole the extractor located must be filled. Prose fidelity proves
  nothing was *invented*; this proves nothing was *lost*, and during development a fix made nine
  items lose their inline mathematics while fidelity still passed on all 42.

Plus: tag balance, exactly-one-correct-choice, no empty choice, no surviving ligature or
unmapped-glyph damage, no hair space, the `f (x)` kerning regex, every figure published with
distinct alt text, and - closing the hole RegentsAlign's `RESUME.md` #64 still records - **every
constructed-response answer cites an official source.**

### Constructed-response answers come from NYSED

The scoring-materials PDF has an `EXEMPLARY RESPONSE` page per CR item that renders the stem with
all its numerals legible plus the worked solution. All eight corroborate the transcription
independently: item 40's $5.67 uses the prices in its own extracted table, item 45's 30 students
uses the 32 total from its table and the 120 decoded from its stem, item 48's 5 games uses the
$3.75/$5.25/$30.00 the glyph decode produced.

## The glyph decode

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

### `tools/extract_items.py` — the first-pass extractor

42 items, 0 unresolved, 16 figures, 7 displayed expressions, 44 labelled glyphs.

**The check that makes it trustworthy: prose fidelity, 42 of 42.** Strip the markup and the
decoded values out of a published stem and what remains is character-identical to the PDF's own
text layer. So no word was invented, dropped or reworded, and that is proven mechanically rather
than asserted.

**But that check alone is not enough, and finding out why was the most useful thing here.** A fix
for one bug made nine items lose their inline maths entirely — `$3.75` back to nothing — and
prose fidelity still passed 42/42, because it proves nothing was *invented*, not that nothing was
*lost*. Preflight needs the complementary check: every located hole must be filled.

### Traps found in the extractor, all fixed

- **Occupancy must be tested per CHARACTER, not per span.** PyMuPDF reports
  `'determine the number of games, , that Nicholas played if he spent a total of '` as ONE span
  whose box straddles the gap where the italic `x` is drawn, so a span-level test discarded that
  variable and published "the number of games, , that" — still a sentence.
- **The item number is printed level with the item's SECOND line.** The anchor sits 5–6pt below
  the first line of prose, so a region starting at the anchor lost every item's opening sentence.
  Item 3 began "between the price, p," instead of "A farm sells blueberries…". Reach back 12pt.
- **`page.get_drawings()` returns fresh dicts on every call.** Calling it twice and tracking
  consumption by `id()` never matched, so every glyph already used as an inline hole reappeared
  as leftover artwork — 42 items produced 173 phantom "displayed expressions".
- **Maths too tall for one line was being silently dropped.** A stacked fraction exceeds the
  inline height limit, and skipping it published "He spends  of his money" and "buys 3 pounds of
  grapes,  pound of turkey". Silent loss is the one failure this whole approach exists to
  prevent; anything too tall is now recorded, never discarded.
- **A raw `<` in decoded output corrupts the HTML.** Item 21's choice B decoded correctly as
  `20x + 5 < 200` and published as `20x + 5`, because the `<` opened a tag that swallowed the
  rest — and that item's four choices differ ONLY by their inequality symbol.
- **A horizontal rule has a third meaning: a repeating-decimal overbar.** Item 7's choices are
  3.3-repeating; reading the bar as a minus published "− y = x + 3.3", a different number with a
  leading minus that is not in the question. And the bar must be attached to the digits it covers,
  since its own rect sits above the digit line and sorted ahead of everything.
- **A figure zone needs structural paths, not just many glyphs.** Counting paths alone made an
  item's three money values into a "figure" spanning the stem. A real figure contains axis lines,
  table borders, plot marks — paths that are not letter shapes.
- **An inline hole is bounded on the right only.** A graph's axis label can share a prose line's
  y-band from far out to the right (item 27 published its y-axis label mid-sentence), but a value
  that wraps to the next line sits to the LEFT of that line's text — bounding both sides cost
  item 48 the `$3.75` that first demonstrated this approach works.
- **A table row of numbers decodes perfectly cleanly**, so "decodes cleanly" alone promoted table
  rows to displayed expressions while their header rows stayed in the figure. Anything inside a
  figure zone belongs to the figure.
- **The item frame is a single path enclosing the whole question**, 468 × 624 — RegentsAlign
  excludes its equivalent with `width > 480 and height > 500`, so an absolute threshold tuned to
  another document misses this one.
- **Re-running left stale crops behind** — 200 files for 16 figures. The asset directory is
  cleared first now; a stale crop that still matches a filename looks current.

### Known remaining imperfections

- Item 27's `y` variable in "the amount of juice, ␣, that can be made" sits inside the graph's
  own bounding box, so the figure-zone exclusion takes it. One missing variable, flagged here
  rather than papered over.
- Item 7's overbar covers `.3` rather than just the `3`, so it renders as 3.[.3 repeating]
  instead of 3.3̄.
- The remaining ~134 unlabelled glyph clusters are letters inside tables and graphs. They block
  nothing, and decoding them is a cheap way to write accurate `longDescription` text — which is
  where RegentsAlign had a real error (its Aug 2025 Q22 description contradicted the PDF's own
  vector data).

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

## Phase 3 — the curriculum index

Three new scripts, all regenerable and all under the deploy gate:

- **`tools/extract_im_ms_lessons.py`** → `data/im_ms_reference.json`. Units, sections, lesson
  titles, and both of the guide's alignment tables, per grade. 152 / 143 / 132 lessons, 43 / 36 /
  39 sections, nine units each, matching the guides exactly.
- **`tools/extract_pacing.py`** → `data/im_ms_pacing.json`. Day ranges, optional lessons, mid-unit
  assessments and start weeks from the 35-week table.
- **`tools/validate_im_ms_lessons.py`**. The exit gate, 23 checks, run by `preflight.py`.

### Two cross-checks that are stronger than anything they replaced

**The pacing table is printed in full in all three guides.** So grade 7's pacing is read from the
grade 6 guide, the grade 7 guide and the grade 8 guide independently, and the three readings must
be identical. Three PDFs, three layouts, one answer — `extract_pacing.py` fails the build if they
differ. This is a real check, not a restatement.

**The day ranges are arithmetically predicted by the lesson counts.** For every one of the 27
units: `days_max = lessons + 2 + (1 if mid-unit assessment)` and `days_min = days_max − optional`,
with Unit 9 (wholly optional, no assessment days) running `[0, lessons]`. Three tables parsed from
different pages by different code, agreeing to the day. The guide's own footnote states the
formula; this confirms it holds and confirms both extractors at once.

### Traps found, all fixed

1. **Seven standards shipped with the wrong cluster description.** `NY-8.G.1a/1b/1c` are rigid
   transformation standards and carried "Use functions to model relationships between quantities";
   `NY-8.EE.1`, `NY-8.EE.4`, `NY-5.NBT.4` and `NY-6.EE.8` each had a neighbouring cluster's text.
   `clusterText` is displayed on the site, so this was wrong data in front of readers. Cause: the
   educator guide's chart uses merged cells and `owner_of()` assigned them by where the text sat.
   Fix: **read the table's own drawn rules**. Every cell boundary is a horizontal rule, and a
   merged cell is drawn by omitting the interior ones, so the rules recover NYSED's structure
   instead of inferring it (`cells_by_rule`). A first attempt — forcing the cluster index to
   advance at a domain change — fixed the four grade 8 cases and missed the other three; that is
   why the rules are worth reading rather than reasoned around.
2. **`NY-7.SP.1`'s cluster is wrong in the source, not in our parse.** The grade 7 chart merges one
   ruled cell (y=406.0–455.0) across `NY-7.SP.1`, `7.SP.3` and `7.SP.4` and labels it with the
   comparative-inferences cluster; NYSED omits the random-sampling cluster heading that `7.SP.1`
   belongs to. Published as printed and recorded in `blueprint.json`'s `knownDataDefects`.
3. **Forty lesson references were silently dropped by a line wrap.** *Lessons by Standard* prints
   "Unit 1, Lesson 6" across a line break — "… Unit 1," then "Lesson 6, …" — so a per-line regex
   lost every straddling pair, including eight of `NY-7.G.1`'s thirteen Unit 1 lessons. Nothing
   looked wrong; the standard still had lessons, just fewer. Caught only because the validator
   requires the guide's two tables to be exact inverses. Fix: join the cell before matching.
4. **A cluster citation is not a standard.** Both tables cite whole clusters in the guide's own
   literal form (`NY-7.EE.Cluster-1`). Mixed in with standards they join to nothing in
   `standards.json` and look like missing standards. They now live in `clusterToLessons` /
   `lessonToClusters`, and their numbers are **deliberately not resolved** to cluster wording:
   `NY-7.SP.Cluster-2` is NGMLS's second SP cluster but NYSED's chart prints it first, and the
   grade 7 guide cites `NY-6.SP.Cluster-5` although the grade 6 guide's own SP clusters stop at 2.
5. **The guide's two alignment tables are not inverses of each other.** Six pairs differ in grade
   7, all in or beside Unit 7 — and `NY-7.NS.2d` is placed at Unit 7 Lesson 16 by one table and
   Unit 8 Lesson 16 by the other, the swapped-unit hazard appearing inside the guide itself.
   Grades 6 and 8 are exact inverses, which is what makes six a fact about the guide rather than
   about the parser. Both readings are published in `tableDisagreements`, and the gate requires
   the disagreements to be **exactly** the ones recorded — a new one fails, and so does one that
   quietly goes away.
6. **17 lessons cite no standard at all, and that is correct.** IM opens most units with an
   invitation to the mathematics that addresses no standard, and the guide's *Standards Addressed*
   cell for it is blank (verified on "Unit 1, Lesson 1"). Recorded in `lessonsWithoutStandards` so
   an empty row on the site reads as "the guide lists none" rather than "extraction failed".
7. **Parent codes cost a whole unit its item count.** The guides cite `NY-7.EE.4`; every released
   item cites `NY-7.EE.4a` or `4b`. Matching the literal string found nothing, and grade 7 Unit 8
   showed **0 released items** — for the geometry unit. Expanding parents took it to 29. The same
   bug rendered `NY-7.RP.2` struck through as "not a standard".
8. **`postTest` alone was the wrong question.** It means "designated for May-to-June instruction in
   the standard's own grade". Grade 7 Unit 7 teaches six grade 6 statistics standards, all flagged,
   all assessed on the grade 7 test — reporting those as "taught after the test" said the opposite
   of the truth. The test is whether the standard is assessed somewhere **other** than this grade.
   Grade 8's post-test standards resolve to nowhere at all: there is no grade 9 State test, so they
   are taught and then never assessed.
9. **A zero needs an explanation or it becomes a claim.** Grade 6 Unit 5 teaches `NY-6.NS.2` and
   `NY-6.NS.3` and neither has ever been released. Left bare that reads as "never tested", which
   the data cannot support — a quarter of every test is withheld. The unit card now says "no
   evidence either way".
10. **Title case is not stable within a single guide.** The grade 6 guide prints its Unit 9 as
    "Putting it All Together" in the Scope and Sequence box and "Putting It All Together" in the
    pacing table. Since the project's rule is *resolve by title*, titles must be matched
    case-insensitively. Grades 7 and 8 use only the capitalised form.
11. **The payload's prose cap fired on legitimate hazard notes.** `CAP_EXEMPT_ROOTS` covers only
    top-level `meta`, so `curriculum.meta` tripped it. Exempting the whole `curriculum` tree would
    have stopped the cap watching 427 lesson titles — exactly the field extracted text could arrive
    in — so the exemption is path-based (`CAP_EXEMPT_PATHS`).
12. **The payload field is `secondary`, not `secondaryStandards`.** `items.json` uses the long
    name, the payload renames it, and the new view used the wrong one — a `TypeError` that blanked
    the whole tab. Worth checking the payload's own field names rather than `items.json`'s.

## The unit filter is DERIVED, and that is the whole story

`data/alignment.json` still does not exist, so no item carries a unit. The filter works by looking
an item's standard up in the curriculum index and taking the units whose lessons teach it. "Unit 3"
means *Unit 3 teaches the standard this item assesses*, not *this item belongs to Unit 3* --
over-inclusive, never wrong, and the same join the Curriculum tab already publishes, so the two
tabs cannot disagree. The caveat renders beside the dropdown and preflight refuses to ship without
it.

Why no Section or Lesson filter: a standard maps to a median of **6-10 lessons**, so a lesson-level
filter would be noise. Unit is usable — grade 8 pins 99 of 135 items to exactly one unit — but
grade 7 averages three units per item, which is why it is labelled and not presented as alignment.

**Preflight section 7d** re-derives the whole mapping in Python and asserts two things: that every
grade has unit options (an empty list would mean the parent-code join broke and the dropdown would
render empty rather than fail), and that **no derived unit has been written onto an item**. That
second check is the important one — section 9 asserts the same negative while `alignment.json` is
absent, and 7d names the dependency so nobody later satisfies section 9 by populating the fields
and quietly turns a derivation into a claim. Verified by writing a unit onto an item and watching
the gate fail.

### Traps found

1. **Parent codes, in reverse.** `expandCode` was written to go parent -> children for the
   Curriculum tab. The item -> unit direction needs the same bridge the other way: the index is
   keyed on `NY-7.EE.4` and every item cites `NY-7.EE.4a`. Building the index by expanding each key
   and filing the lessons under every sub-standard is what makes grade 7 Unit 8 find its 29 items
   instead of none.
2. **The sort readout scrolled away with the table.** It was inside the `.scroll` box, so on a
   table wider than the viewport "Sorted by Year" rendered as "ted by Year". It now sits outside
   the horizontally-scrolling container.
3. **A bare zero is a claim.** Grade 7's Unit 8 shows few items because its standards are post-test,
   and grade 6 has no Unit 5 or Unit 8 option at all because no released item touches them. Both are
   real findings, already explained on the Curriculum tab, and the Items table's "Taught in" column
   now makes them visible per row.
4. **Unit 9 is a catch-all.** "Putting It All Together" cites standards from the whole year and so
   matches 88 of grade 7's 135 items. Its option is labelled "(review unit -- matches broadly)",
   driven off the `whollyOptional` flag rather than hardcoding unit 9.

## 2026 grade 8, and what it taught the decoder

42 items, 21 figures, 8 constructed-response answers from NYSED's own exemplary responses. It
needed 39 new glyph labels grade 7 never used -- radical, angle, congruence, pi, primes, degree,
braces, the comparison circle, and the serif capitals that name triangles.

**Two labels were nearly wrong, and reading the crops rather than the shapes caught both.** `g150`
is a DEGREE sign, not a capital O -- it decodes `60°F` in item 46. `g185` is a PRIME, not a slash,
which is what makes triangle `A′B′C′` the image of `ABC`.

### Exponents

`9² + 12² = 15²` was publishing as `92 + 122 = 152`, and all four of item 7's choices differ only
in where the exponents sit -- so a reader saw four identical options. Grade 8's Unit 8 is exponents
and scientific notation, so this was not a corner case. Four passes, each fixing what the last
broke:

1. *Shorter than the body and raised above its baseline.* Swept in `=`, which is short and centred
   on the maths axis, giving `12^(2 =) 15^2`.
2. *Excluding centred operators.* Fixed that, but the baseline came from a median over every glyph,
   and the PARENTHESES in `(5²)(7⁻²)(5⁴)` are half again as tall as the digits, so the digits looked
   raised and `5²` lost its base.
3. *Most common foot.* Fixed the parentheses, broke `1¹⁶` -- two superscript glyphs outnumber the
   single base and became the "baseline".
4. **The foot of the tallest glyphs.** Superscripts are drawn smaller than the text they sit on, so
   the tallest glyphs are body text by definition. This one holds.

And the comparison must be **within one run**, not one line: a stacked fraction overlaps its
neighbours vertically, so `4(x + 2) = 12/0.25` is all one "line" and the denominator's feet dragged
the baseline down until the `x` looked raised. Numerator and denominator are now measured
separately -- which also fixed `5⁶/7²` publishing as `56/72`.

The minus of a negative exponent was discarded **by two hundredths of a point**: `MIN_H` is 0.5pt
and a superscript minus is drawn at 70% of a full-size one, 0.48 against 0.68. So `(5²)(7⁻²)(5⁴)`
read as `(5²)(7²)(5⁴)` with the negative exponent -- the whole point of the item -- silently gone.

A rule only counts as an exponent's minus if it PREFIXES one. Geometry alone is not enough: a
lowercase `x` has no ascender, so a run of `x −` measures its body at the x-height and an ordinary
minus looks raised by half of it.

### Three values were wrong in the PUBLISHED grade 7 questions

Extracting grade 8 exposed a line-reading bound that had already corrupted live data:

| item | published | should be |
|---|---|---|
| 34 | `−45/9` | `−45/−9` |
| 43 | `$1` and `$1` | `$12.50` and `$10.25` |
| 36 | `x −` | `x − 0.25x` |

One cause: maths on a prose line was admitted only to the end of that line's text plus 12pt, which
cut a value in half and published the remainder as a stray expression beside the sentence. Item
43's `.50` and `.25` had even been written up in the merge spec as a known oddity -- they were the
back half of its prices. The bound now decides only what may START a run; anything touching that
run joins it however far right it reaches, while an axis label alone in white space stays out.

### Whitespace does not occupy a line

Where maths is lifted out of a sentence the text layer leaves a space, and that space's box is as
wide as the missing value -- so treating it as occupied hid the very glyph belonging there. This
closed grade 7 item 27's missing `y` (a documented gap since launch), item 7's, and grade 8 item
31's `line a is parallel to line ,`. The other three variables on item 31's line fell in gaps
BETWEEN text spans and had been found all along, which is what made the one missing letter look
arbitrary.

### Other traps

- **A stacked fraction can be taller than its line band.** `12²⁰/12⁴` spans 28pt where the band
  allows 15, so it decoded as `12/4`. Whatever completes a bar already in the band is pulled in --
  but only a real bar, meaning a rule with content on **both** sides. "Thin and not too wide" alone
  also matched every decimal point and minus sign and pulled neighbours in through them. The reach
  is 14pt, the same window `glyphs.py` uses; at 22pt it spanned the gap between two bullets and
  lifted the minus of `C (−9,3)` into `B (−3,8)`.
- **A line whose only text is a space has no sentence to protect.** Item 41's vertex list is drawn
  entirely as artwork with one space character in the text layer, so the bound landed
  mid-coordinate and the stem read `A (6, . B (− . C (−`.
- **A glyph with prose on both sides is part of the sentence**, even inside a figure's bounding box.
- **An unlabelled glyph can delete a whole expression.** Item 43's comparison circle was unlabelled,
  so `(16⁵)⁴ ○ 16⁸ · 16¹²` failed to decode, was demoted to artwork, and was then dropped for being
  under the minimum figure area -- the item published without the expression it asks about. Item
  30's braces did the same to its set of ordered pairs.
- **A raised full stop is a multiplication dot.** The shapes are identical; only height on the line
  tells `16⁸ · 16¹²` from a sentence ending mid-expression.

## 2026 grade 6

39 items, 11 figures, 8 constructed-response answers. It needed only **eight** new glyph labels --
`×`, `D`, `m`, `n`, `|` and three fraction bars -- against grade 8's 39, because by then the
decoder had learnt most of what these PDFs draw. Nine items had something undecodable on the first
pass; after labelling, none did.

**An absolute-value bar is the same character opening and closing**, so which side it hugs depends
on how many have come before it. `|−5| < |−15|` needs no space inside the bars and a space outside
them; putting `|` in either spacing set flatly gave `| −5| < | −15|` or `|−5|<|−15|`. Parity
decides it.

**`LINE_TOL` existed for this and was not being applied.** A line's key is the top of its text span
rounded to a tenth of a point, and a span set in a different face sits a hair off its neighbours:
the italic `c` in item 41's *"how many baseball cards, c, Dan has"* is at y=109.3 where the prose
either side of it is at 109.2. An exact key made it a line of its own and it was published at the
END of the stem -- *"baseball cards, , Dan has. c"* -- which reads as a typo rather than as a
missing variable. Snapping keys within `LINE_TOL` also closed grade 7 item 40's trailing `$`, the
first half of a documented review note.

## Open questions

1. **P-value population is undefined.** The guide does not say whether the published P-values
   exclude embedded field-test takers, or what the denominator is. Read the guide again before
   writing the site copy, and if it stays unclear, say so on the page rather than implying a
   like-for-like comparison with one class.
2. ~~**`statement` is null for all 146 standards.**~~ **Resolved.** The Teacher Course Guides
   carry the full NYSNGMLS wording, and `extract_standards.py` now fills `statement` for 110 of
   146. The 36 without are 34 grade 5 codes (not in any 6-8 guide, expected) plus `NY-6.G.5` and
   `NY-7.SP.1`. `clusterText` is still labelled as the cluster wherever it is shown.
3. **Which results export will colleagues actually have?** Unknown, which is why the analyzer is
   specified as a sniffing cascade with a fill-in template fallback. Worth simply asking a
   colleague before building Phase 2 rather than guessing at four layouts.
4. ~~**The Imagine IM New York 6–8 course guides have arrived.**~~ **Phase 3 done** — the index is
   built, validated and live; see the Phase 3 section above. All three hazards below are carried in
   `data/im_ms_reference.json`'s `meta.hazards` and shown on the site's Curriculum tab. Original
   note kept for the detail: **the Imagine IM New York 6-8 course guides have arrived** (`ImagineIM_NY_{6,7,8}__TCG_*.pdf`,
   130 pages each, clean text layer), along with three NYCPS pacing workbooks and — fetched from
   links inside them — the NYCPS *NYS Exam IM Alignment* sheets in `sources/nycps/`. Phase 3 is
   unblocked. Three hazards are recorded in `sources/nycps/PROVENANCE.md` and the plan: grades 7
   and 8 **swap Units 7 and 8** between the New York and national editions; the NYCPS workbooks
   use *national* numbering on one sheet and *New York* numbering on its siblings; and grade 8's
   TCG contradicts itself on Unit 6 (11 lessons tabled, 9 everywhere else, because `8.SP.A.4` was
   removed under NGMLS and the table was not regenerated). Resolve lessons by title, never by
   number.
5. ~~**The TCGs contain the full text of every standard.**~~ Done — see 2 above.
6. **Withheld constructed-response credits are the one inferred field in the dataset.** Which
   withheld CR item carries which credit value is derived from the blueprint's credit mix minus
   the released items, assigned in item order. NYSED does not publish it. Every such record
   carries a `basis` string saying so; do not let it leak into anything presented as fact.
