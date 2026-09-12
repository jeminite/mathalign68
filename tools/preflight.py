#!/usr/bin/env python3
"""
The deploy gate. Run it between building and uploading:

  python3 publish.py && python3 tools/preflight.py && netlify deploy --dir=site --prod

The && matters: a failure here prevents the upload.

Every check exists because something like it went wrong once, in this project or
in RegentsAlign, and each says which. Add to it whenever something slips
through. A check that cannot fail is worse than no check, so anything that
degrades to "skipped" says so loudly rather than counting as a pass.
"""

import glob
import hashlib
import json
import os
import re
import subprocess
import sys
from html.parser import HTMLParser

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
SITE = os.path.join(ROOT, "site")
PROV = os.path.join(ROOT, "provenance")

FAILED, WARNED, SKIPPED, PASSED = [], [], [], []
SECTION = [None]


def section(name):
    SECTION[0] = name
    print("\n%s" % name)


def check(name, condition, detail=""):
    if condition:
        PASSED.append(name)
        print("  ok    %s" % name)
    else:
        FAILED.append((SECTION[0], name, detail))
        print("  FAIL  %s%s" % (name, ("\n        " + detail.replace("\n", "\n        ")) if detail else ""))


def warn(name, condition, detail=""):
    if condition:
        PASSED.append(name)
        print("  ok    %s" % name)
    else:
        WARNED.append((SECTION[0], name, detail))
        print("  warn  %s%s" % (name, ("\n        " + detail.replace("\n", "\n        ")) if detail else ""))


def skipped(name, why):
    SKIPPED.append((SECTION[0], name, why))
    print("  SKIP  %s -- %s" % (name, why))


def note(msg):
    """Informational, never fails the deploy. For facts a reader should see --
    a drift worth looking at, a count worth knowing -- that are not defects."""
    print("  note  %s" % msg)


def load(path):
    with open(path) as fh:
        return json.load(fh)


# --------------------------------------------------------------------- 1. freshness

def freshness():
    section("1. Freshness -- site/ was rebuilt after the data changed")
    built = os.path.join(SITE, "index.html")
    if not os.path.exists(built):
        check("site/index.html exists", False, "run: python3 publish.py")
        return
    site_time = min(os.path.getmtime(os.path.join(SITE, f))
                    for f in ("index.html", "data.json")
                    if os.path.exists(os.path.join(SITE, f)))
    # RegentsAlign checks one canonical file. There are four or five here, and
    # the site is stale if ANY of them is newer.
    stale = []
    for name in ("items.json", "standards.json", "blueprint.json", "alignment.json",
                 "im_ms_reference.json"):
        path = os.path.join(DATA, name)
        if os.path.exists(path) and os.path.getmtime(path) > site_time:
            stale.append(name)
    check("site/ is newer than every canonical file in data/", not stale,
          "newer than the build: %s -- re-run publish.py" % ", ".join(stale))


# --------------------------------------------------------------- 2. regenerability

def regenerability():
    section("2. Regenerability -- generated data still matches its sources")
    if not glob.glob(os.path.join(PROV, "itemmap_*.json")):
        skipped("data/items.json rebuilds from provenance/", "no extractions on disk")
    else:
        out = subprocess.run([sys.executable, os.path.join(HERE, "build_items.py"), "--check"],
                             capture_output=True, text=True)
        # The check that makes hand-editing a generated file impossible to hide.
        # RegentsAlign has no equivalent, which is why re-extraction there would
        # clobber hand edits and therefore never runs.
        check("data/items.json rebuilds byte-for-byte from provenance/",
              out.returncode == 0, (out.stdout + out.stderr).strip())

    guide = os.path.join(ROOT, "sources", "3-8-educator-guide-math.pdf")
    if not os.path.exists(guide):
        skipped("data/standards.json rebuilds from the educator guide",
                "sources/3-8-educator-guide-math.pdf not on disk")
        return
    current = open(os.path.join(DATA, "standards.json")).read()
    out = subprocess.run([sys.executable, os.path.join(HERE, "extract_standards.py"),
                          "--stdout"], capture_output=True, text=True)
    strip = lambda s: re.sub(r'"generated": "[^"]*"', '"generated": "-"', s)
    check("data/standards.json rebuilds byte-for-byte from the educator guide",
          out.returncode == 0 and strip(current) == strip(out.stdout),
          (out.stderr or "the rebuilt file differs from the one on disk").strip())

    # The curriculum index, under the same regime: a hand edit to either file
    # cannot survive the gate.
    for data_file, script, needs in (
            ("im_ms_reference.json", "extract_im_ms_lessons.py",
             ["ImagineIM_NY_%d__TCG_NA_V2_EN_DIG.pdf" % g for g in (6, 7, 8)]),
            ("im_ms_pacing.json", "extract_pacing.py",
             ["ImagineIM_NY_%d__TCG_NA_V2_EN_DIG.pdf" % g for g in (6, 7, 8)])):
        label = "data/%s rebuilds byte-for-byte from the course guides" % data_file
        missing = [n for n in needs
                   if not os.path.exists(os.path.join(ROOT, "sources", n))]
        if missing:
            skipped(label, "%s not on disk" % ", ".join(missing))
            continue
        path = os.path.join(DATA, data_file)
        if not os.path.exists(path):
            skipped(label, "data/%s has not been built" % data_file)
            continue
        out = subprocess.run([sys.executable, os.path.join(HERE, script), "--stdout"],
                             capture_output=True, text=True)
        check(label,
              out.returncode == 0 and strip(open(path).read()) == strip(out.stdout),
              (out.stderr or "the rebuilt file differs from the one on disk").strip())


# ------------------------------------------------------------------- 3. the payload

def payload_counts(payload):
    section("3. Counts -- the payload agrees with data/blueprint.json")
    blueprint = load(os.path.join(DATA, "blueprint.json"))
    # Counts live in blueprint.json rather than as literals here. RegentsAlign
    # hardcodes `len(rows) == 280` in its gate, which has to be edited on every
    # ingest and so trains people to edit the gate.
    expected = sum(t["expectedReleasedItems"] for t in blueprint["tests"].values())
    check("released item count matches the blueprint (%d)" % expected,
          len(payload["items"]) == expected,
          "payload has %d" % len(payload["items"]))

    by_test = {}
    for item in payload["items"]:
        by_test[item["testId"]] = by_test.get(item["testId"], 0) + 1
    wrong = [(t, by_test.get(t, 0), s["expectedReleasedItems"])
             for t, s in blueprint["tests"].items()
             if by_test.get(t, 0) != s["expectedReleasedItems"]]
    check("every test's item count matches the blueprint", not wrong, str(wrong))

    check("all 12 tests are present", len(payload["tests"]) == len(blueprint["tests"]),
          "payload has %d tests" % len(payload["tests"]))


# ------------------------------------------------------------- 4. source manifest

