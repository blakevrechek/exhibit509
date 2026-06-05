#!/usr/bin/env python3
"""
Exhibit 509 — data-validation gate.

Runs BEFORE any static regeneration (wired into scripts/build.sh and a dedicated
CI workflow) so the data-generation bug classes that have actually shipped can no
longer reach `main`:

  1. Constant-collapse   — a "should vary" trend whose latest year is the same
                           value across many schools (e.g. fac_trend 2025 == 25
                           for 188 schools).
  2. Truncated trends    — an inline *_trend missing the latest year(s) that the
                           gz history actually has (e.g. WashU lsat_trend cut to
                           2023-2025 when 2018-2025 exists).
  3. Impossible values   — out-of-range / NaN in trends or current-cycle scalars.
  4. Inline<->trend drift— a current-cycle scalar that disagrees with the latest
                           point of its own trend (catches mislabel/stale data).
  5. Structural          — school count + gz id coverage sanity.

Exit status: 0 if no ERRORS (warnings allowed), 1 otherwise.
Usage: python3 scripts/validate_data.py
"""
import gzip
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_JS = os.path.join(ROOT, "data", "exhibit-data.js")
GZ = os.path.join(ROOT, "data", "exhibit_data.json.gz")

# 4 inline-only CLOSED schools that legitimately have no gz history record.
KNOWN_GZ_MISSING = {
    "charlotte-school-of-law", "hamline-university",
    "indiana-tech", "william-mitchell-college-of-law",
}

# inline *_trend  ->  gz per-year history key (for the truncation + range checks).
# NB: bar passage is deliberately excluded — it is a cohort metric with legitimate
# year gaps and a 1-year-newer gz cohort, so it is not a truncation signal.
TREND_GZ = {
    "lsat_trend": "lsat50", "lsat25_trend": "lsat25", "lsat75_trend": "lsat75",
    "gpa_trend": "gpa50", "gpa25_trend": "gpa25", "gpa75_trend": "gpa75",
    "tui_trend": "tui_ft_res", "fac_trend": "fac_ft",
}

# current-cycle scalar  ->  its trend (latest point must agree)
SCALAR_TREND = {
    "lsat50": "lsat_trend", "gpa50": "gpa_trend", "tui": "tui_trend",
    "fac_ft": "fac_trend",
}

# "should vary across schools" trends — a near-constant latest year is a bug.
VARYING_TRENDS = [
    "lsat_trend", "gpa_trend", "fac_trend", "tui_trend",
    "enr_trend", "apps_trend", "offers_trend",
]

# plausible ranges for range-checking (value, or null)
RANGES = {
    "lsat_trend": (120, 180), "lsat25_trend": (120, 180), "lsat75_trend": (120, 180),
    "gpa_trend": (0.0, 4.34), "gpa25_trend": (0.0, 4.34), "gpa75_trend": (0.0, 4.34),
    "tui_trend": (0, 130000), "nrt_trend": (0, 130000),
    "bar_trend": (0, 100), "bar_2yr_trend": (0, 100), "acc_trend": (0, 100),
    "fac_trend": (0, 1500),
}

errors, warnings = [], []
def err(m): errors.append(m)
def warn(m): warnings.append(m)


def extract_S(js):
    """Bracket-walk the inline `const S = [...]` array (string-aware)."""
    i = js.find("const S = ")
    if i < 0:
        raise SystemExit("validate_data: 'const S =' not found in exhibit-data.js")
    start = i + len("const S = ")
    depth = 0; in_str = False; esc = False; j = start
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
                    j += 1; break
        j += 1
    return json.loads(js[start:j])


def years_of(trend):
    if not isinstance(trend, dict):
        return []
    return sorted(int(y) for y in trend if re.fullmatch(r"\d{4}", str(y)))


def is_num(v):
    return isinstance(v, (int, float)) and not (isinstance(v, float) and v != v)


