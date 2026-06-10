# Session handoff — Exhibit 509 (data rebuild + UI/feature sprint)

_Last updated: 2026-06-09. Branch: `claude/festive-galileo-A9Qd9` (all work merged to
`main`, which auto-deploys via Cloudflare Pages). Live version: **v1.90.1**._

This session did two big things: (1) a from-scratch re-derivation of the dataset from
the primary ABA 509 workbooks, shipped as additive backfill + corrections; and (2) a
long run of UI/feature/data-quality changes. Everything below is **live on `main`**.

---

## 1. How the project is wired (read this first)

- **Two data layers**, both consumed by `index.html`:
  - `data/exhibit-data.js` — the **curated display layer**, `const S = [...]` (one record
    per school: current-cycle scalars + `*_trend` dicts) plus `BLS`/`RPP`/`FMR`. It is
    **hand-curated / patched by scripts**, NOT generated from the gz. Drives the map,
    school panel, detail page, and the static per-school pages.
  - `data/exhibit_data.json.gz` — the **raw layer** (206 schools, 2011–2026, ~136
    fields/year). Feeds the over-time charts. Backfilled this session.
- **Pipeline** (`pipeline/`) re-derives everything from the ABA workbooks in
  `sources/509/<year>/` (gitignored; re-downloadable, pinned by `manifest.csv`) into
  `pipeline/facts.sqlite` (gitignored). Key scripts: `extract.py` (12 section
  extractors → facts), `crosswalk.py` (ABA name → slug), `rebuild_gz.py` /
  `rebuild_trends.py` (additive merge of facts into the two data layers),
  `reconcile*.py` (oracle/trend validation), `overrides.py` (identity/adjudication).
- **Build**: `bash scripts/build.sh` runs `validate_data.py` (the gate) →
  `build_school_pages.py` (regenerates static pages + sitemap) → `stamp_version.py`
  (stamps `VERSION` / `SYNC_DATE` across pages). Bump `VERSION` before building.
- **Deploy/branch flow** (important): PRs are **squash-merged**, so after each merge the
  feature branch diverges from `main`. The pattern used all session:
  `commit → git fetch origin main → git reset --hard origin/main → git cherry-pick <commit>
  → push --force-with-lease → open PR → merge`. This keeps each PR's diff to just its own change.
- **CI**: GitHub Actions `validate` (runs `validate_data.py`; only triggers on data-file
  changes) + Cloudflare Pages build. For app-only PRs, `validate` may not trigger —
  gate locally with `python3 scripts/validate_data.py` + `node --check` on the inline JS.
- **The rebuilt 2011–2026 dataset lives in `pipeline/facts.sqlite`** (gitignored). It is
  the source of truth for the additive backfills. If you need it, regenerate with
  `python3 pipeline/extract.py` (needs `sources/509/`).

---

## 2. Data work shipped (the re-derivation)

- **v1.77.0** — Backfilled **2011–2017** history into the gz (72,948 cells) + 5 new
  fields (`cond_enter`/`cond_elim`, `seminars`, `race_nr`, `enr_1l_entering`); extended
  curated `*_trend` series to 2011 (4,500 cells incl. the bar-passage 2012–2017 gap).
  **Additive only** — no existing 2018–2026 value overwritten. The oracle window
  (2018–2026) reproduced the trusted gz 100% before any backfill.
- **v1.78.0 (D1)** — Demographics: `sex_men`/`sex_women` backfilled **2011–2017**
  (2011–16 from `#Total Men/Women`; 2017 via `extract_2017_sex()` summing the per-level
  totals), `enr` + `race_*` backfilled 2011–2016. Verified race-sum == enr 1168/1168.
- **v1.79.0 / 1.81.0 / 1.83.0** — **GRE** (Verbal/Quant/Analytical 25/50/75, 2023+) +
  **JD-Next** (25/50/75, 2024+) + **attrition** backfilled to 2011. Surfaced on all three
  school views (static pages, quick panel, detail page). Sparse by design (ABA suppresses
  small-N GRE; only Arizona & Dayton report JD-Next).
- **v1.90.0** — **Per-credit tuition recovery** (see §4, "tuition" — this is the most
  data-significant change).

### Key data decisions / conventions
- **Tuition is annualized.** 2018–2020 ABA workbooks report **per-semester** → ×2
  (verified vs gz). Per-credit-only schools → × **30** credits/yr (was 29; recalibrated
  this session, see §4).
- **Bar %** uses the ABA composite (FLAGS F4).
- **`enr_trend` is intentionally NOT backfilled** — the curated series is offset ~1 year
  from raw `enr` (a different measure); mixing would seam the chart.
- **Adjudicated identity cases** (kept separate / not auto-overlaid), see `pipeline/FLAGS.md`:
  - **F1 Penn State** — University Park vs Dickinson. Resolved this session (§4).
  - **F2 Rutgers** — Camden/Newark/combined. Still the one adjudicated case driving the
    0.14% disagreement in the cross-validation. Left as-is.

---

## 3. Cross-validation / accuracy (v1.89.0)

Compared two independent compilations vs the pipeline (`pipeline/facts.sqlite`):
- **Exhibit 509 Master workbook** (~2.44M non-null facts / 2,437,481; 218 school ids;
  ~12,200 facts per full-history school) **vs the pipeline → 99.86% agreement**
  (28,747/28,786 headline cells, 17 metrics). 100% on acceptance/apps/offers/enrollment/
  bar-grads/tuition. **Residual is entirely the adjudicated Rutgers case.**
