# Grade 8's second pass, and the test of the test

Grade 7's blind second pass compared 129 items and matched 85 — 65.9% — and
`CLAUDE.md` draws the project's calibration from it: two careful readings agree
on the exact lesson about two thirds of the time, so the unit is solid and the
lesson is an opinion.

Grade 8 does not repeat that pattern, and the difference is the point of this
note.

## The measurement

Four agents re-derived every grade 8 placement from the lesson text, without
sight of `data/alignment.json`, the alignment provenance, NYCPS's sheets, git
history, or each other's answers. All 135 placed, every quote machine-verified as
a literal substring of its activity, zero `no-lesson-found`.

```
compared: 135
     75   same primary lesson          55.6%
     50   same unit, different lesson
     10   different unit               unit agreement 92.6%
```

## Settling it, and why the result was not believed at first

Four settlers re-read the rival lessons for all sixty disagreements. The
verdicts: **50 to the second reading, 6 to a third lesson neither had named, 4 to
the first.**

That is not what two comparable readings produce. Grade 7's first pass won 28 of
its 44 disputes; grade 8's won 4 of 60. Two explanations fit equally well from
the outside:

1. the first pass really was systematically worse, or
2. the settlers anchored on the newer, more thoroughly evidenced reading — they
   saw each side labelled `firstPass` and `secondPass`.

So the settlement was **not applied** until that was tested.

## The first blind test was broken, and it broke in the flattering direction

The instrument took each first-pass entry's `evidence[0]` as its citation. But a
first-pass entry's evidence deliberately spans a RANGE of lessons — `introduces`
at one, `practises` and `assessed` at another — so `evidence[0]` is usually a
citation from a different lesson than the primary. Paired with the entry's
primary lesson, it made the first pass look like it was citing activities from
the wrong lesson: **12 of 18 items, all on the first pass's side, none on the
second's.** The blind judge reported that broken citation was decisive under
"evidence or nothing" in 11 of 18 cases.

It was judging a strawman. The result — 17 of 18 for the second pass — proved
nothing, and is recorded here only so the correction is legible.

The settlement itself was never affected: its packets carried the full evidence
array, so the four settlers saw the first pass accurately. Only the re-test was
contaminated.

## The valid blind test

Same eighteen items — every cross-unit dispute plus ten drawn at random —
readings relabelled A/B with the side randomised per item, provenance stripped,
and **both citations verified to resolve in the lesson they name** so neither
could be dismissed on bookkeeping.

```
to the second reading  18
to the first reading    0
to a third lesson       0
agrees with the labelled settlement  15 of 18
```

The asymmetry is real. A judge who could not tell which reading was which, and
who could not fault either one's citations, chose the same side every time — and
was harsher on the first pass than the labelled settlers had been.

It also named the failure mode independently, in the same terms the settlers had:
the first pass matched **a topic label rather than the item's question**. Three
coordinate-geometry items all placed on a dilation activity that never reflects
or translates anything; three rate-of-change items all placed on a modelling
lesson whose whole point is that the linear model breaks down. Reaching for
"coordinates + transformations" and "linear + rate" as topics.

Its opposite number's characteristic strength was going to where the skill is
**tested** rather than introduced — Cool-downs, and the three-way sort in *Make
Use of Structure*.

Three items remain contested: the blind judge and the settlers disagree on
`g8-2023-043`, `g8-2026-020` and `g8-2026-025`. The settlement stands, because
its settlers saw both readings' full arguments and the blind judge saw only their
conclusions, but each of those three entries records the blind verdict in its
`why` and carries `contested: true`.

## Corroboration from outside

`tools/measure_g8_section_agreement.py` is the only external signal grade 8 has.
Settlement moved the alignment **toward** it, which internal churn would not do:

| | before | after |
|---|---|---|
| our lesson inside the section NYCPS names | 58 of 91 (63.7%) | **63 of 91 (69.2%)** |
| unit agreement | 83 of 91 (91.2%) | **85 of 91 (93.4%)** |

## What this changes

The 66% calibration still holds as the honest ceiling for two *comparably good*
readings. Grade 8's 55.6% is not a second data point for it: **one of the two
readings was worse**, and a blind test says so. A disagreement rate is only a
measure of irreducible judgement once both readings have been shown to be
competent — otherwise it is measuring the weaker one.

The practical rule this earns: **a second pass that wins overwhelmingly is a
warning, not a triumph.** It means the first pass had a systematic fault worth
naming, and the fault here is the one `CLAUDE.md` already warns about —
deferring to the standard-to-lesson table instead of reading the lessons. That
warning was written for RegentsAlign's 26 placement errors. It applied here too,
and the first pass made it anyway.
