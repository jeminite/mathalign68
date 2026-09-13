# Things a person still needs to look at

Three files carry different jobs. `provenance/` explains **why** things are as
they are. `RESUME.md` says **where the work is up to**. This file lists what a
*person* must decide or check — open questions, not finished findings.

Nothing here blocks the deploy gate. That is the point: `preflight.py` catches
what a machine can catch, and everything below is what it cannot.

**Last reviewed 2026-09-13**, after grade 6's alignment, the analyzer rewiring
and the figure audit.

---

## 1. Alt text has never been audited — the largest open risk

152 figures, every one with alt text, median 15 words. `preflight.py` checks
three things about it: that it exists, that no two figures share the same
string, and (new) that it does not contradict its own `longDescription`. Nothing
checks whether it **describes the figure**.

The comparison that makes this urgent: the `longDescription` on the same 152
figures was checked the same three ways, and when 140 of them were finally read
against the artwork, **31.7% failed**. Alt text is the same surface, written by
the same hand, in the same sitting.

The self-consistency check caught one contradiction immediately — `g8-2025-027`'s
alt said "base radius" where the artwork labels a diameter.

**The method is known and cheap.** Every figure is a committed PNG under
`assets/`, named in its own `file` field. `provenance/figure_descriptions.md`
records the two waves, the verdict vocabulary and what the failures had in
common. Alt text is shorter than a long description, so this is a smaller job
than the audit that just finished.

## 2. Three figure descriptions still cannot be written

Each needs a value read off a drawing the audit did not resolve. All grade 7,
all `insufficient`:

| item | what is missing |
|---|---|
| `g7-2023-016` | the two box endpoints (Q1 and Q3) for each class |
| `g7-2026-014` | the dot counts above 0, 1, 2, 3, 4 on Team B's plot |
| `g7-2026-027` | the coordinates of Q, R and S — above all, which point sits at x = 1 apple |

The crops are at `assets/G7-2023/q16.png`, `assets/G7-2026/q14.png`,
`assets/G7-2026/q27.png`.

## 3. Published data that is still wrong

- **`g7-2026-026`'s stem.** Needs the tall delimiters clustered and hand-labelled;
  raising the height cap fixed its target and silently emptied another item's four
  answer choices. `provenance/tall_delimiters.md` has the geometry and the
  nine-item corpus diff.
- **Radical overbars publish as repeating-decimal marks** in 14 grade 8 items —
  `√50` reads as `√5-repeating0-repeating`. `provenance/radical_markup.md`.
- **Two activity names publish with a drawn symbol missing**: `Using` is *Using π*
  (7.3.4), `Does Plus Equal ?` is *Does a² + b² Equal c²?* (8.7.7). Deliberate —
  a citation must quote what the index stores or the gate cannot resolve it. See
  `provenance/lesson_index_glyph_loss.md` for the font-size-aware technique that
  recovers such symbols when a placement turns on one.

## 4. Judgements a teacher should confirm

- **Three contested placements**, where the settlers and a blind re-test disagree
  and both readings are recorded: `g8-2023-043`, `g8-2026-020`, `g8-2026-025`.
  Each carries `contested: true`.
- **Nine placements rest on optional work** — `g8-2024-010` plus eight in grade 6
  (`g6-2023-024`, `g6-2023-044`, `g6-2023-045`, `g6-2025-017`, `g6-2025-021`,
  `g6-2026-019`, `g6-2026-032`, `g6-2026-046`). Each names its non-optional
  runner-up. A class following the pacing table's skips has never met the tested
  form of these questions.
- **58 standards place their items at more than one lesson.** Expected —
  alignment is per item — but it is also what drift looks like. The gate prints
  the list every run.
- **15 entries sit outside every unit the guide tables for their standard.**
  Three are `candidates-only` entries with `unit: null` tripping the report as
  noise; the real set is 12. Deliberate, but these are the first to check if a
  placement is ever questioned.
