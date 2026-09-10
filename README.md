# MathAlign68

**Every released question on the NYS Grades 6, 7 and 8 mathematics tests since the Next
Generation standards took effect — mapped to the standards, to statewide difficulty, and to the
Imagine IM 6–8 curriculum.**

Live at **<https://mathalign68.netlify.app/>** *(built and gated, not yet deployed)*

See `../RELATIONSHIPS.md` for how this fits with the sibling RegentsAlign, AlgebraTeaching and
TeachingBrain projects. RegentsAlign does this for Algebra I; this is its middle-school
counterpart.

---

## What this is for

Three questions, for a middle-school teacher rather than for me:

**"I'm teaching Unit 4 Lesson 9 on Thursday — what has the state actually asked about this?"**
Filter to a unit, section or lesson and see every released item that has tested it.

**"Half my class missed that one — was it us, or was it hard for everyone?"**
Every item carries NYSED's own statewide P-value. You can tell "my class struggled" from
"New York State struggled", which changes what you do next.

**"How did my class actually do, standard by standard?"**
Drop your results file on the analyse page. It runs entirely in your browser, your file is never
uploaded, and it compares your class to the state item by item.

## What you get

| | |
|---|---|
| **Item map** | Every released item 2023–2026, grades 6–8: type, key, credits, standard, cluster, secondary standards |
| **Statewide difficulty** | NYSED's published P-value per item, and average points earned per constructed-response item |
| **Blueprint** | Tested weight by domain against NYSED's own published percent ranges |
| **Post-test standards** | Which prior-grade standards each test assesses, and where they sit in the curriculum |
| **Curriculum alignment** | Unit, section and lesson in Imagine IM 6–8 *(Phase 3)* |
| **Class analysis** | Your results vs. the state, in your browser, nothing uploaded *(Phase 2)* |

## What this is not

**It does not reproduce the questions.** Not an oversight, and not a licensing worry — a
deliberate decision, because it cannot be done honestly from these files. Every number,
variable, expression and figure in the NYSED released-items PDFs is vector artwork with no text
layer: it does not extract at all. A transcription would be either hand-typed for ~420 items or
silently wrong, and a *partly* wrong question is worse than no question. So each item links to
the exact page of the official PDF instead, and the site is an index into NYSED's own documents
rather than a copy of them. `tools/preflight.py` refuses to publish any field that looks like
item text, so this cannot quietly change.

**Not official.** Every curriculum alignment is a judgement call by one teacher, not guidance
from NYSED or Imagine Learning. Where a placement is genuinely uncertain, it says so.
Corrections and disagreement are welcome.

---

## Publishing changes

```bash
cd ~/Desktop/ClaudeProjects/MathAlign68 && python3 publish.py && python3 tools/preflight.py && netlify deploy --dir=site --prod
```

`preflight.py` runs every check before anything goes live and **stops the deploy if any fails** —
the `&&` means a failure prevents the upload. Drop `--prod` for a private draft URL. Then
hard-refresh (Cmd+Shift+R): Netlify updates instantly but browsers cache.

Each check in it exists because something like it went wrong once. Add to it whenever something
slips through.

---

## Layout

```
data/
  items.json           GENERATED item map. Regenerable from sources/. Never hand-edit.
  alignment.json       THE HAND-EDITED FILE — curriculum judgement, one entry per standard
  blueprint.json       Hand-authored NYSED test design, domain ranges, post-test tables
  standards.json       GENERATED standards registry, built from the educator guide
  im_ms_reference.json IM 6-8 units, sections, lessons; standard-to-lesson table   [Phase 3]

sources/               NYSED released-items PDFs and the educator guide (committed)
tools/                 the pipeline and the tests — see below
build/ + templates/    the site generator; publish.py is a thin entry point
site/                  GENERATED — deploy this whole folder
provenance/            audit trail; read by no build step
fixtures/              golden files for the extractor tests
```

**Two files in `data/` are hand-edited and two are generated, and the split is the point.**
`items.json` is machine-extracted fact: preflight re-runs the extractor and fails if the file on
disk differs, so nobody can hand-patch it and have the patch survive unnoticed. `alignment.json`
is human judgement and no script ever writes it. RegentsAlign mixes both in one hand-edited
file, which is exactly why re-extraction there would clobber hand edits and therefore never
runs.

## The pipeline

```bash
python3 tools/fetch_sources.py            # the 12 released-items PDFs + the educator guide
python3 tools/extract_standards.py        # -> data/standards.json
python3 tools/extract_item_map.py <pdf>   # -> provenance/itemmap_<testId>.json
python3 tools/build_pagemap.py <pdf>      # -> provenance/pagemap_<testId>.json
python3 tools/build_items.py              # -> data/items.json
python3 tools/compute_alignment.py        # applies data/alignment.json          [Phase 3]
python3 publish.py && python3 tools/preflight.py
```

Everything except `alignment.json` is reproducible from `sources/` with no human step.

`python3 tools/test_extractor.py` runs 169 checks over all fourteen extractions, and
`python3 tools/preflight.py` runs 53 more against the built site. Two of them are worth knowing
about because they are the reason the rest can be trusted:

- **Every answer key is re-derived by a second, unrelated method.** Preflight re-reads each PDF
  in plain reading order with no geometry at all and compares. 282 keys, two independent code
  paths, no disagreement.
- **The test suite proves it can fail.** The extractor assigns words to columns by centre x
  because two columns are centre-aligned, and that is exactly the subtlety a later refactor
  "simplifies" away. So the suite re-runs the extraction with left-edge x and asserts it breaks.
  If that ever stops breaking, the suite has stopped testing column assignment.

## Three things to know before trusting the data

**The item map is the whole dataset, and it is a real table.** The last page or two of each
released-items PDF is NYSED's *Map to the Standards*: per released item, its type, answer key,
credits, primary standard, cluster, subscore, secondary standards, and the statewide P-value.
That is where every field in `items.json` comes from. It has a genuine text layer and parses
reliably — unlike the questions themselves.

**Reading that table needs geometry, not string splitting.** The Key column is empty on
constructed-response rows, so splitting on whitespace shifts credits into the key column and
produces a plausible-looking, wrong dataset. Column positions also move between years and
grades (the Standard column's left edge is 220.7 on 2026 grade 7, 213.5 on 2026 grade 6, 192.1
on 2023 grade 6), Cluster and Subscore are centre-aligned rather than left-aligned, and a single
logical row spans up to three text baselines — the P-value sits 1–2pt below its own row against
a ~10pt row pitch, which makes a naive parse look as though the P-values are missing entirely.
So the extractor derives its column boundaries from each page's own header row, assigns words by
centre x, and bands rows on the item number. `tools/test_extractor.py` includes a test that
re-runs the assignment with left-edge x and asserts the checks *do* fail, because that
distinction is exactly what a future refactor breaks silently.

**Post-test standards are normal here, not anomalies.** Each grade's test assesses some
standards from the *previous* grade — the guide's own key reads "X = Standards designated for
instruction in May-to-June", so they are taught after their own grade's test is given. Grade 6
never tests Statistics and Probability as grade-6 content; grade 7 tests it. Grade 8 assesses
five grade 7 Geometry standards. `standards.json` reads this from two independent places in the
educator guide and fails the build if they disagree.

---

## Scope, and why it stops where it does

**2023–2026, grades 6–8.** Twelve tests. That is the complete Next Generation standards era:
those maps use `NY-7.EE.4a`-shaped codes, while 2016–2022 use the older CCLS shape
(`7.RP.A.1`). Keeping to one code family means no crosswalk and no silently mismatched
standards. The older tests are available upstream and the extractor already handles their
two-page map layout, but they are not published here.

Standard codes here are **not** the same family as RegentsAlign's. These are
`NY-<grade>.<DOMAIN>.<number><letter>` — grade digit first, no cluster letter. RegentsAlign's
are `AI-<DOMAIN>.<number>`. Neither project reads the other; the boundary is that a code
starting `AI-` is RegentsAlign's and a code starting with a grade digit is this project's.

## The corpus

Released items per test, as extracted:

| | 2023 | 2024 | 2025 | 2026 | total |
|---|---|---|---|---|---|
| Grade 6 | 29 | 29 | 29 | 39 | 126 |
| Grade 7 | 31 | 31 | 31 | 42 | 135 |
| Grade 8 | 31 | 31 | 31 | 42 | 135 |

**396 items across 12 tests**, carrying 489 credits. RegentsAlign is 280 across 7.

Every count was produced twice by independent methods — the geometry parser and a plain-text
count of the type strings — and they agree. Don't replace them with a quick count of standard
codes on the map page: that runs 3–4 high per test, because a secondary-standard citation looks
like an item row.

Two things to read carefully. **2026 released noticeably more than 2023–2025** (39–42 per test
against 29–31), so read any coverage or trend figure per year rather than pooled. And
**2023–2025 released all ten constructed-response items while 2026 released only eight** —
NYSED's stated policy of releasing every scored constructed-response question does not hold for
2026.

There is deliberately **no "percentage of the test released" figure** anywhere in this project.
NYSED's promise is "at least 75 percent of the test questions that counted toward students'
scores", so the denominator is *scored* items — and the designed item counts include embedded
field-test questions that don't count and whose number NYSED doesn't publish. Dividing released
items by designed items gives 63–65% for 2023–2025, which looks like NYSED breaking its own
promise and is just the wrong denominator.

## Status

| | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|
| Grade 6 | ✓ | ✓ | ✓ | ✓ |
| Grade 7 | ✓ | ✓ | ✓ | ✓ |
| Grade 8 | ✓ | ✓ | ✓ | ✓ |

✓ = item map extracted, validated, and published to the site. Curriculum alignment is Phase 3.

**Phases 0 and 1 are complete.** Sources fetched with a hash manifest; standards registry built
from the educator guide and cross-validated against all 420 standard citations in the twelve
item maps; test blueprint authored with its counts confirmed twice; all twelve maps extracted,
plus the two CCLS-era 2022 maps kept as regression coverage; 387 of 396 items deep-linked to
their exact PDF page; the five-tab site built and passing a 53-check deploy gate.

Next is Phase 2 — the class-results analyzer, which is the part your colleagues will actually
use, and which needs no curriculum data. See `RESUME.md`.