def source_manifest():
    section("4. Source manifest -- the PDFs are the ones we recorded")
    manifest_path = os.path.join(PROV, "sources.json")
    if not os.path.exists(manifest_path):
        check("provenance/sources.json exists", False,
              "run: python3 tools/fetch_sources.py")
        return
    files = load(manifest_path)["files"]
    checked, changed, missing = 0, [], []
    for name, rec in files.items():
        if not rec.get("path") or not rec.get("sha256"):
            continue
        path = os.path.join(ROOT, rec["path"])
        if not os.path.exists(path):
            missing.append(rec["path"])
            continue
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        checked += 1
        if h.hexdigest() != rec["sha256"]:
            changed.append(rec["path"])
    # A silently-replaced upstream PDF would otherwise change the published data
    # with no trace.
    check("every local source PDF matches its recorded sha256 (%d checked)" % checked,
          not changed, "changed since it was recorded: %s" % ", ".join(changed))
    if missing:
        skipped("hash-check the missing sources", "not on disk: %s" % ", ".join(missing))

    blueprint = load(os.path.join(DATA, "blueprint.json"))
    no_url = [t for t in blueprint["tests"]
              if not any(r.get("kind") == "released" and
                         "g%d-%d" % (r.get("grade") or 0, r.get("year") or 0) == t
                         for r in files.values())]
    check("every test has a recorded released-items URL", not no_url, str(no_url))


# ------------------------------------------------------------ 5. item structure

def item_structure(payload):
    section("5. Item structure")
    items = payload["items"]
    standards = payload["standards"]
    blueprint = payload["blueprint"]["grades"]

    # Named for the property being asserted, not for the defect. A check that
    # prints "ok  multiple-choice key not in A-D" reads as though the defect is
    # acceptable, which is worse than no name at all.
    KEY_AD = "every multiple-choice item has a key in A-D"
    CR_NO_KEY = "no constructed-response item has an answer key"
    MC_ONE = "every multiple-choice item is worth 1 credit"
    CR_CREDITS = "every constructed-response item is worth 1, 2 or 3 credits"
    PVAL = "every P-value is in (0, 1]"
    AVG_LE = "no average points earned exceeds its item's credits"
    AVG_PRESENT = "every constructed-response item has an average points earned"
    SESSION = "every item is in session 1 or 2"
    DESIGNED = "no item number exceeds its grade's designed item count"
    IN_REG = "every standard is in the registry"
    ASSESSED = "every standard is assessed on the grade that cites it"
    POST_AGREE = "the post-test flag agrees with the code's own grade digit"
    SHAPE = "every code matches the Next Generation shape"

    problems = {k: [] for k in (KEY_AD, CR_NO_KEY, MC_ONE, CR_CREDITS, PVAL, AVG_LE,
                                AVG_PRESENT, SESSION, DESIGNED, IN_REG, ASSESSED,
                                POST_AGREE, SHAPE)}
    shape = re.compile(r"^NY-\d\.[A-Z]{1,3}\.\d+[a-z]?$")

    for i in items:
        tag = i["id"]
        if i["type"] == "Multiple Choice":
            if i["key"] not in ("A", "B", "C", "D"):
                problems[KEY_AD].append(tag)
            if i["credits"] != 1:
                problems[MC_ONE].append(tag)
        else:
            if i["key"] is not None:
                problems[CR_NO_KEY].append(tag)
            if i["credits"] not in (1, 2, 3):
                problems[CR_CREDITS].append(tag)
            if i["avgPointsEarned"] is None:
                problems[AVG_PRESENT].append(tag)
            elif i["avgPointsEarned"] > i["credits"]:
                problems[AVG_LE].append(tag)
        if not (0 < i["pValue"] <= 1):
            problems[PVAL].append(tag)
        if i["session"] not in (1, 2):
            problems[SESSION].append(tag)
        if i["item"] > blueprint[str(i["grade"])]["designedItems"]:
            problems[DESIGNED].append(tag)
        reg = standards.get(i["standard"])
        if reg is None:
            problems[IN_REG].append(tag)
        else:
            if i["grade"] not in reg["assessedOnGrades"]:
                problems[ASSESSED].append(tag)
            # Two independent reads on post-test status: the code's own grade
            # digit, and the educator guide's tables.
            if (reg["grade"] != i["grade"]) != bool(i["postTest"]):
                problems[POST_AGREE].append(tag)
        if not shape.match(i["standard"]):
            problems[SHAPE].append(tag)

    for name, offenders in problems.items():
        check(name, not offenders,
              "%d item(s): %s" % (len(offenders), ", ".join(offenders[:6])))


# ------------------------------------------------------------ 6. page map integrity

def page_links(payload):
    section("6. Page links -- no link points anywhere but its own item's page")
    tests = {t["testId"]: t for t in payload["tests"]}
    beyond, mismatched, unlinked = [], [], []
    for i in payload["items"]:
        if not i["pdfPage"]:
            unlinked.append(i["id"])
            continue
        t = tests[i["testId"]]
        if i["pdfPage"] > t["pdfPageCount"]:
            beyond.append((i["id"], i["pdfPage"], t["pdfPageCount"]))
        want = "#page=%d" % i["pdfPage"]
        if not (i["sourceUrl"] or "").endswith(want):
            mismatched.append((i["id"], i["sourceUrl"]))
    check("no page link is beyond its PDF's page count", not beyond, str(beyond[:5]))
    check("every sourceUrl fragment matches its item's pdfPage",
          not mismatched, str(mismatched[:5]))
    # Unlinked items are expected: some item numbers are vector artwork. What
    # matters is that they carry no link rather than a guessed one.
    no_link_but_fragment = [i["id"] for i in payload["items"]
                            if not i["pdfPage"] and "#page=" in (i["sourceUrl"] or "")]
    check("an item with no located page carries no page fragment",
          not no_link_but_fragment, str(no_link_but_fragment))
    print("        %d of %d items carry a page link; %d have none by design"
          % (len(payload["items"]) - len(unlinked), len(payload["items"]), len(unlinked)))


# --------------------------------------------------------- 7. blueprint sanity

def blueprint_sanity(payload):
    section("7. Blueprint sanity -- released weight against NYSED's ranges")
    # A warning, never a failure. Released items are a sample of each test and
    # the sampled share is not even constant across years, so a hard fail here
    # would be wrong.
    out = []
    for t in payload["tests"]:
        grade_bp = payload["blueprint"]["grades"][str(t["grade"])]
        items = [i for i in payload["items"] if i["testId"] == t["testId"]]
        total = sum(i["credits"] for i in items)
        for dom, rng in grade_bp["domainBlueprint"].items():
            if not rng:
                continue
            got = sum(i["credits"] for i in items if i["domain"] == dom)
            share = 100.0 * got / total if total else 0.0
            if share < rng[0] - 8 or share > rng[1] + 8:
                out.append("%s %s: %.0f%% released vs published %d-%d%%"
                           % (t["testId"], dom, share, rng[0], rng[1]))
    warn("every domain's released share is within 8 points of its published range",
         not out, "\n".join(out))


