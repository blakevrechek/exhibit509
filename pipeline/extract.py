#!/usr/bin/env python3
"""
Exhibit 509 rebuild, step 3: extract workbooks -> tidy facts (SQLite).

Each ABA section is a tidy one-row-per-school sheet. We register, per section,
the source column header for every gz field we can read *directly* (no math),
plus a cleaner. Derived fields (percentages, firm-size buckets, schol_none) are
intentionally NOT here — they belong to the rebuild/derivation step; keeping the
extract layer to raw reads is what makes the oracle diff meaningful.

Output: pipeline/facts.sqlite, table `facts`
  (school_id, year, section, field, value, src_file, sheet, row, col)

Usage: python3 pipeline/extract.py [year ...]   (default: all years present)
"""
import glob
import os
import re
import sqlite3
import sys

import openpyxl

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from crosswalk import build_resolver

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "sources", "509")
DB = os.path.join(ROOT, "pipeline", "facts.sqlite")

SENT_STR = {"", "n/a", "na", "n", "*", "**", "***", "-", "--"}


def clean_int(v):
    if v is None:
        return None
    s = str(v).strip().replace(",", "").replace("$", "")
    if s.lower() in SENT_STR:
        return None
    try:
        return int(round(float(s)))
    except ValueError:
        return None


def clean_money(v):  # tuition/grant $ strings; 0 is a real-but-suspect value, keep
    return clean_int(v)


def clean_float(v):
    if v is None:
        return None
    s = str(v).strip().replace(",", "").replace("%", "").replace("$", "")
    if s.lower() in SENT_STR:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def clean_pct(v):
    return clean_float(v)


def clean_zeronull(v):  # LSAT/uGPA/grant-GPA: stored 0 means "not reported"
    f = clean_float(v)
    return None if f == 0 else f


def clean_str(v):
    if v is None:
        return None
    s = str(v).strip()
    return None if s.lower() in SENT_STR else s


def clean_yn(v):
    s = clean_str(v)
    if s is None:
        return None
    return s[0].upper() if s[:1].upper() in ("Y", "N") else s


