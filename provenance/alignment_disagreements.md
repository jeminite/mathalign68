# Where this project's alignment differs from NYCPS's, and why

Regenerate the list with `python3 tools/measure_alignment_agreement.py`. This file
records the decisions behind the differences that remain after review, so they are
choices on the record rather than drift nobody looked at.

NYCPS's own `sources/nycps/PROVENANCE.md` calls its notes *"suggestive, not
authoritative"*. A difference is not an error on either side; it is a place where
two readings of the same item diverged and somebody has to decide.

## The pattern behind most of them

NYCPS tends to cite **the lesson that carries the standard**, which for a standard
with a dedicated lesson is often the unit's catch-all. Reading the task statements
tends to land on **the lesson that asks the item's question**. Both are defensible
and they are answers to different questions.

Where NYCPS's lesson genuinely teaches the item's content, it has been added to the
item's evidence as `introduces` rather than displacing the primary. That is the
point of publishing a range: the first review pass put agreement at 56.8%, and
adding these -- all of them true, none of them added to move a number -- brought it
to 78.4% without changing a single primary lesson.

## Differences retained after review

**`NY-7.EE.4b` -- three items, ours Lesson 16, NYCPS Lesson 14.** The items ask
*which inequality can be used*, and never solve it. Lesson 16 Activity 1 is
"Choose the inequality that best matches each given situation", which is the task
verbatim. Lesson 14 is where writing such an inequality from a context begins, so
it is now cited as `introduces`.

**`NY-7.RP.3` -- ours Lessons 8, 9 and 10, NYCPS Lesson 12 throughout.** Lesson 12
is "Solving Multi-step Percentage Problems", the unit's catch-all. Read against
the items: g7-2023-032 adds a tax and a tip to a restaurant bill and there is a
lesson called *Tax and Tip* whose Activity 3 is a restaurant bill with both;
g7-2024-029 is a single percentage of an amount, not multi-step at all; and
g7-2023-023 applies one increase to the result of another, which Lesson 12's
Information Gap activity does not do -- its narrative is about discounts.

**`g7-2025-010`, ours Lesson 3, NYCPS Lesson 11.** The item shows a rectangle and
asks which equation finds the length; it solves nothing. Lesson 3's cool-down is a
diagram with four candidate equations, wrong in the same ways as the item's
distractors.

**`g7-2025-025`, ours Lesson 11, NYCPS Lesson 12.** No percentage appears in the
item: a regular price is described as ten dollars less than twice a discounted
price. That is a chain of comparisons, which is Lesson 11's cool-down.

**`g7-2024-017`, ours grade 7 Lesson 6.12, NYCPS Lesson 5.14 -- a different unit.**
The item increases a ticket count by 40% and prices the total. Lesson 5.14 is
"Solving Problems With Rational Numbers", addressing `NY-7.NS.3`; its activities
are scoring margins, net electricity consumption and overdraft fees -- signed
arithmetic, with no percentage anywhere. This citation is rejected.

**`g7-2025-021`, ours grade 7 Lesson 4.5, NYCPS Lesson 6.18 -- a different unit.**
The item rewrites `t - 0.10t` as `0.90t`. Lesson 6.18 is about subtraction inside
equivalent expressions in general; Lesson 4.5 "Say It With Decimals" is where a
percentage decrease is specifically rewritten in the `0.9x` form the item uses.

**`g7-2024-037`, ours Lesson 20, NYCPS Lesson 19.** The item combines two like
terms with fractional coefficients and contains no parentheses, so there is
nothing to expand. Lesson 20 is "Combining Like Terms (Part 1)".

## Unit 5 -- Rational Number Arithmetic (27 items)

Agreement moved 78.4% -> 68.5% when this batch landed, which is the drift the conventions
say to stop and re-read on. Reading all of it changed two placements and confirmed the rest,
taking it to 72.2%. The number did not return to 78.4% and should not be made to: Unit 5's
items sit close together and NYCPS spreads them across the unit differently than reading the
task statements does.

**`g7-2025-023` -- changed, ours Lesson 9 -> Lesson 10, agreeing with NYCPS.** The item asks
for the value of (-6)(-1 1/2), and its distractors -9 and 6 1/2 probe the sign and the
arithmetic separately. Lesson 9 builds the sign rule; Lesson 10's Row Game is where signed
products are evaluated, and column B carries -4/3 times -6/5. The first pass put it at the
lesson that explains and not the lesson that asks.

**`g7-2024-005` -- unchanged, NYCPS's Lesson 2 added as `introduces`.** Both NY-7.NS.1c items
are temperature differences and the other already cited *Winter Temperatures*; this one now
does too.

### Retained after review

**`g7-2025-017`, ours Lesson 5, NYCPS Lesson 7.** The item asks which expression equals
(-0.3) + 1.5, keyed to 1.5 - 0.3. Lesson 5 Activity 2 asks "Which expression has the same
value as 8 + -5?" with four choices of the same shape. NYCPS's Lesson 7 warm-up asks whether
the *solution to an equation* is positive -- a different question.

