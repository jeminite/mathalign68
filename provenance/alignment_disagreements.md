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