# ── section registry ──────────────────────────────────────────────────────────
# file_glob matched within sources/509/<year>/. name_col defaults to col 0.
# fields: gz_field -> (source header, cleaner). Headers matched case/space-loose.
SECTIONS = {
    "admissions": {
        "glob": "First_Year_Class*",
        "fields": {
            "apps": (["Applications", "CompletedApplications"], clean_int),
            "offers": (["Offers", "OffersAdmission"], clean_int),
            "acc": ("AcceptanceRate", clean_pct),
            "enr_1l": (["TotalEnrollees", "TotalFYClassAll"], clean_int),
            "enr_1l_entering": (["Enrollees", "EnrolleesFromApplicantPool"], clean_int),
            "enr_1l_ft": (["FTEnrollees", "TotalFYClassFT"], clean_int),
            "enr_1l_pt": (["PTEnrollees", "TotalFYClassPT"], clean_int),
            "gpa75": (["All75thPercentileUGPA", "All75GPA"], clean_zeronull),
            "gpa50": (["All50thPercentileUGPA", "All50GPA"], clean_zeronull),
            "gpa25": (["All25thPercentileUGPA", "All25GPA"], clean_zeronull),
            "lsat75": (["All75thPercentileLSAT", "All75LSAT"], clean_zeronull),
            "lsat50": (["All50thPercentileLSAT", "All50LSAT"], clean_zeronull),
            "lsat25": (["All25thPercentileLSAT", "All25LSAT"], clean_zeronull),
            "gre_takers": ("GRETotalEnrollees", clean_int),  # absent pre-2023
        },
    },
    "faculty": {
        "glob": "Faculty_Resources*",
        "fields": {
            "fac_ft": (["FTTotal", "Total FT"], clean_int),
            "fac_pt": (["NONFTTotal", "Total NonFT"], clean_int),
            "fac_total": (["TotalFaculties", "Total"], clean_int),
            "fac_men": (["MaleTotal", "Total Male"], clean_int),
            "fac_women": (["FemaleTotal", "Total Female"], clean_int),
            "fac_poc": (["POCTotal", "Total People of Color", "Total Minority"], clean_int),
            "librarians_total": ("TotalLibrarians", clean_int),
        },
    },
    "transfers": {
        "glob": "Transfers*",
        "fields": {
            "trans_out": ("JD1 Transfers Out", clean_int),
            "trans_in": (["TransferIn", "Transfer In"], clean_int),
            "trans_gpa75": ("75th Percentile JD1 GPA", clean_zeronull),
            "trans_gpa50": (["50th Percentile JD1 GPA", "GPA50thPercentile"], clean_zeronull),
            "trans_gpa25": (["25th Percentile JD1 GPA", "GPA25thPercentile"], clean_zeronull),
        },
    },
    "bar_first": {
        "glob": "First_Time_Bar*",
        "name_col_alt": "School Name",
        "fields": {
            "bar_grads": (["Graduates In {Y-1}", "Total Graduates"], clean_int),
            "bar_first_takers": ("Total First Time Takers", clean_int),
            "bar_first_passers": ("Total First Time Passers", clean_int),
            "bar": ("AvgSchoolPassPercent*", clean_pct),
            "bar_state_avg": ("AvgStatePassPercent**", clean_pct),
            "bar_state_diff": ("TotalDifferencePercent***", clean_pct),
        },
    },
    "bar_2yr": {
        "glob": "TwoYear_Ultimate_Bar*",
        "name_col_alt": "School Name",
        "fields": {
            "bar_2yr_grads": (["{Y-3} Graduates", "No. of Graduates"], clean_int),
            "bar_2yr_takers": (["{Y-3} Takers", "No. of Takers"], clean_int),
            "bar_2yr_passers": (["{Y-3} Passers", "No. of Passers"], clean_int),
            "bar_2yr": ("%Passers", clean_pct),
        },
    },
    "grants": {
        "glob": "Grants_and_Scholarships*",
        "fields": {
            "schol_total": (["Total Number # of Recieving Grants Total #",
                             "Total # receiving grants total #"], clean_int),
            "schol_lt": (["Less than half tuition Total Number #",
                          "Less than half tuition total #"], clean_int),
            "schol_mt": (["Half to full tuition total Number #",
                          "Half to full tuition total #"], clean_int),
            "schol_full": (["Full tuition total Number #",
                            "Full tuition total #"], clean_int),
            "schol_gt": (["More than full tuition total Number #",
                          "More than full tuition total #"], clean_int),
            "grant_med_ft": ("FT 50th percentile grant amount", clean_money),
            "grant_p25_ft": ("FT 25th percentile grant amount", clean_money),
            "grant_p75_ft": ("FT 75th percentile grant amount", clean_money),
        },
    },
    "employment": {
        "glob": "Employment_Summary*",
        "fields": {
            # 2023 used the 'Number' suffix + 'BarPassageRequired'; 2024+ use
            # 'Total' + 'BarAdmissionRequired'.
            "emp_grads": (["Total_GraduatesTotal", "Total_GraduatesNumber"], clean_int),
            "ftlt": ("Total_FTLT", clean_int),
            "emp_bar_ftlt": (["Employed_BarAdmissionRequiredFTLT",
                              "Employed_BarPassageRequiredFTLT"], clean_int),
            "emp_jda_ftlt": ("Employed_JDAdvantageFTLT", clean_int),
            "emp_solo_ftlt": ("Solo-FTLT", clean_int),
            "emp_seeking": (["UnEmployedSeekingTotal", "UnEmployedSeekingNumber"], clean_int),
            "emp_not_seeking": (["UnEmployedNotSeekingTotal",
                                 "UnEmployedNotSeekingNumber"], clean_int),
        },
    },
    "curriculum": {
        "glob": "Curricular_Offerings*",
        "fields": {
            # pre-2025 reported a single count (= filled); 2025 split into
            # Available + Filled, and dropped the Seminars column.
            "clinics_available": ("LawClinicsAvailable", clean_int),
            "clinics_filled": (["LawClinicsFilled", "LawClinics", "ClincicSum"], clean_int),
            "field_placements_filled": (["FieldPlacementsFilled", "FieldPlacements",
                                         "FieldPlacementSum"], clean_int),
            "sim_courses_available": ("SimulationCoursesAvailable", clean_int),
            "sim_courses_filled": (["SimulationCoursesFilled", "SimulationCourses",
                                    "SimulationSum"], clean_int),
            "seminars": (["Seminars", "Seminarcount"], clean_int),
            "co_curricular": (["CoCurricularOfferings", "CocurricularCount"], clean_int),
        },
    },
    "attrition": {
        "glob": "Attrition*",
        "fields": {
            "atr_acad_1l": (["AcademicAttrition_TotalJD1Total",
                             "AcadAttrition_TotalJD1Total"], clean_int),
            "atr_acad_1l_pct": (["AcademicAttrition_TotalJD1Percentage",
                                 "AcadAttrition_TotalJD1Percentage"], clean_pct),
            "atr_acad_ul_pct": (["AcademicAttrition_TotalULPercentage",
                                 "AcadAttrition_TotalULPercentage"], clean_pct),
            "atr_other_1l": ("OtherAttrition_TotalJD1Total", clean_int),
            "atr_other_1l_pct": ("OtherAttrition_TotalJD1Percentage", clean_pct),
            "atr_other_ul_pct": ("OtherAttrition_TotalULPercentage", clean_pct),
        },
    },
    "enrollment": {
        "glob": "JD_Enrollment_and_Ethnicity*",
        "fields": {
            "enr": ("TotalGrandTotal", clean_int),
            "grads": ("Total Degrees Awarded", clean_int),
            "race_white": ("WhiteGrandTotal", clean_int),
            "race_black": ("BlackGrandTotal", clean_int),
            "race_hisp": (["HispGrandTotal", "OtherHispGrandTotal"], clean_int),
            "race_asian": ("AsianGrandTotal", clean_int),
            "race_indian": ("AmericanIndianGrandTotal", clean_int),
            "race_native": ("NativeGrandTotal", clean_int),
            "race_multi": (["MultiracialGrandTotal", "RaceGrandTotal"], clean_int),
            "race_nr": ("NRGrandTotal", clean_int),
            "race_unknown": (["UnknownGrandTotal", "UnknownRaceGrandTotal"], clean_int),
        },
    },
    "basics": {
        "glob": "The_Basics*",
        "fields": {
            "school_type": (["SchoolType", "Type of School"], clean_str),
            "app_fee": (["AppFee", "Application Fee"], clean_money),
            "term": ("Term", clean_str),
            "credit_hours_required": (["RequiredCreditHours", "# of Credit Hours for JD"], clean_int),
        },
    },
    "tuition": {
        "glob": "Tuitions_and_Fees*",
        "fields": {
            "tui_ft_res": (["FT_Resident_Annual", "FT_Resident_Semester",
                            "Full Time Resident Semester"], clean_money),
            "tui_ft_nonres": (["FT_NonResident_Annual", "FT_NonResident_Semester",
                               "Full Time Non resident Semester"], clean_money),
            "tui_pt_res": (["PT_Resident_Annual", "PT_Resident_Semester",
                            "Part Time Resident Semester"], clean_money),
            "tui_pt_nonres": (["PT_NonResident_Annual", "PT_NonResident_Semester",
                               "Part Time Non resident Semester"], clean_money),
            "ft_fee": (["FTRS_AnnualFees", "FTRS Annual Fees"], clean_money),
            "living_on_campus": (["Living_On_Campus", "Living On Campus"], clean_money),
            "living_off_campus": (["Living_Off_Campus", "Living Off Campus"], clean_money),
            "living_at_home": (["Living_At_Home", "Living At Home"], clean_money),
            # stored raw to mirror the gz, which is faithful to each year's source
            # ('Yes'/'No' in 2023, 'Y'/'N' in 2024+); column absent pre-2023.
            "cond_offered": ("OfferScholorships", clean_str),
        },
    },
}


