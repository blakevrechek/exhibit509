#!/usr/bin/env python3
"""
Exhibit 509 rebuild, step 2: identity crosswalk (the join backbone).

Resolves an ABA workbook's `SchoolName` to our slug `id`, using the gz as the
authority: exact aba_name, then a normalized form, then the meta name_aliases.
Anything unresolved is reported so we add an alias rather than silently drop a
school. Importable (resolve_name / build_resolver) and runnable as a probe:

    python3 pipeline/crosswalk.py <workbook.xlsx>   # report match rate + misses
"""
import gzip
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GZ = os.path.join(ROOT, "data", "exhibit_data.json.gz")


def norm(s):
    """Loose match key: upper, drop punctuation + 'THE', collapse whitespace."""
    s = (s or "").upper()
    s = re.sub(r"[.,&'()/-]", " ", s)
    s = re.sub(r"\bTHE\b", " ", s)
    s = re.sub(r"\bUNIVERSITY\b", "UNIV", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def build_resolver(gz_path=GZ):
    gz = json.load(gzip.open(gz_path))
    exact, normed = {}, {}
    for s in gz["schools"]:
        sid = s["id"]
        for key in (s.get("aba_name"), s.get("name"), sid.replace("-", " ")):
            if key:
                exact.setdefault(key, sid)
                normed.setdefault(norm(key), sid)
    aliases = {}
    for k, v in gz["meta"].get("name_aliases", {}).items():
        aliases[k] = v
        normed.setdefault(norm(k), v)
    valid_ids = {s["id"] for s in gz["schools"]}

    def resolve(name):
        if name in exact:
            return exact[name]
        if name in aliases:
            return aliases[name]
        n = norm(name)
        return normed.get(n)

    return resolve, valid_ids


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: crosswalk.py <workbook.xlsx>")
    import openpyxl
    resolve, _ = build_resolver()
    wb = openpyxl.load_workbook(sys.argv[1], read_only=True, data_only=True)
    ws = wb.worksheets[0]
    rows = list(ws.iter_rows(values_only=True))
    header = [str(c) if c is not None else "" for c in rows[0]]
    # school name is col A in every sheet seen so far
    names = [r[0] for r in rows[1:] if r and r[0]]
    hits = misses = 0
    miss_list = []
    for nm in names:
        if resolve(nm):
            hits += 1
        else:
            misses += 1
            miss_list.append(nm)
    print(f"{os.path.basename(sys.argv[1])}: {len(names)} schools, "
          f"{hits} matched, {misses} UNMATCHED")
    for m in miss_list:
        print(f"  MISS: {m!r}  (norm={norm(m)!r})")


if __name__ == "__main__":
    main()