**`g7-2023-036`, ours Lesson 3, NYCPS Lesson 7.** "The sum of two numbers is zero" is the
additive inverse, which is Lesson 3's warm-up and whose cool-down opens 56 + -56. Lesson 7's
*Positive or Negative?* is again about the sign of a solution.

**`g7-2024-005` and `g7-2025-037`, ours Lesson 6, NYCPS Lesson 2.** Lesson 2 finds a final
temperature from a stated change; both items are given both temperatures and asked for the
difference, which is Lesson 6 Activity 1's table.

**`g7-2023-005` and `g7-2024-015`, ours Lesson 13, NYCPS Lesson 6.** NYCPS cites *Does the
Order Matter?*, which compares a - b against b - a. Neither item asks that: one regroups a
four-term signed sum, the other evaluates an expression containing a subtracted sum. Lesson 13
is the unit's lesson on expressions with rational numbers.

**`g7-2025-043`, ours Lesson 4, NYCPS Lesson 6.** A $25.00 gift card and a $25.00 purchase.
Lesson 4 is the money lesson and its cool-down is a balance against a purchase; NYCPS cites an
altitude table.

**`g7-2025-032`, ours Lesson 12, NYCPS Lesson 14.** The item is a submarine descending at a
constant rate. Lesson 12 is *Negative Rates*: its Activity 2 is a bathyscaphe descending at -3
feet per second and its cool-down is a submarine descending to a stated depth in a stated
time. Worth noting that NYCPS's own citation is internally inconsistent here -- it prints
"Unit 5, Lesson 12" with Lesson 14's title, and names an activity, *Moving Up and Down*, that
is not in the New York edition's Lesson 14 at all.

**`g7-2025-040`, ours Lesson 13, NYCPS Lesson 10.** 0.5(4-6) over 0.2 combines a subtraction,
a product and a division in one expression. Lesson 10 is titled *Multiply!* and does only
products; Lesson 13 opens the section actually called "Four Operations With Rational Numbers".

**`g7-2024-036`, ours Unit 4 Lesson 4, NYCPS Unit 4 Lesson 2 -- same unit.** Both readings
leave NY-7.NS.3's tabled units of 5 and 9, because the item takes a fraction of a quantity
twice with no signed arithmetic anywhere in it. NYCPS's Lesson 2 is rates with fractions;
Lesson 4 computes a fractional part of a given quantity, which is the item's step.

## Units 1 and 2 -- Scale Drawings, Introducing Proportional Relationships (27 items)

Agreement 72.2% -> 74.6%. One placement changed on review, and it was NYCPS's.

**`g7-2024-039` -- changed, ours Lesson 2.5 -> Lesson 2.6, agreeing with NYCPS.** The item
gives a rate in words (25 words per minute) and asks for an equation. Lesson 5's cool-down
also gives a rate in words with two named variables, which is why the first pass chose it --
but that cool-down HANDS the student the equation d = 50t and asks for a second one. Lesson 6
Activity 2 asks students to write the first equation from a stated rate, which is the item.

### Where NYCPS's Lesson 2.2 is cited as `introduces` rather than as the primary

Five items -- `g7-2023-004`, `g7-2023-013`, `g7-2023-039`, `g7-2024-001`, `g7-2025-002`,
`g7-2025-045` -- are placed at Lesson 3 or Lesson 7 where NYCPS cites Lesson 2. Lesson 2
introduces proportional relationships in tables and every one of these items has a table, so
it is cited on all of them. But Lesson 3 is titled *More About Constant of Proportionality*
and is where the constant is asked for by name, and Lesson 7 is where a table is TESTED for
proportionality. The items split cleanly between those two questions and Lesson 2 asks
neither.

**`g7-2023-025`, ours Lesson 13, NYCPS Lesson 4.** It is the only NY-7.RP.2c item that starts
from a graph, and its distractors are the relationship written backwards. Lesson 13 is where a
point, a line, a table and an equation are put on the same relationship.

**`g7-2023-042`, ours Lesson 6, NYCPS Lesson 4.** The robot item does not stop at the
equation; it then asks how many seconds to travel 11 feet. Lesson 6's goal is to use
equations to solve problems, and Lesson 4 is cited as where the equation form arrives.

## Unit 7 and grade 6 Unit 8 -- probability, sampling and data (19 items)

Agreement 74.6% -> 72.8%. Four differences retained, and all four are NYCPS citing a lesson
about a different activity than the item performs.

**`g7-2023-034` and `g7-2024-047`, ours Lesson 7.9, NYCPS Lessons 7.3 and 7.4.** Both items
give three independent choices and ask for the probability of one named combination. NYCPS
cites *What Are Probabilities?*, which is single-step probability (a letter selected at
random), and *Estimating Probabilities through Repeated Experiments*, which is experimental
probability from trials. Neither is a multi-step theoretical probability, which is Lesson 9.

**`g7-2024-014`, ours grade 6 Lesson 8.16, NYCPS grade 7 Lesson 7.18 -- a different grade.**
The item shows ONE box plot and asks for its interquartile range. NYCPS cites *Comparing
Populations Using Samples*, which compares two box plots drawn from samples; the item has no
comparison and no sample in it. Quartiles, IQR and box plots are built in grade 6 Unit 8
section D, which is where the home-grade rule sends it.

