# Why `g7-2026-026` is still wrong, and what a fix has to survive

`g7-2026-026` publishes as `4/5 (0.2) − 5/8`, a subtraction whose value (−0.465) is not among
its four choices. The PDF draws `(4/5)(0.2)(−5/8) = −1/10`, which is NYSED's key. This is an
attempt at the fix, stopped deliberately, and what it established.

## The cause is certain

Read the vector geometry of page 17, left to right across the stem line:

| x | w × h | what it is |
|---|---|---|
| 182.5 | 4.45 × 22.99 | `(` |
| 189.3 | 7.03 × 0.68 | fraction bar, `4` above and `5` below |
| 198.8 | 4.45 × 22.99 | `)` |
| 206.2–227.3 | small | `(0.2)` |
| 230.2 | 4.45 × 22.99 | `(` |
| 236.6 | 6.81 × 0.68 | a rule with **nothing above or below** — a minus |
| 245.7 | 7.03 × 0.68 | fraction bar, `5` above and `8` below |
| 255.1 | 4.45 × 22.99 | `)` |

The four grouping parentheses are **22.99pt tall**, and `glyphs.py` sets `MAX_H = 16.0`. They
are discarded before clustering ever sees them, so they are not in `data/glyphs.json` at all —
not unlabelled, absent. What survives is `4/5`, `(0.2)`, `−`, `5/8`, and with the grouping gone
the minus reads as a binary operator. The item is a product wearing a subtraction's clothes.

A stretched delimiter grows to fit what it encloses, so height alone can never be the test.

## What was tried, and the two things it proved

`MAX_H` raised to 30.0. That alone produced `((4/5)) (0·2) (− (5/8))` — parens recovered, but
`0.2` became a superscripted `0` and `2` with a multiplication dot between them.

**The baseline estimate assumes the tallest glyph is body text.** Its comment says so outright:
*"Superscripts are always drawn smaller than the text they sit on, so the tallest glyphs are
body text by definition."* True until a 23pt bracket sits beside 8pt digits — then `max_h` is
the bracket, `tall` holds only brackets, and every digit looks raised. Excluding stretched
delimiters from the estimate (much taller than wide, where body text is roughly square) fixed
that cleanly, and `(4/5) (0.2) (−5/8)` came out right.

**But the corpus-wide diff is what settles it.** Re-extracting all twelve tests and diffing
every stem and choice against `provenance/content_*_raw.json`: **9 of 396 items changed. Four
are fixes. Five are regressions.**

Fixed — real parentheses recovered:

- `g7-2026-026` `(4/5)(0.2)(−5/8)`, the target
- `g7-2025-023` `(−6)(−1½)`
- `g7-2026-004` `(−5/6) ÷ (−1/3)`
- `g7-2023-005` `(−1/5 + 2/5) + (−4.4)`

Broken — a spurious paren around the fractional part of a mixed number:

- `g7-2024-037` `17 (1/3) x` for 17⅓x
- `g8-2026-020` `y = − (1/3)x + 3`
- `g7-2026-034` `((−45/−9))`
- `g6-2024-018` all four choices re-bracketed

And the one that stops it outright: **`g8-2024-010` lost all four answer choices.** They
extracted as empty strings. A change that silently empties a published item's choices is not a
change to make on a hunch.

## What a real fix needs

Raising `MAX_H` is necessary but nowhere near sufficient. The tall shapes have to go through
the same route every other glyph does — clustered by `glyphs.py`, rendered as tiles by
`tools/label_glyphs.py`, and **labelled by a person**, so that a tall bracket is distinguished
from a tall *anything else*. The regressions above are what happens when tall shapes are
admitted and then guessed at by geometry: 82 paths corpus-wide are tall and narrow, 42 of them
match the paren signature, and the rest are not parens.

So the work is: raise the cap, re-cluster, label the new clusters by eye, keep the
delimiter-exclusion fix to the baseline estimate, then re-run this same twelve-test diff and
require that **only** the four intended items move.

Until then the stem stays wrong and is recorded here, in `blueprint.json`'s neighbours, and in
the item's own alignment `why`. Preflight cannot catch it: prose fidelity strips the decoded
mathematics before comparing, so the check and the error never meet.

## Reproducing the diff

```bash
for f in sources/20*-released-items-math-g*.pdf; do
  python3 tools/extract_items.py "$f" --stdout > "/tmp/after/$(basename "$f" .pdf).json"
done
# then compare stemHtml, prose and choices against provenance/content_<testId>_raw.json
```

`--stdout` is essential: without it the extractor overwrites the very baseline being compared
against. It does still write figure crops into `assets/`, so check `git status` afterwards —
this attempt left an `assets/G8-2024/q10.png` behind, cropped from the choices it had just
emptied.
