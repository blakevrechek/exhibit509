#!/usr/bin/env python3
"""
Inject current-cycle GRE / JD-Next / 1L-attrition scalars into the curated
data/exhibit-data.js records from pipeline/facts.sqlite, so the page generator
and app can display them. Additive: only sets a field when facts has it for the
school's current cycle and the record doesn't already carry it. Only the
`const S = [...]` array is rewritten; BLS/RPP/FMR untouched.

Run: python3 pipeline/add_curated_metrics.py [--write]
"""
import json
import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_JS = os.path.join(ROOT, "data", "exhibit-data.js")
DB = os.path.join(ROOT, "pipeline", "facts.sqlite")

NEW = ["gre_v25", "gre_v50", "gre_v75", "gre_q25", "gre_q50", "gre_q75",
       "gre_a25", "gre_a50", "gre_a75", "jdnext25", "jdnext50", "jdnext75",
       "atr_acad_1l", "atr_other_1l"]
FLOAT_FIELDS = {"gre_a25", "gre_a50", "gre_a75"}  # Analytical Writing is x.x


def array_bounds(js):
    i = js.find("const S = ") + len("const S = ")
    depth = in_str = esc = 0
    j = i
    while j < len(js):
        c = js[j]
        if in_str:
            if esc: esc = 0
            elif c == "\\": esc = 1
            elif c == '"': in_str = 0
        elif c == '"': in_str = 1
        elif c == "[": depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                return i, j + 1
        j += 1
    raise SystemExit("bracket-walk failed")


def main():
    write = "--write" in sys.argv
    js = open(DATA_JS, encoding="utf-8").read()
    a, b = array_bounds(js)
    S = json.loads(js[a:b])

    conn = sqlite3.connect(DB)
    # each school's current display cycle = its own latest year in the curated record
    facts = {}
    q = "SELECT school_id, year, field, value FROM facts WHERE field IN (%s)" % \
        ",".join("?" * len(NEW))
    for sid, y, f, v in conn.execute(q, NEW):
        facts.setdefault(sid, {}).setdefault(int(y), {})[f] = v

    added = {f: 0 for f in NEW}
    touched = 0
    for s in S:
        sid = s.get("id")
        cur = s.get("_cur_year")
        fy = facts.get(sid, {})
        if not fy:
            continue
        # prefer the record's current cycle, else the latest year facts has
        year = cur if cur in fy else (max(fy) if fy else None)
        if year is None:
            continue
        row = fy[year]
        hit = False
        for f in NEW:
            if f in row and row[f] is not None and s.get(f) is None:
                v = float(row[f])
                s[f] = v if f in FLOAT_FIELDS else (int(v) if v.is_integer() else v)
                added[f] += 1
                hit = True
        if hit:
            touched += 1

    print("add_curated_metrics summary")
    for f in NEW:
        print(f"  +{added[f]:4}  {f}")
    print(f"  schools touched: {touched}")

    if write:
        open(DATA_JS, "w", encoding="utf-8").write(js[:a] + json.dumps(S, ensure_ascii=False) + js[b:])
        print(f"WROTE {DATA_JS}")
    else:
        print("(dry-run; pass --write)")


if __name__ == "__main__":
    main()
