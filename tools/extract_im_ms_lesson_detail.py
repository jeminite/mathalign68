#!/usr/bin/env python3
"""Imagine IM New York per-unit Teacher Guides -> data/im_ms_lessons_detail.json

WHY THIS EXISTS
data/im_ms_reference.json gives a lesson a title, a section and a standard list --
five words and a code. That is not enough to answer the question this project is
actually for: "is this released test item asking students to do what this lesson
asks them to do?" RegentsAlign had only titles to go on, and its own consistency
audit records what that costs: an exponent-rules question filed at a lesson called
"Predicting Populations", because the publisher's standard-to-lesson table said so
and there was no way to check. The per-unit guides carry the real Student Task
Statements, so here that check is possible.

WHAT IT READS
sources/ImagineIM_NY_<g>_<u>_TG_NA_V2_EN_DIG.pdf -- the per-unit guides. These are
gitignored (203MB) and are NOT part of the reproducible build; this script's output
is a convenience index, and tools/validate_im_ms_lesson_detail.py checks it against
the course guide, which IS tracked.

HOW THE PAGES DECODE
Font size separates the layers cleanly, which is the whole reason this is tractable:

  2-4pt    a shrunken facsimile of the Student Workbook page, printed on every
           teacher page. It duplicates each task statement verbatim -- 59K of the
           374K characters on one unit's lesson pages. Reading it would double
           every prompt, so the body filter starts at 10pt.
  7-9pt    sidebar furniture: Alignments, Required Materials, Instructional
           Routines, page footers.
  10-12.5  the main column: headings (Hellix-Bold) and prose.
  16, 20.8 timing badges and the big lesson number. Excluded, or they merge into
           the heading beside them ("Activity 1" + "25" -> "Activity 125").

  SketchnoteText (any size) is the handwriting face used for sample answers, and
  a Hellix-SemiBold run starting "Sample"/"Possible" opens a worked answer. Both
  are cut from the task statement: the prompt is what students are asked, and
  mixing the answer into it would make every similarity judgement read better than
  it is.
"""
import fitz, json, os, re, sys, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SOURCES = os.path.join(ROOT, "sources")
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "im_ms_lessons_detail.json")

BODY_MIN, BODY_MAX = 10.0, 12.5
ANSWER_FONT = "Sketchnote"
ANSWER_RE = re.compile(r"^(Sample|Possible)\b")
TAB_Y, FOOT_Y = 46.0, 820.0
SAME_LINE = 6.0

LESSON_FIELDS = ["Goals", "Learning Targets", "Lesson Narrative",
                 "Student Learning Goal", "Required Preparation",
                 "Lesson Synthesis", "Lesson Summary"]
ACTIVITY_FIELDS = ["Activity Narrative", "Launch", "Student Task Statement",
                   "Building on Student Thinking", "Activity Synthesis",
                   "Are You Ready for More?", "Responding to Student Thinking"]
FIELD_HEADS = set(LESSON_FIELDS) | set(ACTIVITY_FIELDS) | {"Lesson Timeline",
                                                           "Practice Problems"}
# The national CCSS edition writes "Activity 1: Optional" where New York writes
# "Activity 1". Matching only the bare form lost every activity in grade 7 unit 9.
KIND_RE = re.compile(r"^(Warm-up|Activity\s+\d+|Cool-down)(:\s*Optional)?$")
# Lessons long enough to break across pages repeat their heading as
# "Lesson Narrative (continued)"; without stripping that the continuation is
# orphaned and belongs to no field.
CONT_RE = re.compile(r"\s*\(continued\)\s*$", re.I)
# Two grade 6 lesson openers carry an unreplaced template layer -- a literal
# "[Lesson Title]" with "X" timings -- printed alongside the real title.
PLACEHOLDER_RE = re.compile(r"^\[.*\]$")
PROBLEM_RE = re.compile(r"^Problem\s+\d+$")
STD_LABELS = {"Building On", "Addressing", "Building Towards",
              "Mathematical Practice"}
CODE_RE = re.compile(r"(NY-[0-9KA-Z][^,\s]*|MP\.\d+)")

SECTION_RE = re.compile(r"^Section\s+([A-F])\s*[:.]?\s*(.*)$")
LESSON_RE = re.compile(r"^Lesson\s+(\d+)$")


def key(g, u, n):
    return "%s.%s.%s" % (g, u, n)


# ---------------------------------------------------------------- page reading

