#!/usr/bin/env python3
"""
Build curated data/exhibit-data.js records for schools that exist in the gz but
not the curated/display layer — currently penn-state-law-university-park and
golden-gate-university — so they appear on the live site with their full history
and a status note.

Verified (Harvard, 17/17 exact): a curated record is faithfully derivable from a
school's OWN gz data — current scalars from its latest data year, trends from its
history, with a handful of field renames. Each record is built ONLY from that
school's gz entry (no cross-contamination). Structural keys we can't derive
(curriculum cur_*, ranking placement) are left null; the page renders "—".

Review PR — not auto-merged: adds schools to the live map/rankings.
Run: python3 pipeline/build_curated_records.py [--write]
"""
import gzip
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_JS = os.path.join(ROOT, "data", "exhibit-data.js")
GZ = os.path.join(ROOT, "data", "exhibit_data.json.gz")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from validate_data import extract_S

TREND_MAP = {
    "lsat_trend": "lsat50", "lsat25_trend": "lsat25", "lsat75_trend": "lsat75",
    "gpa_trend": "gpa50", "gpa25_trend": "gpa25", "gpa75_trend": "gpa75",
    "tui_trend": "tui_ft_res", "nrt_trend": "tui_ft_nonres",
    "bar_trend": "bar", "bar_2yr_trend": "bar_2yr",
    "bar_takers_trend": "bar_first_takers", "bar_passers_trend": "bar_first_passers",
    "acc_trend": "acc", "apps_trend": "apps", "offers_trend": "offers",
    "trans_in_trend": "trans_in", "trans_out_trend": "trans_out",
    "fac_trend": "fac_ft", "cond_enter_trend": "cond_enter",
    "cond_elim_trend": "cond_elim", "enr_trend": "enr",
}
RENAME = {  # curated scalar key -> gz history field
    "tui": "tui_ft_res", "nrt": "tui_ft_nonres", "grant_med": "grant_med_ft",
    "grant_p25": "grant_p25_ft", "grant_p75": "grant_p75_ft",
    "emp_seek_pct": "emp_seeking_pct", "credit_hours": "credit_hours_required",
    "living": "living_off_campus", "atr_1l": "atr_acad_1l_pct",
}
META = {  # what to override after deriving
    "penn-state-law-university-park": {
        "name": "Penn State Law (University Park)",
        "closed_status": "Reunified into Penn State Dickinson Law 2025 (University Park campus)",
    },
    "golden-gate-university": {
        "name": "Golden Gate University",
        "closed_status": "ABA J.D. program ending 2024; teach-out through 2027",
    },
}


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


def latest_data_year(hist):
    ys = [y for y in hist if hist[y].get("enr") or hist[y].get("lsat50")]
    return max(ys, key=int) if ys else max(hist, key=int)


def build_record(template_keys, gzs):
    h = gzs["history"]
    cy = latest_data_year(h)
    cur = h[cy]
    rec = {}
    for k in template_keys:
        if k in ("id", "name", "state", "lat", "lng", "bls_mean", "closed_status"):
            rec[k] = gzs.get(k)
        elif k == "_cur_year":
            rec[k] = int(cy)
        elif k in TREND_MAP:
            f = TREND_MAP[k]
            rec[k] = {y: h[y][f] for y in sorted(h) if h[y].get(f) is not None}
        elif k in RENAME:
            rec[k] = cur.get(RENAME[k])
        elif k == "race_total":
            rec[k] = cur.get("race_total") or (sum(
                cur.get(r, 0) or 0 for r in ("race_white", "race_black", "race_hisp",
                "race_asian", "race_indian", "race_native", "race_multi",
                "race_nr", "race_unknown")) or None)
        elif k == "race_other":
            rec[k] = sum(cur.get(r, 0) or 0 for r in
                         ("race_indian", "race_native", "race_nr", "race_unknown")) or None
        elif k == "full":
            rec[k] = gzs.get("name")
        elif k == "schol_trend":
            rec[k] = {}
        else:
            # same-named gz field if present, else null (cur_* curriculum,
            # place_top3, cond, etc. that aren't derivable -> null -> renders "—")
            rec[k] = cur.get(k)
    return rec, cy


def main():
    write = "--write" in sys.argv
    js = open(DATA_JS, encoding="utf-8").read()
    a, b = array_bounds(js)
    S = json.loads(js[a:b])
    template_keys = list(S[0].keys())
    gz = {s["id"]: s for s in json.load(gzip.open(GZ))["schools"]}
    have = {s["id"] for s in S}

    added = []
    for sid, meta in META.items():
        if sid in have:
            print(f"  {sid} already in curated — skipping")
            continue
        rec, cy = build_record(template_keys, gz[sid])
        rec.update(meta)
        # null 0-value money sentinels so a non-reporting school doesn't show "$0"
        for mk in ("tui", "nrt", "ft_fee", "grant_med", "grant_p25", "grant_p75", "living"):
            if rec.get(mk) == 0:
                rec[mk] = None
        S.append(rec)
        added.append((sid, cy, rec))

    print("build_curated_records:")
    for sid, cy, rec in added:
        print(f"  + {sid}  (cur_year {cy})  lsat50={rec.get('lsat50')} "
              f"enr={rec.get('enr')} bar={rec.get('bar')} tui={rec.get('tui')} "
              f"note={rec.get('closed_status')!r}")
        nonnull = sum(1 for v in rec.values() if v not in (None, {}, ""))
        print(f"      {nonnull}/{len(rec)} fields populated, "
              f"{len(rec.get('lsat_trend', {}))} trend years")

    if write:
        open(DATA_JS, "w", encoding="utf-8").write(
            js[:a] + json.dumps(S, ensure_ascii=False) + js[b:])
        print(f"WROTE {DATA_JS}  ({len(S)} schools)")
    else:
        print("(dry-run; pass --write)")


if __name__ == "__main__":
    main()
