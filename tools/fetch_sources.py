#!/usr/bin/env python3
"""
Download the NYSED source PDFs and record what was downloaded.

  python3 tools/fetch_sources.py                 # released items for every test
  python3 tools/fetch_sources.py --scoring       # also the scoring-materials PDFs
  python3 tools/fetch_sources.py --grade 7       # one grade
  python3 tools/fetch_sources.py --year 2026     # one year
  python3 tools/fetch_sources.py --verify        # re-hash what is on disk, download nothing

Writes : sources/<basename>.pdf
         sources/scoring/<basename>.pdf   (--scoring only; gitignored, ~10MB each)
         provenance/sources.json          the manifest: url, sha256, bytes, pages, fetched

WHY A MANIFEST EXISTS AT ALL
The URL patterns are not stable enough to leave undocumented. Released items sit
at .../math/<year>/english/... through 2022 and at .../math/<year>/... from 2023;
2017 grade 7 is at a one-off filename; 2020 does not exist; 2021 has released
items but no scoring materials. Recording the URL, the hash and the date for
every file means a silently-replaced upstream PDF is caught by preflight instead
of quietly changing the published data.

Re-running is safe: a file whose sha256 already matches the manifest is skipped.
"""

import argparse
import datetime
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SOURCES = os.path.join(ROOT, "sources")
SCORING = os.path.join(SOURCES, "scoring")
MANIFEST = os.path.join(ROOT, "provenance", "sources.json")

BASE = "https://www.nysedregents.org/ei"

# The Next Generation standards era. Earlier years use CCLS codes (7.RP.A.1)
# and are a separate corpus with no automatic crosswalk -- see the plan.
GRADES = (6, 7, 8)
YEARS = (2023, 2024, 2025, 2026)

# The educator guide is not per-grade and lives on a different host.
EDUCATOR_GUIDE = (
    "3-8-educator-guide-math.pdf",
    "https://www.nysed.gov/sites/default/files/programs/state-assessment/"
    "3-8-educator-guide-math.pdf",
)

# Tests with no scoring-materials PDF published, with the reason. Kept explicit
# so preflight can tell "we know there is none" from "nobody looked".
NO_SCORING = {
    # (grade, year): reason
    (6, 2021): "NYSED published no scoring materials for 2021",
    (7, 2021): "NYSED published no scoring materials for 2021",
    (8, 2021): "NYSED published no scoring materials for 2021",
}


def released_url(grade, year):
    """Released-items URL. The directory moved out of english/ in 2023."""
    name = "%d-released-items-math-g%d.pdf" % (year, grade)
    if year >= 2023:
        return name, "%s/math/%d/%s" % (BASE, year, name)
    return name, "%s/math/%d/english/%s" % (BASE, year, name)


def scoring_url(grade, year):
    name = "%d-scoring-materials-math-g%d.pdf" % (year, grade)
    return name, "%s/math/%d/%s" % (BASE, year, name)


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def page_count(path):
    """Page count via PyMuPDF. Returns None rather than failing the fetch --
    poppler is not installed on this machine, so fitz is the only option and a
    missing fitz should not stop a download."""
    try:
        import fitz
    except ImportError:
        return None
    try:
        with fitz.open(path) as doc:
            return doc.page_count
    except Exception:
        return None


