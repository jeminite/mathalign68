# The published field nothing could contradict

Every other fidelity claim in this project is checked against an independent
source. A stem's prose is compared character for character with the PDF's own
text layer. An answer is compared with NYSED's item map or its exemplary-response
page. A citation's page is compared with the index that citation came from.

A figure's `longDescription` had nothing. It is written by hand from the artwork,
it is what a screen-reader user is given **instead of** the picture, and no check
in `preflight.py` could disagree with it.

So it drifted. An audit of all twelve coordinate-plane figures in the corpus
found **nine** whose stated coordinates disagree with the drawing.

| item | description said | artwork plots |
|---|---|---|
| `g8-2026-029` | B (−4, −2), C (3, −2) | B (−4, −3), C (7, −3) |
| `g8-2026-025` | A (−2, 4), B (−6, 2), C (−2, 2) | A (−2, 3), B (−5, 1), C (−2, 1) |
| `g8-2026-022` | B (−6, 1), C (−2, 3), E (5, −4) | B (−5, 1), C (−1, 3), E (6, −4) |
| `g8-2026-010` | J (1, 8), K (1, 4), L (7, 4), M (7, 8), R/S at y = 5 | J (2, 8), K (2, 4), L (8, 4), M (8, 8), R/S at y = 4 |
| `g8-2026-001` | A (−3, 3), B (0, −1), C (2, 5) | A (−2, 3), B (2, −2), C (3, 5) |
| `g8-2025-046` | B (−6, 0), C (−1, 2) | B (−5, −1), C (1, 2) |
| `g8-2024-041` | A (−1, −4), B (4, 8) | A (2, −4), B (7, 8) |
| `g8-2023-042` | X (−5, 2), Y (−2, 5), Z (−2, 2), image "shifted right" | X (−10, 2), Y (−3, 5), Z (−4, 2), image named vertex by vertex |
| `g6-2024-037` | B (−2, −4) | B (2, −4) |

Two of them break the item outright:

- **`g8-2026-029`** asks for the length of a translated side. As described, that
  side is 5 units long. The item's own answer key, checked against NYSED's item
  map, says **6**.
- **`g8-2026-001`** asks for the coordinates of a translated vertex. As
  described, the answer is (−7, 5), which is **not among the four choices**.

The rest preserve the differences between points while sliding them across the
plane — `g8-2024-041` has both endpoints three units left of where they are
drawn — so the arithmetic still works out and nothing looked wrong. That is the
shape of the problem: a description read off a grid by eye goes wrong by one
unit, and a wrong answer would have been noticed long before a wrong picture
was.

## The check

`tools/check_plotted_points.py` reads the plane back out of the PDF and compares.
A coordinate plane is vector artwork, so this is available and was simply never
used:

- the **grid** gives the spacing, as the modal gap between the ruled lines;
- the **axes** are the two lines long enough to carry an arrowhead at each end —
  found as the longest line *within the plot area*, because the page's own footer
  rule is longer than any axis, and after merging each grid line's two halves,
  which are drawn separately either side of the axis they cross;
- a **plotted point** is a small filled circle landing on a lattice intersection,
  which is what separates it from the round fragments of the letter labels beside
  it.

`preflight.py` now runs it on every figure whose description states two or more
coordinate pairs. It sits outside the extractor-drafts branch on purpose: it does
not depend on the drafts, and a check that disappears when an unrelated source is
missing is worse than one that fails.

## What it will not claim to know

**The units per grid square.** Tick labels are drawn as glyph outlines, not text,
so they cannot be read here; `g6-2024-037` is ruled two units to the square. The
checker tries 1 and 2 and reports which fits, rather than pretending to know.

**The origin, on a plot with no negative quadrant.** There the axis is drawn
along the box edge and nothing distinguishes it, so the origin cannot be told
from the corner. One figure — `g6-2024-045` — is reported as *unchecked* for this
reason rather than passed. Its description was verified by eye instead and is
correct. An unchecked item is printed by name every run, so the exemption cannot
grow quietly.

The audit covered coordinate planes only, because they are the figures whose
content reduces to numbers a script can re-derive. Diagrams, tables and geometric
figures still rest on a person having read them, and this note is the honest
record of that limit.

## A tenth defect, outside the checker's reach

While settling the alignment disagreements, a reader noticed that
`g8-2025-035`'s description said *"Brayden marks a rise of 3 against a run of
2."* The item's own stem says Brayden calculated the slope as **2/3**, and the
artwork labels his triangle 2 up and 3 across. The rise and the run had been
transposed, so the description contradicted both the stem above it and the
answer key, which says both students are right.

`check_plotted_points.py` cannot catch this one and never will: the figure plots
no points. It is two line graphs with labelled arrows, and the numbers that
matter are printed on the arrows rather than implied by a lattice position.

That is the honest boundary. The checker covers coordinate planes, which are the
figures whose content reduces to numbers a script can re-derive from the drawing.
Everything else — diagrams, tables, labelled constructions, geometric figures —
still rests on a person having read the picture, and a description that
contradicts its own stem is the shape those errors take.
