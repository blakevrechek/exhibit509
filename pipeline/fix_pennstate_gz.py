#!/usr/bin/env python3
"""
F1 Penn State — safe data corrections (gz) + closure notes.

The live gz crossed the two Penn State schools for 2023-2024: penn-state-dickinson-law
carried University Park's enrollment (403/385) instead of Carlisle's (295/304), and
the University Park entry was cut off after 2022. This:
  - overwrites penn-state-dickinson-law 2023-2024 with the true Carlisle figures (facts),
  - backfills penn-state-law-university-park 2023-2024 with University Park's own data
    (facts slug 'penn-state-law') and gives it real map metadata,
  - records the 2024-25 reunification (UP became the University Park campus of the
    single Penn State Dickinson Law).

Adding University Park to the curated/display layer is handled separately (review PR).
Run: python3 pipeline/fix_pennstate_gz.py [--write]
"""
import gzip
import json
import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GZ = os.path.join(ROOT, "data", "exhibit_data.json.gz")
DB = os.path.join(ROOT, "pipeline", "facts.sqlite")

# University Park, PA — Lewis Katz Building (public coordinates)
UP_LAT, UP_LNG = 40.7980, -77.8616


def typed(v):
    s = str(v).strip()
    try:
        f = float(s)
        return int(f) if f.is_integer() else f
    except ValueError:
        return s


def main():
    write = "--write" in sys.argv
    gz = json.load(gzip.open(GZ))
    by = {s["id"]: s for s in gz["schools"]}
    conn = sqlite3.connect(DB)

    def facts_rec(sid, year):
        return {f: typed(v) for f, v in conn.execute(
            "SELECT field, value FROM facts WHERE school_id=? AND year=?", (sid, year))}

    changed = []
    # 1. Dickinson (Carlisle) 2023-2024 -> overwrite extracted fields with true facts
    dick = by["penn-state-dickinson-law"]
    for y in ("2023", "2024"):
        rec = facts_rec("penn-state-dickinson-law", int(y))
        before = dick["history"].get(y, {}).get("enr")
        dick["history"].setdefault(y, {}).update(rec)
        changed.append(f"dickinson {y}: enr {before} -> {rec.get('enr')} ({len(rec)} fields)")

    # 2. University Park 2023-2024 backfill (facts slug 'penn-state-law')
    up = by["penn-state-law-university-park"]
    for y in ("2023", "2024"):
        rec = facts_rec("penn-state-law", int(y))
        up["history"].setdefault(y, {}).update(rec)
        changed.append(f"up {y}: enr {rec.get('enr')} backfilled ({len(rec)} fields)")

    # 3. University Park map metadata + reunification status
    up["lat"], up["lng"] = UP_LAT, UP_LNG
    if not up.get("bls_mean"):
        up["bls_mean"] = dick.get("bls_mean")  # same PA legal market (approx.)
    up["status"] = "defunct"
    up["status_note"] = ("Reunified into Penn State Dickinson Law for 2025; "
                         "now its University Park campus")
    changed.append(f"up metadata: lat/lng set, bls={up['bls_mean']}, status_note added")

    print("fix_pennstate_gz:")
    for c in changed:
        print(" -", c)

    if write:
        with gzip.open(GZ, "wt", encoding="utf-8") as f:
            json.dump(gz, f, ensure_ascii=False, separators=(",", ":"))
        print(f"WROTE {GZ}")
    else:
        print("(dry-run; pass --write)")


if __name__ == "__main__":
    main()
