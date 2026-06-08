#!/usr/bin/env python3
"""
Exhibit 509 rebuild, step 4b: reconcile facts vs the CURATED exhibit-data.js
trends. This is the reconciliation oracle for the no-oracle backfill years
(2017-2011): the gz history only reaches 2018, but the curated *_trend series
reach back to 2011 for most metrics, so they are the reference there.

Validated on the overlap years (2018-2020), where facts already match the gz
100%: if facts also match the curated trends there, the trends are a trustworthy
reference below 2018.

Classifies each (school, year, field) the curated layer carries:
  MATCH / MISMATCH / NO-TREND (curated has no value -> rebuild ADDS it).
Usage: python3 pipeline/reconcile_trends.py [year ...]
"""
import os
import re
import sqlite3
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
from validate_data import extract_S
try:
    from overrides import ADJUDICATED
except ImportError:
    from pipeline.overrides import ADJUDICATED

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "pipeline", "facts.sqlite")
DATA_JS = os.path.join(ROOT, "data", "exhibit-data.js")

# extracted fact field -> curated *_trend key. Only fields where the curated
# trend is the SAME quantity as the raw fact (validated ~100% on overlap years).
# Deliberately excluded — the curated layer diverges from raw here:
#   enr_trend    — hand-curated enrollment, != raw total JD or 1L
#   schol_trend  — a {none,lt,mt,full,gt} PERCENTAGE dict, not the schol_total count
FIELD_TREND = {
    "lsat50": "lsat_trend", "lsat25": "lsat25_trend", "lsat75": "lsat75_trend",
    "gpa50": "gpa_trend", "gpa25": "gpa25_trend", "gpa75": "gpa75_trend",
    "bar": "bar_trend", "bar_2yr": "bar_2yr_trend",
    "bar_first_takers": "bar_takers_trend", "bar_first_passers": "bar_passers_trend",
    "acc": "acc_trend", "apps": "apps_trend", "offers": "offers_trend",
    "fac_ft": "fac_trend",
    "tui_ft_res": "tui_trend", "tui_ft_nonres": "nrt_trend",
    "trans_in": "trans_in_trend", "trans_out": "trans_out_trend",
    "cond_enter": "cond_enter_trend", "cond_elim": "cond_elim_trend",
}
FLOAT_FIELDS = {"acc", "bar", "bar_2yr", "gpa25", "gpa50", "gpa75",
                "lsat25", "lsat50", "lsat75"}
TOL = 0.06


def as_num(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def main():
    years = [int(y) for y in sys.argv[1:]] or None
    S = extract_S(open(DATA_JS, encoding="utf-8").read())
    cur = {s["id"]: s for s in S}

    conn = sqlite3.connect(DB)
    q = "SELECT school_id, year, field, value FROM facts WHERE field IN (%s)" % \
        ",".join("?" * len(FIELD_TREND))
    params = list(FIELD_TREND)
    if years:
        q += " AND year IN (%s)" % ",".join("?" * len(years))
        params += years
    rows = conn.execute(q, params).fetchall()

    score = defaultdict(lambda: [0, 0, 0])  # field -> [match, mismatch, no_trend]
    examples = defaultdict(list)
    for sid, year, field, val in rows:
        if sid in ADJUDICATED or (sid, field) in ADJUDICATED:
            continue
        tkey = FIELD_TREND[field]
        trend = cur.get(sid, {}).get(tkey)
        tv = trend.get(str(year)) if isinstance(trend, dict) else None
        if tv is None:
            score[field][2] += 1
            continue
        en, gn = as_num(val), as_num(tv)
        if en is not None and gn is not None:
            ok = abs(en - gn) <= (TOL if field in FLOAT_FIELDS else 0.5)
        else:
            ok = str(val).strip().lower() == str(tv).strip().lower()
        if ok:
            score[field][0] += 1
        else:
            score[field][1] += 1
            if len(examples[field]) < 6:
                examples[field].append(f"{sid}@{year}: facts={val!r} trend={tv!r}")

    tot = [0, 0, 0]
    print(f"{'field':20} {'MATCH':>7} {'MISM':>6} {'noTrend':>8}")
    print("-" * 44)
    for f in sorted(score):
        m, x, n = score[f]
        for idx, v in enumerate((m, x, n)):
            tot[idx] += v
        print(f"{f:20} {m:7} {x:6} {n:8}{'  <<<' if x else ''}")
    print("-" * 44)
    print(f"{'TOTAL':20} {tot[0]:7} {tot[1]:6} {tot[2]:8}")
    den = tot[0] + tot[1]
    print(f"\nmatch rate (excl. noTrend): {100*tot[0]/den:.2f}%" if den else "no comparable cells")
    for f in sorted(examples):
        if examples[f]:
            print(f"  [{f}]")
            for e in examples[f]:
                print(f"     {e}")
    conn.close()


if __name__ == "__main__":
    main()
