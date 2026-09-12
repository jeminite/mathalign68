# What an independent second pass found in grade 7

Four readers re-derived grade 7's placements from the items and the lesson index, without
reading `data/alignment.json`, `provenance/alignment_*`, `sources/nycps/` or git history.
Their answers are in `provenance/second_pass/`; compare them with
`python3 tools/measure_second_pass.py`.

## The headline, and it is about the method rather than about grade 7

**129 items compared. The two readings chose the same lesson 85 times — 65.9%.** 27 landed in
the same unit at a different lesson, and 17 landed in a different unit entirely.

That number is the most important thing this project has measured about itself. It is not a
score to improve: both passes followed the same rules, read the same guides and demanded a
named, paged, quoted activity, and they still disagreed about one placement in three. So

- **the unit is solid and the lesson is an opinion.** Only 17 of 129 disagreements crossed a
  unit, and most of those are the specific cases named below rather than noise.
- **a single lesson number should not be read as the answer.** The published range — the
  `introduces` / `practises` / `assessed` evidence list — is doing more work than the
  primary, and is what a teacher should actually look at.
- an agreement rate against NYCPS in the low 70s is not this project underperforming. Two of
  its own careful readings agree at 66%. Lesson-level alignment has an irreducible spread,
  and claiming precision past it would be false.

## Settled from this pass, with the reasoning in `alignment_disagreements.md`

Eleven placements were re-read and decided. Four moved a unit, three moved a lesson, one was
held against the second pass, and three were kept with the other reading added as evidence.
The four that moved a unit are the important ones: all of **NY-7.EE.2** was at Unit 4 Lesson
5 and is now at Unit 6 Lesson 12, whose warm-up is those items verbatim.

## Findings worth more than the placements

**`NY-7.SP.1` is a phantom code.** It carries no statement in `data/standards.json`;
`NY-7.SP.2` is not in the registry at all; the sampling statements NYSED's chart implies live
at `NY-6.SP.1b` and `NY-6.SP.1c`; and **no Imagine IM lesson in any of grades 6, 7 or 8 maps
to it**. New York moved CCSS 7.SP.1–2 down to grade 6 and NYSED's item map kept citing the
old code, inheriting the neighbouring cluster heading — which is the defect already recorded
in `blueprint.json`, now with its cause. Two released items carry it.

**Five NY-7.NS.3 items contain no negative numbers.** `g7-2023-008`, `g7-2023-040`,
`g7-2024-036`, `g7-2026-029` and `g7-2026-040` are fraction and money arithmetic. Grade 7
Unit 5 is signed throughout — scoring margins, net solar consumption, an overdrawn account —
so the grade 7 half of that standard is not what these items test. The second pass placed all
five in the grade 6 curriculum. **They have been left in grade 7 pending a decision**, because
moving them would cut against the home-grade convention, which searches the grade that teaches
the standard. This is a question about the test rather than about a placement: NYSED tags
these NY-7.NS.3, and a teacher preparing students for them is doing grade 6 work.

**Multi-step arithmetic has no home in the curriculum.** Five NY-7.EE.3 items — a taxi fare
and change from $20, servings to bottles to dollars, an hourly wage over 1 1/3 hours plus
1 hour 25 minutes — are posed as bare arithmetic, and Imagine IM never poses arithmetic that
way. It embeds it in modelling, proportional tables or percentage work. No grade 7 activity
asks students to convert minutes into a fraction of an hour before applying a rate, which is
exactly where `g7-2026-010`'s difficulty sits.

**Unit 6 Lesson 12 runs backwards.** Its warm-up is forward — apply a discount, choose the
expressions — but all three of its other activities find an ORIGINAL from a result. Forward
percentage computations belong in Unit 4.

**The lesson index has an extraction gap, and it is worse than a thin count.** Grade 6 Unit 8
Lessons 8, 9 and 13 lost their activity boundaries: several activities were merged into the
first entry, so Lesson 9 stores one "Warm-up" holding the whole lesson including the mode
task. `validate_im_ms_lesson_detail.py` now reports lessons with fewer than three activities,
which catches the symptom. The cause needs a fix in
`tools/extract_im_ms_lesson_detail.py`, and until then any citation into those lessons names
an activity that is not where the cited text actually sits. `g7-2023-009` is one.

**`g7-2026-026`'s defect was found independently.** A second reader rendered page 17 of the
2026 grade 7 PDF and read the vector artwork without knowing this project had already found
it: the expression is `(4/5)(0.2)(-5/8) = -1/10`, published as a subtraction whose value
matches no choice. Two independent readings of the same page agree, which is the strongest
evidence available that the stem is wrong and the extractor needs the fix.

## Still open

**44 of the 129 comparisons are unsettled** — 27 same-unit and 17 cross-unit. They are listed
by `tools/measure_second_pass.py`. Grade 7's entries stay `draft: true` until they are worked
through: publishing a placement that an equally careful reading puts elsewhere would claim a
precision the evidence does not support.
