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
