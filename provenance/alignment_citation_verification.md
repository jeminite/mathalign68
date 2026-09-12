# Checking the citations against the PDFs rather than against the index

`preflight.py` section 9 verifies that every evidence quote appears in the activity it
cites. It does that against `data/im_ms_lessons_detail.json` — which is itself extracted
from the teacher guides. If the extractor ever mis-attributed text to an activity, the
citation and the check would be wrong together and would agree with each other.

So the citations were checked a second way: find each quote in the unit guide PDF itself
and ask whether the page the citation names is the page it is printed on.

## Result

All 140 distinct citations written for grade 7 resolve. Per unit guide, the implied offset
between the citation's page number and the PDF page holding the text is **0 or −1** and
never more, which is an activity running across a page break rather than a wrong page.

Two quotes could not be found in the PDF by literal search, and both turned out to be
correct citations. They are worth writing down because they say what the quote check does
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
