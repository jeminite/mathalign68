#!/usr/bin/env python3
"""Narrow the lessons a released item could plausibly be taught in.

THIS IS RETRIEVAL, NOT JUDGEMENT. It exists only so that a human or model
reading can look at six lessons instead of a hundred and forty. Nothing it
returns is an alignment, nothing it returns reaches the site, and a high score
is not evidence -- the evidence is a named activity whose task statement a
reader can check. Keep the two separate: the moment a ranking is allowed to
stand in for a reading, this project has reproduced the exact failure
RegentsAlign's consistency audit found.

WHY IT SEARCHES THE WHOLE GRADE
provenance/alignment_baseline_measurement.md measured Imagine Learning's own
Lessons by Standard table against NYCPS's independent citations: it names the
right UNIT 96.3% of the time but the right LESSON only 77.4% of the time. So the
table is used as a prior -- lessons in a unit it names get a bonus -- rather than
as a filter, which would put the right answer out of reach for about one item in
five.

The only property that matters here is RECALL: the lesson a reader would choose
must be in the shortlist. tools/measure_shortlist_recall.py checks that against
NYCPS and is the reason to trust or distrust this file.
"""
import collections
import json
import math
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DETAIL = os.path.join(ROOT, "data", "im_ms_lessons_detail.json")
REF = os.path.join(ROOT, "data", "im_ms_reference.json")

UNIT_PRIOR = 1.30          # multiplier for a lesson in a unit the table names
DEFAULT_K = 8

STOP = set("""a an the and or but if then than that this these those of to in on at by for with
from as is are was were be been being it its it's he she they them his her their you your we our
i me my do does did not no yes so such can could will would shall should may might must have has
had what which who whom whose when where why how all any both each few more most other some only
own same too very just about into over under again further once here there why also use used using
show shows shown find finds found give gives given let lets make makes made get gets got put puts
one two three four five six seven eight nine ten problem problems lesson activity activities
student students teacher answer answers response responses sample explain reasoning following
below above shown following table figure figures""".split())

WORD = re.compile(r"[a-z][a-z0-9']+")
TAG = re.compile(r"<[^>]+>")
GRADE_IN_CODE = re.compile(r"^NY-([1-8])\.")


def home_grade(standard, item_grade):
    """The grade whose curriculum teaches this standard, which is not always the
    grade of the test it appears on. Every NYS test carries post-test standards
    from the year below -- grade 8 items citing NY-7.G.2 through NY-7.G.6, for
    instance -- and searching grade 8's lessons for those returns nothing at all,
    because grade 8 does not teach them. Twenty items across the three grades are
    in this position."""
    m = GRADE_IN_CODE.match(standard or "")
    if m and m.group(1) in ("6", "7", "8"):
        return m.group(1)
    return str(item_grade)


def toks(text):
    out = []
    for w in WORD.findall((text or "").lower()):
        if w in STOP or len(w) < 3:
            continue
        # crude stemmer: enough to join "circle/circles", "measure/measuring"
        for suf in ("ations", "ation", "ings", "ing", "ies", "es", "s"):
            if w.endswith(suf) and len(w) - len(suf) >= 4:
                w = w[: -len(suf)] + ("y" if suf == "ies" else "")
                break
        out.append(w)
    return out


def lesson_text(rec):
    parts = [rec.get("title", ""), rec.get("studentLearningGoal", ""),
             rec.get("lessonNarrative", ""), rec.get("goals", ""),
             rec.get("learningTargets", ""), rec.get("lessonSummary", "")]
    for a in rec.get("activities", []):
        parts += [a.get("name", ""), a.get("activityNarrative", ""),
                  a.get("studentTaskStatement", "")]
    for p in rec.get("practiceProblems", []):
        parts.append(p.get("prompt", ""))
    return " ".join(p for p in parts if p)


def item_text(item, content):
    """The item as words. `prose` is `stem` with the maths removed, so including
    both doubled every term frequency; and any HTML left in contributes the
    tokens "span", "class" and "math" to every single item, which is noise that
    scores identically everywhere."""
    c = content.get(item["id"], {})
    parts = [c.get("stem", "")]
    for ch in c.get("choices", []) or []:
        parts.append(ch.get("text", ""))
    for f in c.get("figures", []) or []:
        parts += [f.get("alt", ""), f.get("longDescription", "")]
    if not any(p for p in parts if p):
        parts = [item.get("clusterText", ""), item.get("standardText", "")]
    return TAG.sub(" ", " ".join(p for p in parts if p))


