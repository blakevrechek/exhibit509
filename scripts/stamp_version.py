#!/usr/bin/env python3
"""Single-source version stamper.

The visible app version was drifting across files (methodology said v1.13, Terms
said v1.16, the service-worker cache said v1.16.2). This script pins ONE canonical
version — the contents of the top-level VERSION file — into every place a version
is displayed or used, so they can no longer disagree.

What it stamps:
  * index.html / methodology.html / terms.html / about.html / contact.html
      - every visible "v<MAJOR.MINOR[.PATCH]>" token  -> v<VERSION>
  * sw.js
      - const CACHE = 'exhibit-v<...>'                -> exhibit-v<VERSION>

Idempotent. Run after bumping VERSION (and alongside build_school_pages.py).
Usage:  python3 scripts/stamp_version.py
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERSION_FILE = os.path.join(ROOT, "VERSION")

# A version token: v + 1-3 dotted numeric components. Deliberately requires a
# DIGIT after the dot so prose like "as of v1.x" (literal x) is never touched.
#
# The leading negative lookbehind keeps this off SVG path data. An SVG vertical
# lineto command (e.g. `h3v1.7c…`, `2.24.2v2.47h…`) also reads as `v<num>.<num>`,
# but its `v` always follows a coordinate digit (or letter/dot), whereas a real
# version token follows a space, `-`, `(`, `>`, etc. Without this guard the
# stamper rewrote the LinkedIn/Facebook share-icon coordinates every bump.
VTOKEN = re.compile(r"(?<![A-Za-z0-9.])v\d+\.\d+(?:\.\d+)?")

# Cache-bust query on the inline dataset (index.html <script src> + sw.js SHELL).
# Bumping it on every release forces a fresh fetch of data/exhibit-data.js instead
# of the service worker serving a stale copy, so data fixes actually reach users.
DATA_QS = re.compile(r"(exhibit-data\.js\?v=)\d+\.\d+(?:\.\d+)?")

HTML_FILES = [
    "index.html",
    "methodology.html",
    "terms.html",
    "about.html",
    "contact.html",
    "glossary.html",
    "blog.html",
]


def read_version():
    if not os.path.exists(VERSION_FILE):
        sys.exit("VERSION file not found at repo root")
    v = open(VERSION_FILE).read().strip()
    if not re.fullmatch(r"\d+\.\d+(?:\.\d+)?", v):
        sys.exit(f"VERSION must be like 1.18.0, got: {v!r}")
    return v


def stamp_html(path, version):
    full = os.path.join(ROOT, path)
    if not os.path.exists(full):
        return 0
    src = open(full, encoding="utf-8").read()
    new, n = VTOKEN.subn("v" + version, src)
    new, n2 = DATA_QS.subn(r"\g<1>" + version, new)
    if n or n2:
        open(full, "w", encoding="utf-8").write(new)
    return n + n2


def stamp_sw(version):
    full = os.path.join(ROOT, "sw.js")
    if not os.path.exists(full):
        return 0
    src = open(full, encoding="utf-8").read()
    new, n = re.subn(
        r"(const CACHE = 'exhibit-v)\d+\.\d+(?:\.\d+)?(')",
        r"\g<1>" + version + r"\g<2>",
        src,
    )
    new, n2 = DATA_QS.subn(r"\g<1>" + version, new)
    if n or n2:
        open(full, "w", encoding="utf-8").write(new)
    return n + n2


def main():
    version = read_version()
    total = 0
    log = []
    for f in HTML_FILES:
        n = stamp_html(f, version)
        total += n
        log.append(f"  {f}: {n}")
    n = stamp_sw(version)
    total += n
    log.append(f"  sw.js (CACHE): {n}")
    out = f"Stamped version v{version} ({total} replacements)\n" + "\n".join(log) + "\n"
    open(os.path.join("/tmp", "stamp_version.log"), "w").write(out)
    sys.stdout.write(out)


if __name__ == "__main__":
    main()
