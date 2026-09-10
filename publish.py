#!/usr/bin/env python3
"""
Build the publishable website.

  python3 publish.py

Reads  : data/items.json, data/standards.json, data/blueprint.json
         data/alignment.json  (optional until Phase 3)
         templates/
Writes : site/index.html   self-contained, payload embedded
         site/data.json    the public contract -- byte-identical payload

This is the file you deploy. Everything in site/ is generated: direct edits
there are lost on the next build.

PRIVACY AND SCOPE, both enforced rather than documented. build/payload.py
refuses to produce a payload containing any student-derived field, and refuses
to produce one containing anything that would present item text. Neither should
ever fire; they exist because the day one does is the day it matters.

Then run the deploy gate, which stops the upload if any check fails:

  python3 publish.py && python3 tools/preflight.py && netlify deploy --dir=site --prod
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from build import payload as payload_mod          # noqa: E402
from build import render as render_mod            # noqa: E402

SITE = os.path.join(HERE, "site")

# Shown under the title on every page. Edit this string to change the wording.
DISCLAIMER = (
    "A working analysis, shared in case it is useful. The item data is NYSED's own, "
    "published with each year's released questions; the curriculum alignment is a "
    "judgement call by one teacher rather than official guidance, and may contain "
    "mistakes. This site reproduces no question text -- every item links to the "
    "official PDF. Corrections and disagreement are welcome."
)

# Leave empty and the feedback link is omitted entirely, so the page never shows
# a dead link.
FEEDBACK_URL = ""
FEEDBACK_LABEL = "Send feedback or report an error"


def main():
    try:
        payload = payload_mod.build(feedback_url=FEEDBACK_URL or None,
                                    disclaimer=DISCLAIMER)
    except payload_mod.PayloadRefused as exc:
        sys.exit("publish.py: %s" % exc)

    html = render_mod.render(payload, DISCLAIMER, FEEDBACK_URL, FEEDBACK_LABEL)

    os.makedirs(SITE, exist_ok=True)
    with open(os.path.join(SITE, "index.html"), "w") as fh:
        fh.write(html)
    with open(os.path.join(SITE, "data.json"), "w") as fh:
        json.dump(payload, fh, indent=2)
        fh.write("\n")

    m = payload["meta"]
    print("wrote site/index.html  (%.0f KB)"
          % (len(html.encode("utf-8")) / 1024.0))
    print("wrote site/data.json   (%.0f KB)"
          % (os.path.getsize(os.path.join(SITE, "data.json")) / 1024.0))
    print("  grades %s, %d-%d, %d tests, %d released items, %d credits"
          % (m["grades"], m["years"][0], m["years"][-1], m["tests"],
             m["releasedItems"], m["releasedCredits"]))
    print("  %d items link to a PDF page, %d assess a prior-grade standard"
          % (m["itemsWithPageLink"], m["postTestItems"]))
    cov = m["alignmentCoverage"]
    print("  curriculum alignment: %d of %d items" % (cov["aligned"], cov["total"]))


if __name__ == "__main__":
    main()
