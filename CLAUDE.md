# Working in MathAlign68

Read `README.md` first for what this project is. This file is about how to work in it.

`../RELATIONSHIPS.md` (via the Desktop symlink) is the authoritative description of how this
project relates to RegentsAlign, AlgebraTeaching and TeachingBrain. If a relationship changes,
fix it there first, then update the pointer here.

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

## Aligning a standard to the curriculum

Use the `mathalign-align-standard` skill. Alignment is **per standard, not per item** — with no
item stem there is no item-specific evidence to judge on. Item-level overrides exist in
`alignment.json.byItem`, and each must name which signal justified it (credits, session, or a
secondary standard). Read `alignment.json.conventions` before writing an entry; it is the
project's alignment prompt and it takes precedence over your own instinct about a placement.

Resolve lessons **by title, never by number**. Editions renumber; titles do not. This is
RegentsAlign's hardest-won rule — it lost a week to a Unit 6 numbering offset — and it applies
here from the first entry rather than after the first mistake.

Have a second pass **re-derive** the placement from the standard-to-lesson table rather than
review the first pass's prose. Reviewing prose finds typos; re-deriving finds wrong answers.

## Privacy

This repository contains no student data and never will. Class results live only in the
teacher's own browser: `site/analyze/` reads the dropped file locally, fetches nothing but
`../data.json`, and uploads nothing. Carry these invariants forward without weakening them:

- Locate the question grid first, and never read a column to the left of it.
- In a long-form export, the student column is read only to group rows, and its values are
  replaced with an opaque row index before anything else sees them.
- `assertNoIdentity()` walks the finished report and throws on anything name-shaped.
- `preflight.py` scans `site/` for OSIS-shaped digit runs and `SURNAME, FORENAME` patterns, and
  strips code comments before scanning so that prose *about* privacy is not mistaken for a breach.

If you ever find yourself adding a `.gitignore` rule to keep student data out of this repo,
something has been put in the wrong folder. Move it.

## Tooling notes

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
