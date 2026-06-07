# Scorched-earth data rebuild — ABA 509 (2011–2025)

Full re-derivation of the dataset from the **primary source** (ABA Standard 509
disclosure workbooks, ~8–12 per year), reconciled against the shipping data.

## Why / ground rules
- **Two layers** (don't conflate): `data/exhibit-data.js` is the curated display
  layer (hand-edited); `data/exhibit_data.json.gz` is the raw layer. This rebuild
  regenerates the **raw layer** from scratch, then reconciles the curated layer
  against it.
- **Call out, don't silently correct** (data-integrity rule, v1.54.0). Every
  divergence is a *flag* for adjudication, not an auto-edit. See `tuition-audit.md`
  for the precedent format.
- **Year convention:** "report year" = year the 509 disclosure was published.
- **Sources are immutable.** Raw workbooks live under `sources/509/<year>/`,
  byte-pinned by `manifest.csv` (sha256). They are gitignored (public, re-
  downloadable from abarequireddisclosures.org); the manifest + this pipeline
  make the build reproducible without committing the binaries.

## The oracle trick (how we trust the 2011–2017 backfill)
The existing gz already covers **2018–2026** and is trusted. So:
1. Run the new extractor over 2018–2025.
2. Diff our fresh extraction against the existing gz for those years.
3. Iterate the extractor until it **reproduces** the trusted gz (mismatches are
   parser bugs, not data bugs — until proven otherwise).
4. Only then extend the *same* extractor to 2011–2017, where there is no oracle.
This converts "is my from-scratch parser correct?" into a measurable diff.

## Pipeline stages
0. **Inventory + schema probe** — `inspect_sources.py` → `manifest.csv` +
   `schema_probe/`. Run this first on every upload; the ABA layout drifts by
   year, so we read the real headers before writing extractors.
1. **Identity crosswalk** — `crosswalk.csv`: ABA school code → slug `id`, with
   opened/closed years. Reconciled against the 206 existing ids + the
   `name_aliases` map in the gz meta. The join backbone — build before extracting.
2. **Extract → tidy facts** — per-section, per-era extractors → `facts.sqlite`,
   one row = `(school_id, year, section, field, value, source_file, sheet, cell)`.
3. **Reconcile** — classify every cell vs `exhibit-data.js` and the gz:
   MATCH / WITHIN-TOL / MISMATCH / MISSING-IN-SITE / MISSING-IN-SOURCE /
   UNIT-AMBIGUITY (the semester-vs-annual tuition trap). → flag report.
4. **Rebuild + adjudicate** — regenerate the gz raw layer from `facts.sqlite`;
   adjudicate flags; patch `data/exhibit-data.js`; run `scripts/build.sh`
   (which gates on `validate_data.py`).

## Approach: vertical slice first
Before scaling to ~180 files, take **one full year end-to-end** (2025 preferred —
it overlaps the gz oracle) to prove the crosswalk + extractor + reconcile loop.
Then scale year by year, newest→oldest (format gets messier going back).

## Status
- [x] sources uploaded — 2025: **12 of 12** ✅
- [x] inventory + schema probe (`inspect_sources.py`)
- [x] identity crosswalk — 196/196 schools resolve to gz ids
- [x] extractors — **all 12 sections** — `extract.py` → `facts.sqlite`
- [x] reconcile vs existing gz (oracle) — **2025: 100.00% match, 0 mismatches
      across 15,904 compared cells** (`reconcile.py 2025`)
- [x] **2025 / 2024 / 2023 / 2022 / 2021 complete — 12/12 sections each at
      100.00%** (Penn State F1, Rutgers bar F2 adjudicated/excluded)
- [ ] scale 2020 → 2018 (oracle-checked), then 2017 → 2011 (no oracle)
- [ ] gz rebuild + curated-layer reconcile

## Cross-year drift handled (so the same code spans 2011–2025)
- **Year-relative cohort headers:** `{Y-1}` (first-time bar), `{Y-3}` (two-year
  ultimate bar) — the cohort year is baked into ABA headers and shifts yearly.
- **Candidate-header fallbacks** (ABA renames columns): tuition `*_Annual` /
  `*_Semester` (values identical — oracle-verified), enrollment `Hisp*` /
  `OtherHisp*`, race-multi `Multiracial*` / `Race*`.
- **Optional fields** present only some years: `race_nr` (`NRGrandTotal`),
  `seminars` (dropped 2025), clinics/sim `*_available` (pre-2025 reported a
  single count = filled; 2025 split into Available + Filled).
- **Identity layer** (`overrides.py`): schools the gz merged are split back out;
  the collision detector flags any new two-rows-one-slug case automatically.

## Field-definition notes (learned from the 2025 oracle pass)
- `enr_1l` = First Year Class **TotalEnrollees** (incl. "other first-year"),
  NOT the `Enrollees` column. `enr_1l_ft`+`enr_1l_pt` sum to it.
- `grads` = **Total Degrees Awarded** (JD Enrollment & Ethnicity sheet), NOT the
  Employment Summary graduate count — that count is `emp_grads`.
- Bar sheets: `School Name` (space), no year column, cohort year baked into
  headers (first-time = "Graduates In 2024"; two-year = "2022 Graduates").
- Sentinels nulled on extract: `$`/`N`/`N/A`, `*`/`**`/`***`, and `0` for
  LSAT / uGPA / transfer-GPA (the ABA "not reported" zero).
- Extract layer is **raw reads only**; derived pcts / firm-size buckets /
  `schol_none` are deferred to the rebuild step so the oracle stays meaningful.