# ------------------------------------------------- 7b. standards registry

DOMAIN_WORDS = {
    "NS":  ("rational", "irrational", "number", "fraction", "divide", "multiply",
            "factor", "integer", "radical", "exponent"),
    "EE":  ("exponent", "equation", "expression", "slope", "linear", "radical",
            "inequalit", "variable", "arithmetic", "proportional"),
    "F":   ("function",),
    "RP":  ("ratio", "proportional", "rate", "percent", "unit"),
    "G":   ("congruen", "transformation", "similar", "angle", "pythagor", "volume",
            "rotation", "dilat", "area", "surface", "circle", "geometr",
            "coordinate", "classify", "two-dimensional", "shapes", "perimeter",
            "figures"),
    "SP":  ("scatter", "bivariate", "associat", "pattern", "data", "frequenc",
            "distribution", "variabilit", "probabilit", "chance", "random",
            "sample", "inference", "population", "statistic"),
    "OA":  ("expression", "pattern", "operation"),
    "NBT": ("place value", "decimal", "multi-digit", "operations"),
    "MD":  ("measure", "data", "volume", "angle", "convert"),
    "NF":  ("fraction", "decimal"),
}


def standards_registry():
    """Three invariants on data/standards.json's chart-derived fields.

    All three exist because seven standards shipped with the WRONG cluster
    description -- NY-8.G.1a/1b/1c (rigid transformations) described as "Use
    functions to model relationships between quantities", plus NY-8.EE.1,
    NY-8.EE.4, NY-5.NBT.4 and NY-6.EE.8. The educator guide's chart uses merged
    cells, and assigning them by where the text sits rather than by the table's
    own drawn rules put those seven under a neighbouring cluster. clusterText is
    displayed on the site, so a teacher read it.

    None of these three checks would have passed with that data, and none of
    them depends on the extractor being right -- they test the output."""
    section("7b. Standards registry -- chart-derived fields")
    reg = load(os.path.join(ROOT, "data", "standards.json"))["standards"]

    # A domain letter names exactly one domain. If a code took its neighbour's
    # cell, the letter picks up two different printed names.
    names = {}
    for code, rec in reg.items():
        if rec.get("domainNameInGuide"):
            names.setdefault(rec["domain"], set()).add(rec["domainNameInGuide"])
    split = ["%s: %s" % (d, sorted(v)) for d, v in sorted(names.items()) if len(v) > 1]
    check("each domain letter maps to exactly one printed domain name",
          not split, "\n".join(split))

    # Cluster descriptions are complete sentences in the guide. A cell whose
    # text was clipped or half-joined does not end in a full stop.
    cut = ["%s: %r" % (c, r["clusterText"]) for c, r in sorted(reg.items())
           if r.get("clusterText") and not r["clusterText"].rstrip().endswith(".")]
    check("every cluster description is a complete sentence",
          not cut, "\n".join(cut))

    # The cluster description has to be about its own domain. This is the check
    # that catches a cross-domain steal, which is the damaging kind.
    #
    # NY-7.SP.1 is a known DEFECT IN THE SOURCE, not a mis-read: the guide's own
    # cluster cell is merged across NY-7.SP.1, 7.SP.3 and 7.SP.4 (one ruled cell
    # from y=406.0 to y=455.0 on the grade 7 chart) and labelled with the
    # comparative-inferences cluster, so NYSED omits the random-sampling cluster
    # heading that 7.SP.1 belongs to. We publish what the guide says.
    off = []
    for code, rec in sorted(reg.items()):
        text = (rec.get("clusterText") or "").lower()
        if not text:
            continue
        if not any(w in text for w in DOMAIN_WORDS.get(rec["domain"], ())):
            off.append("%s (%s): %s" % (code, rec["domain"], rec["clusterText"]))
    check("every cluster description is about its own domain",
          not off, "\n".join(off))


# ------------------------------------------------- 7c. the curriculum index

def curriculum_index(payload):
    """The published index, checked against the files it was built from.

    The deep checks on the numbering itself live in
    tools/validate_im_ms_lessons.py, which this runs rather than duplicates.
    What is checked HERE is the part that gate cannot see: that what reached
    site/data.json is the same thing, and that every lesson in it can be joined
    to a standard a reader can look up."""
    section("7c. Curriculum index -- Imagine IM New York, 6-8")
    if "curriculum" not in payload:
        skipped("the curriculum index is published", "payload carries no curriculum block")
        return

    gate = os.path.join(HERE, "validate_im_ms_lessons.py")
    if os.path.exists(gate):
        out = subprocess.run([sys.executable, gate], capture_output=True, text=True,
                             timeout=600)
        body = out.stdout + out.stderr
        check("the curriculum numbering passes its own validation gate",
              out.returncode == 0 and "safe to build on" in body,
              "\n".join(body.strip().split("\n")[-12:]))

    cur = payload["curriculum"]["grades"]
    check("the index covers grades 6, 7 and 8",
          sorted(cur) == ["6", "7", "8"], "found %s" % sorted(cur))

    # Every unit must carry pacing. A unit with days=None renders an empty cell,
    # which reads as "no lessons scheduled" rather than "not extracted".
    gaps = ["grade %s unit %s" % (g, u) for g, spec in sorted(cur.items())
            for u, unit in sorted(spec["units"].items(), key=lambda kv: int(kv[0]))
            if not unit.get("days") or unit.get("startWeek") is None]
    check("every unit carries its day range and start week",
          not gaps, ", ".join(gaps))

    # Lesson-level standards must be resolvable against the payload's own
    # standards table, allowing for parent codes whose sub-standards are there.
    # Unresolvable ones are reported, not failed: the guides index every NGMLS
    # standard while the payload holds only the tested ones.
    known = set(payload["standards"])
    unresolved, lessons, with_standards = set(), 0, 0
    for g, spec in sorted(cur.items()):
        for u, unit in spec["units"].items():
            for n, lesson in unit["lessons"].items():
                lessons += 1
                if lesson["standards"]:
                    with_standards += 1
                for code in lesson["standards"]:
                    kids = [c for c in known
                            if c.startswith(code) and len(c) == len(code) + 1]
                    if code not in known and not kids:
                        unresolved.add(code)
    # Not "every lesson cites a standard" -- 17 genuinely do not. IM opens most
    # units with an invitation to the mathematics that addresses no standard,
    # and the guide's Standards Addressed cell for it is blank. So the check is
    # that the lessons with nothing cited are exactly the ones the data records,
    # which fails on a new one (an extraction miss) and on a vanished one.
    recorded = {lid for spec in cur.values()
                for lid in spec.get("lessonsWithoutStandards", [])}
    bare = {"%s.%s.%s" % (g, u, n) for g, spec in cur.items()
            for u, unit in spec["units"].items()
            for n, lesson in unit["lessons"].items()
            if not lesson["standards"] and not lesson["clusters"]}
    check("the lessons citing no standard are exactly the ones recorded as such",
          bare == recorded,
          "unrecorded: %s\nrecorded but now cited: %s"
          % (", ".join(sorted(bare - recorded)) or "none",
             ", ".join(sorted(recorded - bare)) or "none"))
    print("        %d lessons across three grades; %d cite a standard directly, "
          "%d cite only a cluster, %d none (the guide lists none)"
          % (lessons, with_standards, lessons - with_standards - len(bare), len(bare)))
    if unresolved:
        print("  note  %d cited code(s) have no counterpart in the payload's "
              "standards table: %s" % (len(unresolved), ", ".join(sorted(unresolved))))

    # The hazards have to travel with the data. They are the reason the site can
    # be trusted about unit numbering at all.
    check("the unit-numbering hazards are published alongside the index",
          len(payload["curriculum"]["meta"].get("hazards", [])) >= 5,
          "%d recorded" % len(payload["curriculum"]["meta"].get("hazards", [])))