class Index(object):
    def __init__(self, detail, ref):
        self.ref, self.docs, self.df = ref, {}, collections.Counter()
        for g, gd in detail["grades"].items():
            for u, ud in gd["units"].items():
                for n, rec in ud["lessons"].items():
                    code = "%s.%s.%s" % (g, u, n)
                    tf = collections.Counter(toks(lesson_text(rec)))
                    self.docs[code] = {"tf": tf, "n": sum(tf.values()), "rec": rec}
                    for t in tf:
                        self.df[t] += 1
        self.N = max(len(self.docs), 1)
        self.avgdl = (sum(d["n"] for d in self.docs.values()) / float(self.N)) or 1.0

    def idf(self, t):
        return math.log((self.N + 1.0) / (self.df.get(t, 0) + 1.0))

    @staticmethod
    def _base(code):
        return (code or "").replace(".", "").replace("-", "").upper()

    def tagged(self, grade, standard):
        """Lessons the UNIT guide tags as Addressing this standard. A different
        document from the course guide's Lessons by Standard table, and measured
        the more accurate of the two: it names NYCPS's cited lesson 82.6% of the
        time against the table's 77.4%."""
        want = self._base(standard)
        out = set()
        for code, doc in self.docs.items():
            if code.split(".")[0] != grade:
                continue
            for c in (doc["rec"].get("standards") or {}).get("Addressing", []):
                a = self._base(c)
                if a == want or want.startswith(a) or a.startswith(want):
                    out.add(code)
                    break
        return out

    def candidate_units(self, grade, standard):
        """A PARENT CODE IS STILL A STANDARD, and so is each of its children.

        The guide indexes some lessons under NY-8.G.1 and others under
        NY-8.G.1a, and in grade 8 those two sets share NO LESSON AT ALL --
        parent 1.2/1.3/1.4/1.6/1.11/1.14 against child 1.7/1.8/1.9/1.10/1.13.
        This used to take the exact code and fall back to a prefix match only
        when the exact code was MISSING, so a sub-letter code never saw its
        parent's lessons and vice versa.

        61 remaining items were affected. The worst case is NY-8.EE.7b, whose
        eight items had a single candidate lesson where the parent supplies four
        more. templates/app.js already merges both directions for the site's own
        unit filter; this brings retrieval in line with it.

        Both directions, and ONLY across a sub-letter suffix: NY-6.RP.3 pairs
        with NY-6.RP.3a but never with NY-6.RP.31 or NY-6.RP.3.Cluster-1.
        """
        s2l = self.ref[grade]["standardToLessons"]
        lessons = set()
        for code, val in s2l.items():
            if code == standard \
                    or (code.startswith(standard) and code[len(standard):].isalpha()) \
                    or (standard.startswith(code) and standard[len(code):].isalpha()):
                lessons |= set(val["lessons"])
        return {c.split(".")[1] for c in lessons}, lessons

    def rank(self, grade, standard, text, k=DEFAULT_K):
        """Three signals, none of which is trusted alone.

        A lesson tagged with the item's standard by EITHER the unit guide or the
        course guide is promoted outright -- those two documents disagree often
        enough that taking the union recovers cases either one misses. Everything
        else is ordered by BM25 against the lesson's own task statements, with a
        bonus for sitting in a unit the table names.

        BM25 rather than raw tf-idf because the query is one test question and
        the documents are whole lessons: without its length normalisation the
        shortest lessons won regardless of content."""
        units, listed = self.candidate_units(grade, standard)
        tagged = self.tagged(grade, standard)
        promoted = tagged | set(listed)
        q = collections.Counter(toks(text))
        k1, b = 1.5, 0.6
        scored = []
        for code, doc in self.docs.items():
            if code.split(".")[0] != grade:
                continue
            s = 0.0
            dl = doc["n"] / self.avgdl
            for t, qn in q.items():
                f = doc["tf"].get(t, 0)
                if not f:
                    continue
                s += self.idf(t) * (f * (k1 + 1)) / (f + k1 * (1 - b + b * dl))
            if code.split(".")[1] in units:
                s *= UNIT_PRIOR
            scored.append((s, code))
        # Promoted lessons first, each group ordered by score.
        scored.sort(key=lambda sc: (sc[1] in promoted, sc[0]), reverse=True)
        return [{"lesson": c, "score": round(s, 3),
                 "inTable": c in listed,
                 "taggedByUnitGuide": c in tagged,
                 "inCandidateUnit": c.split(".")[1] in units,
                 "title": self.docs[c]["rec"].get("title")}
                for s, c in scored[:k]]


def load():
    detail = json.load(open(DETAIL))
    ref = json.load(open(REF))["grades"]
    return Index(detail, ref)


def tiers(idx, grade, standard, text, k=12):
    """Two tiers, because recall and reading cost pull opposite ways.

    Measured against NYCPS's independent citations (n=160):
      tier 1 alone            90.0% recall at k=12, ~12 lessons to read
      tier 1 + tier 2         97.5% recall, median 30 lessons

    So tier 2 is not read by default. It is read when tier 1 produces no
    evidence -- which is precisely when the alternative is recording
    "no lesson found", the one answer it would be worst to get wrong by
    never having looked.
    """
    ranked = idx.rank(grade, standard, text, k=k)
    tier1 = [r["lesson"] for r in ranked]
    units, _ = idx.candidate_units(grade, standard)
    pool = set()
    for u in units:
        pool |= {c for c in idx.docs if c.startswith("%s.%s." % (grade, u))}
    tier2 = sorted(pool - set(tier1),
                   key=lambda c: (int(c.split(".")[1]), int(c.split(".")[2])))
    return {"tier1": ranked, "tier2": tier2, "units": sorted(units, key=int)}


def lesson(idx, code):
    return idx.docs[code]["rec"] if code in idx.docs else None
