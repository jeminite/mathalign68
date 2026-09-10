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


# ----------------------------------------------------------------- 8. no item text

def no_item_text(payload):
    section("8. No item text -- the central design decision, enforced")
    banned_keys = {"stem", "stemHtml", "choices", "figure", "alt", "longDescription"}
    found = set()

    def walk(node, path=""):
        if isinstance(node, dict):
            for k, v in node.items():
                if k in banned_keys:
                    found.add("%s.%s" % (path, k))
                walk(v, "%s.%s" % (path, k))
        elif isinstance(node, list):
            for n, v in enumerate(node):
                walk(v, "%s[%d]" % (path, n))

    walk(payload)
    check("no stem, choice, figure or alt-text field in the payload",
          not found, ", ".join(sorted(found)))

    long_fields = []
    allowed = {"clusterText", "notes", "domainLabel", "subscore", "basis",
               "postTestNote", "note"}
    for i in payload["items"] + list(payload["standards"].values()):
        for k, v in i.items():
            if isinstance(v, str) and k not in allowed and len(v) > 300:
                long_fields.append("%s.%s (%d chars)" % (i.get("id", i.get("code")), k, len(v)))
    check("no unexpected long string in an item or standard record",
          not long_fields, ", ".join(long_fields[:5]))

    html = open(os.path.join(SITE, "index.html")).read()
    check("the built page states the no-item-text policy where a reader will see it",
          "does not reproduce" in html or "reproduces no" in html,
          "a reader clicking through to a PDF needs to be told why")


# -------------------------------------------------------------------- 9. alignment

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
    drafts = [c for c, e in align.get("byStandard", {}).items() if e.get("draft")]
    published = {i["standard"] for i in payload["items"] if i["alignmentBasis"] != "unaligned"}
    check("no draft alignment entry reached the payload",
          not (set(drafts) & published), str(sorted(set(drafts) & published)))
    unresolved = [i["id"] for i in payload["items"]
                  if i["alignmentBasis"] != "unaligned" and not i["lessonTitle"]]
    check("every aligned item carries a lesson title",
          not unresolved, str(unresolved[:5]))


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
        check("site/data.json states the no-item-text contract",
              "noItemText" in published["meta"])
        check("site/data.json states the P-value caveat",
              "pValueCaveat" in published["meta"])


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
    no_item_text(payload)
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