def download(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent": "MathAlign68/1.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        if resp.status != 200:
            raise RuntimeError("HTTP %s" % resp.status)
        body = resp.read()
    if not body.startswith(b"%PDF"):
        raise RuntimeError("not a PDF (got %d bytes starting %r)" % (len(body), body[:16]))
    tmp = dest + ".part"
    with open(tmp, "wb") as fh:
        fh.write(body)
    os.replace(tmp, dest)
    return len(body)


def load_manifest():
    if os.path.exists(MANIFEST):
        with open(MANIFEST) as fh:
            return json.load(fh)
    return {"meta": {}, "files": {}}


def save_manifest(man):
    man["meta"] = {
        "generatedBy": "tools/fetch_sources.py",
        "updated": datetime.date.today().isoformat(),
        "note": "Every source PDF, its URL and its sha256. preflight.py fails if a "
                "local file no longer matches its recorded hash.",
    }
    os.makedirs(os.path.dirname(MANIFEST), exist_ok=True)
    with open(MANIFEST, "w") as fh:
        json.dump(man, fh, indent=2, sort_keys=True)
        fh.write("\n")


def wanted(args):
    """The (kind, grade, year, name, url, directory) tuples to fetch."""
    out = []
    for grade in GRADES:
        if args.grade and grade != args.grade:
            continue
        for year in YEARS:
            if args.year and year != args.year:
                continue
            name, url = released_url(grade, year)
            out.append(("released", grade, year, name, url, SOURCES))
            if args.scoring:
                if (grade, year) in NO_SCORING:
                    continue
                name, url = scoring_url(grade, year)
                out.append(("scoring", grade, year, name, url, SCORING))
    if not args.grade and not args.year:
        name, url = EDUCATOR_GUIDE
        out.append(("guide", None, None, name, url, SOURCES))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--scoring", action="store_true",
                    help="also fetch the scoring-materials PDFs (large, gitignored)")
    ap.add_argument("--grade", type=int, choices=GRADES)
    ap.add_argument("--year", type=int, choices=YEARS)
    ap.add_argument("--verify", action="store_true",
                    help="re-hash local files against the manifest; download nothing")
    ap.add_argument("--force", action="store_true",
                    help="re-download even when the hash already matches")
    args = ap.parse_args()

    os.makedirs(SOURCES, exist_ok=True)
    if args.scoring:
        os.makedirs(SCORING, exist_ok=True)

    man = load_manifest()
    files = man.setdefault("files", {})
    today = datetime.date.today().isoformat()
    failures = []
    changed = False

    for kind, grade, year, name, url, directory in wanted(args):
        dest = os.path.join(directory, name)
        rel = os.path.relpath(dest, ROOT)
        rec = files.get(name)

        if args.verify:
            if not os.path.exists(dest):
                print("MISSING  %s" % rel)
                if kind != "scoring":
                    failures.append(rel)
                continue
            got = sha256_of(dest)
            if rec and rec.get("sha256") and rec["sha256"] != got:
                print("CHANGED  %s\n         manifest %s\n         on disk  %s"
                      % (rel, rec["sha256"][:16], got[:16]))
                failures.append(rel)
            else:
                print("ok       %s" % rel)
            continue

        if os.path.exists(dest) and rec and not args.force:
            if sha256_of(dest) == rec.get("sha256"):
                print("skip     %s (hash matches manifest)" % rel)
                continue

        try:
            size = download(url, dest)
        except (urllib.error.URLError, urllib.error.HTTPError, RuntimeError) as exc:
            print("FAIL     %s\n         %s\n         %s" % (rel, url, exc))
            failures.append(rel)
            continue

        files[name] = {
            "kind": kind,
            "grade": grade,
            "year": year,
            "url": url,
            "path": rel,
            "bytes": size,
            "pages": page_count(dest),
            "sha256": sha256_of(dest),
            "fetched": today,
        }
        changed = True
        print("fetched  %-44s %7.1f KB  %s pages"
              % (rel, size / 1024.0, files[name]["pages"]))

    for (grade, year), reason in sorted(NO_SCORING.items()):
        files.setdefault("no-scoring-g%d-%d" % (grade, year),
                         {"kind": "scoring", "grade": grade, "year": year,
                          "url": None, "reason": reason})

    if changed or not os.path.exists(MANIFEST):
        save_manifest(man)
        print("\nwrote %s (%d entries)" % (os.path.relpath(MANIFEST, ROOT), len(files)))

    if failures:
        print("\n%d problem(s):" % len(failures))
        for f in failures:
            print("  %s" % f)
        sys.exit(1)
    print("\nall ok")


if __name__ == "__main__":
    main()
