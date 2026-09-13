# The raw-score-to-proficiency-level curve, recovered from an ISA export

Written 2026-09-12, from *NYS ISA Student Responses Gr 6 Math.xlsx* — grade 6, 2026, 78 students.
That file is not in this repository and never will be; see `isa_format.md`.

This is the spec for the analyser's `plCurve`, and for every "how many more credits?" claim the
site or any private counterpart makes. Read it before changing that code.

## What was found

The ISA carries two columns this project had no use for until now:

| Column | Header | Content |
|---|---|---|
| E | `NYS Math` | a decimal proficiency level — `1.94`, `3.00`, `4.42` |
| F | `Math Lv` | the integer level — `L1`, `L2`, `L3`, `L4` |

The decimal PL is **a collision-free, strictly increasing function of raw credits earned**. Across
78 students it takes 35 distinct raw values and **not one of them maps to two different PLs**.

That is not a correlation, it is a lookup table. So the conversion is not estimated from this
file, it is *recovered* from it, and every target can be stated in credits — the only unit a
student or a teacher can actually act on.

## The curve

The test is **46 credits** (31 multiple choice at 1 credit, 8 constructed response totalling 15).

| raw | PL | raw | PL | raw | PL | raw | PL | raw | PL |
|---|---|---|---|---|---|---|---|---|---|
| 4 | 1.34 | 14 | 1.98 | 24 | **3.00** | 31 | 3.42 | 39 | **4.00** |
| 6 | 1.53 | 16 | 2.18 | 25 | 3.03 | 32 | 3.48 | 41 | 4.12 |
| 7 | 1.62 | 17 | 2.29 | 26 | 3.10 | 33 | 3.55 | 42 | 4.24 |
| 8 | 1.68 | 19 | 2.47 | 27 | 3.16 | 34 | 3.61 | 44 | 4.36 |
| 9 | 1.74 | 20 | 2.59 | 28 | 3.23 | 35 | 3.71 | 45 | 4.42 |
| 10 | 1.79 | 21 | 2.71 | 29 | 3.29 | 38 | 3.97 | | |
| 11 | 1.85 | 22 | 2.82 | 30 | 3.35 | | | | |
| 12 | 1.89 | 23 | 2.94 | | | | | | |
| 13 | 1.94 | | | | | | | | |

Nine raw values are unobserved: **5, 15, 18, 36, 37, 40, 43, 46**. Nobody in this class scored
them, so the curve has holes and anything between two observed points is interpolation, not fact.
Say so wherever a figure depends on one.

## The cut points

| | raw of 46 | % of test | |
|---|---|---|---|
| Level 2 | 15 or 16 | 33–35% | **bracketed** — raw 14 is 1.98, raw 16 is 2.18, raw 15 unobserved |
| **Level 3 — proficient** | **24** | **52%** | **exact** — raw 24 is observed at precisely 3.00 |
| Level 4 | **39** | **85%** | **exact** — raw 39 is observed at precisely 4.00 |

The two that matter land exactly on observed points. That is luck, and it will not necessarily
repeat on another file, so `plCurve` must report whether each cut is observed or bracketed rather
than presenting all three with equal confidence.

## A credit is worth most just below proficiency

Mean PL gained per credit, measured between adjacent observed points:

| Band | PL per credit | segments |
|---|---|---|
| L1 (1.34–1.98) | 0.061 | 9 |
| **L2 (2.18–2.94)** | **0.112** | 6 |
| L3 (3.00–3.71) | 0.066 | 12 |
| L4 (4.00–4.42) | 0.075 | 4 |

A segment counts toward a band only when **both** endpoints sit inside it. A segment that crosses
a threshold belongs to neither: raw 23→24 is the credit that carries a student from 2.94 into
proficiency, and counting it as an L2 rate pulled L2 down by half a point. Likewise raw 38 (3.97)
is an L3 point, and an earlier pass that lumped it into L4 understated L4 as 0.066.

A credit is worth **roughly double** in the Level 2 band. Students sitting just below proficient
are the cheapest to move, by a wide margin. That is a targeting fact, not a reason to ignore
anyone else, and the page should present it as the former.

