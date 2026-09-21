#!/usr/bin/env python3
"""
Turn a first-pass extraction plus a reviewed spec into data/content.json.

  python3 tools/merge_content.py g7-2026
  python3 tools/merge_content.py g7-2026 --check     # validate, write nothing

Reads  : provenance/content_<testId>_raw.json   the extractor's draft
         provenance/merge_<testId>.json         the reviewed decisions
         provenance/itemmap_<testId>.json       NYSED's own key and credits
Writes : data/content.json                      (backed up first)

WHY THE JUDGEMENT LIVES IN A SPEC FILE
Everything a person had to decide is in provenance/merge_<testId>.json rather
than in this script, so the code is identical for every test, several tests can
be prepared without touching the same file, and there is an auditable record of
what was decided and why. That pattern is RegentsAlign's and it is the part of
that project most worth copying.

WHY NOT data/items.json
items.json is script-owned: preflight re-runs the extractors and fails if it
differs from what the source PDFs produce, which is what makes it trustworthy.
Transcription is judgement and cannot be regenerated, so it lives in its own
hand-owned file and build/payload.py joins the two on item id. An item with no
content entry publishes exactly as it did before, so coverage grows test by test
with nothing half-broken in between.
"""

import argparse
import datetime
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PROV = os.path.join(ROOT, "provenance")
DATA = os.path.join(ROOT, "data")
ASSETS = os.path.join(ROOT, "assets")
OUT = os.path.join(DATA, "content.json")


def die(msg):
    sys.exit("merge_content: " + msg)


def load(path, what):
    if not os.path.exists(path):
        die("missing %s (%s)" % (os.path.relpath(path, ROOT), what))
    with open(path) as fh:
        return json.load(fh)


def plain(html):
    """The searchable, markup-free mirror of a stem.

    Unwinds this project's own span vocabulary rather than blindly stripping
    tags. RegentsAlign's equivalent carries a warning worth repeating: a regex
    written for the wrong span shape matches nothing, the blind strip then runs,
    and "x + 1/2" silently becomes "x + 12" -- a different and entirely
    plausible number.
    """
    s = html or ""
    for _ in range(4):                      # fractions nest
        s = re.sub(r'<span class="frac"><span>(.*?)</span><span>(.*?)</span></span>',
                   r"(\1)/(\2)", s)
    s = re.sub(r'<span class="radical"><span class="radicand">(.*?)</span></span>',
               r"√(\1)", s)
    s = re.sub(r'<span class="segment">(.*?)</span>', r"segment \1", s)
    s = re.sub(r'<span class="repeat">(.*?)</span>', r"\1-repeating", s)
    s = re.sub(r"<sup>(.*?)</sup>", r"^\1", s)
    s = re.sub(r"<sub>(.*?)</sub>", r"_\1", s)
    s = re.sub(r"</?(br|div|p)[^>]*>", " ", s)
    s = re.sub(r"</?[a-z][^>]*>", "", s)
    for ent, ch in (("&minus;", "−"), ("&divide;", "÷"), ("&le;", "≤"),
                    ("&ge;", "≥"), ("&lt;", "<"), ("&gt;", ">"),
                    ("&nbsp;", " "), ("&amp;", "&")):
        s = s.replace(ent, ch)
    return re.sub(r"\s+", " ", s).strip()


