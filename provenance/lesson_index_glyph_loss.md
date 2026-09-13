# Mathematics drawn rather than typed, in the lesson index

`data/im_ms_lessons_detail.json` reproduces the teacher guides' text layer. The
guides set their mathematics as vector artwork, the same way the NYSED item PDFs
do, so a symbol that is drawn rather than typed does not survive extraction.

Three consequences turned up while aligning grade 8, each found by a reader
rather than by a check.

## Activity names lose a symbol, silently

Two are known:

| index stores | the workbook prints |
|---|---|
| `Using` — grade 7, Unit 3, Lesson 4, Activity 1 | Using **π** |
| `Does Plus Equal ?` — grade 8, Unit 7, Lesson 7, Cool-down | Does **a² + b²** Equal **c²**? |

A name that loses a **trailing** symbol is the dangerous case, because what is
left still reads like a title. `Using` looks like a real, if terse, activity
name; nothing about it says a character is missing. A sweep for names with a
doubled space, a space before punctuation, or an empty value finds only three
of the 1,732 activities, and that sweep cannot see `Using` at all.

**An evidence citation must quote the name the index stores**, because
`preflight.py` resolves the activity by that string. So a published citation may
read `Using` where the teacher's book says *Using π*. That is the honest
behaviour — inventing the missing character in the alignment file would make the
citation unresolvable — but it is worth knowing before it looks like a typo.

## Superscripts vanish from task statements

Throughout the index, `2⁴ · 2³` extracts as `2 ⋅ 2`. For most of the curriculum
this costs nothing. For grade 8 Unit 8, where every lesson is about exponents, it
removes precisely the content that distinguishes one lesson from the next: the
student task statements of Lessons 5, 6 and 7 read almost identically once the
exponents are gone.

Those five placements were settled by re-extracting
`sources/ImagineIM_NY_8_8_TG_NA_V2_EN_DIG.pdf` directly with font-size-aware
text extraction, which recovers the superscripts by their smaller size and
raised baseline. That confirmed the decisive content — Lin's list in Lesson 6
Activity 2 is `5⁻⁹` against `(5³)⁻³`, `(5³)⁻²`, `5⁻⁶/5³`, `5⁻⁴·5⁻⁵` — and it is
the technique to reach for the next time a placement turns on an exponent.

Quotes chosen as evidence in that unit deliberately avoid the stripped regions,
so every one of them is still a literal substring of what the index holds.

## One thing that is NOT a defect

Grade 7, Unit 4, Lesson 3's Warm-up has an empty name in the index. The guide
itself prints no title there — the heading reads `Warm-up` and stops, where every
other activity carries a name after it. Checked against the PDF before assuming.
It is the publisher's omission, and it is the only unnamed activity in 1,732.