def main():
    S = extract_S(open(DATA_JS, encoding="utf-8").read())
    gz = json.load(gzip.open(GZ))
    gz_hist = {s["id"]: s.get("history", {}) for s in gz["schools"]}
    n = len(S)

    # ── 5. Structural ────────────────────────────────────────────────────────
    if n < 200 or n > 230:
        err(f"school count {n} is outside the sane 200-230 band")
    ids = [s.get("id") for s in S]
    if len(set(ids)) != n:
        err("duplicate school ids in dataset")
    missing_gz = [i for i in ids if i not in gz_hist and i not in KNOWN_GZ_MISSING]
    if missing_gz:
        warn(f"{len(missing_gz)} inline ids absent from gz history (unexpected): {missing_gz[:6]}")

    # ── 1. Constant-collapse on the latest year of each varying trend ─────────
    for tk in VARYING_TRENDS:
        latest_vals = []
        for s in S:
            ys = years_of(s.get(tk))
            if not ys:
                continue
            v = s[tk].get(str(ys[-1]))
            if is_num(v):
                latest_vals.append(round(float(v), 4))
        if len(latest_vals) < 20:
            continue
        top = max(set(latest_vals), key=latest_vals.count)
        frac = latest_vals.count(top) / len(latest_vals)
        # a single exact value dominating the latest year => generation artifact
        if frac > 0.50:
            err(f"{tk}: latest-year value {top} repeats across {frac:.0%} of "
                f"{len(latest_vals)} schools (constant-collapse bug)")
        elif frac > 0.25:
            warn(f"{tk}: latest-year value {top} repeats across {frac:.0%} of schools "
                 f"(review: possible constant-collapse)")

    # ── 2. Truncated trends vs gz coverage (per metric, aggregated) ───────────
    # A school is "truncated" if its inline trend is missing >=2 of the gz years
    # that carry a value (tolerates the single newest cohort-lag year and the odd
    # one-off gap; the real bug dropped 5+ years, e.g. WashU lsat cut to 2023-25).
    for tk, gk in TREND_GZ.items():
        truncated = 0
        eligible = 0
        examples = []
        for s in S:
            hist = gz_hist.get(s.get("id"))
            if not hist:
                continue
            gz_years = [int(y) for y in hist
                        if re.fullmatch(r"\d{4}", str(y)) and is_num(hist[y].get(gk))]
            if len(gz_years) < 3:
                continue
            eligible += 1
            tyears = set(years_of(s.get(tk)))
            missing = sum(1 for y in gz_years if y not in tyears)
            if missing >= 2:
                truncated += 1
                if len(examples) < 6:
                    examples.append(f"{s['id']} ({missing} of {len(gz_years)} gz yrs missing)")
        if eligible >= 20:
            frac = truncated / eligible
            if frac > 0.05:
                err(f"{tk}: {truncated}/{eligible} schools have trends truncated vs "
                    f"available gz history: {examples}")
            elif truncated:
                warn(f"{tk}: {truncated}/{eligible} schools shorter than gz history: {examples}")

    # ── 3. Impossible values in trends + current-cycle scalars ───────────────
    # NaN / non-numeric and clearly-impossible values are ERRORS; the known LSAT/
    # uGPA 0-sentinels (nulled at runtime) and unusually-high-but-finite tuition
    # are WARNINGS so the gate surfaces them without blocking on pre-existing data.
    LSATGPA = {"lsat_trend", "lsat25_trend", "lsat75_trend",
               "gpa_trend", "gpa25_trend", "gpa75_trend"}
    TUI = {"tui_trend", "nrt_trend"}
    nan_ct = sentinel_ct = highttui_ct = impossible_ct = 0
    for s in S:
        sid = s.get("id")
        for tk, (lo, hi) in RANGES.items():
            tr = s.get(tk)
            if not isinstance(tr, dict):
                continue
            for y, v in tr.items():
                if v is None:
                    continue
                if not is_num(v):
                    nan_ct += 1
                    if nan_ct <= 10: err(f"{sid}.{tk}[{y}] = {v!r} is not numeric")
                    continue
                if tk in LSATGPA and v == 0:
                    sentinel_ct += 1            # known 0-sentinel, nulled at load
                elif tk in TUI and hi < v <= 200000:
                    highttui_ct += 1            # high but finite (often TUI_IRREGULAR)
                elif v < lo or v > hi:
                    impossible_ct += 1
                    if impossible_ct <= 12:
                        err(f"{sid}.{tk}[{y}] = {v!r} impossible (outside [{lo},{hi}])")
        for pk in ("acc", "bar", "ftlt_pct", "emp_bar_pct"):
            v = s.get(pk)
            if v is not None and (not is_num(v) or v < 0 or v > 100):
                err(f"{sid}.{pk} = {v!r} is not a valid percentage")
    if impossible_ct > 12:
        err(f"...and {impossible_ct - 12} more impossible trend values")
    if sentinel_ct:
        warn(f"{sentinel_ct} LSAT/uGPA 0-sentinels in stored trends (nulled at runtime; "
             f"consider nulling in data/exhibit-data.js)")
    if highttui_ct:
        warn(f"{highttui_ct} tuition values above the typical ceiling (verify vs TUI_IRREGULAR)")

    # ── 4. Inline scalar <-> trend latest-point drift ────────────────────────
    TOL = {"lsat50": 0.5, "gpa50": 0.011, "tui": 1.0, "fac_ft": 0.5}
    for sk, tk in SCALAR_TREND.items():
        drift = 0; examples = []
        for s in S:
            sv = s.get(sk)
            ys = years_of(s.get(tk))
            if sv is None or not ys:
                continue
            tv = s[tk].get(str(ys[-1]))
            if not is_num(tv) or not is_num(sv):
                continue
            if abs(float(sv) - float(tv)) > TOL[sk]:
                drift += 1
                if len(examples) < 6:
                    examples.append(f"{s['id']}: {sk}={sv} vs {tk}[{ys[-1]}]={tv}")
        if drift > max(3, 0.05 * n):
            err(f"{sk} disagrees with {tk} latest point for {drift} schools "
                f"(inline/trend drift): {examples}")
        elif drift:
            warn(f"{sk} vs {tk}: {drift} schools differ at the latest year: {examples}")

    # ── report ───────────────────────────────────────────────────────────────
    for w in warnings:
        print(f"  WARN  {w}")
    for e in errors:
        print(f"  ERROR {e}")
    print(f"\nvalidate_data: {len(errors)} error(s), {len(warnings)} warning(s) "
          f"across {n} schools.")
    if errors:
        print("FAILED — fix the data (data/exhibit-data.js) before building.")
        sys.exit(1)
    print("PASSED.")


if __name__ == "__main__":
    main()
