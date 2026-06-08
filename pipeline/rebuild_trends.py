#!/usr/bin/env python3
"""
Additively backfill the curated data/exhibit-data.js *_trend series from
pipeline/facts.sqlite, so the display layer reaches back to 2011 like the
rebuilt gz (keeps validate_data.py's truncation gate satisfied).

ADDITIVE ONLY: a trend year is written only when it's missing from the
trend dict. Existing displayed values are never overwritten — so the F3/F4
source values only land in the historical GAPS, not over live numbers (honours
the call-out-don't-silently-correct rule). Only the `const S = [...]` array is
rewritten; BLS/RPP/FMR and the file header are left byte-identical.

Run: python3 pipeline/rebuild_trends.py [--write]
"""
import json
import os
import re
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_JS = os.path.join(ROOT, "data", "exhibit-data.js")
DB = os.path.join(ROOT, "pipeline", "facts.sqlite")

# curated trend key -> (facts field, lo, hi, allow_zero)
TRENDS = {
    "lsat_trend": ("lsat50", 120, 180, False), "lsat25_trend": ("lsat25", 120, 180, False),
    "lsat75_trend": ("lsat75", 120, 180, False),
    "gpa_trend": ("gpa50", 0.0, 4.34, False), "gpa25_trend": ("gpa25", 0.0, 4.34, False),
    "gpa75_trend": ("gpa75", 0.0, 4.34, False),
    "tui_trend": ("tui_ft_res", 1000, 130000, False),
    "nrt_trend": ("tui_ft_nonres", 1000, 130000, False),
    "fac_trend": ("fac_ft", 0, 1500, True),
    "bar_trend": ("bar", 0, 100, True), "bar_2yr_trend": ("bar_2yr", 0, 100, True),
    "bar_takers_trend": ("bar_first_takers", 0, 100000, True),
    "bar_passers_trend": ("bar_first_passers", 0, 100000, True),
    "acc_trend": ("acc", 0, 100, True),
    "apps_trend": ("apps", 0, 100000, True), "offers_trend": ("offers", 0, 100000, True),
    "trans_in_trend": ("trans_in", 0, 100000, True),
    "trans_out_trend": ("trans_out", 0, 100000, True),
    "cond_enter_trend": ("cond_enter", 0, 100000, True),
    "cond_elim_trend": ("cond_elim", 0, 100000, True),
}


def array_bounds(js):
    i = js.find("const S = ") + len("const S = ")
    depth = 0; in_str = False; esc = False; j = i
    while j < len(js):
        c = js[j]
        if in_str:
            if esc: esc = False
            elif c == "\\": esc = True
            elif c == '"': in_str = False
        else:
            if c == '"': in_str = True
            elif c == "[": depth += 1
            elif c == "]":
                depth -= 1
                if depth == 0:
                    return i, j + 1
        j += 1
    raise SystemExit("could not bracket-walk const S")


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def main():
    write = "--write" in sys.argv
    js = open(DATA_JS, encoding="utf-8").read()
    a, b = array_bounds(js)
    S = json.loads(js[a:b])

    conn = sqlite3.connect(DB)
    facts = {}
    fields = {f for f, *_ in TRENDS.values()}
    q = "SELECT school_id, year, field, value FROM facts WHERE field IN (%s)" % \
        ",".join("?" * len(fields))
    for sid, year, field, value in conn.execute(q, list(fields)):
        facts.setdefault(sid, {}).setdefault(field, {})[str(year)] = value

    added = {}; schools_touched = 0
    for s in S:
        sid = s.get("id")
        f = facts.get(sid)
        if not f:
            continue
        touched = False
        for tkey, (field, lo, hi, allow_zero) in TRENDS.items():
            tr = s.get(tkey)
            if not isinstance(tr, dict):
                continue  # don't create new trend series, only extend existing
            for y, raw in f.get(field, {}).items():
                if y in tr:
                    continue  # ADDITIVE: never overwrite an existing year
                v = num(raw)
                if v is None or v < lo or v > hi or (v == 0 and not allow_zero):
                    continue
                tr[y] = int(v) if float(v).is_integer() and field not in (
                    "gpa50", "gpa25", "gpa75", "acc", "bar", "bar_2yr") else v
                added[tkey] = added.get(tkey, 0) + 1
                touched = True
        if touched:
            schools_touched += 1

    print("rebuild_trends summary (additive backfill)")
    print(f"  schools touched: {schools_touched}")
    for k in sorted(added):
        print(f"  +{added[k]:5}  {k}")
    print(f"  total cells added: {sum(added.values())}")

    if write:
        new_js = js[:a] + json.dumps(S, ensure_ascii=False) + js[b:]
        open(DATA_JS, "w", encoding="utf-8").write(new_js)
        print(f"\nWROTE {DATA_JS}")
    else:
        print("\n(dry-run; pass --write to apply)")


if __name__ == "__main__":
    main()