# ------------------------------------------- 7d. the derived unit filter

def derived_unit_filter(payload):
    """The Questions and Items tabs filter by unit without any per-item alignment.

    The unit is DERIVED in the browser: an item's standard is looked up in the
    curriculum index, and the units whose lessons teach it are the answer. These
    checks re-derive the same mapping here, in different code, and assert the
    two properties that make the feature safe to publish.

    The first is the important one. A derived unit is not an alignment, and the
    moment it is written onto an item it starts reading like one. Section 9
    already asserts the negative while data/alignment.json is absent; this names
    the dependency so nobody satisfies that check later by populating the fields
    and quietly turns a derivation into a claim."""
    section("7d. Derived unit filter")
    if "curriculum" not in payload:
        skipped("the derived unit filter has options for every grade",
                "payload carries no curriculum block")
        return

    # A derived unit is not an alignment, and the moment it is written onto an
    # item it starts reading like one. Before data/alignment.json existed this
    # asserted the flat negative. Now that a real per-item alignment exists the
    # claim has to be stronger, not weaker: a populated unit must trace to an
    # alignment ENTRY, never to the browser's derivation.
    align_path = os.path.join(DATA, "alignment.json")
    populated = [i for i in payload["items"]
                 if i.get("unit") is not None or i.get("lesson") is not None
                 or i.get("sectionLetter") is not None]
    if not os.path.exists(align_path):
        check("no derived unit has been written onto an item",
              not populated,
              "%d item(s) carry a unit or lesson, e.g. %s -- the unit filter "
              "derives these in the browser and they must stay null until a real "
              "per-item alignment exists"
              % (len(populated), ", ".join(i["id"] for i in populated[:5])))
    else:
        untraceable = [i["id"] for i in populated if i["alignmentBasis"] == "unaligned"]
        check("every populated unit traces to an alignment entry, not a derivation",
              not untraceable,
              "%d item(s) carry a unit or lesson while alignmentBasis is "
              "'unaligned', e.g. %s -- that is the browser's derivation leaking "
              "into the payload as though it were a judgement"
              % (len(untraceable), ", ".join(untraceable[:5])))

    known = set(payload["standards"])

    def expand(code):
        if code in known:
            return [code]
        return sorted(c for c in known
                      if c.startswith(code) and len(c) == len(code) + 1
                      and c[-1].isalpha())

    empty, coverage = [], []
    for grade, spec in sorted(payload["curriculum"]["grades"].items()):
        index = {}
        for code, lessons in spec["standardToLessons"].items():
            units = {l.split(".")[1] for l in lessons}
            for c in (expand(code) or [code]):
                index.setdefault(c, set()).update(units)
        items = [i for i in payload["items"] if i["grade"] == int(grade)]
        units, bare = set(), 0
        for item in items:
            hit = set(index.get(item["standard"], ()))
            for c in item.get("secondary") or []:
                hit |= set(index.get(c, ()))
            if hit:
                units |= hit
            else:
                bare += 1
        if not units:
            empty.append("grade %s" % grade)
        coverage.append("grade %s: %d unit options over %d items, %d with no unit"
                        % (grade, len(units), len(items), bare))

    # An empty option list means the standard-to-lesson join silently broke --
    # a parent-code regression would do it -- and the dropdown would render with
    # nothing in it rather than failing.
    check("the derived unit filter has options for every grade",
          not empty, "no unit resolves for %s" % ", ".join(empty))

    # The caveat has to ship with the filter. A unit dropdown with no note beside
    # it reads as an alignment, which is exactly what this is not.
    html = open(os.path.join(SITE, "index.html")).read()
    check("the derived-unit caveat ships with the filter",
          "derived from the standard, not assigned per item" in html)
    for line in coverage:
        print("        %s" % line)


# ----------------------------------------------------------------- 8. no item text