- Historic 262-school roster: 253 (96.6%) resolve; 9 misses are name-format variants.
- Documented in: `pipeline/ACCURACY_REPORT.md`, `pipeline/COMPARISON.md`,
  `pipeline/README.md`, and the public `methodology.html` "Data quality" section.

---

## 4. Notable corrections & features this session

- **F1 Penn State (v1.79.1 + v1.80.0):** gz had Dickinson carrying University Park's
  2023–24 enrollment. Corrected Dickinson → true Carlisle (295/304); backfilled UP's own
  2023–24 + map metadata; recorded the 2024–25 reunification. Added **University Park +
  Golden Gate** as curated school records (they existed only in the gz) via
  `build_curated_records.py` — built from each school's own gz data (verified 17/17 vs a
  reference school). Both show closed banners + are excluded from rankings.
- **Tuition "not disclosed" recovery (v1.90.0 + v1.90.1):** most "not disclosed" years
  weren't missing — they were **per-credit-only schools** whose rate was never converted
  to annual (sat as `$0`, tripped the banner). `recover_percredit_tuition.py` converts
  the cross-validated per-credit rate at **×30** (calibrated vs each school's adjacent
  annual years, median ~5% err; guarded by plausible-range + neighbor-ratio) and mirrors
  non-resident→resident for private single-tuition schools. **~190 cells recovered across
  42 schools; banner cleared for them.** **12 schools keep the banner** (genuinely empty
  even in the primary source: Stanford 2018, the closed schools, a few public one-offs) —
  and v1.90.1 marks those exact years **on the tuition graph** (dotted column + "n/a" +
  floor marker, via the new `bandChart` `missingYears` option keyed on `s._tuiMissing`).
- **Charts (v1.82.0 / v1.88.0):** `$0` magnitude/rate sentinels are flagged with an open
  "not reported" circle (lineChart/bandChart `zeroAsMissing`); percentage charts capped at
  100% (`pct` flag — caps the ceiling, still auto-scales below); the 4-year forecast/
  projection now shows on **all** metric charts (panel apps/enr/tui gained it).
- **Detail page (v1.85.0):** reordered to the applicant lifecycle —
  **Admissions(1) → Cost(2) → Outcomes(3)** then Math(4), Market(5), Class(6), and the
  15-year **Arc(7)** as the closing retrospective (was the lead). Section ids unchanged so
  jump-links still work. Orange section dividers (v1.87.1).
- **Hero (v1.86.0):** "Is it worth it?" removed; now "The ~~evidence~~ **data** on every
  law school" (evidence struck by a **red pen** effect, v1.87.1; "data" in BLS green).
  Subtitle → "The independent alternative to LSAC-owned tools."
- **Light mode (v1.87.1):** the bimodal "two humps" + "How to read these" bullets darkened
  (`#C6D8E6` was invisible); **global yellow** switched from black-outlined to a darker
  amber (`#8A6A00`).
- **Mobile (v1.84.0 / v1.85.1):** fixed "Back to map" exit pill on the full-screen school
  page (sticky back fails on iOS); tightened the enlarged-chart modal buttons + fixed the
  missing school name when enlarging from the quick panel.
- **Consultant's Corner (v1.87.0 / v1.88.1 / v1.89.1):** new `consultants.html` advisor
  landing page from supplied copy; the top-right header **"Tour" tile was repurposed** to
  link it (tour still in the mobile menu + feedback bar). Now behind a **"coming soon"
  gate** — public sees the teaser + "Be among the first in" (mailto); **preview password
  `sell`** reveals the full page (client-side soft gate, `noindex`, off the sitemap). Em
  dashes + "first 10/ten" scarcity removed.

---

## 5. Open / deferred items

- **F2 Rutgers** — still the one adjudicated identity case (Camden/Newark). Not resolved;
  it's the sole driver of the cross-validation residual.
- **12 schools keep a genuine tuition gap** — recoverable only from the raw ABA PDFs
  (offered to source them; not done).
- **`enr_trend` offset** — the curated enrollment trend is ~1yr offset from raw `enr`;
  worth a dedicated fix if you want them to match.
- **Consultant's Corner gate is client-side** (soft). For a real gate, move behind
  Cloudflare Access / server auth. CTAs are `mailto:` (no form/Calendly yet).
- **Baylor 2021 recovered tuition** is an outlier ($61,782) flagged by the existing
  "under review" anomaly caveat — verify against the source PDF if convenient.
- The full ABA 509 workbook set (2011–2025, all sections) was uploaded this session and is
  available if you want to extend the pipeline (e.g., per-credit extraction directly from
  source rather than via the Master).

---

## 6. Quick reference

| | |
|---|---|
| Live version | v1.90.1 · SYNC_DATE "June 8, 2026" |
| Build | `bash scripts/build.sh` (bump `VERSION` first) |
| Validate gate | `python3 scripts/validate_data.py` |
| JS sanity | extract inline `<script>` → `node --check` |
| Re-derive data | `python3 pipeline/extract.py` then `rebuild_gz.py --write` / `rebuild_trends.py --write` (needs `sources/509/`) |
| Adjudications/flags | `pipeline/FLAGS.md` |
| Accuracy report | `pipeline/ACCURACY_REPORT.md` |
| After deploy | `python3 scripts/indexnow_ping.py` (pings search engines) |
