# The statistics blind spot

Found 2026-09-12, while placing proficiency-gating standards on the pacing calendar. It is a
finding about the *structure* of grades 6 and 7, not about any class, and nothing in the code
acts on it. Recorded because acting on it is a curriculum decision and this is the evidence.

## The shape of it

Three facts, each checkable from `site/data.json`:

1. **`6.SP` is not on the grade 6 test at all.** Zero released credits across 2023–2026. All
   fourteen `NY-6.SP.*` codes in the standards registry carry `postTest: true` and
   `testedInGrade: 7`.
2. **It is assessed on the grade 7 test**, as post-test items: 2 credits in 2023, 1 in 2024, 1 in
   2025, 3 in 2026.
3. **Unit 8, *Data Sets and Distributions*, is the only grade 6 unit that teaches it** — nine of
   the fourteen codes — and it runs **weeks 29–32** of a 35-week year, 20 to 21 days.

The grade 6 State test sits at roughly week 30.

## Why that matters

Put together: this content is taught **last**, is **never assessed in the grade in which it is
taught**, and is separated from the test that does assess it by the rest of grade 6, a summer, and
most of grade 7.

So nobody has any data on it. A grade 6 teacher finishes Unit 8 with no external check of whether
it landed, and a grade 7 teacher inherits students carrying 1–3 credits of assessed content that
was taught a year earlier by someone else and has never been measured. The analyser cannot help
here either: an ISA export reports the items on the test, and `6.SP` is not among them.

This also bounds what the per-student plans in the private counterpart can claim. Their focus
standards come from the outgoing cohort's results on the test the incoming cohort is about to sit
— which for an incoming grade 7 cohort means `6.SP` appears as something the test will ask about
and nothing in the data can say how ready anyone is for it.

## What it is not

It is not a scheduling mistake. Units have to go somewhere, the year ends after the test, and
something has to be taught in weeks 29–35. Nor is Unit 8 wasted: its payoff is real, it is simply
deferred by a year.

It is also not the same finding as the weeks-21–29 one the analyser already reports. That one is
about gating content arriving late *before its own test*. This one is about content whose test is
a year away.

## What would address it

Not decided, and deliberately not coded. The options worth weighing:

- **A September diagnostic in grade 7 on `6.SP`.** This is precisely what AlgebraTeaching built
  for its own prerequisites — two hardcoded standards placed in weeks 1–2 of its Snorkl calendar,
  carrying `purpose: 'DIAGNOSTIC — prerequisite check'`, because the prior grade's results showed
  the incoming cohort weak on content the heaviest unit assumed. The parallel is close.
- **A retention check late in grade 6**, after Unit 8, accepting that it measures nothing the
  grade 6 test will reward.
- **Moving part of Unit 8 earlier**, which costs time from units that *are* on the grade 6 test.
  The pacing evidence already argues the opposite direction for units 6 and 7, so this trade is
  not obviously worth making.

There are four years of released grade 7 items on `6.SP` to build any of these from, with NYSED's
own answers — 7 credits in total across 2023–2026. That is thin for a diagnostic and is the
constraint to design around.
