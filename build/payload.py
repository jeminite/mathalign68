#!/usr/bin/env python3
"""
Turn the canonical data into the published payload, or refuse to.

`site/data.json` is the public contract: anything built on this project should
read that file rather than the project's internals. So this module flattens the
canonical files into stable rows, and owns the two refusals that must happen
before anything reaches disk.

REFUSAL ONE: STUDENT DATA
Carried over from RegentsAlign's publish.py, which has the same list and the
same behaviour -- raise rather than write. This project holds no student data at
all, so the check should never fire; it exists because the day it does fire is
the day it matters.

REFUSAL TWO: ITEM TEXT
Specific to this project. The stems in the NYSED PDFs are vector artwork and do
not extract, so any field here that looked like a question stem would be either
hand-typed or quietly wrong -- and a subtly wrong question is worse than a link
to the real one. Publishing one would undo the central design decision, so it is
gated in code rather than left to discipline.
"""

import datetime
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")

# Anything student-derived. Same list as RegentsAlign's publish.py, extended.
BANNED_STUDENT = {
    "pctCorrect", "distractors", "zeroCredit", "results", "perStudent",
    "uid", "studentName", "osis", "roster",
}

# Anything that would present extracted prose as the question.
BANNED_ITEM_TEXT = {
    "stem", "stemHtml", "choices", "figure", "alt", "longDescription",
}

# Fields allowed to carry long prose. Everything else is capped, so a wall of
# extracted text cannot arrive in a field nobody thought to check.
LONG_TEXT_FIELDS = {"clusterText", "notes", "domainLabel", "subscore", "basis",
                    "postTestNote", "note"}
MAX_FIELD_CHARS = 300

# Subtrees the length cap does not apply to. Everything under these is written
# by this file or by data/blueprint.json -- author prose, not extracted text --
# and it is where the caveats a reader needs actually live. The banned-key
# checks still apply here; only the cap is lifted.
CAP_EXEMPT_ROOTS = ("meta", "blueprint")


class PayloadRefused(Exception):
    """Raised instead of writing. Never caught inside the build."""


def _scan(node, path=""):
    """Walk the payload and enforce both refusals plus the length cap."""
    if isinstance(node, dict):
        for key, value in node.items():
            where = "%s.%s" % (path, key) if path else key
            if key in BANNED_STUDENT:
                raise PayloadRefused(
                    "refusing to publish: %s is a student-derived field. This project "
                    "holds no student data; something has been put in the wrong folder."
                    % where)
            if key in BANNED_ITEM_TEXT:
                raise PayloadRefused(
                    "refusing to publish: %s would present item text. The stems in these "
                    "PDFs do not extract, so this field can only hold something wrong. "
                    "Link to the PDF page instead." % where)
            _scan(value, where)
    elif isinstance(node, list):
        for i, value in enumerate(node):
            _scan(value, "%s[%d]" % (path, i))
    elif isinstance(node, str):
        leaf = path.rsplit(".", 1)[-1].split("[")[0]
        root = path.split(".")[0].split("[")[0]
        if (root not in CAP_EXEMPT_ROOTS
                and leaf not in LONG_TEXT_FIELDS
                and len(node) > MAX_FIELD_CHARS):
            raise PayloadRefused(
                "refusing to publish: %s holds %d characters. Only %s may carry prose; "
                "a long string anywhere else is how extracted item text would arrive."
                % (where_of(path), len(node), ", ".join(sorted(LONG_TEXT_FIELDS))))


def where_of(path):
    return path or "(root)"


def load(name):
    with open(os.path.join(DATA, name)) as fh:
        return json.load(fh)


