# Why `g7-2026-026` was wrong, and what the fix had to survive

> **Fixed 2026-09-21.** The first attempt, recorded below as it was written, stopped because
> it counted five regressions. **Four of the five were not regressions.** Read the last
> section before relying on anything in the middle of this note.

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


## The second attempt, 2026-09-21 -- and what the first one got wrong

Done the way the section above asks. Every tall glyph-shaped path on an item page was
clustered and **looked at in its page context**: 61 paths, 12 clusters.

| cluster | n | w x h | what it is |
|---|---|---|---|
| T00, T01 | 22, 22 | 4.47 x 23.0 | stretched `(` and `)` |
| T02, T03 | 4, 4 | 3.05 x 23.1 | stretched `[` and `]` -- `g8-2024-010`'s four choices |
| T09, T10 | 1, 1 | 4.2 x 23.1 | stretched `{` and `}` -- `g8-2025-015`'s set |
| T04 | 2 | 13.6 x 23.6 | the double edge of a hexagon, in a figure |
| T05, T07, T11 | 1, 1, 1 | 1.0 x 16-22 | dashed height lines, in figures |
| T06 | 1 | 13.6 x 19.1 | a spinner's arrowhead |
| T08 | 1 | 11.6 x 18.1 | a kite |

**Width separates them completely.** Every delimiter is between 3 and 4.5pt wide; no figure
piece is. So `shape_of` admits a tall shape only if it is that narrow (`DELIM_*` in
`tools/glyphs.py`), and the six figure pieces never reach the decoder. What each admitted shape
*is* remains a label: a stretched parenthesis normalises to the same outline as an ordinary
one, so T00, T01, T09 and T10 matched clusters a person had already labelled, and only the two
square brackets were new (`g442`, `g443`, labelled by eye from the page). The
delimiter-exclusion fix to the baseline estimate is kept, as this note said it must be.

**The corpus diff: 27 fields in 13 items, nothing else in 396.** The four items the first
attempt called fixes, and then:

| item | the first attempt called it | what the page shows |
|---|---|---|
| `g7-2024-037` | regression, "a spurious paren around the fractional part of a mixed number" | **17(1/3)x** -- a product. There is no mixed number. The published "17 1/3 x" was the error: it reads as seventeen and a third. |
| `g8-2026-020` | regression | **y = -(1/3)x + 3**, parentheses drawn, in choices C and D |
| `g7-2026-034` | regression | **(-45/-9)** in the stem and **-(45/9)** in choice A, both drawn |
| `g6-2024-018` | regression, "all four choices re-bracketed" | **-(2 1/2), -(-2 1/2), -2(1/2), 2(-1/2)**. Published, choice C read as minus two and a half where the page says minus one, and D read as one and a half where the page says minus one. |
| `g8-2024-010` | "lost all four answer choices" | gains its square brackets; nothing is emptied. That loss came from guessing at the tall shapes by geometry, which this attempt does not do. |

Every one was checked against a render of the page, not against the published text. **That is
the whole lesson of this note's first half:** its diff was judged against what the site already
said, so where the site was wrong, being right looked like breakage. A corpus diff says what
moved. Only the page says which side was correct.

Four more items changed shape rather than wording. `g7-2023-005`, `g7-2024-015`,
`g7-2026-047` and `g8-2025-015` each showed their expression as a picture, because a block
holding a discarded delimiter was not all glyphs and fell back to a figure; they are text now,
and the site publishes 148 figures rather than 152. And `g8-2024-045` -- "Two ordered pairs of
a linear function are shown below" -- had been publishing **no pairs at all**, neither as text
nor as a picture. It shows (2, 4 1/2), (3, 5 1/4) now.

Left ugly rather than patched: `g8-2025-015`'s set reads `{ 1/3 ,1.13...` with a space before
its first comma, because a stacked fraction is its own line and the comma after it is spaced as
if it began a new one.
