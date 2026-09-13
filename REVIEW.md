# Things a person still needs to look at

Three files carry different jobs. `provenance/` explains **why** things are as they are.
`RESUME.md` says **where the work is up to**. This file lists what a *person* must decide or
check — open questions, not finished findings.

Nothing here blocks the deploy gate. That is the point: `preflight.py` catches what a machine
can catch, and everything below is what it cannot.

---

## Published data that may be wrong

### 1. 140 figure descriptions have never been checked against the artwork

| grade | figures with a description |
|---|---|
| 6 | 41 |
| 7 | 46 |
| 8 | 65 |
| **total** | **152** |

Only **12** of those are coordinate planes, which is the one kind
`tools/check_plotted_points.py` can verify by reading the drawing back out of the PDF. When that
check was first run against those 12, **nine were wrong** — see
`provenance/figure_descriptions.md`. Two broke their item outright: one described a segment 5
units long where NYSED's own key says 6, and one described vertices making the answer a
coordinate pair that is not among the four choices.

The remaining 140 are diagrams, tables, labelled constructions and geometric figures. No check
can reach them, and a 75% error rate in the only sample anyone could measure is not a reassuring
prior. **This is what a screen-reader user is given instead of the picture.**

Scheduled for after grade 6's alignment. It needs a person and a rendered page per figure.

### 2. `g6-2024-045`'s coordinate plane cannot be read back

Its plot has no negative quadrant, so the axis is drawn along the box edge and the origin cannot
be told from the corner. The checker reports it as *unchecked* rather than passing it — by name,
every run, so the exemption cannot grow quietly. Verified by eye once and correct at that time.

### 3. `g7-2026-026`'s stem is still wrong

The fix needs the tall delimiters clustered and hand-labelled, not a height cap raised — raising
the cap fixed the target item and silently emptied another item's four answer choices.
`provenance/tall_delimiters.md` has the geometry, the nine-item corpus diff and the reproduction
command.

### 4. Radicals publish with a repeating-decimal mark

Several grade 8 stems render a radical's overbar as a repeating-decimal mark, so `√50` reads as
`√5-repeating0-repeating` and segment `DF` as `DF-repeating`. It does not change what the item
asks, but it is visible on the page. `provenance/radical_markup.md` also needs its own fix.

### 5. Two activity names publish with a symbol missing

The guides set their mathematics as artwork, so a drawn symbol does not survive extraction:

| publishes as | the workbook prints |
|---|---|
| `Using` (grade 7, 3.4) | Using **π** |
| `Does Plus Equal ?` (grade 8, 7.7) | Does **a² + b²** Equal **c²**? |

A citation has to quote the name the index stores or `preflight.py` cannot resolve it, so these
publish as-is deliberately. `provenance/lesson_index_glyph_loss.md` has the detail and the
font-size-aware extraction technique that recovers the symbols when a placement turns on one.

---

## Judgements a teacher should confirm

### 6. Three contested placements

Two honest procedures disagree on these, and both readings are recorded in the entry's `why`,
which carries `contested: true`:

| item | settled at | the blind judge preferred |
|---|---|---|
| `g8-2023-043` | 8.4.5 *Solving Any Linear Equation* | 8.4.4 *More Balanced Moves* |
| `g8-2026-020` | 8.3.10 *Calculating Slope* | 8.2.12 *Using Equations for Lines* |
| `g8-2026-025` | 8.1.7 *No Bending or Stretching* | 8.1.10 *Composing Figures* |

The settlement stands because its reading saw both arguments in full and the blind judge saw
only their conclusions. A teacher's eye would settle it better than either.

### 7. `g8-2024-010` rests on optional work

Its evidence is *The Right Fit (Optional)*, 8.5.21 — the only place students apply the sphere
and cone formulas to separately dimensioned figures, and it even uses the item's exact cone
(radius 3, height 8). A teacher may never have set it. The non-optional fallback is named in the
entry.

