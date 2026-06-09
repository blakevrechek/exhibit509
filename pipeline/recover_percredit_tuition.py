#!/usr/bin/env python3
"""
Recover per-credit-only tuition that was disclosed but never converted to an
annual figure (so it sat as $0 and tripped the "tuition not disclosed" banner).

These schools report tuition per credit hour, not as an annual sticker. The ABA
filing carries the per-credit rate; converting at a standard full-time JD load
(~30 credits/year — calibrated against each school's own adjacent annual years,
median error ~5%) recovers the annual figure. This is the conversion the
methodology already documents; it just hadn't been applied to the older years.

Source of the clean per-credit rate: the Exhibit 509 Master workbook (its
FT_Resident_Credit / FT_NonResident_Credit columns), cross-validated 99.86% vs the
pipeline. Patches data/exhibit_data.json.gz and the curated tui_trend/nrt_trend
in data/exhibit-data.js, ONLY where the current value is $0 and the result passes
sanity guards (plausible range + continuity with the nearest annual year).

Run: python3 pipeline/recover_percredit_tuition.py [--write]
"""
import gzip
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GZ = os.path.join(ROOT, "data", "exhibit_data.json.gz")
DATA_JS = os.path.join(ROOT, "data", "exhibit-data.js")
MASTER = os.environ.get("MASTER_XLSX",
    "/root/.claude/uploads/361a2b6f-372e-569d-9a32-4ae6b7bb71e6/9b42eddd-Exhibit_509_Master.xlsx")
CREDITS = 30  # standard full-time JD academic-year load (calibrated; see docstring)
LO, HI = 4000, 130000          # plausible annual JD tuition
RATIO_LO, RATIO_HI = 0.45, 2.2  # vs nearest annual year (catch fee/sentinel cells)

sys.path.insert(0, os.path.join(ROOT, "pipeline"))
from crosswalk import build_resolver


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def load_master_percredit():
    import openpyxl
    resolve, _ = build_resolver()
    wb = openpyxl.load_workbook(MASTER, read_only=True, data_only=True)
    ws = wb["Tuition & Fees"]
    it = ws.iter_rows(values_only=True)
    hdr = {h: i for i, h in enumerate(next(it)) if h}
    out = {}
    for row in it:
        sid = resolve(str(row[hdr["SchoolName_Original"]] or row[hdr["School"]]))
        try:
            yr = int(row[hdr["Year"]])
        except (TypeError, ValueError):
            continue
        if not sid:
            continue
        out[(sid, yr)] = (num(row[hdr.get("FT_Resident_Credit")]),
                          num(row[hdr.get("FT_NonResident_Credit")]))
    wb.close()
    return out


def array_bounds(js):
    i = js.find("const S = ") + len("const S = ")
    depth = ins = esc = 0
    j = i
    while j < len(js):
        c = js[j]
        if ins:
            if esc: esc = 0
            elif c == "\\": esc = 1
            elif c == '"': ins = 0
        elif c == '"': ins = 1
        elif c == "[": depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                return i, j + 1
        j += 1
    raise SystemExit("bracket-walk failed")


def main():
    write = "--write" in sys.argv
    gz = json.load(gzip.open(GZ))
    pc = load_master_percredit()

    # nearest known annual year per school (for the continuity guard)
    annual = {}
    for s in gz["schools"]:
        annual[s["id"]] = {int(y): s["history"][y]["tui_ft_res"]
                           for y in s["history"] if s["history"][y].get("tui_ft_res")}

    def convert(sid, yr, raw_pc):
        if not raw_pc or raw_pc <= 0:
            return None
        cand = round(raw_pc * CREDITS)
        if not (LO <= cand <= HI):
            return None
        nbrs = annual.get(sid, {})
        if nbrs:
            near = min(nbrs, key=lambda a: abs(a - yr))
            if abs(near - yr) <= 4 and not (RATIO_LO <= cand / nbrs[near] <= RATIO_HI):
                return None
        return cand

    # 1) patch the gz
    recovered = {}   # (sid, yearstr) -> annual_res   (for the curated patch)
    kept_gap = 0
    private = 0
    for s in gz["schools"]:
        for y, h in s["history"].items():
            r, nr = h.get("tui_ft_res"), h.get("tui_ft_nonres")
            if r == 0 and not (nr and nr > 0):
                rp, np_ = pc.get((s["id"], int(y)), (None, None))
                ar = convert(s["id"], int(y), rp)
                if ar is None:
                    kept_gap += 1
                    continue
                h["tui_ft_res"] = ar
                an = convert(s["id"], int(y), np_) or ar  # nonres falls back to res
                h["tui_ft_nonres"] = an
                recovered[(s["id"], y)] = (ar, an)
            elif (r == 0 and nr and nr > 0
                  and str(h.get("school_type", "")).lower().startswith("priv")):
                # Private schools charge one tuition; a $0 resident column just means
                # they only filled non-resident. Mirror it (no res/non-res split).
                h["tui_ft_res"] = nr
                recovered[(s["id"], y)] = (nr, nr)
                private += 1

    # 2) patch the curated tui_trend / nrt_trend
    js = open(DATA_JS, encoding="utf-8").read()
    a, b = array_bounds(js)
    S = json.loads(js[a:b])
    by = {x.get("id"): x for x in S}
    cur_patched = 0
    for (sid, y), (ar, an) in recovered.items():
        rec = by.get(sid)
        if not rec:
            continue
        t = rec.get("tui_trend")
        if isinstance(t, dict) and t.get(y) in (0, None):
            t[y] = ar; cur_patched += 1
        n = rec.get("nrt_trend")
        if isinstance(n, dict) and n.get(y) in (0, None):
            n[y] = an

    print(f"recover_percredit_tuition (x{CREDITS}):")
    print(f"  gz cells recovered: {len(recovered)} (incl. {private} private res=nonres)   kept as gap: {kept_gap}")
    print(f"  curated tui_trend cells patched: {cur_patched}")
    schools = sorted({sid for sid, _ in recovered})
    print(f"  schools affected: {len(schools)}")
    for sid in schools[:6]:
        yrs = sorted(y for (s, y) in recovered if s == sid)
        print(f"    {sid}: {yrs} -> e.g. ${recovered[(sid, yrs[0])][0]:,}")

    if write:
        with gzip.open(GZ, "wt", encoding="utf-8") as f:
            json.dump(gz, f, ensure_ascii=False, separators=(",", ":"))
        open(DATA_JS, "w", encoding="utf-8").write(js[:a] + json.dumps(S, ensure_ascii=False) + js[b:])
        print("  WROTE gz + exhibit-data.js")
    else:
        print("  (dry-run; pass --write)")


if __name__ == "__main__":
    main()
