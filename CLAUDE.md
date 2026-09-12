# Working in MathAlign68

Read `README.md` first for what this project is. This file is about how to work in it.

`~/Desktop/ClaudeProjects/RELATIONSHIPS.md` is the authoritative description of how this
project relates to RegentsAlign, AlgebraTeaching and TeachingBrain. If a relationship changes,
fix it there first, then update the pointer here.

The path is absolute on purpose. This repository actually lives at
`~/Developer/ClaudeProjects/MathAlign68` and is symlinked into the Desktop hub, so a relative
`../RELATIONSHIPS.md` resolves to `~/Developer/ClaudeProjects/`, where the file does not exist.

## The one rule that matters most

**`data/alignment.json` is the only file in `data/` a person edits.**

`data/items.json` and `data/standards.json` are generated. `preflight.py` re-runs the extractors
and fails the deploy if what is on disk differs from what the sources produce, so a hand edit to
either one will be caught rather than silently published. If a generated value is wrong, fix the
extractor or fix `data/blueprint.json` — never the output.

`data/blueprint.json` is hand-authored but holds only published NYSED facts. Adding an inference
to it defeats its purpose: `preflight.py` reads its counts *instead of* holding literals, so
anything wrong in there is wrong everywhere with no second opinion.

## Do not publish unreviewed item text

This began as a rule against publishing item text at all, because the stems do not extract and
anything automatic would be either hand-typed or quietly wrong. That reasoning was about
publishing *extraction output* as if it were the question, and it still holds.

Reviewed transcription is a different thing, and the replacement rule is stricter. Content
reaches the site only from `data/content.json`, which `tools/merge_content.py` writes from a
reviewed spec and stamps `reviewed: true`; `build/payload.py` refuses a payload containing a stem
that arrived any other way. Then `preflight.py` checks the result three ways: every published
stem's prose must be character-identical to the PDF's text layer, every hole the extractor
located must be filled, and every answer must agree with an independent source — NYSED's item
map for multiple choice, its exemplary-response page for constructed response.

**Never hand-edit a stem to tidy it up.** The prose-fidelity check is what makes this data worth
trusting, and editing the wording breaks it. If a stem is wrong, fix the extractor. If it is
merely ugly, record it in the spec's `reviewNotes` and leave it visible.

## Adding a test

Use the `mathalign-ingest-test` skill. In brief:

```bash
python3 tools/fetch_sources.py --grade 7 --year 2026
python3 tools/extract_item_map.py sources/2026-released-items-math-g7.pdf --grade 7 --year 2026
python3 tools/build_pagemap.py  sources/2026-released-items-math-g7.pdf --grade 7 --year 2026
python3 tools/build_items.py
python3 publish.py && python3 tools/preflight.py
```

Then record the released-item count in `data/blueprint.json` and **confirm it by opening the
PDF**, because that number is what every later count check is measured against. Never copy it
from a count you did not verify: an early rough count of these maps came out 3–4 items high per
test because secondary-standard citations look like item rows.

## Aligning an item to the curriculum

Use `tools/alignment_packet.py <standard>`, which assembles the items on a
standard beside the lessons worth reading. `data/alignment.json` is the only file
in `data/` a person edits, and `alignment.json.conventions` is the project's
alignment prompt: read it before writing an entry, and let it take precedence
over your own instinct about a placement.

**Alignment is per item, not per standard.** This reverses what this file used to
say. The old rule existed because there were no stems -- "with no item stem there
is no item-specific evidence to judge on" -- and that stopped being true when 387
of 396 items became reviewed transcriptions. Two items on one standard routinely
ask different things: of the three grade 8 items citing `NY-7.G.4`, one asks for
an area from a diameter and another for a radius from a circumference, and they
belong at different lessons.

**Evidence or nothing.** A lesson is recorded only when a specific activity can
be named, paged and quoted. Topical similarity is not evidence, and `preflight.py`
refuses an evidence entry without an activity and a page. If nothing in the
searched lessons asks what the item asks, the entry is `no-lesson-found` -- a
finding about the curriculum, not a failure.

**Do not treat the standard-to-lesson table as the search space.**
`provenance/alignment_baseline_measurement.md` measures it against NYCPS's
independent citations: it names the right unit 96.3% of the time and the right
lesson only 77.4%. Use it to pick the unit, then read the lessons. Deferring to
that table against your own reading is the documented cause of RegentsAlign's 26
placement errors.

Resolve lessons **by title, never by number**. Editions renumber; titles do not.
Preflight checks the number and the title as a pair, because a citation whose
number and title disagree is the exact shape an edition renumbering leaves behind.

Every entry is written `draft: true`. `build/payload.py` drops drafted entries
before they reach the site, so an unreviewed judgement cannot claim anything.
Clearing the flag is the act of review and is done by a person against the cited
activity.