COLLISIONS = []  # (year, section, sid, field, kept_name, kept_val, dropped_name, dropped_val)

# The canonical tui_* fields are ANNUAL. Through 2020 the ABA reported tuition
# PER SEMESTER (verified: gz/source ratio is exactly 2.0 for every non-zero
# 2020 value); 2021+ report annual. So for these years we annualize (×2) the
# four tuition fields on extract. Earlier years get added here as the oracle /
# curated trends confirm them.
PER_SEMESTER_TUITION_YEARS = {2020}
ANNUALIZE_FIELDS = {"tui_ft_res", "tui_ft_nonres", "tui_pt_res", "tui_pt_nonres"}

# fields that legitimately exist only in some years' workbooks — a missing header
# here is expected, not a problem, so it is not warned about.
OPTIONAL_FIELDS = {"race_nr", "enr_1l_entering",
                   "clinics_available", "sim_courses_available", "seminars",
                   "cond_offered",  # cond_offered column absent pre-2023
                   "gre_takers"}    # GRE takers count absent pre-2023


def hkey(s):
    return re.sub(r"\s+", " ", str(s or "").strip()).lower()


def candidates(src, year):
    """A field's source header may be a str or a list of fallbacks (ABA renames
    columns across years). Tokens {Y-1}/{Y-3} expand to cohort years (e.g. the
    two-year-ultimate bar cohort is report-year minus 3)."""
    opts = src if isinstance(src, (list, tuple)) else [src]
    out = []
    for o in opts:
        o = o.replace("{Y-1}", str(year - 1)).replace("{Y-3}", str(year - 3))
        out.append(o)
    return out


