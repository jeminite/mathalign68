# Radicals are published with a repeating-decimal bar, not a radical sign

> **Fixed 2026-09-21.** What follows is the record of the defect as found; the fix and
> what it turned out to involve are at the end.

Sixteen radicals across ten grade 8 items are marked up as a literal `√` followed by a
`<span class="repeat">`, which is the class for a repeating decimal. The stylesheet carries a
dedicated pair for this — `.radical` and `.radicand`, complete with a `\221A` pseudo-element —
and **nothing in `data/content.json` uses them.**

## What it looks like

`g8-2023-035`, whose subject is whether √50 is rational:

```html
<span class="math">√<span class="repeat">5</span><span class="repeat">0</span></span>
```

Two separate repeat spans, one per digit. `g8-2025-042` renders √1.44 as `1.44` under a repeat
bar. `g8-2023-040` puts segment overbars through the same path, so its stem reads
*"Side − DF-repeating has a length of 9 inches"*.

## Why it matters, and why it is not merely ugly

`.repeat` draws a `border-top`, so on screen the result is close to a radical and a reader would
probably not notice. The problem is what it *says*.

- **The claim is mathematically different.** An overbar on a decimal means the digits repeat.
  √1.44 is exactly 1.2 — a terminating rational — and the item asks students to classify it as
  rational or irrational. Marking it "1.44 repeating" asserts the opposite of what makes the
  item's answer correct.
- **`g8-2023-035` splits the radicand.** "50" becomes two spans, so the bar is drawn twice
  rather than once across both digits.
- **Anything reading the data rather than the pixels gets the wrong text.** The plain-text
  rendering is `√5-repeating0-repeating`; a screen reader would say the same.

Affected: `g8-2023-008`, `g8-2023-035`, `g8-2023-040`, `g8-2024-037`, `g8-2024-047`,
`g8-2025-015`, `g8-2025-037`, `g8-2025-042`, `g8-2026-005`, `g8-2026-007`, `g8-2026-038`.

## Why it is recorded rather than fixed

The markup lives in `data/content.json`, which is reviewed transcription, so this is a
transcription defect and the rule is to fix the extractor rather than the file. That is the same
class of change as `provenance/tall_delimiters.md` describes, and it carries the same risk: the
last extractor change that looked obviously right silently emptied another item's four answer
choices. Any fix here must re-extract all twelve tests with `--stdout` and diff every stem and
choice, and must show that **only** these sixteen move.

Worth checking at the same time whether the `.radical` path is dead code or whether
`extract_items.py` has a branch that was meant to reach it and never does.

None of this affects where the items are taught: all eleven are placed in grade 8 Unit 7 on
what they ask, and the alignment reads through the defect without difficulty.

## The fix, 2026-09-21

In `tools/glyphs.py`, not in the data, and verified the way this note asked: all twelve tests
re-extracted with crops redirected to a scratch directory, every stem, choice, display and
figure rect diffed against `provenance/content_*_raw.json`. **25 fields moved in 15 items and
nothing else in 396.** The count above was low: there were sixteen radicals, and also nineteen
segment bars going through the same path.

Three things were wrong, and only the first was the one this note describes.

**Every bar was a repetend.** `decode()` had one output for a rule sitting over glyphs:
`.repeat`. What a bar means is decided by what it is attached to, so it now looks: a radical
sign whose right edge meets the bar's left end makes it a vinculum (`.radical` / `.radicand`,
and the sign itself is dropped because the stylesheet draws it); letters and primes beneath it
make it a segment (`.segment`, new); only otherwise is it a repetend. The `.radical` path was
dead code from the day it was transplanted -- nothing in `extract_items.py` ever reached it.

**A bar is drawn as overlapping dashes, and the merge only accepted abutting ones.** The
vinculum over the 50 in `g8-2023-035` is two pieces, 271.0-277.9 and 276.7-283.6, a 1.2pt
overlap; the merge's floor was -0.6, so each digit kept a bar of its own. The bar over segment
DF in `g8-2023-040` is nineteen 1.4pt dashes stepping 0.8pt; some merged, and the leftovers
were read as minus signs. A bar's rect sits above the line it marks, so it forms a line of its
own and sorts ahead of everything -- which is how **`g8-2023-007` published "− 1.25 > 3.3"
for a page that says "1.25 > 3.3"**: a phantom minus, in a live answer choice, that no one had
noticed and that was not on this note's list. A piece that starts anywhere inside the bar so
far, or just off its end, is now more of the same bar; the left bound still keeps another
radical's vinculum out.

**The bar over the last digit of 3.3-repeating claimed the decimal point too.** The 1.5pt of
slack that gathers a fraction's numerator is right for a fraction and wrong for an overbar; the
point fell inside it by 0.05pt, so every repeating decimal in the corpus published with the bar
over ".3". `_under()` keeps only the glyphs a bar actually covers.

`plain()` in `tools/merge_content.py` gained the two new spans -- `√(50)`, `segment DF` -- so
the searchable text no longer says "repeating" either.

**Found on the way, and also fixed:** `g8-2024-047` asks the student to classify five numbers
and published three. √32 and 7/2 sit close enough to be one block, 50pt tall because of the
stacked fraction; the displayed-expression test allowed 34pt; the block went on to be a figure,
was under the minimum area, and was dropped without a word. Its own answer said √32 is
irrational about a number the question never showed. The bound is 70pt now; the corpus diff for
that change is that one item.

`preflight.py`: *every bar says what it is: no bare radical sign, no repetend of letters.* It
fails 12 items on the old `content.json`.
