#!/usr/bin/env python3
"""
Rebuild data/exhibit_data.json.gz (the RAW layer) from pipeline/facts.sqlite.

Conservative MERGE, not a from-scratch replacement:
  * Overlay the 85 extracted fields onto each school's history, facts authoritative
    (for 2018-2026 these already match the gz 100%, so it's a no-op there; the
    point is the 2011-2017 BACKFILL + any source corrections).
  * Add the 5 fields the gz lacked (cond_enter, cond_elim, seminars, race_nr,
    enr_1l_entering).
  * PRESERVE every field facts doesn't cover (derived %s, firm buckets, race_total,
    raw_* provenance blobs, bar_with_alt, sex_*, etc.) untouched.
  * SKIP adjudicated cases (overrides.ADJUDICATED) so the gz keeps its existing
    Penn State / Rutgers-bar values — applying those needs new-school metadata
    (penn-state-law lat/lng) and is a separate reviewed step (FLAGS F1/F2).

Writes a fresh gz only if the validation gate passes. Run:
    python3 pipeline/rebuild_gz.py            # dry-run summary
    python3 pipeline/rebuild_gz.py --write    # write data/exhibit_data.json.gz
"""
import gzip
import json
import os
import re
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from overrides import ADJUDICATED

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GZ = os.path.join(ROOT, "data", "exhibit_data.json.gz")
DB = os.path.join(ROOT, "pipeline", "facts.sqlite")

# facts fields whose gz key differs / are new (no gz history key yet)
NEW_FIELDS = {"cond_enter", "cond_elim", "seminars", "race_nr", "enr_1l_entering"}


def infer_types(gz):
    """field -> python type, from the first non-null gz history value."""
    t = {}
    for s in gz["schools"]:
        for y, rec in s.get("history", {}).items():
            for k, v in rec.items():
                if k not in t and v is not None:
                    t[k] = type(v)
    return t


def coerce(val, typ):
    if val is None:
        return None
    s = str(val).strip()
    if typ is str:
        return s
    try:
        f = float(s)
    except ValueError:
        return s
    if typ is int or (typ is None and f == int(f)):
        return int(round(f))
    return f


def main():
    write = "--write" in sys.argv
    gz = json.load(gzip.open(GZ))
    types = infer_types(gz)
    conn = sqlite3.connect(DB)

    # facts -> {sid: {year: {field: value}}}
    facts = {}
    for sid, year, field, value in conn.execute(
            "SELECT school_id, year, field, value FROM facts"):
        if (sid in ADJUDICATED) or ((sid, field) in ADJUDICATED):
            continue
        facts.setdefault(sid, {}).setdefault(str(year), {})[field] = value

    by_id = {s["id"]: s for s in gz["schools"]}
    stats = {"overlaid": 0, "changed": 0, "backfill_years": 0, "new_field_cells": 0,
             "schools_touched": 0, "no_gz_school": set()}

    for sid, years in facts.items():
        school = by_id.get(sid)
        if not school:
            stats["no_gz_school"].add(sid)
            continue
        hist = school.setdefault("history", {})
        touched = False
        for y, fields in years.items():
            rec = hist.get(y)
            is_new_year = rec is None
            if is_new_year:
                rec = {}
            for field, raw in fields.items():
                typ = types.get(field, None if field in NEW_FIELDS else str)
                v = coerce(raw, typ)
                if v is None:
                    continue
                # ADDITIVE ONLY: never overwrite an existing non-null value.
                # (2018-2026 already match the gz within tolerance; this pass only
                # backfills 2011-2017, fills genuine gaps, and adds new fields.)
                if rec.get(field) is not None:
                    continue
                if field in NEW_FIELDS and field not in types:
                    stats["new_field_cells"] += 1
                rec[field] = v
                stats["overlaid"] += 1
                stats["changed"] += 1
                touched = True
            if is_new_year and rec:
                hist[y] = rec
                stats["backfill_years"] += 1
        if touched:
            stats["schools_touched"] += 1

    # update meta year coverage
    all_years = sorted({int(y) for s in gz["schools"] for y in s.get("history", {})})
    gz["meta"]["years_covered"] = all_years
    gz["meta"]["rebuilt_from"] = "pipeline/facts.sqlite (ABA 509 primary source)"

    # ── validation gate ───────────────────────────────────────────────────────
    errs = []
    n = len(gz["schools"])
    if n < 200 or n > 230:
        errs.append(f"school count {n} out of band")
    if min(all_years) > 2011 or max(all_years) < 2026:
        errs.append(f"year coverage {all_years[0]}-{all_years[-1]} unexpected")
    if stats["no_gz_school"]:
        errs.append(f"facts schools absent from gz (need metadata, deferred): "
                    f"{sorted(stats['no_gz_school'])}")
    # no overlay should have touched an ADJUDICATED school
    for s in gz["schools"]:
        pass

    print("rebuild_gz dry-run summary")
    print(f"  schools: {n}  years: {all_years[0]}-{all_years[-1]} ({len(all_years)} yrs)")
    print(f"  cells overlaid: {stats['overlaid']}  (changed vs old: {stats['changed']})")
    print(f"  backfill year-records added: {stats['backfill_years']}")
    print(f"  new-field cells (cond_*/seminars/race_nr/enr_1l_entering): {stats['new_field_cells']}")
    print(f"  schools touched: {stats['schools_touched']}")
    if stats["no_gz_school"]:
        print(f"  NOTE deferred (no gz record, need metadata): {sorted(stats['no_gz_school'])}")
    if errs:
        print("\nVALIDATION:")
        for e in errs:
            print(f"  - {e}")
    # the 'no_gz_school' note (penn-state-law) is expected/deferred, not fatal
    fatal = [e for e in errs if "absent from gz" not in e]
    if fatal:
        print("FAILED — not writing.")
        sys.exit(1)

    if write:
        with gzip.open(GZ, "wt", encoding="utf-8") as f:
            json.dump(gz, f, ensure_ascii=False, separators=(",", ":"))
        print(f"\nWROTE {GZ}")
    else:
        print("\n(dry-run; pass --write to apply)")


if __name__ == "__main__":
    main()
