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

REFUSAL TWO: UNREVIEWED ITEM TEXT
This started life as a refusal to publish item text at all, because the stems in
the NYSED PDFs are vector artwork and anything auto-extracted would be either
hand-typed or quietly wrong. That reasoning was about publishing EXTRACTION
OUTPUT as if it were the question, and it still holds.

Reviewed transcription is a different thing, and the replacement rule is
stricter rather than looser: content may be published only from
data/content.json, which is written by tools/merge_content.py from a reviewed
spec and carries `reviewed: true` on every item. A stem reaching the payload by
any other route is refused, and preflight then checks separately that each
published stem's prose is character-identical to the PDF's own text layer.
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
                    "postTestNote", "note", "stem", "stemPlain", "stemHtml",
                    "stemAfter", "prose", "text", "alt", "longDescription",
                    "answer", "check", "creditLine", "source", "itemText"}
MAX_FIELD_CHARS = 300

# Subtrees the length cap does not apply to. Everything under these is written
# by this file or by data/blueprint.json -- author prose, not extracted text --
# and it is where the caveats a reader needs actually live. The banned-key
# checks still apply here; only the cap is lifted.
CAP_EXEMPT_ROOTS = ("meta", "blueprint")

# Prose-bearing subtrees that are not at the root. Exempting the whole
# `curriculum` tree would stop the cap watching 427 lesson titles, which is
# exactly the kind of field extracted text could arrive in; `curriculum.meta`
# is hand-written caveats and hazard notes and nothing else.
CAP_EXEMPT_PATHS = ("curriculum.meta",)


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
            _scan(value, where)
    elif isinstance(node, list):
        for i, value in enumerate(node):
            _scan(value, "%s[%d]" % (path, i))
    elif isinstance(node, str):
        leaf = path.rsplit(".", 1)[-1].split("[")[0]
        root = path.split(".")[0].split("[")[0]
        if (root not in CAP_EXEMPT_ROOTS
                and not path.startswith(CAP_EXEMPT_PATHS)
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

    content_path = os.path.join(DATA, "content.json")
    content_doc = (json.load(open(content_path))
                   if os.path.exists(content_path) else {"items": {}, "meta": {}})
    content = content_doc.get("items") or {}

    # The curriculum index. Optional so the site still builds before Phase 3's
    # extractors have been run; the preflight gate is what requires it.
    ref_path = os.path.join(DATA, "im_ms_reference.json")
    pacing_path = os.path.join(DATA, "im_ms_pacing.json")
    curriculum_doc = json.load(open(ref_path)) if os.path.exists(ref_path) else None
    pacing_doc = json.load(open(pacing_path)) if os.path.exists(pacing_path) else None

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

    # A standard the CURRICULUM cites has to be here too, or a lesson's standard
    # list renders codes the reader cannot look up. Several standards are taught
    # in the curriculum but have not yet appeared on a released item -- NY-8.EE.4
    # and NY-8.EE.8a/8b among them -- and those are exactly the ones a teacher
    # planning from this index would want to read.
    if curriculum_doc:
        for spec in curriculum_doc["grades"].values():
            cited.update(spec["standardToLessons"])
            for codes in spec["lessonToStandards"].values():
                cited.update(codes)

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

    unreviewed = [k for k, v in content.items() if not v.get("reviewed")]
    if unreviewed:
        raise PayloadRefused(
            "refusing to publish: %d item(s) in data/content.json are not marked "
            "reviewed (%s). Content reaches the site only through a reviewed spec."
            % (len(unreviewed), ", ".join(sorted(unreviewed)[:4])))

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

        # The transcription, when there is one. An item without a content entry
        # publishes exactly as it did before this feature existed.
        c = content.get(item["id"])
        if c:
            rows[-1].update({
                "stem": c["stemHtml"],
                "stemPlain": c["stem"],
                "stemAfter": c.get("stemAfter"),
                "creditLine": c.get("creditLine"),
                "instructions": c.get("instructions") or [],
                "display": c.get("display") or [],
                "choiceList": c.get("choices") or [],
                "figures": c.get("figures") or [],
                "tablesInImage": bool(c.get("tablesInImage")),
                "choicesInImage": bool(c.get("choicesInImage")),
                "cr": c.get("constructedResponse"),
                "transcribed": True,
            })
        else:
            rows[-1]["transcribed"] = False

    tests = []
    for test in items_doc["tests"]:
        tests.append({k: v for k, v in test.items() if k != "repairs"})

    aligned = sum(1 for r in rows if r["alignmentBasis"] != "unaligned")
    transcribed = sum(1 for r in rows if r["transcribed"])
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
            "itemText": "Where `transcribed` is true, the stem, answer choices and figures are "
                        "a reviewed transcription of the official released item, not an "
                        "automatic extraction: the prose comes from the PDF's own text layer "
                        "character for character and only the mathematics is filled in, from "
                        "vector glyph geometry. Where `transcribed` is false there is no "
                        "question text at all -- use sourceUrl, which points at the exact page. "
                        "Every item links to the official PDF either way.",
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
            "transcriptionCoverage": {
                "transcribed": transcribed,
                "total": len(rows),
                "keySources": content_doc.get("meta", {}).get("keySources") or {},
                "reviewNotes": content_doc.get("meta", {}).get("reviewNotes") or {},
            },
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

    if curriculum_doc:
        payload["curriculum"] = _curriculum(curriculum_doc, pacing_doc)

    _scan(payload)
    return payload


def _curriculum(ref, pacing):
    """The Imagine IM New York index, with pacing folded into each unit.

    Folded here rather than joined in the browser so the page cannot get the
    join wrong, and so the two files' unit keys are reconciled once, at build
    time, where a mismatch is a build failure instead of a blank cell.

    Titles are carried from the SCOPE AND SEQUENCE box, not the pacing table:
    the grade 6 guide capitalises its Unit 9 differently in the two places and
    the Scope and Sequence box is the one the lesson titles come from, so taking
    both from the same table keeps a unit and its lessons consistent."""
    out = {
        "meta": {
            "edition": ref["meta"]["edition"],
            "numbering": ref["meta"]["numbering"] if "numbering" in ref["meta"] else "newYork",
            "generated": ref["meta"]["generated"],
            "lessonCodeFormat": ref["meta"]["lessonCodeFormat"],
            "unitNumberingByTable": ref["meta"]["unitNumberingByTable"],
            "hazards": ref["meta"]["hazards"],
            "weeks": (pacing or {}).get("meta", {}).get("weeks"),
            "pacingConventions": (pacing or {}).get("meta", {}).get("conventions"),
            "pacingAgreement": (pacing or {}).get("meta", {}).get("agreement"),
        },
        "grades": {},
    }
    for grade, spec in sorted(ref["grades"].items()):
        pace = ((pacing or {}).get("grades", {}) or {}).get(grade, {})
        units = {}
        for unit, u in sorted(spec["units"].items(), key=lambda kv: int(kv[0])):
            block = pace.get(unit, {})
            if block and block.get("title", u["title"]).lower() != u["title"].lower():
                raise SystemExit(
                    "payload: grade %s unit %s is %r in the scope and sequence but "
                    "%r in the pacing table" % (grade, unit, u["title"], block["title"]))
            lessons = {}
            for n, lesson in sorted(u["lessons"].items(), key=lambda kv: int(kv[0])):
                code = "%s.%s.%s" % (grade, unit, n)
                lessons[n] = {
                    "title": lesson["title"],
                    "sectionLetter": lesson["sectionLetter"],
                    "sectionTitle": lesson["sectionTitle"],
                    "standards": spec["lessonToStandards"].get(code, []),
                    "clusters": spec.get("lessonToClusters", {}).get(code, []),
                    "optional": (block.get("optionalLessons") == "all"
                                 or int(n) in (block.get("optionalLessons") or [])),
                }
            units[unit] = {
                "title": u["title"],
                "sections": u["sections"],
                "lessons": lessons,
                "days": block.get("days"),
                "startWeek": block.get("startWeek"),
                "midUnitAssessment": block.get("midUnitAssessment"),
                "whollyOptional": block.get("optionalLessons") == "all",
            }
        out["grades"][grade] = {
            "units": units,
            "standardToLessons": {c: v["lessons"]
                                  for c, v in spec["standardToLessons"].items()},
            "tableDisagreements": spec.get("tableDisagreements", []),
            "lessonsWithoutStandards": spec.get("lessonsWithoutStandards", []),
            "counts": spec["counts"],
        }
    return out
