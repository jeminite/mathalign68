# What a NYSED ISA export actually looks like

Written 2026-09-12, from the first real one this project has seen:
*NYS ISA Student Responses Gr 6 Math.xlsx*, a grade 6 export covering 78 students
in four sections. The file itself is **not** in this repository and never will be
-- see "Why the fixture is synthetic" at the end.

`RESUME.md` open question 3 asked which results export colleagues would actually
have, and said the analyzer should not be built until somebody looked at one
rather than guessing at four layouts. This is that look.

## The layout

One sheet. One header row, then one row per student. No banner rows, no merged
cells, no key row.

| Columns | Content |
|---|---|
| A | `Student Name` -- **never read** |
| B | `Class` -- section codes, here `6A1`-`6A4` at 23 / 27 / 19 / 9 students |
| C-F | `MC%`, `CR%`, `NYS Math`, `Math Lv` -- the school's own computed figures |
| G-AK | 33 multiple-choice items, header `Q1 (6.RP.2)`, cell = the letter chosen |
| AL-AS | 6 constructed-response items, header `Q38 (6.EE.2b)`, cell = points earned |

Four things about it decide how the analyzer is built.

**1. There is no answer key in the file.** A multiple-choice cell holds the letter
the student chose whether that letter was right or wrong. Nothing in the workbook
says which letter was correct. Scoring is possible *only* by joining to `key` in
`data.json`.

This is the exact inverse of the ATS REDS export that RegentsAlign's analyzer
reads, where a correct answer is written as a dash and the option number is
recorded only when the student was wrong. RegentsAlign's `findKeyRow` looks for a
row of `1-4` beneath the question numbers and errors out when it finds none, so
that function does not survive the crossing. What the ISA gives up in
self-sufficiency it repays in the next section: a chosen letter is a distractor
observation, and REDS-style "correct or not" is not.

**2. The headers identify the test on their own.** Each header carries the item
number and the standard it assesses. Scoring those 39 `(item -> standard)` pairs
against all twelve published tests:

| test | agree / 39 |
|---|---|
| g6-2023 | 1 |
| g6-2024 | 1 |
| g6-2025 | 2 |
| **g6-2026** | **39** |
| g7-2023 | 0 |
| g7-2024 | 0 |
| g7-2025 | 0 |
| g7-2026 | 0 |
| g8-2023 | 0 |
| g8-2024 | 0 |
| g8-2025 | 0 |
| g8-2026 | 0 |

39 against a runner-up of 2. The teacher never has to be asked which test this
is, and more to the point is never given the chance to answer wrongly. The
margin is wide enough that `identifyTest` can demand a decisive winner and refuse
rather than guess -- an ISA from a test this project has not published should
produce a legible refusal, not a confident join against the nearest neighbour.

**3. Standards are written bare.** `6.RP.2`, not `NY-6.RP.2`. One normalisation
step on the way in. Note `Q42 (5.OA.3)` -- a prior-grade post-test standard, which
normalises to `NY-5.OA.3` and is present in the payload like any other.

**4. Only released items appear.** The question numbers skip 7, 13, 18, 25, 36,
37 and 40. That set is *exactly* `tests[g6-2026].withheldItems`. The ISA reports
the operational items and is silent about the embedded field-test ones, which is
the same cut NYSED makes when it releases questions.

Two consequences. It is a free second identification signal. And it is an
independent corroboration of a list this project derived by a different route --
`withheldItems` comes from which items the released-items PDF does not contain,
and the ISA agrees item for item without having been consulted.

Do not build on the coincidence, though. A test where NYSED released less than it
reported back would put items in the ISA that `data.json` has no key or P-value
for. The analyzer counts matched and unmatched items and says so, rather than
assuming the sets are equal.

## What the join yields

Every one of the 39 items matched. Every multiple-choice item had a `key`, every
constructed-response item an `avgPointsEarned`, and the observed score ranges
agreed with `credits` throughout -- Q46 is a 3-credit item and its cells run 0-3,
the 2-credit items run 0-2, the 1-credit items 0-1.

Class P-value against NYSED's statewide figure, worst gaps first:

```
Q43  NY-6.G.1     0.09 vs 0.29   -0.20
Q23  NY-6.EE.8    0.46 vs 0.64   -0.18
Q9   NY-6.NS.1    0.46 vs 0.60   -0.14
```

These three numbers are the analyzer's end-to-end test. If a change makes the
page disagree with them, the change is wrong.

**The two P-values are not the same quantity.** For a constructed-response item
NYSED's figure is average points earned over points possible; for multiple choice
it is percent correct. `meta.pValueCaveat` says not to put them on one axis, and
the page does not. NYSED also does not publish the population its figure is
computed over, which is `RESUME.md` open question 1 and is stated on the page
beside the comparison rather than buried.

## The Class column, and the rule it bends

`CLAUDE.md` says to locate the question grid first and never read a column to the
left of it. Column B is to the left of it.

The exception is deliberate and narrow: a column is read as sections only when
its header is exactly `Class`, its index is not 0, and its values survive the
uniqueness guard RegentsAlign already carries -- a code appearing once per row is
a per-student identifier rather than a section, and one 2024 export used initials
plus year (`DC24`, `JF24`) in that position. Column A is never read whatever it
contains.

It earns the exception. Q23 whole-cohort is 0.46 against the state's 0.64, which
reads as a cohort-wide gap. By section it is 0.61 / 0.44 / 0.42 / 0.22 -- a spread
of 0.39, which is a different finding with a different response.

## Why the fixture is synthetic

`fixtures/isa_g6_2026_synthetic.xlsx` has this file's shape and invented
responses. The real workbook is not committed.

Its name column had already been redacted to the literal string `name` before it
reached this project, so no name was ever at risk. But 78 real students' real
response patterns are still student data, and `CLAUDE.md` is unconditional: this
repository contains no student data and never will. A fixture only needs the
shape.