**`g7-2024-007`, ours grade 6 Lesson 8.14, NYCPS grade 7 Lesson 7.13 -- a different grade.**
NYCPS cites *What Makes a Good Sample?*. Mr. Moore's data is his whole class, not a sample,
and the item asks which statement about the distribution is true. Retained in grade 6 Unit 8,
where distributions are described -- but see the caveat in the entry: the only place in that
unit where an outlier is put in front of students is Lesson 14, and it is there to show what
an outlier does to the mean against the median, not as a feature to spot.

### A caveat about two of these placements

`g7-2023-009` cites Lesson 6.8.13, and the lesson-detail index holds only two activities for
it and one for Lesson 6.8.9, the mode lesson. Ordinary lessons in this curriculum carry four
or five. Twenty-eight of the 427 indexed lessons are this thin and most are Unit 9 project
lessons, which genuinely are -- but grade 6 Unit 8's Lessons 8, 9, 10, 12 and 13 are not
project lessons, and spot-checking the teacher guide shows activity text present on pages the
index did not attribute to an activity. `validate_im_ms_lesson_detail.py` only requires each
lesson to have AT LEAST ONE activity, so it passes. This needs fixing before grade 6 is swept,
since it is grade 6 Unit 8's own items that would be judged against it.

## Settled against an independent second pass (11 items)

Four readers re-derived grade 7 without seeing this file or `data/alignment.json`; the
measurement is in `provenance/alignment_second_pass_g7.md`. Eleven placements were re-read
and decided.

### Moved a unit -- all four NY-7.EE.2 items, Unit 4 Lesson 5 -> Unit 6 Lesson 12

`g7-2024-011`, `g7-2025-021`, `g7-2025-036`, `g7-2026-036` all ask the same thing: a price is
discounted by a percentage and the student picks the equivalent single-coefficient form
(x - 0.25x and 0.75x). Unit 6 Lesson 12's warm-up *20% Off* is that question verbatim, down
to offering the discount itself as the first distractor, which is what every one of these
items uses for its choice A. Unit 4 Lesson 5 describes its changes as FRACTIONS and never
shows the subtraction form. NYCPS independently places `g7-2025-021` in Unit 6 too, so three
readings put this standard outside the unit the first pass chose.

### Moved a lesson

**`g7-2023-048` and `g7-2025-048` -> Unit 4 Lesson 6.** Two items, each applying a percent
decrease to two separate prices and then comparing or summing. Lesson 6 *Increasing and
Decreasing* is where a forward percent decrease is taught; Lesson 11's subject is the
markup, commission and tip vocabulary neither item uses. The second pass put `g7-2025-048`
at Lesson 12 instead and this pass diverges: Lesson 12's "multi-step" means operations
CHAINED on one quantity, as in its cool-down where tax is added to a discounted price. Two
parallel decreases are not that, and splitting these twins would assert a distinction the
items do not make.

**`g7-2024-029` -> Unit 4 Lesson 11.** The library receives 35% of what the class earns --
a share of someone else's total, which is the commission shape Lesson 11 teaches as its own
category. Lesson 9's actual subject is fractions OF a percent (0.3%, 0.03%), which this item
never touches.

**`g7-2025-046` -> Unit 6 Lesson 20.** Simplify -5y + 3 - 6y + 10y - 1: no parentheses, so
nothing to expand. This also makes the project consistent with itself, since `g7-2024-037`
was already placed at Lesson 20 on exactly that recorded ground.

### Held, with the second pass's lesson added as evidence

**`g7-2023-041`** stays at Lesson 19 *Expanding and Factoring* -- its cool-down is
`-1/2(-2x + 4y)`, the same fractional expansion -- with Lesson 18's *Organizing Work*, where
1/2 is first distributed over a sum, cited as `introduces`.

**`g7-2024-048`** stays at Lesson 12 *Solving Multi-step Percentage Problems*, which is the
discount-then-tax chain the item performs, with Lesson 7 cited for the reverse step of
backing $575 out of $460. At p = 0.25 the item is hard precisely because it needs both.

**`g7-2024-021`** stays at Lesson 4 -- the task is writing one equation from a table -- with
Lesson 5 cited for the reciprocal distinction its distractor y = 4x turns on.

### Per-one from a table: three readings against one

`g7-2023-004` and `g7-2024-001` moved from Lesson 3 to Lesson 2. Both ask a per-one question
-- pages in 1 day, cost per package -- and Lesson 2's cool-down *Green Paint* asks exactly
that of a table before naming it as the constant. The second pass and NYCPS both read them
that way. Lesson 3 stays cited as where the constant is named and its reciprocal taught.

`g7-2023-042` moved from Lesson 6 to Lesson 4, whose cool-down *It's Snowing in Syracuse* is
the item's own structure: find a value, write the equation, then use it for a new input. The
first pass had reached for Lesson 6 because the item uses its equation, not noticing Lesson
4's cool-down already does both.
