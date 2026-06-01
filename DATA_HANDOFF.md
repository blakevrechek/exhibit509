# Exhibit rev3 — Build Handoff (resume cold from these artifacts)

## STATE: FULL SPAN DONE — 2011–2025 (15 years) — all 0 validation exceptions, 203,811 facts, tuition fully sanitized.

| Year | Schools | Facts |
|---|---|---|
| 2011 | 206 | 11,863 |
| 2012 | 206 | 12,685 |
| 2013 | 206 | 12,725 |
| 2014 | 206 | 12,762 |
| 2015 | 208 | 12,680 |
| 2016 | 207 | 12,799 |
| 2017 | 203 | 12,136 |
| 2018 | 203 | 14,037 |
| 2025 | 196 | 14,685 |
| 2024 | 196 | 14,733 |
| 2023 | 196 | 14,475 |
| 2022 | 201 | 14,428 |
| 2021 | 202 | 14,509 |
| 2020 | 204 | 14,525 |
| 2019 | 206 | 14,769 |

(Fact counts DROPPED vs earlier versions on purpose: fake `0`s — mostly part-time tuition at
schools with no PT program — became honest nulls. Resident tuition + LSAT/GPA stay 196/196.)

## TO RESUME (cold start after compaction)
1. The container working dir is `/home/claude/exhibit/`. If it's gone, recreate it and copy
   ALL files from this outputs folder back into `/home/claude/exhibit/` (db -> `out/exhibit.db`,
   scripts -> both `exhibit/` and `exhibit/out/`).
2. Upload the next year's 12 raw files. Copy them to `raw<YEAR>/` e.g. `raw2018/`.
3. Run the pipeline (see PIPELINE below).

## PIPELINE (per year)
```
mkdir -p raw<YEAR> && cp <uploads>/*_<YEAR>.xlsx raw<YEAR>/
# drift check first — see if any metric has no column this year:
python3 -c "from resolve import effective_map; ..."   # (or just run ingest, it prints gaps)
python3 ingest.py <YEAR> raw<YEAR>      # idempotent: clears that year first
python3 sanitize_tuition.py            # RUN AFTER EACH NEW YEAR — recomputes semester x2 across all years
python3 validate.py <YEAR>             # MUST be 0 unreviewed exceptions
python3 plot_trajectories.py           # eyeball out/trajectories.png for spikes/steps/zero-bands
```
When ingest prints a gap for a metric: open that year's file, find the renamed column, add it to
the `ALIASES` dict in `resolve.py` (priority-ordered list, matched case-insensitively + whitespace-
collapsed via hnorm). Then re-run ingest. **Edit the ALIASES dict directly with str_replace — do
NOT append `ALIASES.update({...})`; that silently no-ops if the marker text isn't found.**

## STORE: out/exhibit.db (SQLite)
- `dim_school` (217: 208 active + 6 closed + Newark/Camden legacy; surrogate school_id, cleaned
  canonical names, name_history JSON, row_type, successor_id)
- `name_alias` (261 normalized name->school_id; handles casing/glyph/year drift)
- `fact_school_year` (school_id, year, metric, value, value_text, adjusted, adjust_rule, source)
- `raw_long` (1.39M cells — EVERY raw column verbatim; full demographic fidelity preserved)
- `exceptions`, `reconcile`

## LOCKED DERIVATION DECISIONS (Blake-approved)
- schol_none = students_total - receiving (derived)
- bar_pct = ABA published AvgSchoolPassPercent (takers/passers also stored, recomputable)
- attrition attr_Nl = Academic + Other total for JD level N
- tuition res_tui/nr_tui = FT annual

## TUITION SANITIZATION (the hard-won part — in sanitize_tuition.py + ingest.py)
- **zero_to_null**: `0` in tuition/LSAT/GPA fields -> null (teach-out or per-credit school).
- **per_credit fallback** (ingest.py): Credit-col value <8000 = true per-credit rate -> x29.
  Value >=8000 = annual figure mislabeled "Credit" -> x1 (caught Indiana-Indianapolis 831k spike).