### 8. 39 standards place their items at more than one lesson

Expected — alignment is per item, not per standard, and two items on one standard routinely ask
different things. But it is also what drift looks like. Worth one pass asking whether each split
is a real difference in what the items ask. `preflight.py` prints the list every run.

### 9. 12 entries sit outside every unit the guide tables for their standard

Eight are grade 7 `NY-7.EE.3`, placed in Units 2 and 4 where the guide's table says 3, 5 and 6.
Deliberate — the table names the right unit only 96% of the time and the right lesson 77% — but
these are the ones to check first if a placement is ever questioned.

### 10. Grade 7's six `candidates-only` items

`g7-2023-001`, `-002`, `-017`, `-018`, `g7-2024-030`, `-031`. Their PDF page is undetermined, so
there is no stem and no item-specific evidence to judge on. They carry a unit and candidate
lessons, stay drafted, and never publish. They become answerable only if those pages are
resolved.

### 11. Three cited standards have no counterpart in the standards table

`NY-6.SP.7a`, `NY-8.EE.8c`, `NY-8.SP.4`. `NY-8.SP.4` is understood — it was removed under NGMLS
and the guide's *Standards by Lesson* table was never regenerated, which is also why every Unit 6
lesson number that table gives above lesson 8 is two too high. The other two want a look.

---

## Curriculum findings worth acting on in teaching

These are not defects. They are things the alignment turned up that a teacher can use.

### 12. No required Unit 2 activity dilates about the origin

"Origin" appears in grade 8 Unit 2 only inside the word "original". Dilation about (0, 0) is
there — in Lesson 4's *lesson summary*, in an *optional* Are-You-Ready-for-More, and in Lesson
5's *practice problems* — but in no required activity.

**Every NYSED dilation item is centred at the origin**, and they are the low-scoring ones:
p = 0.34, 0.41, 0.42.

### 13. The decimal test for irrationality is teacher-facing only

IM's working definition throughout is the *fraction* test. The non-terminating, non-repeating
decimal test appears only in 8.7.17's lesson synthesis and lesson summary — never in a student
task statement or activity narrative, so a class can miss it entirely.

**Three items and their distractors are built on the decimal test**: `g8-2023-035`,
`g8-2024-047`, `g8-2026-005`.

### 14. No Unit 5 activity compares an equation to a table

The unit compares equation to graph, and description to graph, but never equation to table. The
hardest item in that whole set — `g8-2025-041` at **p = 0.23** — needs exactly that, plus
extrapolating a table back to x = 0 to read an initial value, which appears nowhere in Unit 5.
Its only real home is 8.3.5 *Stacking Cups*.

Related: the test says "rate of change", Unit 3 says "slope", and the lesson that welds them is
8.3.5 Activity 2 *Connecting Slope to Rate of Change*. Students who met slope in Unit 3 and
functions in Unit 5 without that weld will read those items as unfamiliar.

### 15. Several of Unit 5's best matches are optional

The closest Unit 5 activity for comparing rates across representations (*Which Is Growing
Faster?*), for reading m and b off a graph, and for combining the sphere and cone formulas
(*The Right Fit*) is optional in every case, and 8.5.18 and 8.5.22 are optional lessons.
Skipping the optional work leaves those exact item types untouched.

---

## Two working habits this project paid for

Both were caught by looking at a result and disbelieving it, and both instruments were wrong in
the direction that flattered the conclusion being tested.

- **A blind test of grade 8's settlement fed the first pass a strawman.** It took each entry's
  `evidence[0]`, which is usually the *introduces* citation at a different lesson than the
  primary, and paired it with the primary lesson — making the first pass appear to cite
  activities from the wrong lesson in 12 of 18 items, all on its side. Thrown away and re-run.
- **The citation checker reported page offsets of −59.** Every one was the quote appearing in
  the unit's front matter, because the checker took the *first* page containing it rather than
  the nearest.

When a measurement comes out lopsided, check the instrument before believing the result.
