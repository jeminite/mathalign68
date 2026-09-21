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


---

# The audit, and the real error rate

The 9-of-12 figure at the top of this note came from coordinate planes alone,
which are the only kind a script can check. It was never a safe estimate for the
rest. **140 distinct figures were then audited by hand**, in two waves, against
one question: *does this description, on its own, let a reader reach the item's
answer?*

| | audited | sound | wrong | insufficient |
|---|---|---|---|---|
| wave 1 — by arithmetic, descriptions carrying numbers | 111 | 89 | 9 | 13 |
| wave 2 — against the artwork, the rest | 31 | 8 | 7 | 16 |
| **total** | **142 verdicts, 140 figures** | **97** | **16** | **29** |

**45 of 142 failed: 31.7%.** Wave 1's residue ran 19.8%; wave 2, which took the
descriptions arithmetic could not reach, ran 74%.

`wrong` means the description states something the artwork does not show.
`insufficient` means every word is true and a fact the reader needs is missing —
the more common failure, and the harder one to see.

## Every failure is one failure

The numbers are transcribed carefully and **the relationship the numbers hang on
is summarised away**:

- angle diagrams that give both labels and never say opposite or adjacent, when
  the distractors are precisely the alternative relations;
- lines described as "rising steeply" instead of by a point — where a
  description named a plotted coordinate it was right, every time;
- the origin asserted where false, omitted where true and load-bearing;
- a labelled **diameter** called a radius, on the one item where that changes the
  answer, handing the reader a printed distractor.

## Two things the audit changed about how to check this

**The artwork was always available.** Every figure is committed as a cropped PNG
under `assets/`, named in each figure's own `file` field. Checking against it
never needed the source PDFs — and it is not optional. Arithmetic alone would
have passed three of wave 1's nine `wrong` verdicts, and *every* one of wave 2's
seven exists only because somebody looked. `g6-2026-029` reaches the right answer
by luck: it calls a diagonal "the top" and a side "the height", and those two
happen to be perpendicular.

**Summarising is not merely incomplete, it is error-prone.** Of the five
answer-choice figures in grade 6's final wave, three did not just fail to map the
letters — they misstated what varies. "Only one keeps a constant ratio" when two
do. "Whether they climb in a straight line" when all four point sets are
collinear. Compressing four choices into one clause requires a judgement about
what they have in common, and that judgement was wrong more often than right.
Enumerating each letter removes the opportunity to be wrong.

Two independent agents also found that the choices are laid out two-by-two, so
**visual reading order is A, C, B, D** — down the columns, not across the rows.
That is very likely how several of these went wrong at the source, and
`g7-2025-002`'s stored `choices` array is in exactly that order.

## What now holds the line

- `every answer-choice figure says which choice is which` — 12 of 15 failed this
  before the audit; all 15 pass now. The rule is mechanical because the judgement
  it replaces was unreliable.
- `no figure's alt text contradicts its own description` — alt text is the other
  screen-reader surface, 152 of 152 populated and checkable against nothing.
  It can at least be checked against its sibling. It caught `g8-2025-027`, whose
  alt said "base radius" where the artwork labels a diameter.
- `every figure description's coordinates are the ones the artwork plots` — the
  original mechanical check, still narrow: it engages only when the prose states
  two or more coordinate pairs, so 12 of the 28 coordinate planes reach it.
  `g8-2026-026` is a coordinate plane that states intercepts instead of pairs and
  so was never checked — and it was wrong.

## Still open

Four failures have no replacement, each needing a value read off a drawing that
the audit did not resolve: `g7-2023-016` (box-plot five-number summaries),
`g7-2026-014` (Team B's dot counts), `g7-2026-027` (the coordinates of Q, R, S)
and `g8-2026-034`'s companion reading.

~~**Alt text has never been audited.**~~ Done 2026-09-21; see below.


---

# The alt-text audit

All 152, each read against its crop, 2026-09-21. The question was narrower than
the one asked of a `longDescription`: *is every fact the alt states drawn, and
does it identify the figure?* An alt is an identification, not a substitute for
the picture, and was not failed for leaving the answer out of reach.

| | figures | sound | wrong | insufficient |
|---|---|---|---|---|
| first reading | 152 | 137 | 11 | 4 |
| after a second reading of every failure | 152 | 138 | 10 | 4 |

**14 of 152 failed: 9.2%**, not the third that was feared. A short
identification has less room to be wrong than a description does, and most alts
name a kind of figure and stop.

Where they failed, it was where they went past that and asserted a count, a
name or a range: a quadrilateral called a triangle, three lines called two,
three blanks called two, "about a dozen points" where there are ten, a range
true of the x-axis given for the whole plane (three times). The rule the first
audit arrived at holds here too -- **where the text named something it had
counted, it was right; where it summarised, it was wrong.**

The second reading mattered once. `g7-2025-003`'s choice D was failed for
saying "four desserts" when two of the four letters are main courses; but the
artwork itself labels that row "Dessert", so the alt says what is drawn. Kept.

The corrections went into `provenance/merge_<test>.json` and through
`tools/merge_content.py`; a diff of `data/content.json` before and after shows
14 `alt` fields and the date, nothing else. `figure_audit/alt_verdict_*.json`
and `alt_applied.json` are the record.

**The larger finding was not about alt text.** Reading every crop found 23
defective ones, 21 of them carrying a clipped line of the stem. `REVIEW.md`
section 1 has the list and the cause, in `grow_for_labels()`.
