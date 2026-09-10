#!/usr/bin/env python3
"""
Serve site/ locally so the page can actually be looked at.

  python3 tools/preview.py            # http://localhost:8766
  python3 tools/preview.py --port N

A built page is not evidence that it works. Open it.
"""

import argparse
import functools
import http.server
import os
import socketserver

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):
        if "404" in (fmt % args):
            super().log_message(fmt, *args)

    def end_headers(self):
        # No caching, or an edit-and-reload shows the previous build.
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


def main():
    ap = argparse.ArgumentParser(description="Serve site/ for local preview.")
    ap.add_argument("--port", type=int, default=8766)
    args = ap.parse_args()
    if not os.path.exists(os.path.join(SITE, "index.html")):
        raise SystemExit("site/index.html does not exist -- run: python3 publish.py")
    handler = functools.partial(Quiet, directory=SITE)
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", args.port), handler) as httpd:
        print("serving %s at http://localhost:%d  (ctrl-c to stop)"
              % (os.path.relpath(SITE, ROOT), args.port))
        httpd.serve_forever()


if __name__ == "__main__":
    main()
