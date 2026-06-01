#!/usr/bin/env python3
"""Emit the website data layer (data/exhibit-data.js `S`) from the rev3 SQLite store.

MERGE strategy (owner-approved): rev3 is authoritative for the core ABA-509 metrics
it validates (admissions, LSAT/GPA, tuition/fees, scholarships, bar, employment
firm-size, faculty FT, attrition, transfers); every field rev3 does NOT produce
(geo lat/lng, economic bls_mean, curriculum cur_*, demographics race_*/sex_*,
conditional scholarships cond_*, placement, transfer-GPA, total-JD enr) is carried
over verbatim from the current data layer.

The rev3 DB is NOT in the repo; it ships in exhibit.7z. Point --db at the extracted
exhibit.db. This script only rewrites the `S` array; BLS/RPP/FMR globals are untouched.

Forks (flip via the FORKS dict): see README block at bottom of the report.
"""
import json, re, sqlite3, argparse, sys

# --- configurable definitional forks (defaults = conservative "no regression") ---
FORKS = {
    # employer-type sector %s: "new data controls 100%" -> adopt rev3 FTLT-based values.
    'sector_types_from_rev3': True,
    # closed/inline-only schools: populate from rev3 final reporting year (gaps -> dashed in UI).
    'populate_closed': True,
    # trends (*_trend): overlay rev3's full 2011-2025 series onto the current trends -
    # fills missing years + adopts bulletproof values, never drops a year rev3 lacks.
    'rebuild_trends': True,
}

MANUAL = {'la-verne-university-of': 184, 'hamline-university': 218}

def slug(n):
    return re.sub(r'[^a-z0-9]+', '-', n.lower()).strip('-')

def parse_S(js_src):
    st = js_src.index('const S = ') + len('const S = ')
    d = 0; i = st
    while i < len(js_src):
        c = js_src[i]
        if c == '[': d += 1
        elif c == ']':
            d -= 1
            if d == 0: end = i + 1; break
        i += 1
    return json.loads(js_src[st:end]), st, end

def build_crosswalk(S, cur):
    dim = {r[0]: r[1] for r in cur.execute("SELECT school_id,canonical_name FROM dim_school")}
    has_facts = set(r[0] for r in cur.execute("SELECT DISTINCT school_id FROM fact_school_year"))
    rev_slug = {sid: slug(cn) for sid, cn in dim.items()}
    xw = {}
    for s in S:
        wid = s['id']
        if wid in MANUAL:
            xw[wid] = MANUAL[wid]; continue
        key = slug(wid)
        hit = [sid for sid, sl in rev_slug.items() if sl == key]
        if not hit:
            hit = [sid for sid, sl in rev_slug.items() if sl.startswith(key) and len(key) >= 18]
        if not hit:
            raise SystemExit(f"crosswalk: no rev3 match for website id '{wid}'")
        xw[wid] = next((h for h in hit if h in has_facts), hit[0])
    return xw

def r1(x):  # 1-decimal round, None-safe
    return None if x is None else round(x, 1)

def ri(x):  # int round, None-safe
    return None if x is None else int(round(x))

# rev3 metric -> website field, with value transform
DIRECT_INT = {  # website field : rev3 metric  (counts/scores; stored as int)
    'apps': 'apps', 'offers': 'offers', 'enr_1l': 'enroll_total',
    'lsat25': 'lsat25', 'lsat50': 'lsat50', 'lsat75': 'lsat75',
    'tui': 'res_tui', 'nrt': 'nr_tui', 'ft_fee': 'ft_fee',
    'grant_med': 'grant50', 'grant_p25': 'grant25', 'grant_p75': 'grant75',
    'grads': 'emp_grads_total', 'ftlt': 'emp_total_ftlt', 'credit_hours': 'credit_hours',
    'gre_takers': 'gre_enrolled', 'trans_in': 'transfer_in', 'trans_out': 'transfer_out',
    'living': 'living_off',  # fac_ft handled specially (latest positive year)
}
DIRECT_FLOAT = {  # 1-decimal fields
    'acc': 'acc_rate', 'bar': 'bar_pct', 'bar_2yr': 'bar2yr_pct',
    'bar_state_avg': 'bar_state_avg', 'atr_1l': 'attr_1l',
}
# gpa kept at 2 decimals
GPA = {'gpa25': 'gpa25', 'gpa50': 'gpa50', 'gpa75': 'gpa75'}