Have a second pass **re-derive** the placement from the lessons rather than
review the first pass's prose. Reviewing prose finds typos; re-deriving finds
wrong answers.

## Privacy

This repository contains no student data and never will. Class results live only in the
teacher's own browser: `site/analyze/` reads the dropped file locally, fetches nothing but
`../data.json`, and uploads nothing. Carry these invariants forward without weakening them:

- Locate the question grid first, and never read a column to the left of it. **One exception,
  and it is narrow:** a column headed exactly `Class` is read for section codes, because the
  per-section view is the most actionable thing the analyser produces -- on the one real export
  in hand, an item that reads as a 0.18 cohort-wide gap is 0.65 / 0.48 / 0.37 / 0.11 by room.
  Three guards make it mechanical rather than a judgement: the header must be exactly `Class`,
  the index must not be 0 (column 0 is where the name lives, and no header spelling may unlock
  it), and every value must be short, comma-free and not name-shaped. Then the inherited
  uniqueness guard discards the column anyway if its codes are mostly unique, because a code
  appearing once per row is a per-student identifier.
- The name column is never read at all. The warning that a file still has names in it is raised
  by counting **distinct** name-shaped values, not occurrences: a redacted export repeats one
  placeholder down that column, and warning every time trains a teacher to click past the
  warning that matters.
- In a long-form export, the student column is read only to group rows, and its values are
  replaced with an opaque row index before anything else sees them. *(No such export has been
  seen yet; the ISA is wide-form. `provenance/isa_format.md` records the format that exists.)*
- `assertNoIdentity()` walks the finished report and throws on anything name-shaped. It skips
  the fields that carry NYSED's own item text, or a word problem's characters would read as a
  roster.
- `preflight.py` scans `site/` for OSIS-shaped digit runs and `SURNAME, FORENAME` patterns, and
  strips code comments before scanning so that prose *about* privacy is not mistaken for a breach.
  It also checks that the analyse page has no `<script src>` at all, fetches nothing but
  `../data.json`, and actually *calls* `assertNoIdentity` -- checking for the bare name passed
  on a deliberately renamed function, because the new name contained the old one.

If you ever find yourself adding a `.gitignore` rule to keep student data out of this repo,
something has been put in the wrong folder. Move it.

## Working on the analyser

`provenance/isa_format.md` is the spec: what a NYSED ISA export looks like, how it differs from
the ATS REDS export RegentsAlign parses, and the three figures a change must not move. Read it
before touching `templates/analyze/`.

- `templates/analyze/` is the source; `site/analyze/` is generated by `publish.py` and a direct
  edit there is lost on the next build. Preflight rebuilds the page and compares.
- The page may load **nothing** from another origin, which is why `templates/analyze/xlsx.js`
  exists rather than a vendored SheetJS. `xlsx` stays in devDependencies for one reason: the
  engine suite reads each fixture both ways and asserts the grids match.
- `fixtures/*.xlsx` are generated by `tools/make_isa_fixture.js` and are synthetic on purpose.
  A real export holds real students' real response patterns, which is student data whatever the
  name column says. To re-check against a real file, set `MATHALIGN_ISA` and run the engine
  suite; it skips without it.
- `npm test` needs `npm install` once.

## Tooling notes

- `data/im_ms_lessons_detail.json` holds the 427 lessons' actual task statements,
  rebuilt by `tools/extract_im_ms_lesson_detail.py` from the per-unit teacher
  guides. Both are gitignored -- the guides for their size, the index because it
  reproduces licensed text -- so neither survives a fresh clone, and the build
  never reads either. Run `tools/validate_im_ms_lesson_detail.py` after a rebuild.
- **poppler is not installed on this machine.** No `pdftotext`, `pdfinfo` or `pdftoppm`, which
  also means the Read tool cannot render a PDF page here. Use PyMuPDF (`import fitz`), which is
  available to system python3.9.
- Parse the item map with `page.get_text("words")` and geometry. See README's "Reading that table
  needs geometry" section for the four specific reasons string splitting fails.
- The engine tests need one package: `npm install` in this folder, once.
- `python3 tools/preview.py` serves `site/` locally so the page can actually be looked at.

## House conventions carried over from RegentsAlign

- One canonical source of truth per kind of data; everything in `site/` is generated and direct
  edits are lost on the next build.
- Human judgement lives in a spec file, not in code, so the code is identical for every test.
- Every check in `preflight.py` exists because something went wrong once. Say which, in a comment.
- Cross-implementation agreement is tested, not assumed — two independent extraction paths
  agreeing is the only reason to trust a parse.
- Write down *why*, not just what. A comment explaining which past failure a rule prevents is
  worth more than one restating the code.
