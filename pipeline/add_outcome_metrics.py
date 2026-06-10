#!/usr/bin/env python3
"""
Inject derived outcome metrics into data/exhibit-data.js:

  1. Adjusted employment ("real-world" FTLT) — subtracts school/university-FUNDED
     full-time long-term positions from the FTLT employment count, per the raw ABA
     Employment Summary (history[year].raw_emp in the gz). Fields:
        emp_funded_pct        latest-cycle funded FTLT as % of graduates
        emp_adj_pct           latest-cycle (FTLT - funded) / grads * 100
        emp_funded_pct_trend  {year: funded %}
        emp_adj_pct_trend     {year: adjusted FTLT %}

  2. Splitter lean — an HONEST, marginal-data signal of whether a school's LSAT is
     nationally more selective than its GPA (favours splitters: high LSAT/low GPA)
     or vice-versa (reverse splitters). It is NOT a measured admit rate; the ABA
     data is marginal, not joint. lean = pctlRank(LSAT median) - pctlRank(GPA median),
     range about -100..100; positive = splitter-leaning. Fields:
        splitter_lean         latest-cycle lean (int)
        splitter_lean_trend   {year: lean}

Additive + idempotent: every record gets every field (null / {} when no data), so
the curated template stays uniform. Only the `const S = [...]` array is rewritten.

Run: python3 pipeline/add_outcome_metrics.py [--write]
"""
import gzip
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_JS = os.path.join(ROOT, "data", "exhibit-data.js")
GZ = os.path.join(ROOT, "data", "exhibit_data.json.gz")

NEW_FIELDS = ["emp_funded_pct", "emp_adj_pct", "emp_funded_pct_trend",
              "emp_adj_pct_trend", "splitter_lean", "splitter_lean_trend"]


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


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def funded_employment(gz):
    """{id: {'pct': {...}, 'adj': {...}}} from raw ABA Employment Summary rows."""
    out = {}
    for sc in gz["schools"]:
        pct, adj = {}, {}
        for y, row in sc.get("history", {}).items():
            r = row.get("raw_emp")
            if not r:
                continue
            grads = num(r.get("Total_GraduatesTotal"))
            if grads is None:
                grads = num(r.get("Total_GraduatesNumber"))
            ftlt = num(r.get("Total_FTLT"))
            if not grads or grads <= 0 or ftlt is None:
                continue
            funded = (num(r.get("Funded_BarPassgeFullTimeLongTerm")) or 0) + \
                     (num(r.get("Funded_JDAdvantageFullTimeLongTerm")) or 0)
            pct[int(y)] = round(funded / grads * 100, 1)
            adj[int(y)] = round((ftlt - funded) / grads * 100, 1)
        if pct:
            out[sc["id"]] = {"pct": pct, "adj": adj}
    return out


def pctl_ranks(pairs):
    """pairs = [(id, value)] -> {id: percentile rank 0..100} (fraction <= value)."""
    vals = sorted(v for _, v in pairs)
    n = len(vals)
    import bisect
    return {sid: round(bisect.bisect_right(vals, v) / n * 100) for sid, v in pairs}


def splitter_leans(S):
    """Latest lean per id + per-year lean trend, from marginal LSAT/GPA medians."""
    # latest
    cur = [(s["id"], s.get("lsat50"), s.get("gpa50")) for s in S
           if not s.get("closed_status")]
    lat = {}
    lp = pctl_ranks([(i, l) for i, l, g in cur if num(l) is not None])
    gp = pctl_ranks([(i, g) for i, l, g in cur if num(g) is not None])
    for i, l, g in cur:
        if i in lp and i in gp:
            lat[i] = lp[i] - gp[i]
    # trend: rank within each year across all schools that reported both that year
    years = set()
    for s in S:
        years.update((s.get("lsat_trend") or {}).keys())
    trends = {s["id"]: {} for s in S}
    for y in years:
        pairs_l = [(s["id"], (s.get("lsat_trend") or {}).get(y)) for s in S]
        pairs_g = [(s["id"], (s.get("gpa_trend") or {}).get(y)) for s in S]
        lpy = pctl_ranks([(i, v) for i, v in pairs_l if num(v) is not None])
        gpy = pctl_ranks([(i, v) for i, v in pairs_g if num(v) is not None])
        for i in lpy:
            if i in gpy:
                trends[i][int(y)] = lpy[i] - gpy[i]
    return lat, trends


def main():
    write = "--write" in sys.argv
    js = open(DATA_JS, encoding="utf-8").read()
    a, b = array_bounds(js)
    S = json.loads(js[a:b])
    gz = json.load(gzip.open(GZ))

    emp = funded_employment(gz)
    lean_cur, lean_trend = splitter_leans(S)

    n_emp = n_lean = 0
    for s in S:
        sid = s.get("id")
        e = emp.get(sid)
        if e and e["pct"]:
            ly = max(e["pct"])
            s["emp_funded_pct"] = e["pct"][ly]
            s["emp_adj_pct"] = e["adj"][ly]
            s["emp_funded_pct_trend"] = {str(y): e["pct"][y] for y in sorted(e["pct"])}
            s["emp_adj_pct_trend"] = {str(y): e["adj"][y] for y in sorted(e["adj"])}
            n_emp += 1
        else:
            s["emp_funded_pct"] = None
            s["emp_adj_pct"] = None
            s["emp_funded_pct_trend"] = {}
            s["emp_adj_pct_trend"] = {}
        lt = {str(y): lean_trend.get(sid, {})[y] for y in sorted(lean_trend.get(sid, {}))}
        s["splitter_lean"] = lean_cur.get(sid)
        s["splitter_lean_trend"] = lt
        if sid in lean_cur:
            n_lean += 1

    print("add_outcome_metrics summary")
    print(f"  adjusted-employment populated: {n_emp}/{len(S)}")
    print(f"  splitter-lean populated:       {n_lean}/{len(S)}")
    # spot check
    for sid in ("georgetown-university", "harvard-university", "baylor-university"):
        s = next((x for x in S if x["id"] == sid), None)
        if s:
            print(f"  {sid}: funded%={s['emp_funded_pct']} adj%={s['emp_adj_pct']} "
                  f"lean={s['splitter_lean']}")

    if write:
        open(DATA_JS, "w", encoding="utf-8").write(
            js[:a] + json.dumps(S, ensure_ascii=False) + js[b:])
        print(f"WROTE {DATA_JS}")
    else:
        print("(dry-run; pass --write)")


if __name__ == "__main__":
    main()
