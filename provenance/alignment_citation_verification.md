# Checking the citations against the PDFs rather than against the index

`preflight.py` section 9 verifies that every evidence quote appears in the activity it
cites. It does that against `data/im_ms_lessons_detail.json` — which is itself extracted
from the teacher guides. If the extractor ever mis-attributed text to an activity, the
citation and the check would be wrong together and would agree with each other.

So the citations were checked a second way: find each quote in the unit guide PDF itself
and ask whether the page the citation names is the page it is printed on.

## Result

Grade 7's 129 evidenced items carry 365 evidence entries, which reduce to **142 distinct
citations** once the shared ones are counted once. **140 of the 142 were found in their own
unit guide by literal search.** Per unit guide the implied offset between the citation's
page number and the PDF page holding the text is **0 or −1** and never more, which is an
activity running across a page break rather than a wrong page.

The remaining two could not be found by literal search, and both turned out to be correct
citations. They are worth writing down because they say what the quote check does
and does not prove.

## The index is a cleaned rendering, not the PDF's own characters

`7.5.3` *Add 'Em Up* is printed in the guide as:

> Find each sum. 1. ​56 + ​(-56)​ 0 2. ​-240 + 370​ 130 3. ​-5.7 + ​(-4.2)​ -9.9

The parentheses around each negative are in the PDF, and `0`, `130` and `-9.9` are the
**answers, interleaved with the questions**. The index renders that as
`Find each sum. 1. 56 + -56 2. -240 + 370 3. -5.7 + -4.2`, stripping both.

`7.5.11` *Matching Division Expressions* is worse: the PDF prints

> Match each expression with its value. 5 min Addressing NY-7.NS.2.b A4 A. 15 ÷ 12

so the duration, the standard and the answer-key letters sit between the instruction and
the first choice. The index removes them.

## What follows from this

**A lesson quote is not held to the item stems' standard, and cannot be.** Published item
stems must be character-identical to the PDF's text layer — that is what makes the
transcription trustworthy. A lesson quote is checked against the index's rendering of the
activity, which is a normalisation of the guide: mathematics is reformatted, and answers
and metadata printed inline are removed.

That is the right behaviour — a quote carrying `A4` or an interleaved answer would be
unreadable — but it means **"the quote appears in the activity" is a claim about the index,
not about the PDF.** A reader following the citation to page 151 will find the words with
other text between them. The citation still lands them on the right activity, which is what
it is for.

It also means the hazard commit `88eea88` fixed — a quote that joins fragments across an
elision — can now arise from the extractor rather than from the person writing the
citation, and the quote check cannot see the difference. Re-running this PDF comparison
after a batch is the check that can.

Regenerate with the script in this commit's message, or re-derive it: for each evidence
entry, search its unit guide for the normalised quote and compare the hit's page index
against the cited page.

---

# Grade 8, after the second pass and settlement

Re-run once every grade 8 placement had been settled, because settlement moved
56 of 60 disputed entries and rewrote their evidence.

**204 distinct citations. 198 found in their own unit guide by literal search.**
The offset between the page a citation names and the PDF page holding the text:

```
  0 : 126      +1 : 53      -1 : 17      +2 : 2
```

Never more than two, which is an activity running across a page break on top of
the one-page difference between printed and PDF numbering that most of these
guides carry. Two citations name a page that is not itself among the pages
holding their quote — `8.2.6 Similarity Transformations (Part 1)` and
`8.3.7 Rising Water Levels`, both +2 — and both are long activities whose teacher
notes open on the cited page and whose student task statement prints two leaves
later. The index records an activity's START page, so this is the expected shape,
not a wrong page.

**A caution about how this was measured.** The first run of this check took the
FIRST page in the guide containing each quote, and reported offsets as large as
−59. Every one of those was the quote appearing earlier in the unit's front
matter or a "lesson at a glance" spread. Searching all pages and keeping the
nearest hit is the correct instrument; taking the first hit invents errors.

## The six not found are all rendering, not misplacement

Two are apostrophes. `7.3.8 A Circumference of 44` is printed with a typographic
apostrophe — *The circle's diameter is approximately 14 cm* — where the citation
carries a straight one. The text is on page 141, exactly as cited.

Four are mathematics drawn rather than typed, the limitation recorded in
`provenance/lesson_index_glyph_loss.md`: `√18`, `√49`, `2t + 6 = 2t + 3` and an
exponent expression that reaches the index as `2 ⋅ 2`. The index holds what the
text layer gave it, the citation quotes the index faithfully, and the PDF's own
characters differ. Nothing is misplaced.

So all 204 stand.

---

# Grade 6, after settlement and widening

**278 distinct citations. 268 found in their own unit guide by literal search.**
Offsets between the page a citation names and the PDF page holding the text:

```
  0 : 213      +1 : 40      -1 : 12      +2 : 3
```

The three at +2 are all the same activity — `6.1.11 Quadrilateral Strategies`,
cited at its start page 191 with its student task printing on 193. The index
records where an activity *starts*, so this is the expected shape.

## The ten not found are all drawn mathematics

Every one contains a fraction, an exponent or a symbol that the guides set as
vector artwork rather than type: `How many 1/8 s are in 1 1/4 ?`, `5 ÷ 1/3`,
`3 inches by 1 inch by 1 1/3 inch`, `the coefficient 1/3`, `3 x and 3x`,
`-1.5, -3`. The index holds a cleaned rendering of these; the PDF's text layer
holds nothing to match. The citations are faithful to the index, which is what
`preflight.py` checks, and the underlying text is genuinely on the cited page.

This is the same limitation recorded for grade 7 — see *The index is a cleaned
rendering, not the PDF's own characters* above — and it bites grade 6 hardest
because a sixth-grade curriculum is full of fractions. Ten of 278 is 3.6%,
against grade 8's 6 of 204.

So all 278 stand.
