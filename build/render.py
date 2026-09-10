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


def render(payload, disclaimer, feedback_url, feedback_label):
    html = read("index.html")
    css = read("base.css")
    app = read("app.js")

    years = payload["meta"]["years"]
    feedback = ""
    if feedback_url:
        feedback = ('<a href="%s" target="_blank" rel="noopener">%s</a>.'
                    % (feedback_url, feedback_label))

    # The payload goes inside <script type="application/json">, so the only
    # sequence that can break out is "</script". Escaping the slash keeps the
    # JSON valid and the parser happy.
    data = json.dumps(payload, separators=(",", ":")).replace("</", "<\\/")

    subs = [
        ("/*__CSS__*/", css),
        ("/*__APP__*/", app),
        ("__DATA__", data),
        ("__DISCLAIMER__", disclaimer),
        ("__FEEDBACK__", feedback),
        ("__BUILT__", payload["meta"]["built"].replace("T", " at ")),
        ("__YEARS__", "%d–%d" % (years[0], years[-1])),
    ]
    for token, value in subs:
        if token not in html and token not in css and token not in app:
            raise RuntimeError("placeholder %s is not in any template -- a rename "
                               "would silently drop content" % token)
        html = html.replace(token, value)

    left = PLACEHOLDER_RE.findall(html)
    if left:
        raise RuntimeError("unreplaced placeholder(s) in the built page: %s"
                           % ", ".join(sorted(set(left))))
    return html