def extract_year(year, resolve, conn):
    ydir = os.path.join(SRC, str(year))
    if not os.path.isdir(ydir):
        return 0
    rows_out = 0
    for section, spec in SECTIONS.items():
        matches = glob.glob(os.path.join(ydir, spec["glob"] + ".xls*"))
        if not matches:
            continue
        path = matches[0]
        fname = os.path.basename(path)
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        ws = wb.worksheets[0]
        rows = list(ws.iter_rows(values_only=True))
        header = [hkey(c) for c in rows[0]]
        hidx = {h: i for i, h in enumerate(header)}
        # resolve each field's column index once
        colmap = {}
        for gzf, (src, cleaner) in spec["fields"].items():
            i = next((hidx[hkey(c)] for c in candidates(src, int(year))
                      if hkey(c) in hidx), None)
            if i is None:
                if gzf not in OPTIONAL_FIELDS:
                    print(f"  !! {section}: header {src!r} not found in {fname}")
                continue
            colmap[gzf] = (i, cleaner)
        seen = {}  # (sid, field) -> (value, source_name) within this sheet
        for r in rows[1:]:
            if not r or not r[0]:
                continue
            sid = resolve(r[0])
            if not sid:
                continue  # footnote / unmatched (reported by crosswalk probe)
            for gzf, (i, cleaner) in colmap.items():
                if i >= len(r):
                    continue
                val = cleaner(r[i])
                if val is None:
                    continue
                if (int(year) in PER_SEMESTER_TUITION_YEARS
                        and gzf in ANNUALIZE_FIELDS and isinstance(val, (int, float))):
                    val = val * 2  # per-semester -> annual
                key = (sid, gzf)
                if key in seen and str(seen[key][0]) != str(val):
                    # two distinct source rows collapse to one slug — FLAG, keep
                    # first (canonical), record the collision for adjudication.
                    COLLISIONS.append(
                        (int(year), section, sid, gzf,
                         seen[key][1], seen[key][0], r[0], val))
                    continue
                if key in seen:
                    continue
                seen[key] = (val, r[0])
                conn.execute(
                    "INSERT INTO facts VALUES (?,?,?,?,?,?,?,?,?)",
                    (sid, int(year), section, gzf,
                     str(val), fname, ws.title, None, i),
                )
                rows_out += 1
        wb.close()
    return rows_out


def main():
    years = sys.argv[1:] or sorted(
        d for d in os.listdir(SRC) if d.isdigit() and os.path.isdir(os.path.join(SRC, d))
    )
    resolve, _ = build_resolver()
    conn = sqlite3.connect(DB)
    conn.execute("DROP TABLE IF EXISTS facts")
    conn.execute(
        "CREATE TABLE facts (school_id TEXT, year INT, section TEXT, field TEXT, "
        "value TEXT, src_file TEXT, sheet TEXT, row INT, col INT)"
    )
    total = 0
    for y in years:
        n = extract_year(y, resolve, conn)
        print(f"{y}: {n} facts")
        total += n
    conn.commit()
    print(f"\n{total} facts -> {DB}")
    if COLLISIONS:
        seen_pairs = {(c[2], c[6]) for c in COLLISIONS}
        print(f"\n!! {len(COLLISIONS)} id collisions (two source rows -> one slug) "
              f"across {len(seen_pairs)} school-pairs — FLAG for adjudication:")
        for yr, sec, sid, fld, kn, kv, dn, dv in COLLISIONS[:12]:
            print(f"   {yr} {sid}.{fld}: kept {kn!r}={kv} / dropped {dn!r}={dv}")
    conn.close()


if __name__ == "__main__":
    main()