def build(feedback_url=None, disclaimer=None):
    items_doc = load("items.json")
    standards_doc = load("standards.json")
    blueprint = load("blueprint.json")

    alignment_path = os.path.join(DATA, "alignment.json")
    alignment = (json.load(open(alignment_path))
                 if os.path.exists(alignment_path) else
                 {"byStandard": {}, "byItem": {}, "unaligned": {}})

    by_standard = alignment.get("byStandard", {})
    by_item = alignment.get("byItem", {})

    # Only the standards actually cited, plus the ones each grade could cite.
    cited = {i["standard"] for i in items_doc["items"]}
    for i in items_doc["items"]:
        cited.update(i["secondaryStandards"])

    standards = {}
    for code, rec in standards_doc["standards"].items():
        if code not in cited and not rec["assessedOnGrades"]:
            continue
        standards[code] = {
            "code": code,
            "grade": rec["grade"],
            "domain": rec["domain"],
            "domainName": rec["domainName"],
            "clusterText": rec["clusterText"],
            "note": rec["note"],
            "postTest": rec["postTest"],
            "testedInGrade": rec["testedInGrade"],
            "assessedOnGrades": rec["assessedOnGrades"],
            "everReleased": code in cited,
        }

    rows = []
    for item in items_doc["items"]:
        align = dict(by_standard.get(item["standard"], {}))
        override = by_item.get(item["id"])
        if override:
            align.update(override)
            basis = "item-override"
        elif align:
            basis = "standard-default"
        else:
            basis = "unaligned"

        rows.append({
            "id": item["id"],
            "testId": item["testId"],
            "grade": item["grade"],
            "year": item["year"],
            "item": item["item"],
            "session": item["session"],
            "type": item["type"],
            "key": item["key"],
            "credits": item["credits"],
            "standard": item["standard"],
            "domain": item["domain"],
            "domainLabel": item["domainLabel"],
            "subscore": item["subscore"],
            "secondary": item["secondaryStandards"],
            "pValue": item["pValue"],
            "avgPointsEarned": item["avgPointsEarned"],
            "postTest": item["postTest"],
            "postTestFromGrade": item["postTestFromGrade"],
            "released": True,
            "pdfPage": item["pdfPage"],
            "printedPage": item["printedPage"],
            "sourceUrl": item["sourceUrl"],
            # Phase 3 curriculum fields. Present and null from the first
            # publish so the public contract does not change shape later.
            "course": align.get("course"),
            "unit": align.get("unit"),
            "unitTitle": align.get("unitTitle"),
            "sectionLetter": align.get("sectionLetter"),
            "sectionTitle": align.get("sectionTitle"),
            "lesson": align.get("primaryLesson"),
            "lessonTitle": align.get("lessonTitle"),
            "lessonEdition": align.get("edition"),
            "alignmentStatus": align.get("status"),
            "alignmentBasis": basis,
            "notes": align.get("notes") or align.get("why"),
        })

    tests = []
    for test in items_doc["tests"]:
        tests.append({k: v for k, v in test.items() if k != "repairs"})

    aligned = sum(1 for r in rows if r["alignmentBasis"] != "unaligned")
    payload = {
        "meta": {
            "schemaVersion": "1.0",
            "generatedBy": "publish.py",
            "built": datetime.datetime.now().isoformat(timespec="seconds"),
            "project": "MathAlign68",
            "what": "NYS Grades 6-8 mathematics tests, Next Generation standards era, "
                    "mapped to standards, statewide difficulty and the Imagine IM 6-8 "
                    "curriculum.",
            "contract": "This file is the public contract. Build on it rather than on the "
                        "project's internals: it is versioned with each deploy, contains no "
                        "student data by construction, and reproduces no item text.",
            "noItemText": "This dataset deliberately contains no question text, answer-choice "
                          "text or figures. Every numeral and figure in the NYSED released-items "
                          "PDFs is vector artwork with no text layer, so a transcription would be "
                          "hand-typed or wrong. Use sourceUrl, which points at the exact page.",
            "pValueCaveat": "pValue is NYSED's own published statewide figure. For a "
                            "constructed-response item it is average points earned divided by "
                            "total possible points, so it is not the same quantity as a "
                            "multiple-choice percent-correct -- do not put them on one axis. "
                            "NYSED does not publish the population it is computed over.",
            "releaseCaveat": blueprint["meta"]["doNotComputeReleaseShare"],
            "standardsEra": "nextgen",
            "codeShape": standards_doc["meta"]["codeShape"],
            "grades": items_doc["meta"]["grades"],
            "years": items_doc["meta"]["years"],
            "tests": len(tests),
            "releasedItems": len(rows),
            "releasedCredits": sum(r["credits"] for r in rows),
            "itemsWithPageLink": sum(1 for r in rows if r["pdfPage"]),
            "postTestItems": sum(1 for r in rows if r["postTest"]),
            "alignmentCoverage": {
                "aligned": aligned,
                "total": len(rows),
                "note": "Curriculum alignment is Phase 3. Until then alignmentBasis is "
                        "'unaligned' on every item and the lesson fields are null.",
            },
            "disclaimer": disclaimer,
            "feedbackUrl": feedback_url,
        },
        "blueprint": {
            "grades": {g: {"designedItems": spec["designedItems"],
                           "totalCredits": spec["totalCredits"],
                           "itemNumbering": spec["itemNumbering"],
                           "sessions": spec["sessions"],
                           "domainBlueprint": spec["domainBlueprint"],
                           "domainBlueprintNote": spec["domainBlueprintNote"]}
                       for g, spec in blueprint["grades"].items()},
            "domains": standards_doc["meta"]["domains"],
            "postTestLegend": standards_doc["meta"]["postTestLegend"],
            "postTestTables": standards_doc["postTestTables"],
        },
        "tests": tests,
        "standards": standards,
        "items": rows,
        "unreleased": items_doc["unreleased"],
    }

    _scan(payload)
    return payload