def transcription(payload):
    section("8. Transcription integrity")
    rows = [r for r in payload["items"] if r.get("transcribed")]
    if not rows:
        skipped("published stems match the PDF's own prose", "nothing transcribed yet")
        check("no item text reached the payload without a reviewed transcription",
              not any(r.get("stem") for r in payload["items"]))
        return

    print("        %d of %d items transcribed" % (len(rows), len(payload["items"])))

    # ---- the check that makes this trustworthy -------------------------
    # Strip the markup and the decoded mathematics out of a published stem and
    # what is left must be the PDF's own text layer, character for character.
    # The prose is never retyped, so "nothing was invented, dropped or reworded"
    # is proven rather than asserted.
    # ---- the drafts, which hold the PDF's own prose --------------------
    # Prose fidelity proves nothing was INVENTED. It does not prove nothing was
    # LOST: during development a fix made nine items lose their inline
    # mathematics entirely -- item 48 went back to "a one time fee of  to rent
    # shoes" -- and prose fidelity still passed on all 42. Every hole the
    # extractor located must therefore be accounted for.
    drafts = {}
    for path in glob.glob(os.path.join(PROV, "content_*_raw.json")):
        doc = load(path)
        for it in doc["items"]:
            drafts["%s-%03d" % (doc["meta"]["testId"], it["item"])] = it
    if not drafts:
        skipped("published stems match the PDF's own prose", "no extractor drafts on disk")
        skipped("every located hole is filled", "no extractor drafts on disk")
    else:
        bad_prose = []
        for r in rows:
            draft = drafts.get(r["id"])
            if draft is None:
                continue
            if bare_prose(r["stem"]) != squash(draft["prose"]):
                bad_prose.append(r["id"])
        check("every published stem's prose is character-identical to the PDF's "
              "text layer", not bad_prose,
              "%d item(s): %s" % (len(bad_prose), ", ".join(bad_prose[:6])))

        unfilled, no_draft = [], []
        for r in rows:
            draft = drafts.get(r["id"])
            if draft is None:
                no_draft.append(r["id"])
                continue
            if draft["unresolved"]:
                unfilled.append("%s (%d)" % (r["id"], len(draft["unresolved"])))
        check("no published item still has an unresolved hole",
              not unfilled, "%d item(s): %s" % (len(unfilled), ", ".join(unfilled[:6])))
        check("every published transcription has an extractor draft behind it",
              not no_draft, ", ".join(no_draft[:6]))

    # ---- structure -----------------------------------------------------
    problems = {
        "every stem, stemAfter and choice has balanced tags": [],
        "no multiple-choice item has fewer than 4 choices": [],
        "exactly one choice is marked correct": [],
        "no published choice is empty": [],
        "every constructed-response item has an answer": [],
        "no ligature or unmapped-glyph damage survives": [],
        "no hair or thin space survives": [],
        "no function name is kerned open, as in f (x)": [],
    }
    for r in rows:
        tag = r["id"]
        texts = [r.get("stem") or "", r.get("stemAfter") or ""]
        texts += [c.get("text") or "" for c in (r.get("choiceList") or [])]
        for t in texts:
            if not balanced(t):
                problems["every stem, stemAfter and choice has balanced tags"].append(tag)
                break
        blob = " ".join(texts)
        if re.search(r"[\u0100\u0101\ufffd]", blob):
            problems["no ligature or unmapped-glyph damage survives"].append(tag)
        if re.search(r"[\u2009\u200a]", blob):
            problems["no hair or thin space survives"].append(tag)
        if KERN.search(strip_tags(blob)):
            problems["no function name is kerned open, as in f (x)"].append(tag)

        choices = r.get("choiceList") or []
        if r["type"] == "Multiple Choice" and not r.get("choicesInImage"):
            if len(choices) < 4:
                problems["no multiple-choice item has fewer than 4 choices"].append(tag)
            elif sum(1 for c in choices if c["isCorrect"]) != 1:
                problems["exactly one choice is marked correct"].append(tag)
            elif any(not strip_tags(c["text"]).strip() for c in choices):
                problems["no published choice is empty"].append(tag)
        if r["type"] != "Multiple Choice" and not r.get("cr", {}):
            problems["every constructed-response item has an answer"].append(tag)

    for name, offenders in problems.items():
        check(name, not offenders,
              "%d item(s): %s" % (len(offenders), ", ".join(offenders[:6])))

    # ---- the key, and the answers --------------------------------------
    imap_keys = {}
    for path in glob.glob(os.path.join(PROV, "itemmap_*.json")):
        doc = load(path)
        for it in doc["items"]:
            imap_keys["%s-%03d" % (doc["meta"]["testId"], it["item"])] = it["key"]
    wrong_key = []
    for r in rows:
        choices = r.get("choiceList") or []
        if not choices:
            continue
        published = next((c["label"] for c in choices if c["isCorrect"]), None)
        official = imap_keys.get(r["id"])
        if official and published and official != published:
            wrong_key.append("%s: published %s, item map %s" % (r["id"], published, official))
    check("every published correct choice matches NYSED's own item map",
          not wrong_key, "; ".join(wrong_key[:4]))

    # Closes the hole RegentsAlign's RESUME #64 still records: there, no
    # constructed-response answer has ever been checked against an official
    # source. Here every one cites its exemplary-response page.
    no_source = [r["id"] for r in rows
                 if r.get("cr") and not (r["cr"].get("source") or "").strip()]
    check("every constructed-response answer cites an official source",
          not no_source, ", ".join(no_source[:6]))

    # ---- figures -------------------------------------------------------
    missing, no_alt = [], []
    used, alts = set(), {}
    for r in rows:
        for f in r.get("figures") or []:
            used.add(f["file"])
            if not os.path.exists(os.path.join(SITE, "assets", f["file"])):
                missing.append(f["file"])
            if not (f.get("alt") or "").strip():
                no_alt.append(f["file"])
            alts.setdefault((f.get("alt") or "").strip(), set()).add(f["file"])
    check("every referenced figure is published", not missing, ", ".join(missing[:4]))
    check("every figure has alt text", not no_alt, ", ".join(no_alt[:4]))
    shared = {a: sorted(fs) for a, fs in alts.items() if len(fs) > 1}
    check("no two figures share alt text", not shared, str(shared)[:200])

    unref = []
    adir = os.path.join(SITE, "assets")
    for root, _, files in os.walk(adir):
        for f in files:
            rel = os.path.relpath(os.path.join(root, f), adir)
            if rel not in used:
                unref.append(rel)
    warn("no unreferenced image in site/assets", not unref,
         "%d file(s), e.g. %s" % (len(unref), unref[0] if unref else ""))

    # ---- the page tells the reader what this is ------------------------
    html = open(os.path.join(SITE, "index.html")).read()
    check("the built page explains where the question text comes from",
          "text layer" in html or "reviewed transcription" in html,
          "a reader needs to know the stem is a transcription, not the scan")


def squash(text):
    return re.sub(r"\s+", "", text)


def strip_tags(html):
    return re.sub(r"<[^>]+>", "", html or "")


def bare_prose(html):
    """A stem with all markup and all decoded mathematics removed.

    The maths spans have to be removed by tracking depth, not by a regex: they
    contain fraction spans, and a non-greedy regex stops at the inner </span>.
    """
    out, i = [], 0
    html = html or ""
    while i < len(html):
        m = re.compile(r'<span class="math">').match(html, i)
        if not m:
            out.append(html[i])
            i += 1
            continue
        depth, j = 1, m.end()
        while j < len(html) and depth:
            if html.startswith("<span", j):
                depth += 1
                j = html.index(">", j) + 1
            elif html.startswith("</span>", j):
                depth -= 1
                j += 7
            else:
                j += 1
        i = j
    text = re.sub(r"<span[^>]*>|</span>|\u27e6\?\u27e7", "", "".join(out))
    for ent, ch in (("&lt;", "<"), ("&gt;", ">"), ("&amp;", "&"), ("&nbsp;", " "),
                    ("&minus;", "\u2212"), ("&divide;", "\u00f7"),
                    ("&le;", "\u2264"), ("&ge;", "\u2265")):
        text = text.replace(ent, ch)
    return squash(text)


class Balance(HTMLParser):
    """Counts unclosed tags. Void elements need no closing."""

    VOID = {"br", "img", "hr", "input", "meta", "link"}

    def __init__(self):
        super().__init__()
        self.depth = 0
        self.bad = False

    def handle_starttag(self, tag, attrs):
        if tag not in self.VOID:
            self.depth += 1

    def handle_endtag(self, tag):
        self.depth -= 1
        if self.depth < 0:
            self.bad = True