## The questions this was built to answer

| From | To | Credits needed |
|---|---|---|
| 3.5 | 4.0 | **7** (raw 32 → 39) |
| 2.75 | above 3.25 | **8** (raw 21 → 29) |
| 3.25 | above 3.25 | **1** (raw 28 → 29) |
| 1.75 | above 2.25 | **8** (raw 9 → 17) |
| 2.25 | above 2.25 | **1** (raw 16 → 17) |

**A band-level answer would be wrong for almost everyone in the band.** "2.75 to 3.25" spans 8
credits at the bottom and 1 at the top. Recommendations have to be per student; anything
aggregated to a band is a different and much weaker claim.

## Two things this proves on the way

**The withheld items do not score.** The designed test is 54 credits and 46 were released. If the
PL were computed over all 54, a student's released-raw of 24 could sit at several different total
raws and the PL column would collide. It never collides, across 35 distinct values. So the seven
items NYSED withheld are embedded field-test items that carry no credit — which the project had
previously only inferred from the fact that the ISA omits them.

This is adjacent to, but not the same as, `RESUME.md` open question 1 (what population the
statewide P-values are computed over). It settles the scoring denominator, not the P-value
denominator. Do not let the stronger claim follow from the weaker evidence.

## Why this is trustworthy: two independent paths agree

The curve above was recovered by **scoring 39 items against NYSED's answer key** and pairing each
student's credit total with the level in their ISA row.

The school's own roster workbook contains the same conversion by a completely different route: a
`RS` column and a `PR` column, both written by the reporting system, with no item-level scoring
anywhere in between. `MS343Teaching/tools/build_curves.js` recovers the curve from those.

**The two agree on all 35 shared raw scores**, and on where Level 3 begins (raw 24). Nothing is
shared between the paths but the truth: one reads the answer key and counts credits, the other
reads two numbers off a report. That agreement is the only reason to trust either, and it is worth
re-running whenever either side changes:

```bash
cd ../MS343Teaching && node tools/build_curves.js && node tools/test_curves.js
```

The roster workbooks also yield curves for **grades 5 and 7**, which this project cannot see —
grade 5 is outside its scope and no grade 7 ISA has arrived. Level 3 begins at a scale score of
**450 in all three grades**, which is what makes a cross-grade target possible at all: the raw
score is grade-specific, the scale score is not.

## What does not carry to another test

The curve is **this test's**. 2027's grade 6 test will have its own conversion, and a grade 5 PL
sits on grade 5's curve, which this project cannot see at all — MathAlign68 covers grades 6–8.

That is survivable because of where each number is used. A prior-year PL is only ever a *starting
point and a target-setter*; the credits are always counted on the curve of the test the student is
about to sit. "You were 3.5 last year; on a test like 2026's, 39 of 46 credits is a 4.0" is
honest. "You need exactly 7 more credits" is not — the conversion will move. Phrase every target
as approximate, on a test like this one.

Derive a fresh curve from every ISA that arrives. Never reuse this table for another grade or
year, and have `plCurve` refuse rather than guess when a file carries no PL column.

## Maintaining a 4 is harder than it sounds

Level 4 starts at **85% of the whole test**. A student sitting at exactly 4.00 leaves Level 4 by
losing a **single credit**, and a student at 4.42 is one credit off perfect and has nowhere to go.
Any report that treats "maintain a 4" as the easy case has it backwards.

AlgebraTeaching reached the same conclusion from the other end and made it a mandatory caution —
that the conversion is "punishing at the top", and that a cohort finishing near the ceiling will
look like it declined whatever it does. This curve is the grade 6 evidence for the same effect.

## The honesty constraint

This class averaged 48.7% — about 22 of 46 credits, just below the Level 3 cut. Closing the
**entire** gap to the state average of 54.8% is **+2.8 credits**, moving the average student from
roughly 2.82 to 3.10. Moving a mid-Level-2 student to solidly proficient takes about **8**.

**So closing the gap to the state does not move a band.** A report that ranks standards by state
gap and implies otherwise is misleading, and this sentence belongs on the page, not in a footnote.