def main():
    ap = argparse.ArgumentParser(description="Merge a reviewed transcription.")
    ap.add_argument("testId")
    ap.add_argument("--check", action="store_true",
                    help="validate the spec against the draft; write nothing")
    args = ap.parse_args()
    test_id = args.testId

    raw = load(os.path.join(PROV, "content_%s_raw.json" % test_id), "run extract_items.py")
    spec = load(os.path.join(PROV, "merge_%s.json" % test_id), "the reviewed spec")
    imap = load(os.path.join(PROV, "itemmap_%s.json" % test_id), "run extract_item_map.py")

    if spec.get("testId") != test_id:
        die("the spec says testId %r but you asked for %r" % (spec.get("testId"), test_id))

    # ---- the answer key, which is the one thing that must not be casual ----
    key = spec.get("answerKey") or ""
    key_items = spec.get("answerKeyItems") or []
    mc = [i for i in imap["items"] if i["type"] == "Multiple Choice"]
    if len(key) != len(mc):
        die("answerKey has %d characters but the test has %d released multiple-choice "
            "items" % (len(key), len(mc)))
    if len(key_items) != len(key):
        die("answerKeyItems lists %d items for a %d-character key"
            % (len(key_items), len(key)))
    if set(key) - set("ABCD"):
        die("answerKey may only contain A-D, got %r" % sorted(set(key) - set("ABCD")))
    if not (spec.get("keySource") or "").strip():
        die("the spec needs keySource: say in prose how the key was verified")

    # The key must agree with NYSED's own item map, item by item. This is not a
    # formality: it is the check that would catch a spec transcribed by hand
    # from the wrong column or shifted by one released item.
    disagree = []
    for letter, number in zip(key, key_items):
        official = next((i["key"] for i in mc if i["item"] == number), None)
        if official is None:
            die("answerKeyItems names item %d, which is not a released "
                "multiple-choice item" % number)
        if official != letter:
            disagree.append("item %d: spec says %s, the item map says %s"
                            % (number, letter, official))
    if disagree:
        die("the spec's answer key disagrees with NYSED's item map:\n  "
            + "\n  ".join(disagree))

    # ---- constructed responses -------------------------------------------
    cr_items = [i["item"] for i in imap["items"] if i["type"] == "Constructed Response"]
    cr = spec.get("constructedResponse") or {}
    missing_cr = [n for n in cr_items if str(n) not in cr]
    if missing_cr:
        die("no answer in the spec for constructed-response item(s) %s" % missing_cr)
    for n, entry in cr.items():
        if not (entry.get("answer") or "").strip():
            die("constructed-response item %s has an empty answer" % n)
        if not (entry.get("source") or "").strip():
            die("constructed-response item %s has no source. Say where the answer came "
                "from -- for this test family that is NYSED's own exemplary response "
                "page, which is exactly the check RegentsAlign still lacks." % n)

    # ---- figures ----------------------------------------------------------
    visuals = spec.get("visuals") or {}
    referenced = {f["file"] for it in raw["items"] for f in it["figures"]}
    for path in sorted(referenced):
        entry = visuals.get(path)
        if entry is None:
            die("no visuals entry for %s. Every published figure needs alt text." % path)
        if not (entry.get("alt") or "").strip():
            die("%s has no alt text" % path)
        if not os.path.exists(os.path.join(ASSETS, path)):
            die("%s is referenced but not on disk" % path)
    orphans = sorted(set(visuals) - referenced)
    if orphans:
        print("  note: %d visuals entr(y/ies) in the spec match no figure: %s"
              % (len(orphans), ", ".join(orphans)))

    # Alt text must differ per file, or a screen-reader user gets the same
    # sentence twice for two different pictures.
    alts = {}
    for path, entry in visuals.items():
        if path in referenced:
            alts.setdefault(entry["alt"].strip(), []).append(path)
    dupes = {a: p for a, p in alts.items() if len(p) > 1}
    if dupes:
        die("two figures share alt text: %s" % dupes)

    # ---- build -----------------------------------------------------------
    tables_in_image = set(spec.get("tablesInImage") or [])
    choices_in_image = set(spec.get("choicesInImage") or [])
    stem_override = spec.get("stemHtml") or {}
    stem_after = spec.get("stemAfter") or {}

    items = {}
    for it in raw["items"]:
        n = it["item"]
        stem_html = stem_override.get(str(n), it["stemHtml"])
        figures = [{
            "file": f["file"],
            "type": visuals[f["file"]].get("type") or "Figure",
            "alt": visuals[f["file"]]["alt"],
            "longDescription": visuals[f["file"]].get("long") or "",
        } for f in it["figures"]]

        entry = {
            "id": "%s-%03d" % (test_id, n),
            "item": n,
            "stemHtml": stem_html,
            "stem": plain(stem_html),
            "prose": it["prose"],
            "creditLine": it["creditLine"],
            "instructions": it["instructions"],
            "display": [d["html"] for d in it["display"]],
            "choices": [],
            "figures": figures,
            "tablesInImage": n in tables_in_image,
            "choicesInImage": n in choices_in_image or bool(it["choicesInImage"]),
            "sourcePage": it["page"],
            "reviewed": True,
        }

        if it["choices"]:
            correct = None
            if n in key_items:
                correct = key[key_items.index(n)]
            entry["choices"] = [{
                "label": c["label"],
                "text": c["html"],
                "isCorrect": c["label"] == correct,
            } for c in it["choices"]]

        if str(n) in cr:
            entry["constructedResponse"] = {
                "answer": cr[str(n)]["answer"],
                "note": cr[str(n)].get("answerNote"),
                "source": cr[str(n)]["source"],
                "check": cr[str(n)].get("check"),
            }
        if str(n) in stem_after:
            entry["stemAfter"] = stem_after[str(n)]
        items[entry["id"]] = entry

    # Every multiple-choice item must end up with exactly one correct choice,
    # unless its choices are pictures.
    for entry in items.values():
        if entry["choices"]:
            n_correct = sum(1 for c in entry["choices"] if c["isCorrect"])
            if n_correct != 1:
                die("%s has %d correct choices" % (entry["id"], n_correct))

    existing = json.load(open(OUT)) if os.path.exists(OUT) else {"items": {}}
    merged = dict(existing.get("items") or {})
    merged.update(items)

    payload = {
        "meta": {
            "schemaVersion": "1.0",
            "generatedBy": "tools/merge_content.py",
            "updated": datetime.date.today().isoformat(),
            "note": "HAND-OWNED. The transcription: stems, choices, figures and "
                    "constructed-response answers, merged from a reviewed spec in "
                    "provenance/merge_<testId>.json. Not regenerable -- unlike "
                    "data/items.json, which is. Do not hand-edit this file either; "
                    "edit the spec and re-run tools/merge_content.py.",
            "tests": sorted({v["id"].rsplit("-", 1)[0] for v in merged.values()}),
            "items": len(merged),
            "keySources": dict(
                (existing.get("meta", {}).get("keySources") or {}),
                **{test_id: spec["keySource"]}),
            "reviewNotes": dict(
                (existing.get("meta", {}).get("reviewNotes") or {}),
                **{test_id: spec.get("reviewNotes") or []}),
        },
        "items": dict(sorted(merged.items())),
    }

    if args.check:
        print("spec validates against the draft: %d items, %d figures, %d "
              "constructed-response answers"
              % (len(items), len(referenced), len(cr)))
        return

    if os.path.exists(OUT):
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        bdir = os.path.join(PROV, "backups", stamp)
        os.makedirs(bdir, exist_ok=True)
        shutil.copy2(OUT, os.path.join(bdir, "content.json"))

    os.makedirs(DATA, exist_ok=True)
    with open(OUT, "w") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print("wrote data/content.json")
    print("  %s: %d items, %d figures, %d constructed-response answers"
          % (test_id, len(items), len(referenced), len(cr)))
    print("  %d items in the file across %s"
          % (len(merged), ", ".join(payload["meta"]["tests"])))
    for note in spec.get("reviewNotes") or []:
        print("  review note: %s" % note[:96])


if __name__ == "__main__":
    main()
