#!/usr/bin/env python3
"""Phase 1b: back-extend / refresh the deep-dive history gz from the rev3 store.

The current data/exhibit_data.json.gz holds a rich 2018-2026 history (demographics,
curriculum, raw blobs from the v2 pipeline). rev3 adds the missing 2011-2017 depth and
the bulletproof core values. This overlays rev3's core+derived metrics onto EVERY gz
year (adds 2011-2017, refreshes 2018-2025 core), preserving the gz's richer fields where
they already exist. 2026 is left untouched (rev3 has no 2026). Years/fields rev3 lacks
stay absent -> the UI renders them as dashed gaps.

Usage: python3 scripts/emit_gz_from_rev3.py --db /path/to/exhibit.db
"""
import json, gzip, re, sqlite3, argparse

MANUAL = {'la-verne-university-of': 184, 'hamline-university': 218}

def slug(n): return re.sub(r'[^a-z0-9]+', '-', n.lower()).strip('-')

def build_crosswalk(ids, cur):
    dim = {r[0]: r[1] for r in cur.execute("SELECT school_id,canonical_name FROM dim_school")}
    has = set(r[0] for r in cur.execute("SELECT DISTINCT school_id FROM fact_school_year"))
    rev_slug = {sid: slug(cn) for sid, cn in dim.items()}
    xw = {}
    for wid in ids:
        if wid in MANUAL: xw[wid] = MANUAL[wid]; continue
        key = slug(wid)
        hit = [sid for sid, sl in rev_slug.items() if sl == key] or \
              [sid for sid, sl in rev_slug.items() if sl.startswith(key) and len(key) >= 18]
        if hit: xw[wid] = next((h for h in hit if h in has), hit[0])
    return xw

def r1(x): return None if x is None else round(x, 1)
def ri(x): return None if x is None else int(round(x))

def rev3_year_fields(f, grads, stot, sttype):
    """Map a rev3 (school,year) fact dict -> the gz history core fields. Omit None values."""
    out = {}
    def put(k, v):
        if v is not None: out[k] = v
    def pct(num, den): return r1(100 * num / den) if (den and num is not None) else None
    if sttype: put('school_type', sttype)
    put('apps', ri(f.get('apps'))); put('offers', ri(f.get('offers'))); put('acc', r1(f.get('acc_rate')))
    put('enr_1l', ri(f.get('enroll_total')))
    for k, m in (('lsat25','lsat25'),('lsat50','lsat50'),('lsat75','lsat75')):
        put(k, ri(f.get(m)))
    for k, m in (('gpa25','gpa25'),('gpa50','gpa50'),('gpa75','gpa75')):
        put(k, round(f[m], 2) if f.get(m) is not None else None)
    put('tui_ft_res', ri(f.get('res_tui'))); put('tui_ft_nonres', ri(f.get('nr_tui')))
    put('tui_pt_res', ri(f.get('pt_res_tui'))); put('tui_pt_nonres', ri(f.get('pt_nr_tui')))
    put('ft_fee', ri(f.get('ft_fee')))
    put('living_on_campus', ri(f.get('living_on'))); put('living_off_campus', ri(f.get('living_off')))
    put('living_at_home', ri(f.get('living_home')))
    put('credit_hours_required', ri(f.get('credit_hours'))); put('gre_takers', ri(f.get('gre_enrolled')))
    put('trans_in', ri(f.get('transfer_in'))); put('trans_out', ri(f.get('transfer_out')))
    # bar
    put('bar', r1(f.get('bar_pct'))); put('bar_state_avg', r1(f.get('bar_state_avg')))
    if f.get('bar_pct') is not None and f.get('bar_state_avg') is not None:
        put('bar_state_diff', r1(f['bar_pct'] - f['bar_state_avg']))
    put('bar_first_takers', ri(f.get('bar_takers'))); put('bar_first_passers', ri(f.get('bar_passers')))
    put('bar_2yr', r1(f.get('bar2yr_pct')))
    put('bar_2yr_takers', ri(f.get('bar2yr_takers'))); put('bar_2yr_passers', ri(f.get('bar2yr_passers')))
    put('bar_2yr_grads', ri(f.get('bar2yr_grads')))
    # scholarships (counts + %s)
    put('schol_none', ri(f.get('schol_none'))); put('schol_lt', ri(f.get('schol_lt_half')))
    put('schol_mt', ri(f.get('schol_half_full'))); put('schol_full', ri(f.get('schol_full')))
    put('schol_gt', ri(f.get('schol_gt_full'))); put('schol_total', ri(stot))
    if stot:
        put('schol_none_pct', pct(f.get('schol_none'), stot)); put('schol_lt_pct', pct(f.get('schol_lt_half'), stot))
        put('schol_mt_pct', pct(f.get('schol_half_full'), stot)); put('schol_full_pct', pct(f.get('schol_full'), stot))
        put('schol_gt_pct', pct(f.get('schol_gt_full'), stot))
    put('grant_med_ft', ri(f.get('grant50'))); put('grant_p25_ft', ri(f.get('grant25')))
    put('grant_p75_ft', ri(f.get('grant75')))
    # employment counts + %s (FTLT / grads)
    put('emp_grads', ri(grads)); put('ftlt', ri(f.get('emp_total_ftlt')))
    if grads:
        put('ftlt_pct', pct(f.get('emp_total_ftlt'), grads))
        put('emp_bar_pct', pct(f.get('emp_bar_ftlt'), grads))
        put('emp_jda_pct', pct(f.get('emp_jdadv_ftlt'), grads))
        put('emp_seeking_pct', pct(f.get('emp_unemp_seeking'), grads))
        put('emp_solo_pct', pct(f.get('emp_solo_ftlt'), grads))
        small = sum((f.get(k) or 0) for k in ('emp_1_10_ftlt','emp_11_25_ftlt','emp_26_50_ftlt','emp_51_100_ftlt'))
        put('emp_small_pct', pct(small, grads))
        put('emp_mid_pct', pct(f.get('emp_101_250_ftlt'), grads))
        put('emp_biglaw_pct', pct(f.get('emp_251_500_ftlt'), grads))
        put('emp_megalaw_pct', pct(f.get('emp_501_ftlt'), grads))
        clk = (f.get('emp_fedclk_ftlt') or 0) + (f.get('emp_slclk_ftlt') or 0)
        put('emp_clk_pct', pct(clk, grads)); put('emp_clk_fed_pct', pct(f.get('emp_fedclk_ftlt'), grads))
        put('emp_gov_pct', pct(f.get('emp_gov_ftlt'), grads)); put('emp_pi_pct', pct(f.get('emp_pubint_ftlt'), grads))
        put('emp_biz_pct', pct(f.get('emp_biz_ftlt'), grads)); put('emp_edu_pct', pct(f.get('emp_edu_ftlt'), grads))
    # faculty
    put('fac_ft', ri(f.get('fac_ft'))); put('fac_pt', ri(f.get('fac_pt')))
    if f.get('fac_ft') is not None:
        put('fac_total', ri((f.get('fac_ft') or 0) + (f.get('fac_pt') or 0)))
    # attrition (rev3 combined academic+other for 1L/2L/3L)
    put('atr_1l', ri(f.get('attr_1l'))); put('atr_2l', ri(f.get('attr_2l'))); put('atr_3l', ri(f.get('attr_3l')))
    # provenance: rev3 fields adjusted by sanitization this year
    return out