- **semester->annual x2** (sanitize_tuition.py): 2019-2020 values ~0.5x of the first confirmed-annual
  year (2021) get doubled. Anchors on 2021 (NOT immediate neighbor — both 2019+2020 are semester so
  neighbor-comparison fails). Ratio window 1.7-2.3. Idempotent (reverts prior run first). Confined to
  pre-2021 BUT when 2018 lands the anchor logic extends back automatically — just re-run the script.

## DRIFTS HANDLED (all in resolve.py ALIASES, matched via hnorm)
- Tuition col: FT_Resident_Annual (2025) / FT_Resident_Semester (2024) / "Full Time Resident Semester"
  (2019, spaced). LABEL != VALUE in BOTH directions — never trust label, use cross-year ratio.
- Two-year bar cohort cols = report_year - 3 (dynamic). Also "No. of Graduates/Takers/Passers".
- Employment 2023: *Total->*Number, BarAdmissionRequired->BarPassageRequired, 501Plus->501.
- Employment 2020: EnrolledInGraduateStudies* -> PursuingGraduateDegreeNumber.
- Attrition prefix: AcademicAttrition_ (2023+) vs AcadAttrition_ (2022-).
- Admissions 2021: Applications->CompletedApplications, etc.; LSAT cols order 75/50/25 but resolved
  by semantic name (no inversion).
- Admissions 2019: spaced human-readable headers ("Completed Apps", "50th percentile LSAT ALL",
  "Offer", "Enrollees from App pool"). School-key col varies (School List/School Name/SchoolName/
  school list) — ingest reads col[0] positionally so this is harmless.

## ENTITY LIFECYCLE (school count rises going back, all legitimate)
- 196 (2023-25) -> 206 (2019): closing schools reappear going backward.
- Rutgers: unified(148), Newark(215)+Camden(217) seeded legacy_premerger -> successor_id=148. No dbl-count.
- Concordia, La Verne (last reported 2020), Valparaiso, Whittier, Arizona Summit, Florida Coastal,
  Indiana Tech, Thomas Jefferson = closed; appear in their active years with teach-out nulls.

