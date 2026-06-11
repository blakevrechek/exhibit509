# Adjudicated corrections ledger

Curated/display-layer corrections that override a raw ABA cell in
`data/exhibit-data.js`. The raw gz (`data/exhibit_data.json.gz`) keeps the
original ABA value as the source of record; on a source re-upload + re-extract
the gz is regenerated, but curated overrides for existing schools persist.

Corrections flagged on the interactive chart (amber hollow ring + hover note)
are registered in `FIXES` in `index.html`; nonresident-only and percentile
fixes that don't surface on the resident chart are recorded here only.

## 2026-06-11 — anomaly sweep (Tier 3)

### Tuition — misreported per-semester halves (raised to fit trend) · ON-CHART
| school | year(s) | from (res/nr) | to (res/nr) | basis |
|---|---|---|---|---|
| Texas | 2017, 2018 | 17,857 / 26,517 | 35,714 / 53,034 | per-semester halves; trend is ~$34–38k throughout. Reverses the Tier-2 sheet's 2018 = 17,857 (that was the misreport). |
| Cincinnati | 2021 | 12,005 / 14,505 | 24,010 / 29,010 | lone half; every other year 2014–2025 = 24,010 / 29,010. |
| South Carolina | 2021 | 9,653 / 24,661 | 18,556 / 35,342 | half-value outlier; aligned to the 2022–23 plateau. |

### Tuition — Stanford fill (interpolated 2017→2021) · ON-CHART
| year | from | to | basis |
|---|---|---|---|
| 2018 | 0 | 61,290 | $0 text-marker corruption; interpolated. |
| 2019 | 41,450 | 62,310 | partial/quarter figure; interpolated. |
| 2020 | 42,900 | 63,330 | partial/quarter figure; interpolated. |
nr mirrors res (private); nr 2017 filled 60,270; nrt scalar 0 → 77,454.

### Tuition — Florida Coastal · ON-CHART
- 2019 resident 79,580 → 39,790 (private; res = nr).

### Enrollment — Montana · ON-CHART
- `enr_trend` 2021 = 3 → 248 (curated corruption; gz total JD enrollment is 248).
  Note: `enr` = total JD enrollment (ABA "Total Grand Total"); `enr_1l` = entering 1L class.

### LSAT percentiles — South Dakota (ledger only)
- 2011 25th/75th were inverted (152/148) → restored to 148 / 152 (50th = 150 unchanged).

### Nonresident = resident (private; remove divergent nonres) (ledger only)
- Detroit Mercy: `nrt_trend` mirrored to resident for all years (2023–25 nr 45,037/45,936/46,864 dropped); nrt scalar 46,864 → 56,143. **2025 resident → $27,800** (tuition cut; res=nr; scalar updated). **2023 & 2024 still pending** owner values — they carry the old ~$53–54k sticker, inconsistent with a 2025 of $27,800.
- Northwestern 2025 nr 79,722 → 79,772 (+ scalar); Boston College 2016 nr 50,700 → 50,770; Denver 2012 nr 39,480 → 39,840; Willamette 2020 nr 46,530 → 47,130; Mitchell/Hamline 2016 nr 40,470 → 40,570.

### Public — nonresident correction (ledger only)
- Indiana-Indianapolis 2016 nr 22,614 → 45,227 (resident 26,379 unchanged).

## Deferred / not changed
- **E — apostrophe near-zero cells** (Stanford 2018 prior, Dayton, Washburn, UIC, Widener ×2, Indiana-Indianapolis, Inter-American PR + closed schools): await the ABA 509 re-upload + re-extract (parser fix already in place). Closed schools stay missing.
- **F — Nebraska** grant_med > resident tuition: not a bug (grants scaled to nonresident/sticker, pooled school-wide).
