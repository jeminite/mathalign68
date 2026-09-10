# NYCPS "NYS Exam IM Alignment" sheets

Fetched 2026-09-10 as CSV from three public Google Sheets linked from the
`Unit N` tabs of the NYCPS pacing workbooks in `../`:

| grade | spreadsheet id |
|---|---|
| 6 | `1NSYpKWQ35tmjqfA9K0eBdOyrTWh1a3vykkvPJZvKbxg` |
| 7 | `1rM6lHrsQq33tWpuGIkrt-BOmkhg9_QLX_tI5qMBfV20` |
| 8 | `1k8zc8ADZQqtXYwIf69UhOnjieWef5P5ysdUIobk6xuo` |

Titled *Grade N NYS Exam IM Alignment* / *State Assessment Aligned Problems*.
273 rows covering Spring 2023, 2024 and 2025 — 29 per year for grade 6, 31 per
year for grades 7 and 8, which matches this project's own released-item counts
exactly. 2026 is not covered.

Columns: `Exam, Type, Q#, Grade, Unit, Section, Cluster, Standard, Curriculum Notes`.

## How much to trust it

Joined against `data/items.json`, **256 of 273 standards match exactly (94%)** and
every row corresponds to a real released item. That is meaningful mutual
corroboration: this file was authored by NYCPS, ours comes from NYSED's own Map
to the Standards.

The 17 differences are all cases where **ours is the more precise or the
authoritative reading**, so ours wins:

- compound notation merging a primary with a secondary standard —
  `NY-7.EE.4a&EE.1`, `NY-7.NS.1b&NS.1a`, `NY-7.SP.8a&SP.8b`, `NY-7.G.2/NY-8.G.5`
  (we hold these as `standard` plus `secondaryStandards`)
- a dropped sub-letter — theirs `NY-8.G.1` and `NY-8.EE.7` against our
  `NY-8.G.1a` / `NY-8.G.1b` and `NY-8.EE.7b`
- four genuine disagreements: g8-2023 item 34 (`NY-8.EE.5` vs their `NY-8.F.2`),
  g8-2024 item 30 (`NY-8.G.6` vs `NY-8.G.8`), g8-2024 item 34 (`NY-8.G.1a` vs
  `NY-8.G.2`), g8-2024 item 4. Ours is NYSED's published alignment.

## Two hazards before using the Unit column

**Unit numbering is the NATIONAL sequence, not New York.** Grade 7 item 3 of 2025
is filed under `Unit 8 Probability and Sampling`, but the Imagine IM New York
Teacher Course Guide places Probability and Sampling at **Unit 7** — New York
swaps Units 7 and 8 in grades 7 and 8. Any use of this Unit column must record
that provenance and resolve to a lesson **by title, never by number**.

**The `Curriculum Notes` prose is suggestive, not authoritative.** It cites a
specific lesson and quotes a parallel activity, but the citation sometimes
disagrees with the row's own Section field — grade 6's first row cites
"Unit 3, Lesson 7" while its Section reads `6.3.2, 6.3.3, 6.3.4, 6.3.9`. Useful
as a prompt for a human aligning an item; not evidence.

Grade 8's 2023 rows have no Curriculum Notes at all.