def page_spans(page):
    out = []
    for b in page.get_text("dict")["blocks"]:
        if b["type"] != 0:
            continue
        for l in b["lines"]:
            for s in l["spans"]:
                if not s["text"].strip():
                    continue
                x0, y0 = s["bbox"][0], s["bbox"][1]
                if y0 < TAB_Y or y0 > FOOT_Y:      # tab strip / running footer
                    continue
                out.append({"x": x0, "x1": s["bbox"][2], "y": y0,
                            "size": s["size"], "font": s["font"],
                            "text": s["text"]})
    return out


ZERO_WIDTH = dict.fromkeys(map(ord, "\u00ad\u200b\u200c\u200d\ufeff"), None)


def clean(t):
    # Titles and prose carry zero-width joiners around inline maths; left in,
    # they make "Translating to y = mx + b" compare unequal to itself.
    t = t.translate(ZERO_WIDTH)
    t = t.replace("\u2005", " ").replace("\u2009", " ").replace("\u00a0", " ")
    return re.sub(r"\s+", " ", t).strip()


def render(spans):
    """Spans -> prose. Lines ending in '-' join without a space, keeping the
    hyphen: the guides break 'one-dimensional' across lines and dropping the
    hyphen there produced 'onedimensional'."""
    spans = sorted(spans, key=lambda s: (s["y"], s["x"]))
    # 5pt, not 3pt: italic maths variables sit a shade off the prose baseline, and
    # at 3pt "y = 1.5x + 2" split into its own line and came back as "= 1.5 + 2 ...
    # yxxy". Same baseline-grouping failure the item extractor hit with exponents.
    lines, cur, cy = [], [], None
    for s in spans:
        if cy is not None and abs(s["y"] - cy) > 5.0:
            lines.append(cur)
            cur, cy = [], None
        cur.append(s)
        if cy is None:
            cy = s["y"]
    if cur:
        lines.append(cur)
    out = ""
    for ln in lines:
        ordered = sorted(ln, key=lambda s: s["x"])
        buf = ""
        prev = None
        for s in ordered:
            # Table cells are separate spans on one line with a wide gap between
            # them; without this they ran together as "ObjectDiametCircumf".
            if prev is not None and s["x"] - prev["x1"] > 2.0 and not buf.endswith(" "):
                buf += " "
            buf += s["text"]
            prev = s
        part = clean(buf)
        if not part:
            continue
        if not out:
            out = part
        elif out.endswith("-"):
            out += part
        else:
            out += " " + part
    return clean(out)