## LEGITIMATE GAPS (not errors)
- gre_enrolled: 2023+ has count; 2022- splits GRE into Verbal/Quant/Analytical percentiles (in raw_long).
- jdnext_enrolled: only 2024+ (test didn't exist before).
- attr_acad_1l: unused MAP placeholder (real attrition is derived attr_1l).

## RESIDUAL TODO
- **UNMAPPED-FIELD TUITION (now diagnosed, needs Blake sign-off):** private/single-tuition schools
  file under `Other Semester`/`Other Credit`, not `FT_Resident_Semester`. Confirmed: **Stanford 2018**
  has all FT/PT Resident+Nonresident fields = 0, real tuition $20,791/sem sits in `Other Semester`
  (-> ~$41,582 annual after x2). Same class: Dayton/UIC/Indiana-Indianapolis/Washburn/Widener x2 show
  sub-$600 res_tui in 2018 (stray value in mapped field, real figure elsewhere). Boston College +
  Loyola-Marymount 2019-2020 are the same pattern. FIX: add an `Other` fallback to tuition derivation
  when FT_Resident fields are 0/blank — but verify per-school what `Other` means before applying, and
  it touches all years, so confirm before baking in.
- **MISSING FILE — Attrition_2018.xlsx was not in the 2018 upload** (11 files, not 12). attr_1l/2l/3l
  are absent for 2018 only. Send Attrition_2018 and re-run `ingest.py 2018` to fill (idempotent).
- STILL TODO (deferred, not blocking): successor wiring Hamline/Wm Mitchell->Mitchell Hamline,
  Penn State UP(138)->Dickinson. Reconciliation vs Historic+v2 (agreement %, disagreement CSV).
  Economic context join (BLS wages 2018+, BEA RPP 2012+, HUD SAFMR 2019+ — keyed on school state,
  which must be harvested from raw addresses; v2 _SchoolState sheet is empty scaffold).
- COSMETIC (final emit only): legacy closed-school names are ALLCAPS from v2 seed; Title-case them
  when generating workbook/JSON.

## 2018 NOTES (new this session)
- **emp_1_10_ftlt drift:** pre-2019 has no combined `1-10-FTLT` column; it splits into `Solo-FTLT` +
  `2-10-FTLT`. Reconstructed in ingest.py as a derived sum (Solo + 2-10), fires only when no direct
  1-10 column set it. emp_solo_ftlt still populated directly. 200 schools.
- **bar takers<passers guard:** Utah 2018 source had takers=86 < passers=96 (@ published 86.48%, so
  true takers ~111). Added reproducible ingest.py guard: when first-time passers>takers, null the
  corrupt takers cell; bar_pct + passers retained as authoritative (DECISION 2). raw_long keeps verbatim.
- **ft_fee gone:** 2018 Tuitions file has no annual-fees column at all (schema thinning). Legit gap;
  expect absent 2018 and earlier.

## 2017 NOTES (new this session)
- **Column drift fixed in resolve.py ALIASES** (file present, headers renamed):
  - First_Year_Class 2017: `Total FY class` (single col, no ALL/FT/PT split), `25/50/75th percentile
    LSAT` and `UGPA` (no ` ALL` suffix). enroll_ft/enroll_pt legitimately absent (no split this year).
  - Tuitions 2017: bare `Full Time Resident` / `Full Time Non resident` / `Part Time *` — NO
    Semester/Credit suffix, NO Other/Credit cols. **VALUES ARE ANNUAL** (2021/2017 ratio ~1.08, not
    doubled). So the semester artifact is confined to **2018-2020 only**; 2017 and 2021+ are annual.
  - Transfers 2017: `Transfers In`, `1L Transfers Out` (transfer_out got its first alias entry).
- **MISSING FILES — 2017 has no bar data:** both `First_Time_Bar_Passage_2017` and
  `Two-Year_Ultimate_Bar_Passage_2017` were absent from the upload (10 files, not 12). All bar metrics
  are 0/203 for 2017. Send both and re-run `ingest.py 2017` (idempotent) to fill.
- ft_fee absent (schema thinning, as 2018). gre/jdnext absent (known). Attrition_2017 WAS present, so
  attr_1l/2l/3l populated for 2017 (unlike 2018, still missing its Attrition file).

## NEXT: 2016, then 2015->2011.
Tuition: semester artifact is ONLY 2018-2020 (2017 confirmed annual) — sanitize_tuition.py handles it
automatically off the 2021 anchor. Watch pre-2017 for bar/employment vocab drift and deeper schema
thinning. Pre-2014 likely missing whole metric families (expected and OK per spec).

## 2016 NOTES (new this session) — heaviest reformatting year so far
- **ALL files renamed by ABA.** Added FILEKEY substrings (distinct, no collision): `GPA_and_LSAT`->
  First_Year_Class, `Tuition_and_Fees`->Tuitions, `J_D__Enrollment`->JD_Enrollment, `Bar_Passage_Rates`
  ->First_Time_Bar, `Curriculum`->Curricular_Offerings, `Faculty_and_Administrators`->Faculty_Resources.
- **Admissions** moved to `GPA_and_LSAT_Scores` file: apps/offers/matriculants split FT/PT/Total.
  `# Of Matriculants Total`->enroll_1l (the entering-class metric; collided with enroll_total in EFF
  which is keyed by (file,col) — kept it on enroll_1l since that's core+funnel; enroll_total is a 2016
  gap). `25/50/75th Percentile LSAT/GPA Total`. No acceptance-rate column (acc_rate gap).
- **Tuition** bare `Full-Time Resident` (hyphenated). ANNUAL (not doubled). Semester artifact stays 2018-2020.
- **BAR is long-format** (jurisdiction x exam-year, 3 exam yrs per file). New aggregator in ingest.py:
  filter `Reporting Year`==YEAR, take the row with populated `Composite Avg. School Pass %` -> bar_pct,
  `Composite Avg. State Pass %` -> bar_state_avg, `Total First-Time Takers` -> bar_takers. Emits the
  canonical MAP column names so no resolve.py change needed. **bar_passers left NULL** (no clean
  school-total; only per-jurisdiction passers). REUSE this handler for other pre-2017 bar years.
- **Attrition** `#1st/2nd/3rd Year Academic`+`Other` -> added to ATTR_COLS pick() (_ORD16).
- **Name truncation:** 2016 files cut names at 50 chars; UC Hastings became `...SAN F`. Added alias to
  school_id 28 (and to seed_dim.py SUPPLEMENTAL_ALIASES for durability). Watch for more truncations.
- Gaps (all expected): enroll_total, acc_rate, transfer_out (inbound-only file), credit_hours (lives in
  Curriculum but MAP keys it to The_Basics), bar2yr_* + bar_passers.

## NEXT: 2015, then 2014->2011.
Bar long-format aggregator is now reusable for pre-2017 bar years. Tuition is annual pre-2018. Watch for
more name truncation (add to seed_dim SUPPLEMENTAL_ALIASES), more file renames (extend FILEKEY), and
metric families thinning out pre-2014 (expected per spec).

## 2015 NOTES (new this session) — rode the 2016 machinery; entity work was the story
- All 2016 file-rename/alias/bar-aggregator handling carried over with **zero new drift fixes needed**.
  Tuition annual (Yale 2015 $58,050, smooth into 2016). Bar long-format aggregated (199 schools).
- **Pre-merger entities wired (was a deferred TODO):** 2015 academic files (enrollment/attrition/
  tuition/bar) report **Hamline** and **William Mitchell** separately (merger was Dec 2015); the
  **employment** file reports them already **consolidated as Mitchell Hamline (112)** (employment is
  collected ~9mo post-grad). Seeded legacy_premerger entities **218 (Hamline)** + **219 (William
  Mitchell)**, successor_id=112, in db AND seed_dim.py SUPPLEMENTAL_ENTITIES. No double-count: 218/219
  hold 2015 academics, 112 holds 2015 employment only. Mirrors the Rutgers Newark/Camden pattern.
- **Cooley Tampa Bay** branch appears in 2015 employment alongside the consolidated Cooley(45) row.
  Left **intentionally unresolved** (redundant subset; aliasing it to 45 would overwrite the
  consolidated figure via INSERT OR REPLACE). Expect this 1 unresolved name in 2015.
- seed_dim.py now has both SUPPLEMENTAL_ENTITIES and SUPPLEMENTAL_ALIASES blocks for durable rebuilds.

## NEXT: 2014, then 2013->2011.
Same post-rename file format + long-format bar expected to continue. Watch for more pre-merger/branch
entities (add to seed_dim SUPPLEMENTAL_ENTITIES), more name truncations, and metric families thinning
out pre-2014 (expected and OK per spec).

## 2014 NOTES (new this session)
- Rode the 2016/2015 machinery with **zero new column drift fixes**. Tuition annual (Yale 2014 $56,200,
  smooth into 2015). Bar long-format aggregated (202 schools). Cooley Tampa Bay not present this year.
- **Penn State pre-split wired (last deferred successor TODO — now DONE):** 2014 'PENNSYLVANIA STATE
  UNIVERSITY' is the single combined law school *before* it split into Penn State Law/University Park
  (138) and Penn State Dickinson Law (137), which both separate out 2015+. Seeded legacy_presplit
  entity **220** (successor_id=138 primary, 137 Dickinson co-successor) in db + seed_dim.py. 2014-and-
  earlier combined data -> 220; no double-count with 137/138.
- **All three deferred successor-wiring items are now complete** (Rutgers, Hamline/Wm Mitchell, Penn State).

## NEXT: 2013, then 2012->2011.
Same format expected. Watch for metric-family thinning pre-2013 (older years may drop whole metrics per
the original spec — file them in, prioritize recent) and any further legacy/branch entities.

## 2013 NOTES (new this session)
- Rode existing machinery, **zero new drift fixes**. Tuition annual (Yale 2013 $54,650). Bar aggregated
  (203 schools). 11 files (no Conditional_Scholarships — unused). No metric thinning yet at 2013.
- **Cooley branch campuses:** 2013 employment lists Cooley's 4 Michigan branches (Ann Arbor, Auburn
  Hills, Grand Rapids, Lansing) separately. The consolidated total is filed under the parent name
  **'WESTERN MICHIGAN UNIVERSITY'** (already aliased to 45; grads 1143 = sum of branches). The 4 branch
  rows are redundant -> left intentionally unresolved (same handling as Tampa Bay 2015). Expect 4
  unresolved Cooley-branch names in 2013.

