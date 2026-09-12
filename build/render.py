#!/usr/bin/env python3
"""
Assemble site/index.html from templates/ and the payload.

The templates are real files on disk -- editable, lintable, syntax-highlighted --
rather than string constants inside the builder. RegentsAlign keeps a 1242-line
publish.py with the whole page as Python strings, and the cost is that the HTML,
CSS and JS get no tooling at all.

Substitution is deliberately dumb: exact placeholder strings, each replaced once,
and a check afterwards that none is left behind. A silently unreplaced
placeholder ships a page with "__DATA__" in it.
"""

import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TEMPLATES = os.path.join(ROOT, "templates")

PLACEHOLDER_RE = re.compile(r"__[A-Z_]+__|/\*__[A-Z_]+__\*/")


def read(name):
    with open(os.path.join(TEMPLATES, name)) as fh:
        return fh.read()


def render(payload, disclaimer):
    html = read("index.html")
    css = read("base.css")
    question_css = read("question.css")
    app = read("app.js")

    years = payload["meta"]["years"]

    # The payload goes inside <script type="application/json">, so the only
    # sequence that can break out is "</script". Escaping the slash keeps the
    # JSON valid and the parser happy.
    data = json.dumps(payload, separators=(",", ":")).replace("</", "<\\/")

    subs = [
        ("/*__CSS__*/", css),
        ("/*__QUESTION_CSS__*/", question_css),
        ("/*__APP__*/", app),
        ("__DATA__", data),
        ("__DISCLAIMER__", disclaimer),
        ("__BUILT__", payload["meta"]["built"].replace("T", " at ")),
        ("__YEARS__", "%d–%d" % (years[0], years[-1])),
    ]
    for token, value in subs:
        if token not in html and token not in css and token not in app \
                and token not in question_css:
            raise RuntimeError("placeholder %s is not in any template -- a rename "
                               "would silently drop content" % token)
        html = html.replace(token, value)

    left = PLACEHOLDER_RE.findall(html)
    if left:
        raise RuntimeError("unreplaced placeholder(s) in the built page: %s"
                           % ", ".join(sorted(set(left))))
    return html


def render_analyze(disclaimer):
    """Assemble site/analyze/index.html.

    Self-contained like the main page: the reader, the engine and the page code
    are inlined rather than loaded as separate files. That is not only house
    style -- preflight.py refuses an analyze page that loads anything from a
    third-party origin, and a page with no <script src> at all cannot acquire
    one by accident.

    It deliberately does NOT embed the payload. The analyzer fetches
    ../data.json at runtime so there is one copy of the item data on the site
    rather than two that can drift.
    """
    html = read(os.path.join("analyze", "index.html"))

    subs = [
        ("/*__CSS__*/", read("base.css")),
        ("/*__QUESTION_CSS__*/", read("question.css")),
        ("/*__ANALYZE_CSS__*/", read(os.path.join("analyze", "analyze.css"))),
        ("/*__XLSX__*/", read(os.path.join("analyze", "xlsx.js"))),
        ("/*__ENGINE__*/", read(os.path.join("analyze", "engine.js"))),
        ("/*__ANALYZE_APP__*/", read(os.path.join("analyze", "app.js"))),
        ("__DISCLAIMER__", disclaimer),
    ]
    for token, value in subs:
        if token not in html:
            raise RuntimeError("placeholder %s is not in templates/analyze/index.html -- "
                               "a rename would silently drop content" % token)
        html = html.replace(token, value)

    left = PLACEHOLDER_RE.findall(html)
    if left:
        raise RuntimeError("unreplaced placeholder(s) in the built analyse page: %s"
                           % ", ".join(sorted(set(left))))
    return html