# Trend overlay: trend field -> (rev3 metric, value formatter). rev3 fills new years and
# updates overlapping years; years rev3 lacks are preserved from the current trend (no drop).
def _f_int(v): return int(round(v))
def _f_float(v): return float(v)
def _f_2dp(v): return round(v, 2)
TREND_MAP = {
    'apps_trend': ('apps', _f_float), 'offers_trend': ('offers', _f_float),
    'acc_trend': ('acc_rate', _f_2dp),
    # NOTE: enr_trend is total-JD enrollment; rev3 enroll_total is the entering class only -> carry over.
    # NOTE: fac_trend basis is ambiguous (FT-only in live data, but internally inconsistent) -> carry over.
    'lsat_trend': ('lsat50', _f_float), 'lsat25_trend': ('lsat25', _f_float), 'lsat75_trend': ('lsat75', _f_float),
    'gpa_trend': ('gpa50', _f_2dp), 'gpa25_trend': ('gpa25', _f_2dp), 'gpa75_trend': ('gpa75', _f_2dp),
    'tui_trend': ('res_tui', _f_int), 'nrt_trend': ('nr_tui', _f_int),
    'bar_trend': ('bar_pct', _f_2dp), 'bar_2yr_trend': ('bar2yr_pct', _f_2dp),
    'bar_takers_trend': ('bar_takers', _f_float), 'bar_passers_trend': ('bar_passers', _f_float),
    'trans_in_trend': ('transfer_in', _f_float), 'trans_out_trend': ('transfer_out', _f_float),
}
# fac_trend (fac_ft+fac_pt per year) and schol_trend (derived buckets per year) handled separately.
# cond_enter_trend / cond_elim_trend: rev3 lacks conditional scholarships -> left as-is.

