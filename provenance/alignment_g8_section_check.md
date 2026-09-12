# Grade 8's only outside opinion

Grades 6 and 7 can be checked against NYCPS's own item-by-item IM alignment,
which cites a specific lesson and quotes a parallel activity. Grade 8 cannot:
of the 93 rows in `sources/nycps/nycps-exam-im-alignment-g8.csv`, five carry a
Curriculum Note and all five read `***in 7th grade`. So the check that caught a
whole standard sitting in the wrong unit in grade 7 is simply unavailable, and
grade 8 would otherwise publish on this project's own reading alone.

Every row does name a **section**: `5.D: Cylinders and Cones`, `8.B: Pythagorean
Theorem`. A grade 8 unit averages four sections, so that is coarser than a
lesson and much finer than a unit. `tools/measure_g8_section_agreement.py` asks
of each aligned item whether the lesson we chose sits inside the section NYCPS
named.

## First pass, before the second pass settles anything

```
   93  rows read
   91  section resolved by title
   58    our lesson is INSIDE the cited section
   25    same unit, different section
    8    different unit

section-level agreement: 58 of 91 (63.7%)
unit-level agreement:    83 of 91 (91.2%)
```

Read it the way `CLAUDE.md` says to read the 66% figure: two careful readings of
the same lesson text agree on the exact lesson about two thirds of the time, and
this is a *section*-level number sitting in the same band. The unit is solid at
91%; the section is an opinion.

**23 rows print a unit number this project does not use** — the New York edition
swaps Units 7 and 8 in both grades 7 and 8, and NYCPS records national numbers.
Every one of them resolved correctly through the title, which is the rule working
rather than a correction table.

## Matching the titles

The section names are typed by hand and misspelt often: `Pythaogrean Thoerem`,
`Asociations in Numerical Data`, `Equivilent Equations`, `Linear Relatinships`,
`Equivilent`, `Linear Equations in One Variables`. Exact matching throws away a
fifth of the sheet.

Character similarity alone is worse than useless here, and the two cases that
prove it are in the data:

| typed | closest string | the right answer |
|---|---|---|
| `Rational And Irrational Numbers` | Adding and Subtracting Rational Numbers (0.714) | Decimal Representation of Rational and Irrational Numbers (0.705) |
| `Linear Relatinships` | Angle Relationships (0.789) | Representing Linear Relationships (0.731) |

Both are fixed by scoring which **words** the two names share, in both
directions — so a title cannot win by being a prefix of a longer one, which is
what keeps `Exponent Rules` from matching `More Exponent Rules` — and keeping
character similarity only as a tiebreak, where its tolerance for misspelling is
exactly what is wanted. All 41 distinct section names were then checked by hand:
every resolution is correct.

Two rows do not resolve and are printed with their near-miss rather than
silently dropped:

- `Slicing Solids` → best candidate *Solid Geometry* at 0.46. NYCPS used the
  national section name; the New York edition renamed it. Genuinely
  unresolvable by title.
- `The Pythogram Theorem` → *The Pythagorean Theorem* at 0.59, just under the
  floor. Obvious to a person, and left failing on purpose: a threshold lowered
  until every row passes is measuring itself.

## A section title that was missing

Building this found that grade 8 Unit 6's five Section B lessons carried an
**empty** `sectionTitle`, so seven NYCPS rows had nothing to compare against.
The cause is the publisher's: the guide's PDF bookmark reads `Section B` and
stops, where every other one of the 112 sections reads `Section A: Does This
Predict That?`. The title is printed on the section's own opening page and in
the guide's table of contents — *Associations in Numerical Data*, which is what
NYCPS calls it too.

`tools/extract_im_ms_lesson_detail.py` now falls back to the opening page's 12pt
run when the bookmark gives no title. Checked against all 112 sections in the
twelve New York guides: the page agrees with the bookmark on 99, and every
disagreement is one the bookmark wins — a curly apostrophe, a title whose
mathematics is drawn rather than typed (`px+q=r` prints as stripped-out
zero-width spaces), and one guide whose page still reads `[Section Title]` where
the publisher never filled the placeholder in. So the fallback fires exactly
once, which is the point.

`tools/validate_im_ms_lesson_detail.py` now fails if any lesson does not name
its section, because a blank there does not look like a defect — it looks like
a comparison with nothing to compare.
