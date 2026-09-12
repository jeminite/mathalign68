# Radicals are published with a repeating-decimal bar, not a radical sign

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