def main(db_path, gz_path):
    cur = sqlite3.connect(db_path).cursor()
    with gzip.open(gz_path) as fh: H = json.load(fh)
    ids = [s['id'] for s in H['schools']]
    xw = build_crosswalk(ids, cur)
    # also map S ids that may be missing from gz (the 4 inline-only closed) - add them below
    by_year = {}  # rid -> {year -> factdict}
    sttype = {}   # rid -> school_type text (latest)
    for sid, yr, m, v, vt in cur.execute("SELECT school_id,year,metric,value,value_text FROM fact_school_year"):
        by_year.setdefault(sid, {}).setdefault(yr, {})[m] = v if v is not None else vt
    for sid, vt in cur.execute("SELECT school_id,value_text FROM fact_school_year WHERE metric='school_type' AND value_text IS NOT NULL"):
        sttype[sid] = vt.strip().title() if vt else None

    added_years = 0; updated_years = 0
    for s in H['schools']:
        rid = xw.get(s['id'])
        if rid is None or rid not in by_year: continue
        hist = s.setdefault('history', {})
        for yr, f in sorted(by_year[rid].items()):
            if yr == 2026: continue  # rev3 has no 2026
            grads = f.get('emp_grads_total'); stot = f.get('students_total')
            core = rev3_year_fields(f, grads, stot, sttype.get(rid))
            ys = str(yr)
            if ys in hist:
                hist[ys].update(core); updated_years += 1   # overlay core, keep rich fields
            else:
                hist[ys] = core; added_years += 1            # new 2011-2017 year
    # meta refresh
    H['meta']['years_covered'] = sorted({int(y) for s in H['schools'] for y in (s.get('history') or {})})
    H['meta']['generated'] = H['meta'].get('generated')
    rev3_note = ('rev3 overlay: core ABA-509 metrics 2011-2025 from the bulletproof rev3 store '
                 '(203,811 facts, 0 validation exceptions); 2011-2017 newly added, 2018-2025 core '
                 'refreshed, demographics/curriculum preserved from v2 where present, 2026 untouched.')
    notes = H['meta'].get('notes', '')
    if isinstance(notes, list):
        H['meta']['notes'] = notes + [rev3_note]
    else:
        H['meta']['notes'] = (str(notes) + ' | ' + rev3_note).strip(' |')
    out = json.dumps(H, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    with gzip.open(gz_path, 'wb', compresslevel=9) as fh: fh.write(out)
    print(f"gz rewritten: {len(H['schools'])} schools | +{added_years} new year-records, "
          f"{updated_years} refreshed | years now {H['meta']['years_covered']}")

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', required=True)
    ap.add_argument('--gz', default='data/exhibit_data.json.gz')
    a = ap.parse_args()
    main(a.db, a.gz)
