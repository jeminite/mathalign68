# The Imagine Learning guides: not in the repository, and what depends on them

Imagine IM New York's Teacher Course Guides and per-unit Teacher Guides are **gitignored**.
They are Imagine Learning's copyrighted curriculum and are not this project's to redistribute.

The three course guides were tracked until 2026-09-12, when the repository was first pushed to
GitHub and 101 MB of licensed PDF went to a third party's servers with it. They were purged from
history with `git filter-repo`, the GitHub repository was deleted and rebuilt from the clean
history, and they are now ignored alongside the per-unit guides. **Do not re-add them.**

## The edition this project was built against

Verify a restored copy against these before rebuilding anything. A different edition renumbers
lessons, and this project's whole alignment resolves lessons *by title* precisely because
editions renumber.

| file | bytes | sha256 |
|---|---|---|
| `ImagineIM_NY_6__TCG_NA_V2_EN_DIG.pdf` | 45,373,508 | `6feb7c5015d5e43b864681602975f8f6ebedf0ba8525398861a9c2cee6f89ecf` |
| `ImagineIM_NY_7__TCG_NA_V2_EN_DIG.pdf` | 43,823,920 | `019f866396b195767d348b4a6bb07765c236ec945166f544ff2d5caac75db78e` |
| `ImagineIM_NY_8__TCG_NA_V2_EN_DIG.pdf` | 11,587,306 | `e9d3d72e01c27ac8425bc5aec40a201e19e5cc836e2d4d4f2e629696515325fb` |

```bash
shasum -a 256 sources/ImagineIM_NY_?__TCG_NA_V2_EN_DIG.pdf
```

**There is no URL to fetch them from.** `provenance/sources.json` records a URL and a hash for
every NYSED source, and `tools/fetch_sources.py` re-downloads all of them unattended — but it
has no Imagine entry and no flag that could get one. These arrived by hand, and so did the nine
per-unit guides. That is a real gap: if this machine loses them, restoring them means going back
to Imagine Learning or the district, not running a script.

## What reads them, and what that costs a fresh clone

| script | reads | produces |
|---|---|---|
| `tools/extract_standards.py` | all three TCGs | the `statement` field on 110 of 146 standards in `data/standards.json` |
| `tools/extract_im_ms_lessons.py` | all three TCGs | `data/im_ms_reference.json` — units, sections, 427 lessons, the standard-to-lesson tables |
| `tools/extract_pacing.py` | all three TCGs | `data/im_ms_pacing.json` — days per unit, optional lessons, cross-checked between the three guides |
| `tools/extract_im_ms_lesson_detail.py` | the per-unit guides | `data/im_ms_lessons_detail.json`, also gitignored — it reproduces Student Task Statements verbatim |

**Every one of those outputs is committed**, so a clone builds and deploys the site without a
single PDF. What a clone cannot do is *re-derive* them, which is why `preflight.py` skips those
three regenerability checks with a reason rather than failing.

So the README's old claim — everything but `alignment.json` is reproducible from `sources/` with
no human step — now has one documented exception. The published site is unaffected: no field
that reaches `site/data.json` carries guide wording. `standards.json`'s statements are NYSNGMLS
text that Imagine reprints rather than Imagine's own authorship, and they are not published.

## What is still tracked, and why that is different

NYSED's released-items PDFs and educator guide **are** tracked. They are public state assessment
material, posted by NYSED, and every one has a public URL and sha256 in `provenance/sources.json`
that `fetch_sources.py` will re-download. NYCPS's alignment CSVs are exports of public Google
Sheets, documented in `sources/nycps/PROVENANCE.md`. Those are a different category from a
commercial publisher's curriculum.