def emit(db_path, data_js_path, out_path, report_path):
    cur = sqlite3.connect(db_path).cursor()
    src = open(data_js_path).read()
    S, sstart, send = parse_S(src)
    xw = build_crosswalk(S, cur)
    latest = {sid: yr for sid, yr in cur.execute("SELECT school_id,MAX(year) FROM fact_school_year GROUP BY school_id")}

    def facts(rid, yr):
        return {m: v for m, v, vt in cur.execute(
            "SELECT metric,value,value_text FROM fact_school_year WHERE school_id=? AND year=?", (rid, yr))}
    def latest_positive(rid, metric):
        """Latest year where metric has a value > 0 (faculty: ignore the Duke-style 0 in the newest year)."""
        row = cur.execute("SELECT value FROM fact_school_year WHERE school_id=? AND metric=? AND value>0 "
                          "ORDER BY year DESC LIMIT 1", (rid, metric)).fetchone()
        return row[0] if row else None

    diffs = {}  # field -> list[(wid, old, new)]
    def setf(rec, wid, field, newv):
        if newv is None:            # never replace a real value with null (rev3 gap -> keep current)
            return
        old = rec.get(field)
        if old != newv:
            diffs.setdefault(field, []).append((wid, old, newv))
        rec[field] = newv

    def overlay_trends(rec, wid, rid):
        """rev3 fills new years + updates overlaps; never drops a year the current trend already has."""
        def rev_series(metric, fmt):
            return {str(y): fmt(v) for y, v in cur.execute(
                "SELECT year,value FROM fact_school_year WHERE school_id=? AND metric=? "
                "AND value IS NOT NULL ORDER BY year", (rid, metric))}
        for tf, (metric, fmt) in TREND_MAP.items():
            rev = rev_series(metric, fmt)
            if not rev:
                continue
            merged = dict(rec.get(tf) or {})   # preserve current (incl. years rev3 lacks)
            for y, v in rev.items():
                if merged.get(y) != v:
                    diffs.setdefault(tf, []).append((wid + '@' + y, merged.get(y), v))
                merged[y] = v
            rec[tf] = merged
        # fac_trend = total faculty (fac_ft + fac_pt) per year. The live fac_trend is
        # internally broken (FT-only in old years, garbage in recent), and the row it
        # annotates is "Total Faculty" -> rebuild as the FT+PT total. Overlay (keep
        # current years rev3 lacks).
        facyrs = {}
        for y, m, v in cur.execute("SELECT year,metric,value FROM fact_school_year WHERE school_id=? "
                                   "AND metric IN ('fac_ft','fac_pt') AND value IS NOT NULL", (rid,)):
            facyrs.setdefault(y, {})[m] = v
        if facyrs:
            merged = dict(rec.get('fac_trend') or {})
            for y, mm in facyrs.items():
                if 'fac_ft' in mm:  # need FT present to form a meaningful total
                    nv = float(mm.get('fac_ft', 0) + mm.get('fac_pt', 0))
                    if merged.get(str(y)) != nv:
                        diffs.setdefault('fac_trend', []).append((wid + '@' + str(y), merged.get(str(y)), nv))
                    merged[str(y)] = nv
            rec['fac_trend'] = merged
        # schol_trend = {year:{none,lt,mt,full,gt}} derived from counts/students_total; overlay
        sch = {}
        for y, m, v in cur.execute("SELECT year,metric,value FROM fact_school_year WHERE school_id=? "
            "AND metric IN ('students_total','schol_none','schol_lt_half','schol_half_full','schol_full','schol_gt_full') "
            "AND value IS NOT NULL", (rid,)):
            sch.setdefault(y, {})[m] = v
        if sch:
            before = rec.get('schol_trend') or {}
            merged = dict(before)
            for y, mm in sch.items():
                tot = mm.get('students_total')
                if not tot:
                    continue
                merged[str(y)] = {
                    'none': r1(100 * mm.get('schol_none', 0) / tot), 'lt': r1(100 * mm.get('schol_lt_half', 0) / tot),
                    'mt': r1(100 * mm.get('schol_half_full', 0) / tot), 'full': r1(100 * mm.get('schol_full', 0) / tot),
                    'gt': r1(100 * mm.get('schol_gt_full', 0) / tot),
                }
            if merged != before:
                diffs.setdefault('schol_trend', []).append((wid, 'updated', len(merged)))
            rec['schol_trend'] = merged
        # sanitize enr_trend (carried-over v2 total-JD enrollment): drop implausibly
        # tiny points (a real JD program can't have ~0-3 total students) so the chart
        # shows a dashed gap instead of a corrupt spike (e.g. Montana 2021=3, Howard 0).
        et = rec.get('enr_trend')
        if et:
            yvals = [v for k, v in et.items() if re.match(r'\d{4}', k) and isinstance(v, (int, float)) and v > 0]
            if len(yvals) >= 4:
                med = sorted(yvals)[len(yvals) // 2]
                for k in [k for k in et if re.match(r'\d{4}', k)]:
                    v = et.get(k)
                    if isinstance(v, (int, float)) and v < 0.4 * med and v < 60:
                        diffs.setdefault('enr_trend_sanitized', []).append((wid + '@' + k, v, None))
                        del et[k]

    skipped_closed = []
    newS = []
    for s in S:
        rec = dict(s)               # start from current -> all carry-over fields preserved
        wid = s['id']; rid = xw[wid]; yr = latest.get(rid)
        # trend overlay runs for ALL schools (incl. closed) -> historical trajectory is additive
        if FORKS['rebuild_trends'] and yr is not None:
            overlay_trends(rec, wid, rid)
        # closed / inline-only schools: populate from rev3 final year too (new data controls 100%)
        if s.get('closed_status') and not FORKS['populate_closed']:
            skipped_closed.append(wid); newS.append(rec); continue
        if yr is None:
            newS.append(rec); continue
        f = facts(rid, yr)
        # --- direct integer fields ---
        for wf, rm in DIRECT_INT.items():
            if f.get(rm) is not None:
                setf(rec, wid, wf, ri(f[rm]))
        # --- direct 1-decimal fields ---
        for wf, rm in DIRECT_FLOAT.items():
            if f.get(rm) is not None:
                setf(rec, wid, wf, r1(f[rm]))
        # --- gpa (2-decimal) ---
        for wf, rm in GPA.items():
            if f.get(rm) is not None:
                setf(rec, wid, wf, round(f[rm], 2))
        # school_type is carried over (rev3 stores it ALLCAPS-padded; live is Private/Public)
        # --- derived: scholarship %s (counts / students_total) ---
        stot = f.get('students_total'); grads = f.get('emp_grads_total')
        def pct(num, den):
            return r1(100 * num / den) if (den and num is not None) else None
        if stot:
            setf(rec, wid, 'schol_none_pct', pct(f.get('schol_none'), stot))
            setf(rec, wid, 'schol_lt_pct', pct(f.get('schol_lt_half'), stot))
            setf(rec, wid, 'schol_mt_pct', pct(f.get('schol_half_full'), stot))
            setf(rec, wid, 'schol_full_pct', pct(f.get('schol_full'), stot))
            setf(rec, wid, 'schol_gt_pct', pct(f.get('schol_gt_full'), stot))
        # --- derived: employment rate + firm-size %s (FTLT / grads) ---
        if grads:
            setf(rec, wid, 'ftlt_pct', pct(f.get('emp_total_ftlt'), grads))
            setf(rec, wid, 'emp_bar_pct', pct(f.get('emp_bar_ftlt'), grads))
            setf(rec, wid, 'emp_seek_pct', pct(f.get('emp_unemp_seeking'), grads))
            setf(rec, wid, 'emp_solo_pct', pct(f.get('emp_solo_ftlt'), grads))
            small = sum((f.get(k) or 0) for k in
                        ('emp_1_10_ftlt', 'emp_11_25_ftlt', 'emp_26_50_ftlt', 'emp_51_100_ftlt'))
            setf(rec, wid, 'emp_small_pct', pct(small, grads))
            setf(rec, wid, 'emp_mid_pct', pct(f.get('emp_101_250_ftlt'), grads))
            setf(rec, wid, 'emp_biglaw_pct', pct(f.get('emp_251_500_ftlt'), grads))
            setf(rec, wid, 'emp_megalaw_pct', pct(f.get('emp_501_ftlt'), grads))
            # clerkships (confirmed FTLT in live data)
            clk = (f.get('emp_fedclk_ftlt') or 0) + (f.get('emp_slclk_ftlt') or 0)
            setf(rec, wid, 'emp_clk_pct', pct(clk, grads))
            setf(rec, wid, 'emp_clk_fed_pct', pct(f.get('emp_fedclk_ftlt'), grads))
            if FORKS['sector_types_from_rev3']:
                setf(rec, wid, 'emp_biz_pct', pct(f.get('emp_biz_ftlt'), grads))
                setf(rec, wid, 'emp_gov_pct', pct(f.get('emp_gov_ftlt'), grads))
                setf(rec, wid, 'emp_pi_pct', pct(f.get('emp_pubint_ftlt'), grads))
                setf(rec, wid, 'emp_edu_pct', pct(f.get('emp_edu_ftlt'), grads))
        # --- faculty: latest year with a positive count (handles Duke 2025 == 0) ---
        fac_ft = latest_positive(rid, 'fac_ft')
        fac_pt = latest_positive(rid, 'fac_pt')
        if fac_ft is not None:
            setf(rec, wid, 'fac_ft', ri(fac_ft))
            setf(rec, wid, 'fac_total', ri(fac_ft + (fac_pt or 0)))
        # --- derived: bar_state_diff ---
        if f.get('bar_pct') is not None and f.get('bar_state_avg') is not None:
            setf(rec, wid, 'bar_state_diff', r1(f['bar_pct'] - f['bar_state_avg']))
        # --- provenance: which current-cycle fields rev3 sanitized (adjusted=1) ---
        adj = {}
        for wf, rm in (('tui', 'res_tui'), ('nrt', 'nr_tui')):
            row = cur.execute("SELECT adjust_rule FROM fact_school_year WHERE school_id=? AND year=? "
                              "AND metric=? AND adjusted=1", (rid, yr, rm)).fetchone()
            if row and row[0]:
                adj[wf] = row[0]
        if adj:
            rec['_adj'] = adj
        elif '_adj' in rec:
            del rec['_adj']
        newS.append(rec)

    # write candidate: splice new S back into the original file (preserve BLS/RPP/FMR + header)
    new_arr = '[' + ',\n'.join(json.dumps(r, ensure_ascii=False) for r in newS) + ']'
    out_src = src[:sstart] + new_arr + src[send:]
    open(out_path, 'w').write(out_src)

    # diff report
    total = sum(len(v) for v in diffs.values())
    schools = len({w for v in diffs.values() for (w, _, _) in v})
    lines = [f"EMIT DIFF  (rev3 {db_path} -> {data_js_path})",
             f"forks: {FORKS}",
             f"schools changed: {schools}/{len(S)} | total field changes: {total}", ""]
    for fld in sorted(diffs, key=lambda k: -len(diffs[k])):
        ex = diffs[fld][:3]
        exs = '; '.join(f"{w}:{o}->{n}" for w, o, n in ex)
        lines.append(f"  {fld}: {len(diffs[fld])}   e.g. {exs}")
    open(report_path, 'w').write('\n'.join(lines) + '\n')
    print('\n'.join(lines))
    return total

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', required=True)
    ap.add_argument('--data', default='data/exhibit-data.js')
    ap.add_argument('--out', default='/tmp/exhibit-data.candidate.js')
    ap.add_argument('--report', default='/tmp/emit-diff.txt')
    a = ap.parse_args()
    emit(a.db, a.data, a.out, a.report)