## NEXT: 2012, then 2011.
Same format expected. Watch for metric-family thinning pre-2012 and any further legacy/branch entities.
Two years left.

## 2012 NOTES (new this session)
- Rode existing machinery, **zero new drift fixes**. Tuition annual (Yale 2012 $53,600). Bar aggregated
  (203 schools). 0 unresolved names. New file 'Informational_and_Library_Resources_2012' (replaces the
  unused Conditional_Scholarships) — not mapped to any metric, skipped by FILEKEY. No metric thinning yet.

## CONFIRMED ABSENT AT SOURCE (Blake-confirmed, triple-checking)
- **2017 bar files** (First_Time_Bar + Two-Year_Ultimate_Bar) do NOT exist -> bar_pct/bar2yr_* are 0/203
  for 2017 by source, not a pending upload.
- **Attrition_2018.xlsx** does NOT exist -> attr_1l/2l/3l absent for 2018 by source.
These are no longer open TODOs; treat as permanent source gaps.

## NEXT: 2011 — FINAL year.
Same format expected. After 2011, the year-by-year ingest is COMPLETE (14 yrs 2012-2025 + 2011 = the full
2011-2025 span the project targeted). Then revisit the deferred non-year items: reconciliation vs
Historic+v2 (agreement %, disagreement CSV), economic context join (BLS/BEA/HUD on harvested school
state), and Title-casing legacy ALLCAPS names at final emit.

