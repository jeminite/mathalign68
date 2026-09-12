# MathAlign68

**Every released question on the NYS Grades 6, 7 and 8 mathematics tests since the Next
Generation standards took effect — mapped to the standards, to statewide difficulty, and to the
Imagine IM 6–8 curriculum.**

Live at **<https://mathalign68.netlify.app/>**

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
Drop your school's ISA export on the analyse page. It works out which test it is from the file
itself, runs entirely in your browser, and compares your class to the state item by item. Your
file is never uploaded, and the student-name column is never read.

## What you get

| | |
|---|---|
| **Item map** | Every released item 2023–2026, grades 6–8: type, key, credits, standard, cluster, secondary standards |
| **Statewide difficulty** | NYSED's published P-value per item, and average points earned per constructed-response item |
| **Blueprint** | Tested weight by domain against NYSED's own published percent ranges |
| **Post-test standards** | Which prior-grade standards each test assesses, and where they sit in the curriculum |
| **The questions** | Stem, answer choices, figures and constructed-response answers, where transcribed |
| **Curriculum alignment** | Unit, section and lesson in Imagine IM 6–8 *(Phase 3)* |
| **Class analysis** | Your results vs. the state, in your browser, nothing uploaded |

**Corrections and disagreement are welcome.** There's a form on the *About & corrections* tab;
submissions arrive through Netlify Forms. That tab also lists what is already known to be wrong,
so nobody spends their time reporting a problem that's already recorded.

## What this is not

**A shown question is a transcription, not a scan — and the PDF is the authority.** Every
number, variable, expression and figure in the NYSED PDFs is vector artwork with no text layer.
The prose, though, *is* text and extracts exactly, so a stem is a template with holes and only
the holes need filling. That is what makes this checkable rather than merely plausible: strip
the markup and the reconstructed mathematics out of a published stem and what remains is
character-identical to the PDF's own text layer, which `tools/preflight.py` verifies on every
deploy. The mathematics is decoded from vector glyph geometry against a hand-labelled table, so
an unrecognised shape stops the build instead of guessing.

Reconstructed mathematics can still be wrong. Every item therefore links to the exact page of
the official PDF, and that page is the authority. Where an item has not been transcribed there
is no question text at all — just the link.

**Not official.** Every curriculum alignment is a judgement call by one teacher, not guidance
from NYSED or Imagine Learning. Where a placement is genuinely uncertain, it says so.
Corrections and disagreement are welcome.

---

## Publishing changes

**Check which site is linked first. Every time.**

```bash
cd ~/Desktop/ClaudeProjects/MathAlign68
netlify status | grep 'Current project'      # must say: mathalign68
```

This is not a formality. The Netlify CLI keeps one linked project per directory, and
`~/Developer/ClaudeProjects/RegentsAlign` is linked to `regentsalign` — a live site other
teachers use. A deploy run from the wrong directory, or from a checkout that has lost its
`.netlify/state.json`, would overwrite it. The two project ids are:

| project | id |
|---|---|
| mathalign68 | `04752dc2-50fa-4a6f-8482-6456070148c5` |
| regentsalign | `bcda36e2-84e6-4c75-96f8-1525d569ab69` |

### Two project settings that are not obvious, and were both wrong at first

The Netlify account has visitor SSO on by default, so a newly created project
gates **production** as well as previews and the live URL answers 401 to
everyone. RegentsAlign does not, because its `sso_login_context` is
`non_production`. MathAlign68 now matches it:

```bash
netlify api updateSite --data '{"site_id":"04752dc2-50fa-4a6f-8482-6456070148c5",
  "body":{"sso_login_context":"non_production"}}'
```

That is the setting worth keeping: preview and draft URLs stay private to the
account, which is what makes `netlify deploy` without `--prod` a safe way to
look a change over, while production is public.

Form detection is also off by default (`processing_settings.ignore_html_forms:
true`), so the correction form was deployed but collected nothing. It is on now,
and **the HTML is only re-scanned on a deploy** — so if the form ever stops
appearing under Forms in the dashboard, check that flag and redeploy:

```bash
netlify api listSiteForms --data '{"site_id":"04752dc2-50fa-4a6f-8482-6456070148c5"}'
```

Then:

```bash
python3 publish.py && python3 tools/preflight.py && netlify deploy --dir=site          # draft URL
python3 publish.py && python3 tools/preflight.py && netlify deploy --dir=site --prod   # live
```

`preflight.py` runs every check before anything goes live and **stops the deploy if any fails** —
the `&&` means a failure prevents the upload. Deploy without `--prod` first: it returns a private
draft URL, visible only while signed in to the Netlify account, which is the right place to look
a change over before other people see it. Then hard-refresh (Cmd+Shift+R): Netlify updates
instantly but browsers cache.

Each check in preflight exists because something like it went wrong once. Add to it whenever
something slips through.

---

## Layout

```
data/
  items.json           GENERATED item map. Regenerable from sources/. Never hand-edit.
  alignment.json       THE HAND-EDITED FILE — curriculum judgement, one entry per standard
  blueprint.json       Hand-authored NYSED test design, domain ranges, post-test tables
  standards.json       GENERATED standards registry, built from the educator guide
  im_ms_reference.json IM 6-8 units, sections, lessons; standard-to-lesson table   [Phase 3]

sources/               NYSED released-items PDFs and the educator guide (committed).
                       Imagine Learning's guides are NOT -- see provenance/imagine_guides.md
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
python3 publish.py && python3 tools/preflight.py
```

Everything except `alignment.json` is reproducible from `sources/` with no human step —
with one documented exception. `data/standards.json`'s 110 standard statements,
`data/im_ms_reference.json` and `data/im_ms_pacing.json` are built from Imagine Learning's
course guides, which are gitignored as licensed material. All three outputs are committed, so
a clone builds and deploys without them; what a clone cannot do is re-derive them, and
`preflight.py` skips those three regenerability checks with a reason rather than failing.
`provenance/imagine_guides.md` records their sha256 and what depends on them.

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
their exact PDF page; the site built and passing a 108-check deploy gate.

**Phase 2, the class-results analyzer, is built** — the part your colleagues will actually use.
Drop a NYSED *Item Student Analysis* export on `/analyze/` and it identifies the test from its
own headers, scores it against NYSED's answer key, and puts each item beside the statewide
P-value. `provenance/isa_format.md` documents the format and what it can be trusted for.

Next is the per-item curriculum alignment (`data/alignment.json`), which is what fills the
analyser's "Imagine IM" column. Grade 7 is placed and published; grades 8 and 6 are not
started, so for a grade 6 export — which is the only real ISA in hand — that column still
reads "not yet placed" for every item. See `RESUME.md`.