def balanced(html):
    p = Balance()
    p.feed(html or "")
    return p.depth == 0 and not p.bad


# NYSED kerns a function name with a HAIR SPACE -- "f (x)" -- so the italic f
# does not collide with the parenthesis. Collapsing that into an ordinary space
# publishes "f (x)", which reads as a typo. RegentsAlign shipped it 25 times
# across four exams before anyone noticed. The pattern is deliberately narrow: a
# SINGLE-letter name, a space, then a parenthesised variable optionally plus or
# minus an integer. A wider rule flags "Time (seconds)", where the space is real.
KERN = re.compile(r"(?<![A-Za-z0-9])[A-Za-z] \([A-Za-z](?:\s*[-+\u2212]\s*\d+)?\)")


# -------------------------------------------------------------------- 9. alignment

def _squash(t):
    """Compare quotes on words alone: apostrophes and dashes differ between the
    PDF's typography and anything retyped from it."""
    t = (t or "").lower().replace("\u2019", "'").replace("\u2018", "'")
    t = t.replace("\u2013", "-").replace("\u2014", "-")
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def _norm_title(t):
    t = (t or "").lower().replace("\u2019", "'").replace("\u2018", "'")
    t = t.replace("\u2013", "-").replace("\u2014", "-")
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def alignment(payload):
    section("9. Curriculum alignment integrity")
    path = os.path.join(DATA, "alignment.json")
    if not os.path.exists(path):
        skipped("alignment entries resolve to real lessons",
                "data/alignment.json does not exist yet (Phase 3)")
        cov = payload["meta"]["alignmentCoverage"]
        check("the page does not claim alignment it does not have",
              cov["aligned"] == 0 and all(i["lesson"] is None for i in payload["items"]),
              "alignmentCoverage says %d aligned but lesson fields are populated"
              % cov["aligned"])
        return
    align = load(path)
    by_std = align.get("byStandard", {})
    by_item = align.get("byItem", {})

    # Drafts are dropped by build/payload.py, so this asserts that the drop
    # actually happened rather than trusting it. byItem is checked as well as
    # byStandard: the original check looked only at byStandard, and a drafted
    # per-item entry -- which is what this project now writes -- was invisible.
    drafted_std = {c for c, e in by_std.items() if e.get("draft")}
    drafted_item = {i for i, e in by_item.items() if e.get("draft")}
    published_std = {i["standard"] for i in payload["items"]
                     if i["alignmentBasis"] != "unaligned"}
    published_item = {i["id"] for i in payload["items"]
                      if i["alignmentBasis"] != "unaligned"}
    leaked = sorted((drafted_std & published_std) | (drafted_item & published_item))
    check("no draft alignment entry reached the payload", not leaked, str(leaked[:8]))
    note("%d of %d entries are still in draft and are not published"
         % (len(drafted_std) + len(drafted_item), len(by_std) + len(by_item)))

    # An entry may legitimately stop at the unit -- a grade whose per-unit
    # teacher guides are not on disk cannot produce lesson-level evidence -- so
    # the demand is keyed off the entry's own status rather than applied flatly.
    UNIT_ONLY = ("candidates-only", "no-lesson-found")
    unresolved = [i["id"] for i in payload["items"]
                  if i["alignmentBasis"] != "unaligned" and not i["lessonTitle"]
                  and i.get("alignmentStatus") not in UNIT_ONLY]
    check("every aligned item carries a lesson title, unless its status says otherwise",
          not unresolved, str(unresolved[:5]))

    # Everything below checks the ENTRIES, published or not, because a drafted
    # entry with a wrong citation should be caught while it is being written and
    # not on the day someone clears its draft flag.
    ref_path = os.path.join(DATA, "im_ms_reference.json")
    ref = load(ref_path)["grades"] if os.path.exists(ref_path) else {}

    def lesson_record(course_grade, unit, num):
        try:
            return ref[str(course_grade)]["units"][str(unit)]["lessons"][str(num)]
        except (KeyError, TypeError):
            return None

    def grade_of(entry, item_id):
        # The grade whose curriculum teaches it, which for a prior-grade standard
        # is not the grade of the test the item sits on.
        m = re.search(r"Grade\s+([678])", entry.get("course") or "")
        return m.group(1) if m else (item_id[1] if item_id.startswith("g") else None)

    # The lesson-detail index is gitignored (it reproduces licensed task text),
    # so quote fidelity can only be checked on a machine that has rebuilt it.
    detail_path = os.path.join(DATA, "im_ms_lessons_detail.json")
    detail = load(detail_path) if os.path.exists(detail_path) else None

    def activity_text(course_grade, unit, num, activity):
        try:
            rec = detail["grades"][str(course_grade)]["units"][str(unit)]["lessons"][str(num)]
        except (KeyError, TypeError):
            return None
        for a in rec.get("activities", []):
            if _norm_title(a.get("name")) == _norm_title(activity):
                return " ".join(filter(None, [a.get("studentTaskStatement"),
                                              a.get("activityNarrative"),
                                              a.get("studentTaskAnswer")]))
        for pp in rec.get("practiceProblems", []):
            if _norm_title(pp.get("problem")) == _norm_title(activity):
                return pp.get("prompt")
        return ""

    def activity_page(course_grade, unit, num, activity):
        """The page the index says this activity starts on, or None if unknown."""
        try:
            rec = detail["grades"][str(course_grade)]["units"][str(unit)]["lessons"][str(num)]
        except (KeyError, TypeError):
            return None
        for a in rec.get("activities", []):
            if _norm_title(a.get("name")) == _norm_title(activity):
                return a.get("page")
        for pp in rec.get("practiceProblems", []):
            if _norm_title(pp.get("problem")) == _norm_title(activity):
                return pp.get("page")
        return None

    missing, mistitled, wrong_unit, thin, longquote = [], [], [], [], []
    noactivity, unquoted, wrongpage = [], [], []
    for item_id, entry in sorted(by_item.items()):
        g = grade_of(entry, item_id)
        for ev in entry.get("evidence") or []:
            where = "%s -> %s.%s.%s" % (item_id, g, entry.get("unit"), ev.get("lesson"))
            rec = lesson_record(g, entry.get("unit"), ev.get("lesson"))
            if rec is None:
                missing.append(where)
                continue
            # RESOLVE BY TITLE, NEVER BY NUMBER. A citation that names a lesson
            # number and a title that do not belong together is the exact shape
            # of the error an edition renumbering produces, and the only way to
            # see it is to check the pair.
            if _norm_title(rec["title"]) != _norm_title(ev.get("lessonTitle")):
                mistitled.append("%s: index %r, entry %r"
                                 % (where, rec["title"], ev.get("lessonTitle")))
            if not ev.get("activity") or not ev.get("page"):
                thin.append(where)
            words = len((ev.get("quote") or "").split())
            if words > 15:
                longquote.append("%s: %d words" % (where, words))
            # A quote nobody can find is not evidence. This is the check that
            # makes the published citation worth anything: the words must appear
            # in the activity the entry names, in the text extracted from the
            # teacher guide itself.
            if detail is not None and ev.get("activity"):
                hay = activity_text(g, entry.get("unit"), ev.get("lesson"),
                                    ev["activity"])
                # A page number was required to be PRESENT but never to be true,
                # so a transposed digit was invisible -- and the page is half of
                # what makes a citation checkable by a reader. The index knows
                # where every activity starts; all 161 evidence pages written
                # before this check matched it exactly, so exact is the bar.
                idx_page = activity_page(g, entry.get("unit"), ev.get("lesson"),
                                         ev["activity"])
                if idx_page is not None and ev.get("page") != idx_page:
                    wrongpage.append("%s %r: entry says p%s, index says p%s"
                                     % (item_id, ev["activity"], ev.get("page"),
                                        idx_page))
                if hay is None:
                    continue
                if not hay:
                    noactivity.append("%s: no activity named %r in %s"
                                      % (item_id, ev["activity"], where))
                elif ev.get("quote"):
                    a = _squash(ev["quote"])
                    b = _squash(hay)
                    if a not in b:
                        unquoted.append("%s %r not found in %r"
                                        % (item_id, ev["quote"][:60],
                                           ev["activity"]))
        prim = entry.get("primaryLesson")
        if prim is not None:
            rec = lesson_record(g, entry.get("unit"), prim)
            if rec is None:
                missing.append("%s primaryLesson %s" % (item_id, prim))
            elif _norm_title(rec["title"]) != _norm_title(entry.get("lessonTitle")):
                mistitled.append("%s primaryLesson: index %r, entry %r"
                                 % (item_id, rec["title"], entry.get("lessonTitle")))
            elif entry.get("evidence") and prim not in [e.get("lesson") for e
                                                        in entry["evidence"]]:
                wrong_unit.append("%s: primaryLesson %s has no evidence entry"
                                  % (item_id, prim))

    check("every cited lesson exists in the curriculum index",
          not missing, "\n".join(missing[:8]))
    check("every cited lesson's title matches the index",
          not mistitled, "\n".join(mistitled[:8]))
    check("every primary lesson is one the evidence actually supports",
          not wrong_unit, "\n".join(wrong_unit[:8]))
    check("every piece of evidence names an activity and a page",
          not thin, "\n".join(thin[:8]))
    check("no evidence quote exceeds 15 words",
          not longquote, "\n".join(longquote[:8]))
    if detail is None:
        skipped("every evidence quote appears in the activity it cites",
                "data/im_ms_lessons_detail.json is not on this machine -- rebuild "
                "it with tools/extract_im_ms_lesson_detail.py")
    else:
        check("every cited activity exists in the lesson",
              not noactivity, "\n".join(noactivity[:8]))
        check("every evidence quote appears in the activity it cites",
              not unquoted, "\n".join(unquoted[:8]))
        check("every evidence page is the page the index gives that activity",
              not wrongpage, "\n".join(wrongpage[:8]))

    # Reported, never failed. RegentsAlign's audit found 25 standards whose
    # questions had drifted to different lessons and judged 9 of them legitimate
    # content variation, so a drift is a prompt to look, not a defect.
    drift = {}
    for item_id, entry in by_item.items():
        std = next((i["standard"] for i in payload["items"] if i["id"] == item_id), None)
        if std and entry.get("primaryLesson") is not None:
            drift.setdefault(std, set()).add((entry.get("unit"), entry["primaryLesson"]))
    spread = {k: v for k, v in drift.items() if len(v) > 1}
    if spread:
        note("%d standard(s) place their items at more than one lesson -- check "
             "each is a real difference in what the items ask, not drift"
             % len(spread))
        for k in sorted(spread)[:8]:
            note("  %s: %s" % (k, sorted(spread[k])))