- **Three cited standards have no counterpart in `standards.json`**:
  `NY-6.SP.7a`, `NY-8.EE.8c`, `NY-8.SP.4`. The last is understood (removed under
  NGMLS, and the guide's table was never regenerated). The other two want a look.

## 5. Two permanent categories, not backlog

- **Nine `candidates-only` items sit on image-only PDF pages.** The released PDFs
  carry pages with no text layer, so `build_pagemap.py` will not place an item
  there and the prose-fidelity rule cannot be satisfied. Closing this means OCR
  plus a human proofread, or relaxing the rule that makes every transcription
  worth trusting. **A decision, not a task.**
- **Two `NY-5.OA.3` items are `no-lesson-found`** (`g6-2025-033`, `g6-2026-042`).
  It is a grade 5 standard, there is no grade 5 curriculum in this repository,
  and the home-grade rule has no grade to search. Both blind readings reached
  this independently. NYCPS also had to leave grade 6 to place it.

## 6. Data with no independent check

- **`data/glyphs.json`** — 441 clusters, 174 labelled by hand, 267 unlabelled, and
  no regenerability check. A *missing* label fails loudly; a *wrong* one decodes
  silently wrong, and prose fidelity cannot catch it because it strips the decoded
  mathematics before comparing. Two near-misses are on record.
- **`data/content.json`** has no regenerability check, unlike `data/items.json`
  where `build_items.py --check` makes a hand patch impossible to hide. Its own
  meta says not to hand-edit it; nothing enforces that.
- **`meta.reviewNotes` is populated for exactly one test of twelve.** Whether that
  means "reviewed, nothing to note" or "not reviewed" is a question only the
  author can answer, and it changes how much the other eleven can be trusted.
- **No placement has ever been checked against whether students who were taught
  that lesson did better on that item.** 385 items carry a judged placement, each
  with a named activity and page, and the blind second pass is good evidence the
  *method* works — grade 8 agreed with itself 55.6% of the time, grade 6 settled 18
  disagreements. But that measures two readings against each other, not either
  against reality. The only real test is next year's performance on the exact
  standard, which is the same once-a-year signal AlgebraTeaching's gaps register
  calls `verified`. Worth looking back at in 2027 planning.
- **Nor has any credit target.** MS343Teaching tells a student they need six more
  credits, off a curve recovered from one year's conversion. Nothing checks a year
  later whether they got them.

## 7. Smaller things a maintainer would trip over

- `README.md` still tells a first-time reader that grades 6 and 8 are "not
  started", and its `data/` layout block documents five of the nine files —
  omitting `content.json` (634 KB, hand-owned) and `glyphs.json` entirely.
- The phase table in `RESUME.md` uses the number 4 for two different phases and
  runs 0, 1a–c, 2, 3, 4, 5, 3a, 3b, 3c, 4. It wants renumbering.
- `g7-2024-015` has `choicesInImage: false` while its crop shows choice A.
- `g7-2025-002`'s `choices` array is stored A, C, B, D — the two-by-two visual
  order, not alphabetical. The `label` fields are right; confirm nothing
  downstream indexes that array positionally.
- Figure `type` labels are not normalised: `Data Table`/`Data Tables`,
  `Box Plot`/`Box Plots`, `Dot Plot`/`Dot Plots`. Nothing keys off `type` today
  except the new answer-choice rule, which matches on a substring.
- `tools/test_engine.js`'s only end-to-end check against a **real** ISA export
  skips unless `MATHALIGN_ISA` is set, so it never runs on the gate.
- **And when it is set, three of its checks fail — today, and for a reason nobody
  has looked at.** `MATHALIGN_ISA=<the grade 6 2026 export> node tools/test_engine.js`
  reports 3 of 125 failed: Unit 6 carries 8 gating credits where 11 is pinned,
  weeks 21–29 carry 13 where 17 is pinned, and `NY-6.G.5` is no longer in
  `placement.unplaced`. All three have the same cause and it is the *good* kind:
  grade 6's judged alignment landed, the judged placement replaced the
  standard-to-lesson table, and `NY-6.G.5`'s item 22 moved to Unit 1 Lesson 17
  *Squares and Cubes*. The fixture-based checkpoint test WAS rewritten for exactly
  this (its comment says so — "it no longer works as a fixture"); the real-ISA
  pins beside it were missed. So these are stale expectations rather than a
  regression, and re-deriving them means confirming the three new numbers by hand
  rather than pasting in what the run prints. **Verified identical before and
  after the September 2026 placement change**, so nothing in that work caused
  them. The reason this sat unnoticed is the bullet above: the gate never runs
  this path.
- **`/analyze/` is live and has never been opened by a human.** It passes 57 render
  checks, two of which are the nearest automated substitute — every class it uses is
  styled, and the print rules cover the checkpoint sheet — but "every class is
  styled" is not "it looks right". Everything reachable from a shell checks out:
  extension 1.0.93 in Chrome Profile 4, that profile signed in as the matching
  account, the native host registered at `~/.claude/chrome/chrome-native-host` and
  executable, the extension ID allow-listed. Restarting Chrome fixed one real thing
  — the process had been up ten days running 1.0.90 with three newer versions
  unloaded on disk. What remains is inside the extension UI: site permission for
  `localhost`, and a claude.ai login in that profile. Check in particular that a
  checkpoint prints one page per unit with the answer key last; a sheet that prints
  badly will not get used.

## 8. Curriculum findings — not defects, and not backlog

These belong in a teaching document rather than an open-items list. Collecting
them is the next piece of work after the alt-text audit.

- **No required grade 8 Unit 2 activity dilates about the origin**, yet every
  NYSED dilation item does. Those items sit at p = 0.34–0.42.
- **Grade 6 never asks for a part-to-total ratio**; two items ask exactly that.
- **Combining like terms lives only in an optional grade 6 lesson** (U6 L11);
  three items need it.
- **No grade 6 activity asks for a perimeter expression with a variable** —
  including `g6-2023-040`, the hardest item on any of these tests at p = 0.13.
- **The decimal test for irrationality is teacher-facing only** (8.7.17's
  synthesis and summary, never a student task); three grade 8 items are built on
  it.
- **No grade 8 Unit 5 activity compares an equation to a table**, which
  `g8-2025-041` (p = 0.23) needs.
- **Finding the whole from a non-benchmark percent is barely taught** in grade 6.

These were derived from grades 6 and 8. **The equivalent sweep for grade 7 has
never been done** and is cheap now that all three grades are aligned.

## 9. Phases never started

- **National IM 6–8 alignment from the public tables** — `RESUME.md` marks it
  "after 2" and Phase 2 finished long ago. Only two national-edition unit guides
  are on disk, so the corpus for it is fragmentary.
- **The CCLS-era archive (2016–2022)** stays deferred. `fetch_sources.py` already
  encodes the shape of that archive — the URL split at 2023, the one-off 2017
  grade 7 filename, that 2020 does not exist and 2021 has no scoring materials.
  One open fact: **`sources/ccls/` holds 2022 grade 6 and grade 7 but no grade 8**,
  and nothing records whether that test exists upstream or was skipped.
- **2027** needs one number changed in `fetch_sources.py` and three new
  `blueprint.json` entries. Nothing else appears year-hardcoded.

## Two working habits this project paid for

Both were caught by looking at a result and disbelieving it, and both instruments
were wrong in the direction that flattered the conclusion being tested.

- **A blind test of grade 8's settlement fed the first pass a strawman.** It took
  each entry's `evidence[0]`, which is usually the *introduces* citation at a
  different lesson than the primary, and paired it with the primary lesson —
  making the first pass appear to cite activities from the wrong lesson in 12 of
  18 items. Thrown away and re-run.
- **The citation checker reported page offsets of −59.** Every one was the quote
  appearing in the unit's front matter, because the checker took the *first* page
  containing it rather than the nearest.

A third, from the figure audit: **arithmetic alone would have passed three of the
nine `wrong` descriptions**, and every failure in the second wave existed only
because somebody looked at the picture. When a check and a reading disagree,
find out which is wrong before trusting either.
