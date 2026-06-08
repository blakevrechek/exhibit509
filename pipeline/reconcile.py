#!/usr/bin/env python3
"""
Exhibit 509 rebuild, step 4 (oracle mode): diff extracted facts vs the gz.

For every (school, year, field) in facts.sqlite that the gz also carries, compare
and classify: MATCH / MISMATCH / MISSING-IN-GZ. Numeric compares use a per-kind
tolerance (pcts/GPAs are float, counts are exact). Reports a per-field scoreboard
plus example mismatches — the goal for 2018-2025 is ~100% MATCH (any miss is a
parser bug to chase before trusting the no-oracle 2011-2017 backfill).

Usage: python3 pipeline/reconcile.py [year ...]
"""
import gzip
import json
import os
import sqlite3
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "pipeline", "facts.sqlite")
GZ = os.path.join(ROOT, "data", "exhibit_data.json.gz")

try:
    from overrides import ADJUDICATED
except ImportError:
    from pipeline.overrides import ADJUDICATED

# fields whose gz key differs from the extract field name
ALIAS = {}

FLOAT_FIELDS = {
    "acc", "bar", "bar_2yr", "bar_state_avg", "bar_state_diff",
    "gpa25", "gpa50", "gpa75", "lsat25", "lsat50", "lsat75",
    "trans_gpa25", "trans_gpa50", "trans_gpa75",
}
TOL = 0.06  # float tolerance (gz rounds pcts to 1 dp; GPAs to 2 dp)


def as_num(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def main():
    years = [int(y) for y in sys.argv[1:]] or None
    gz = json.load(gzip.open(GZ))
    hist = {s["id"]: s.get("history", {}) for s in gz["schools"]}

    conn = sqlite3.connect(DB)
    q = "SELECT school_id, year, field, value FROM facts"
    if years:
        q += " WHERE year IN (%s)" % ",".join("?" * len(years))
    rows = conn.execute(q, years or []).fetchall()

    score = defaultdict(lambda: [0, 0, 0])  # field -> [match, mismatch, no_gz]
    examples = defaultdict(list)
    adj_match = adj_mism = 0  # adjudicated schools/fields, reported but excluded
    for sid, year, field, val in rows:
        if sid in ADJUDICATED or (sid, field) in ADJUDICATED:
            gzf = ALIAS.get(field, field)
            h = hist.get(sid, {}).get(str(year), {})
            gv = h.get(gzf)
            en, gn = as_num(val), as_num(gv)
            ok = (en is not None and gn is not None and abs(en - gn) <= 0.5) or \
                 str(val).strip().lower() == str(gv).strip().lower()
            adj_match += ok
            adj_mism += not ok
            continue
        gzf = ALIAS.get(field, field)
        h = hist.get(sid, {}).get(str(year))
        if not h or gzf not in h or h[gzf] is None:
            score[field][2] += 1
            continue
        ev, gv = val, h[gzf]
        en, gn = as_num(ev), as_num(gv)
        if en is not None and gn is not None:
            ok = abs(en - gn) <= (TOL if field in FLOAT_FIELDS else 0.5)
        else:
            ok = str(ev).strip().lower() == str(gv).strip().lower()
        if ok:
            score[field][0] += 1
        else:
            score[field][1] += 1
            if len(examples[field]) < 6:
                examples[field].append(f"{sid}: extracted={ev!r} gz={gv!r}")

    tot = [0, 0, 0]
    print(f"{'field':24} {'MATCH':>7} {'MISM':>6} {'noGZ':>6}")
    print("-" * 46)
    for f in sorted(score):
        m, x, n = score[f]
        for i, v in enumerate((m, x, n)):
            tot[i] += v
        flag = "  <<<" if x else ""
        print(f"{f:24} {m:7} {x:6} {n:6}{flag}")
    print("-" * 46)
    print(f"{'TOTAL':24} {tot[0]:7} {tot[1]:6} {tot[2]:6}")
    pct = 100 * tot[0] / (tot[0] + tot[1]) if (tot[0] + tot[1]) else 0
    print(f"\nmatch rate (excl. noGZ): {pct:.2f}%")
    if adj_match or adj_mism:
        print(f"adjudicated schools (excluded; see FLAGS.md): "
              f"{adj_match} agree / {adj_mism} differ-by-design")

    mismatched = [f for f in sorted(examples) if examples[f]]
    if mismatched:
        print("\nmismatch examples:")
        for f in mismatched:
            print(f"  [{f}]")
            for e in examples[f]:
                print(f"     {e}")
    conn.close()


if __name__ == "__main__":
    main()
