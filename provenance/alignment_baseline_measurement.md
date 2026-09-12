# Does the publisher's table predict where an item is actually taught?

Measured 2026-09-11, before a single alignment entry was written, because the
answer decides the design. Reproduce with `python3 tools/measure_nycps_agreement.py`.

## The question

The obvious way to align an item to a lesson is the way RegentsAlign did it: take
the item's standard, look it up in the publisher's *Lessons by Standard* table,
and pick the most apt lesson from the list it returns. That makes the returned
list the search space. Is the right answer actually in it?

## The check

NYCPS published its own item-by-item IM alignment for 2023–2025. For grades 6 and
7 its `Curriculum Notes` name a specific lesson and quote a parallel activity —
84 of 87 grade 6 rows and 93 of 93 grade 7 rows. It was written without reference
to this project, so it is a genuinely independent expert reading of the same
items. Grade 8's sheet carries no lesson citations at all and cannot be used.

Every citation is resolved **by title**, never by number, because NYCPS records
national unit numbers and this project uses the Imagine IM New York edition.

## Result

164 citations were comparable (same grade, resolvable title, standard present in
the table).

| | |
|---|---|
| NYCPS's lesson is **inside** the publisher's candidate set | **127 / 164 — 77.4%** |
| outside the set, but inside a unit the set names | 31 / 164 — 18.9% |
| in a unit the candidate set never mentions | 6 / 164 — 3.7% |
| **unit-level agreement** | **158 / 164 — 96.3%** |

## What this means

**The unit is reliable; the lesson list is not.** Imagine Learning's own table
gets the unit right 96% of the time and the lesson right 77% of the time. Nearly
one placement in five is a lesson that genuinely teaches the item's content but
that the table does not associate with the item's standard.

So the candidate list **must not be the search space**. If it were, roughly a
quarter of items would be placed at a defensible-but-not-best lesson, or not
placed at all — and nothing in the process would reveal it. That is precisely the
failure RegentsAlign's own consistency audit found and attributed to deferring to
the table: *"the aligning agent even flagged that Unit 2 Lessons 2–3 was the real
instructional match but deferred to the official list."*

**Design consequence.** Use the table to choose the *unit* (96% reliable), then
search **every lesson in that unit** by reading its actual Student Task
Statements. That is 11–22 lessons per unit, which the lesson-detail index makes
tractable. The table becomes a prior, not a filter.

The six cases where NYCPS names a unit the candidates never mention are three
standards repeated — `NY-6.RP.3a` (×3, NYCPS says 6.3.7 *More Rate Comparisons*),
`NY-6.EE.2b` (×2, 6.6.7 *Write Expressions with Variables*), and `NY-7.NS.3` (×1,
7.4.2). For these the search space has to widen past the unit, and each needs an
explicit decision rather than a default.

## A side result worth keeping

Ten grade 7 citations resolved to a unit number different from the one NYCPS
printed — every one of them the documented Units 7↔8 swap between the national
and New York editions (`7.8.8` → `7.7.8` *Keeping Track of All Possible
Outcomes*, and so on). They were resolved correctly with no correction table,
purely because the match was made on the title. This is the project's
resolve-by-title rule working on live data rather than being asserted.

## Limits

- Grade 8 is absent entirely: no lesson citations in its NYCPS sheet, and no
  per-unit Teacher Guides on disk.
- 2026 is absent: the NYCPS sheets stop at 2025, so 123 of the 396 items have no
  independent check of any kind.
- NYCPS's own `PROVENANCE.md` calls these notes *"suggestive, not authoritative"*
  and records that a row's citation sometimes disagrees with its own Section
  column. Agreement here is corroboration, not proof; disagreement is a prompt to
  look, not a verdict.

---

# Part 2 — narrowing the reading, and whether that loses the answer

Added 2026-09-11, after the grade 8 per-unit Teacher Guides arrived and the
lesson index was completed to all **427 lessons** across grades 6–8.

A reader cannot look at 140 lessons per item, so the reading has to be narrowed.
Narrowing can only do harm one way: by leaving out the lesson a reader would have
chosen, because no care taken afterwards recovers it. So the measured property is
**recall**, again against NYCPS's independent citations (n=160 with item text).
Reproduce with `python3 tools/measure_shortlist_recall.py`.

## What actually predicts the right lesson

Three signals, measured separately against the same 160-odd citations:

| signal | names NYCPS's lesson |
|---|---|
| course guide's *Lessons by Standard* table | 77.4% |
| **unit guide's own per-lesson `Addressing` tag** | **82.6%** |
| lexical similarity alone (tf-idf, first attempt) | 58.1% at k=8 |

The unit guide's tagging is both better than the course guide's table and from a
different document, so the two are taken as a union rather than either being
preferred. That union, ordered by BM25 over the lessons' actual task statements,
is what the shortlist is.

## Why lexical similarity alone fails

Worth writing down, because it is a property of test items rather than a bug.
Released items wrap the mathematics in an invented context, and the context words
are the most distinctive words in the item. A grade 6 percentage question about
students voting for a favourite hobby retrieved Unit 9's *How Do We Choose?*,
*More than Two Choices* and *Comparing Voting Systems* as its top three — lessons
about voting systems, matching every context word and none of the mathematics.
The correct lesson, *Solving Percentage Problems*, ranked 22nd.

This is the same trap a human skim falls into, which is the reason to record a
named activity as evidence rather than a similarity score.

## Recall after combining the signals

| | |
|---|---|
| recall@5 | 74.4% |
| recall@8 | 84.4% |
| **recall@12 (tier 1)** | **90.0%** |
| recall@20 | 93.1% |
| **tier 1 + every other lesson in the candidate units (tier 2)** | **97.5%** |

Tier 2 costs a median of 32 lessons to read against tier 1's 12, so it is not
read by default. It is read whenever tier 1 yields no evidence — precisely when
the alternative is recording *no lesson found*, the answer it would be worst to
reach without having looked.

## The four that neither tier reaches

- `NY-6.RP.3a` → 6.3.7 *More Rate Comparisons* (three items). Neither document
  tags that lesson with the standard and the wording does not overlap.
- `NY-7.NS.3` → 7.4.2 *Ratios and Rates With Fractions* (one item).

These are known-hard and are to be decided explicitly, not left to a default.

## Standing limits

Unchanged from Part 1, and they bound everything above: grade 8 has no NYCPS
lesson citations, so none of these recall figures are measured on grade 8; and
the NYCPS sheets stop at 2025, so the 123 items from 2026 have no independent
check of any kind.