## 2011 NOTES (new this session) — final span year
- Rode existing machinery. Tuition annual (Yale 2011 $52,525). Bar aggregated (203 schools). 0 unresolved.
- **Metric thinning (expected, oldest year):** grant amounts are a single `Full-Time Median grant amount`
  (no percentiles) -> mapped to **grant50** (median = 50th pctile); grant75/grant25 absent. Employment
  lacks law-school-funded + Education employer-type FTLT columns (taxonomy expanded post-2011) ->
  emp_lawschool_ftlt/emp_edu_ftlt absent. All per the original spec.
- **New percentile-inversion guard:** if lsat25>lsat75 or gpa25>gpa75 (impossible — source 25<->75
  transposition; median sits between), swap to monotonic. Caught **South Dakota LSAT 2011** (148/150/152).
  Reproducible, runs every year.

## ===== FULL 2011-2025 SPAN COMPLETE: 15 years, 203,811 facts, 0 validation exceptions across all years =====

## NEXT: 2026 (incoming — Blake has 2 files)
2026 is likely a PARTIAL year (only some files exist yet). Ingest what's provided; expect many gaps
(that's fine — idempotent, backfill later). It becomes the 16th/newest year. The post-rename file format
+ long-format bar handler should apply. After 2026, the remaining work is the deferred NON-YEAR items:
- Reconciliation vs Historic + v2 sources (agreement %, disagreement CSV).
- Economic-context join: BLS lawyer wages, BEA RPP, HUD SAFMR — keyed on school state (harvest from raw
  addresses; v2 _SchoolState sheet is an empty scaffold). Note: BEA RPP has no Puerto Rico (UPR gets
  BLS+HUD only).
- Title-case the legacy closed/ALLCAPS school names at final workbook/JSON emit.
- CONFIRMED ABSENT (not TODOs): 2017 bar files, Attrition_2018.
