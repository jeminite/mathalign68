# Thirty-three wrong crops, two causes

Every other published field in this project is checked against something. A
figure crop was checked against nothing: not the PDF, not its neighbours, not
its own description. The alt-text audit of 2026-09-21 had a reader open all 152
PNGs for a different reason, and 33 of them were wrong. `REVIEW.md` had known
of two.

## Cause one: short is not the same as a label (22 crops)

`grow_for_labels` extends a crop to enclose the text that belongs to the
figure -- tick labels, axis titles -- and told a label from prose by length:
twelve characters or fewer, within 34pt below the artwork.

But a line of prose is not one span. The mathematics in it is set in another
font, so *What will be the coordinates of vertex A' ?* arrives as one long span
and then `A`, a prime and `?` as spans of their own. Each is short. Where a
question carried on beneath its picture they were taken for labels, the crop
grew down to their baseline, and the line was published sliced off at the
figure's own left and right edges -- which is why every stray line was clipped
at the sides and nearly every one ended in a prime, a fraction or a question
mark.

The fix: a short span is a label only if it does not share a line with prose.
`PROSE_BAND` (8pt) is how far off a prose line's box its own fragments may sit,
because a fraction's numerator and a prime are not on the baseline.

## Cause two: a union that cannot see a line (11 crops, and more by luck)

`bbox_of` unions drawing rectangles with PyMuPDF's `|`. A stroked horizontal or
vertical has a rectangle of no height or no width; PyMuPDF calls that *empty*,
and its union ignores an empty rectangle without a word:

    Rect(121, 90, 413, 171) | Rect(102.7, 85.6, 102.7, 176.6)  ->  Rect(121, 90, 413, 171)

So no figure's box ever included its ruled lines. A table's border was in the
crop only when the glyphs inside it, plus the 8pt padding, happened to reach
that far. For eleven figures they did not. Nine tables published with their
outer border sliced off and their rules running into the image edge;
`g8-2023-034` lost the left border of one table of two; and on `g8-2026-037`
the box was 19pt too narrow, which put the choice letters A and B one point
outside `grow_for_labels`' horizontal reach, so an answer-choice figure
published with half its letters missing.

The fix is `extent_of`, used **for the crop only**. `bbox_of` still decides what
is a figure, a choice or a displayed expression, and still applies the
minimum-area test, because changing either moves stems and creates figures.

## The corpus diff

Per this project's rule, an extractor change is verified against the whole
corpus, not the items it was meant to fix. `--stdout` still writes crops into
`assets/`, so the runs were made with `extract_items.ASSETS` pointed at a
scratch directory.

| | crops changed | byte-identical | stems, choices, holes, anything else |
|---|---|---|---|
| baseline, unmodified extractor, against the committed `assets/` | 0 | 152 | -- |
| cause one fixed | 22 | 130 | none |
| cause two fixed, on top | 22 | 130 | none |
| **both, against the committed crops** | **39** | **113** | **none** |

The 22 moved by the first fix are exactly the 22 the audit had named, and none
other. Of the 22 moved by the second, 11 moved by more than the padding -- that
is, content had been outside the old crop -- and 11 by 0 to 5pt. All 39 were
looked at. One alt changed as a consequence: `g7-2023-005`'s crop had included
answer choice A beneath its expression and its alt said so; the choice line is
prose-adjacent and is gone, and the choice was always published as text.

## What holds the line now

`preflight.py`: *no figure crop slices through a line of the page's text.* A
line lying wholly inside a crop is a title or a label; one that crosses its edge
never is. It flags 21 of the 22 on the old coordinates and none on the new. It
cannot see a border cut off -- that half is fixed at the cause and guarded by
nothing.
