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
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from build import payload as payload_mod          # noqa: E402
from build import render as render_mod            # noqa: E402

SITE = os.path.join(HERE, "site")
ASSETS = os.path.join(HERE, "assets")
SITE_ASSETS = os.path.join(SITE, "assets")

# Shown under the title on every page. Edit this string to change the wording.
DISCLAIMER = (
    "A working analysis, shared in case it is useful. The item data and the statewide "
    "P-values are NYSED's own, published with each year's released questions. Where a "
    "question is shown, its wording comes from the PDF's own text layer character for "
    "character and only the mathematics is reconstructed -- but reconstructed maths can "
    "be wrong, so every item links to the official page and that page is the authority. "
    "Curriculum alignment is a judgement call by one teacher rather than official "
    "guidance. Corrections and disagreement are welcome."
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

    # Copy only the figures the payload actually references, into a directory
    # cleared first. RegentsAlign learned both halves of that: a stale crop left
    # behind still matches its filename and therefore looks current, and copying
    # the whole master tree publishes superseded ones.
    referenced = sorted({f["file"] for r in payload["items"] for f in r.get("figures", [])})
    if os.path.isdir(SITE_ASSETS):
        shutil.rmtree(SITE_ASSETS)
    missing = []
    for rel in referenced:
        src = os.path.join(ASSETS, rel)
        if not os.path.exists(src):
            missing.append(rel)
            continue
        dst = os.path.join(SITE_ASSETS, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
    if missing:
        sys.exit("publish.py: refusing to publish, %d referenced image(s) are missing: %s"
                 % (len(missing), ", ".join(missing[:4])))

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
    tc = m["transcriptionCoverage"]
    print("  %d of %d items transcribed; %d figure(s) published"
          % (tc["transcribed"], tc["total"], len(referenced)))
    cov = m["alignmentCoverage"]
    print("  curriculum alignment: %d of %d items" % (cov["aligned"], cov["total"]))


if __name__ == "__main__":
    main()