# --------------------------------------------------------------------- 10. privacy

def privacy(payload):
    section("10. Privacy -- nothing student-derived reached site/")
    banned = {"pctCorrect", "distractors", "zeroCredit", "results", "perStudent",
              "uid", "studentName", "osis", "roster"}
    found = set()

    def walk(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if k in banned:
                    found.add(k)
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(payload)
    check("no student-derived field in the payload", not found, ", ".join(sorted(found)))

    # Scan the built files for identifier-shaped text. Comments are stripped
    # first, or prose *about* privacy counts as evidence of a breach -- a
    # false positive RegentsAlign hit and fixed the same way.
    for name in ("index.html", "data.json"):
        path = os.path.join(SITE, name)
        if not os.path.exists(path):
            continue
        text = open(path).read()
        text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
        text = re.sub(r"(?m)^\s*//.*$", " ", text)
        text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
        osis = re.findall(r"\b\d{9}\b", text)
        names = re.findall(r"\b[A-Z]{2,}, ?[A-Z]{2,}\b", text)
        check("site/%s has no OSIS-shaped 9-digit runs" % name, not osis,
              "found %d, e.g. %s" % (len(osis), osis[:3]))
        check("site/%s has no SURNAME, FORENAME patterns" % name, not names,
              "found %s" % names[:3])

    analyze = os.path.join(SITE, "analyze")
    if not os.path.exists(analyze):
        skipped("the analyze page fetches nothing but ../data.json",
                "site/analyze/ does not exist yet (Phase 2)")
    else:
        blob = "".join(open(os.path.join(analyze, f)).read()
                       for f in os.listdir(analyze) if f.endswith((".html", ".js")))
        urls = re.findall(r"""(?:fetch|XMLHttpRequest|src\s*=|href\s*=)\s*\(?\s*["']([^"']+)""", blob)
        outside = [u for u in urls
                   if u.startswith(("http://", "https://", "//"))
                   and "nysedregents.org" not in u and "nysed.gov" not in u]
        check("the analyze page loads nothing from a third-party origin",
              not outside, str(sorted(set(outside))))


# ----------------------------------------------------------------- 11. the site

def site_shape(payload):
    section("11. The built site")
    html_path = os.path.join(SITE, "index.html")
    check("site/index.html exists", os.path.exists(html_path))
    if not os.path.exists(html_path):
        return
    html = open(html_path).read()
    check("no unreplaced template placeholder",
          not re.search(r"__[A-Z_]+__", html),
          str(sorted(set(re.findall(r"__[A-Z_]+__", html)))))
    check("the payload is embedded", '<script id="D"' in html)
    check("no </script> escaped the embedded payload",
          html.count("</script>") == 2,
          "found %d closing script tags; the payload may have broken out"
          % html.count("</script>"))
    for view in ("standards", "difficulty", "blueprint", "posttest", "items"):
        check('the %s tab is wired up' % view, 'data-view="%s"' % view in html)
    for grade in payload["meta"]["grades"]:
        check("the grade %d switch is wired up" % grade,
              'data-grade="%d"' % grade in html)
    check("site/data.json exists and parses",
          os.path.exists(os.path.join(SITE, "data.json")))
    if os.path.exists(os.path.join(SITE, "data.json")):
        published = load(os.path.join(SITE, "data.json"))
        check("site/data.json holds the same items as the embedded payload",
              len(published["items"]) == len(payload["items"]),
              "%d vs %d" % (len(published["items"]), len(payload["items"])))
        check("site/data.json explains where its question text comes from",
              "itemText" in published["meta"])
        check("site/data.json states the P-value caveat",
              "pValueCaveat" in published["meta"])

    feedback_form(html)


def feedback_form(html):
    """The correction form is the whole point of a public launch, so check it.

    Netlify finds forms by scanning the deployed HTML, so the form must be in
    the static markup -- not built by app.js, which renders every tab at
    runtime and would leave submissions going nowhere with no visible sign.
    """
    check("the correction form is in the static HTML, where Netlify can find it",
          'data-netlify="true"' in html and 'name="correction"' in html,
          "a form built by app.js is never detected, and submissions vanish silently")
    check("the form carries the form-name field Netlify requires",
          'name="form-name"' in html and 'value="correction"' in html)
    check("the form has a honeypot against spam",
          'data-netlify-honeypot="bot-field"' in html and 'name="bot-field"' in html)
    check("the form has a message field and a submit button",
          'name="message"' in html and "fb-send" in html)
    check("the About tab is wired up", 'data-view="about"' in html)

    # This is the first thing in the project that collects anything from
    # anyone, on a project whose whole posture is that student data lives in
    # exactly one folder and never travels. A field inviting a class list or a
    # student name would quietly undo that.
    form = html[html.find('<form'):html.find("</form>") + 7] if "<form" in html else ""
    banned = ("student", "students", "roster", "class list", "osis", "names",
              "pupil", "child")
    attr = r"(?:name|id|placeholder|aria-label)\s*=\s*['" + chr(34) + r"][^'" + chr(34) + r"]*"
    hits = sorted({w for w in banned
                   if re.search(attr + r"\b" + w + r"\b", form, re.I)})
    check("no form field invites student data", not hits,
          "field(s) mentioning %s -- this form asks for a grade, a year and an item, "
          "never anything about a class" % ", ".join(hits))
    check("the form says where a submission goes",
          "Netlify" in form or "site" in form,
          "a reader should be told before they type")


# ------------------------------------------------------------ 12. the test suites

def suites():
    section("12. Test suites")
    runs = [("extractor", [sys.executable, os.path.join(HERE, "test_extractor.py")],
             "all checks passed")]
    for name, cmd, sentinel in runs:
        if not os.path.exists(cmd[1]):
            skipped("%s suite" % name, "%s does not exist" % os.path.basename(cmd[1]))
            continue
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        body = out.stdout + out.stderr
        check("%s suite passes" % name,
              out.returncode == 0 and sentinel in body,
              "\n".join(body.strip().split("\n")[-8:]))

    for name, script in (("engine", "test_engine.js"), ("render", "test_render.js")):
        path = os.path.join(HERE, script)
        if not os.path.exists(path):
            skipped("%s suite" % name, "%s does not exist yet (Phase 2)" % script)


# --------------------------------------------------- 13. keys, by a second method

def keys_second_method(payload):
    section("13. Answer keys, re-derived by a second, independent method")
    try:
        import fitz
    except ImportError:
        skipped("published keys match a naive re-read of the PDFs", "PyMuPDF not available")
        return

    tests = {t["testId"]: t for t in payload["tests"]}
    disagree, checked = [], 0
    for test_id, t in sorted(tests.items()):
        pdf = None
        for rec in load(os.path.join(PROV, "sources.json"))["files"].values():
            if rec.get("kind") == "released" and \
               "g%d-%d" % (rec.get("grade") or 0, rec.get("year") or 0) == test_id:
                pdf = os.path.join(ROOT, rec["path"])
        if not pdf or not os.path.exists(pdf):
            continue
        doc = fitz.open(pdf)
        # Deliberately naive: plain reading order, no geometry at all. If this
        # agrees with the geometry parser on every key, two unrelated code paths
        # agree and the keys can be trusted. RegentsAlign's convention: cross
        # implementation agreement is tested, not assumed.
        naive = {}
        for page_no in t["mapPages"]:
            lines = doc[page_no - 1].get_text().split("\n")
            for n, line in enumerate(lines):
                m = re.match(r"^\s*(\d{1,2})\s*$", line)
                if not m:
                    continue
                window = [x.strip() for x in lines[n + 1:n + 6]]
                if not any(w.startswith("Multiple") for w in window):
                    continue
                letter = next((w for w in window if re.match(r"^[A-D]$", w)), None)
                if letter:
                    naive[int(m.group(1))] = letter
        published = {i["item"]: i["key"] for i in payload["items"]
                     if i["testId"] == test_id and i["type"] == "Multiple Choice"}
        overlap = set(naive) & set(published)
        checked += len(overlap)
        for item in sorted(overlap):
            if naive[item] != published[item]:
                disagree.append("%s item %d: geometry says %s, naive read says %s"
                                % (test_id, item, published[item], naive[item]))
    if not checked:
        skipped("published keys match a naive re-read of the PDFs",
                "no source PDFs on disk to re-read")
        return
    check("every answer key agrees with an independent naive re-read (%d keys)" % checked,
          not disagree, "\n".join(disagree[:8]))


def main():
    if not os.path.exists(os.path.join(SITE, "data.json")):
        sys.exit("preflight: site/data.json does not exist -- run python3 publish.py first")
    payload = load(os.path.join(SITE, "data.json"))

    freshness()
    regenerability()
    payload_counts(payload)
    source_manifest()
    item_structure(payload)
    page_links(payload)
    blueprint_sanity(payload)
    standards_registry()
    curriculum_index(payload)
    derived_unit_filter(payload)
    transcription(payload)
    alignment(payload)
    privacy(payload)
    site_shape(payload)
    suites()
    keys_second_method(payload)

    print("\n" + "-" * 68)
    print("%d passed, %d failed, %d warned, %d skipped"
          % (len(PASSED), len(FAILED), len(WARNED), len(SKIPPED)))
    for where, name, why in SKIPPED:
        print("  skipped: %s -- %s" % (name, why))
    for where, name, detail in WARNED:
        print("  warning: %s" % name)
    if FAILED:
        print("\nDEPLOY BLOCKED. %d check(s) failed:" % len(FAILED))
        for where, name, detail in FAILED:
            print("  [%s] %s" % (where, name))
        sys.exit(1)
    print("\nall preflight checks passed -- safe to deploy")


if __name__ == "__main__":
    main()
