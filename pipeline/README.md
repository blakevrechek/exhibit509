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
- [ ] sources uploaded
- [ ] inventory + schema probe
- [ ] identity crosswalk
- [ ] extractors (per section)
- [ ] reconcile vs existing gz (oracle)
- [ ] 2011–2017 backfill
- [ ] gz rebuild + curated-layer reconcile