def headings(spans):
    """Structural headings. Grouped by (line, coarse column) so that two headings
    printed side by side -- Goals and Learning Targets share a baseline on every
    lesson opener -- are not concatenated into one meaningless string."""
    bold = [s for s in spans if s["font"] == "Hellix-Bold"
            and BODY_MIN <= s["size"] <= BODY_MAX]
    groups = {}
    for s in bold:
        groups.setdefault((round(s["y"] / 3.0), int(s["x"] // 200)), []).append(s)
    hs = []
    for g in groups.values():
        t = clean("".join(x["text"] for x in sorted(g, key=lambda x: x["x"])))
        t = CONT_RE.sub("", t)
        y, x = min(v["y"] for v in g), min(v["x"] for v in g)
        if t in FIELD_HEADS:
            kind = "field"
        elif KIND_RE.match(t):
            kind = "kind"
        elif PROBLEM_RE.match(t):
            kind = "problem"
        else:
            kind = "bold"                 # inline emphasis: "1 minute", "1.", "pi"
        hs.append({"y": y, "x": x, "text": t, "kind": kind})
    return sorted(hs, key=lambda h: (h["y"], h["x"]))


def region(spans, hs, h):
    """The text under heading h, bounded by its column and the next structural
    heading. Only structural headings bound: bolded list markers and mid-sentence
    emphasis are bold too, and letting those close a region truncated every
    numbered task statement after its first sentence."""
    struct = [o for o in hs if o["kind"] != "bold"]
    left = h["x"] - 15
    rights = [o["x"] for o in struct
              if abs(o["y"] - h["y"]) <= SAME_LINE and o["x"] > h["x"] + 5]
    right = min(rights) - 5 if rights else (470.0 if h["x"] < 200 else 670.0)
    belows = [o["y"] for o in struct
              if o["y"] > h["y"] + SAME_LINE and left <= o["x"] < right]
    bottom = min(belows) if belows else FOOT_Y + 1
    sel = [s for s in spans if left <= s["x"] < right
           and h["y"] + SAME_LINE < s["y"] < bottom]
    return sel, bottom > FOOT_Y


def split_answer(sel):
    """Prompt, answer. The answer starts at the first Hellix-SemiBold 'Sample...'
    run, or at the handwriting face, whichever comes first."""
    cut = None
    for s in sorted(sel, key=lambda s: (s["y"], s["x"])):
        if ANSWER_FONT in s["font"] or (
                s["font"].startswith("Hellix-SemiBold") and ANSWER_RE.match(s["text"].strip())):
            cut = (s["y"], s["x"])
            break
    def body(ss):
        return [s for s in ss if BODY_MIN <= s["size"] <= BODY_MAX
                and ANSWER_FONT not in s["font"]]
    if cut is None:
        return render(body(sel)), ""
    before = [s for s in sel if (s["y"], s["x"]) < cut]
    after = [s for s in sel if (s["y"], s["x"]) >= cut]
    return render(body(before)), render(body(after))


def page_standards(spans):
    """The Alignments sidebar: a 9pt bold label then 8pt codes."""
    out = {}
    marks = sorted([s for s in spans if s["font"] == "Hellix-Bold"
                    and 8.6 <= s["size"] <= 9.4 and clean(s["text"]) in STD_LABELS],
                   key=lambda s: s["y"])
    for i, m in enumerate(marks):
        top = m["y"]
        bot = marks[i + 1]["y"] if i + 1 < len(marks) else top + 26
        codes = [s for s in spans if s["font"].startswith("Hellix-SemiBold")
                 and 7.6 <= s["size"] <= 8.4
                 and abs(s["x"] - m["x"]) < 40 and top < s["y"] < bot]
        found = CODE_RE.findall(clean("".join(c["text"] for c in
                                              sorted(codes, key=lambda s: (s["y"], s["x"])))))
        if found:
            out.setdefault(clean(m["text"]), []).extend(found)
    return {k: sorted(set(v)) for k, v in out.items()}


# ------------------------------------------------------------------- assembly

def unit_structure(doc):
    """TOC -> ordered entries with page ranges. The outline is flat but ordered,
    so a lesson's section is simply the most recent Section entry above it."""
    toc = [(t.strip(), p - 1) for _, t, p in doc.get_toc()]
    entries, section = [], (None, None)
    for i, (title, pg) in enumerate(toc):
        end = toc[i + 1][1] if i + 1 < len(toc) else doc.page_count
        m = SECTION_RE.match(title)
        if m:
            section = (m.group(1), m.group(2).strip())
            continue
        m = LESSON_RE.match(title)
        if m:
            entries.append({"lesson": int(m.group(1)), "start": pg, "end": end,
                            "sectionLetter": section[0], "sectionTitle": section[1]})
    return entries


def parse_lesson(doc, ent):
    pages = []
    for pi in range(ent["start"], ent["end"]):
        ss = page_spans(doc[pi])
        pages.append({"i": pi, "spans": ss, "heads": headings(ss),
                      "std": page_standards(ss)})

    rec = {"lesson": ent["lesson"], "title": None,
           "sectionLetter": ent["sectionLetter"], "sectionTitle": ent["sectionTitle"],
           "pageStart": ent["start"] + 1, "pageEnd": ent["end"],
           "optional": False,
           "standards": {}, "activities": [], "practiceProblems": []}

    # The lesson title is the 12pt run on the opener page. It is not a single
    # span: a title containing maths ("Translating to y = mx + b") is split
    # across Hellix-Bold and an italic maths face sitting 3pt off the baseline,
    # so the whole 12pt line is gathered rather than the first bold span.
    for p in pages:
        anchors = [s for s in p["spans"] if s["font"] == "Hellix-Bold"
                   and 11.8 <= s["size"] <= 12.2]
        for a in sorted(anchors, key=lambda s: (s["y"], s["x"])):
            if PLACEHOLDER_RE.match(clean(a["text"])):
                continue          # the unreplaced template layer, not a title
            line = [s for s in p["spans"] if 11.8 <= s["size"] <= 12.2
                    and abs(s["y"] - a["y"]) <= 5.0 and s["x"] >= a["x"] - 1]
            # Some openers draw two 12pt runs at IDENTICAL coordinates: the title
            # twice over, or the unreplaced template title underneath the real
            # one. Overlaid, not spaced, so a gap test cannot see them -- keep one
            # span per x position, preferring the real title to the placeholder.
            best = {}
            for sp in line:
                k = round(sp["x"], 1)
                cur = best.get(k)
                if cur is None:
                    best[k] = sp
                    continue
                cur_ph = bool(PLACEHOLDER_RE.match(clean(cur["text"])))
                sp_ph = bool(PLACEHOLDER_RE.match(clean(sp["text"])))
                if cur_ph and not sp_ph:
                    best[k] = sp
                elif cur_ph == sp_ph and len(sp["text"]) > len(cur["text"]):
                    best[k] = sp
            line = sorted(best.values(), key=lambda s: s["x"])
            # Stop at the first wide gap. Some openers print the title twice on
            # one line, or print it beside the leftover template title, and
            # taking the whole line produced "Creating Double Number Line
            # DiagramsCreating Double Number Line Diagrams".
            run, prev = [], None
            for sp in line:
                if prev is not None and sp["x"] - prev["x1"] > 25.0:
                    break
                run.append(sp)
                prev = sp
            t = clean("".join(sp["text"] for sp in run))
            if t and t != "Practice Problems" and not PLACEHOLDER_RE.match(t):
                rec["title"] = t
                break
        if rec["title"]:
            break

    if rec["title"] and rec["title"].lower().endswith("(optional)"):
        rec["optional"] = True
        rec["title"] = re.sub(r"\s*\(optional\)\s*$", "", rec["title"], flags=re.I)

    for p in pages:
        for label, codes in p["std"].items():
            rec["standards"].setdefault(label, [])
            for c in codes:
                if c not in rec["standards"][label]:
                    rec["standards"][label].append(c)

    cur, in_practice = None, False
    for p in pages:
        for h in p["heads"]:
            if h["kind"] == "bold":
                continue
            sel, _ = region(p["spans"], p["heads"], h)
            if h["kind"] == "kind":
                name = render([s for s in sel if BODY_MIN <= s["size"] <= BODY_MAX
                               and ANSWER_FONT not in s["font"]])
                kind = h["text"]
                optional = ":" in kind
                cur = {"kind": kind.split(":")[0].strip(),
                       "optional": optional,
                       "name": name.split("  ")[0].strip(),
                       "page": p["i"] + 1, "standards": p["std"]}
                rec["activities"].append(cur)
                in_practice = False
            elif h["kind"] == "problem":
                prompt, answer = split_answer(sel)
                rec["practiceProblems"].append(
                    {"problem": h["text"], "page": p["i"] + 1,
                     "prompt": prompt, "answer": answer})
            elif h["text"] == "Practice Problems":
                in_practice, cur = True, None
            elif h["text"] == "Lesson Timeline":
                continue
            elif h["text"] in ACTIVITY_FIELDS and cur is not None:
                prompt, answer = split_answer(sel)
                fld = h["text"][0].lower() + h["text"][1:].replace(" ", "")
                cur[fld] = (cur.get(fld, "") + " " + prompt).strip()
                if h["text"] == "Student Task Statement" and answer:
                    cur["studentTaskAnswer"] = (
                        cur.get("studentTaskAnswer", "") + " " + answer).strip()
            elif h["text"] in LESSON_FIELDS and not in_practice:
                prompt, _ = split_answer(sel)
                fld = h["text"][0].lower() + h["text"][1:].replace(" ", "")
                rec[fld] = (rec.get(fld, "") + " " + prompt).strip()
    return rec


def main(argv):
    grades = [int(a) for a in argv[1:]] or [6, 7]
    out = {"meta": {"schemaVersion": 1,
                    "generatedBy": "tools/extract_im_ms_lesson_detail.py",
                    "generated": datetime.date.today().isoformat(),
                    "edition": "Imagine IM New York, 6-8",
                    "note": "Derived from the per-unit Teacher Guides, which are "
                            "gitignored. Not published to site/data.json: see the "
                            "quoting limits in the alignment plan.",
                    "sources": {}},
           "grades": {}}
    for g in grades:
        gd = out["grades"].setdefault(str(g), {"units": {}})
        for u in range(1, 10):
            names = ["ImagineIM_NY_%d_%d_TG_NA_V2_EN_DIG.pdf" % (g, u),
                     "ImagineIM_%d_%d_TG_CCSS_V1_EN_DIG.pdf" % (g, u)]
            path = next((os.path.join(SOURCES, n) for n in names
                         if os.path.exists(os.path.join(SOURCES, n))), None)
            if not path:
                sys.stderr.write("  no guide for grade %d unit %d\n" % (g, u))
                continue
            doc = fitz.open(path)
            ents = unit_structure(doc)
            lessons = {}
            for ent in ents:
                rec = parse_lesson(doc, ent)
                lessons[str(rec["lesson"])] = rec
            gd["units"][str(u)] = {
                "source": os.path.basename(path),
                "edition": ("national-ccss-v1" if "CCSS" in path else "newYork"),
                "pages": doc.page_count,
                "lessons": lessons}
            out["meta"]["sources"][key(g, u, "")[:-1]] = os.path.basename(path)
            sys.stderr.write("  grade %d unit %d: %d lessons, %d pages\n"
                             % (g, u, len(lessons), doc.page_count))
            doc.close()
    with open(OUT, "w") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False)
    sys.stderr.write("wrote %s (%.1f MB)\n" % (OUT, os.path.getsize(OUT) / 1e6))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
