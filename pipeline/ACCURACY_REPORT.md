# Accuracy report — two independent 509 compilations vs the Exhibit pipeline

_Generated June 9, 2026. Compares two externally-supplied compilations against
`pipeline/facts.sqlite` (the primary-source re-derivation that backs Exhibit)._

## Inputs

1. **Exhibit 509 Master** (`Exhibit_509_Master.xlsx`) — a hand-built, 17-sheet
   compilation of the ABA Standard 509 disclosures (one tidy school×year sheet
   per section). Scale of this compilation:
   - **~2.44 million data points** — **2,437,481** non-null facts across the 14
     data sheets (excluding the Dashboard, the hidden `_lists`, and the spine
     columns School/Year/Status).
   - Two sheets dominate on column width: **Attrition (866K** — now including the
     gender "Other" residuals), **JD Enrollment & Ethnicity (534K)**, then
     **Employment (467K)**; everything else is under ~125K each.
   - **218** distinct school identifiers. Per school **~12,200** facts for a
     typical full-history school: **median 12,178**, range **75–12,821**, mean
     **11,181** (the mean sits lower, dragged down by a dozen-plus small rows for
     short-lived / late-entering schools).
2. **Extensive Data … Historic** (`…Historic__20251.xlsx`) — a **262-school**
   roster (name + full 509 name); used here as a coverage cross-check.

## Method

Each compilation's school name is resolved to an Exhibit slug with the project's
own crosswalk (`pipeline/crosswalk.py`), then joined to `facts.sqlite` on
(school, year, metric). Multiple year-era column variants in the Master (the ABA
renamed columns over the years) are coalesced to a single value per cell.
Tolerances: LSAT ±0.5, uGPA ±0.02, rates ±0.6 pts; counts and tuition exact.

## Result — Master vs Exhibit pipeline

**Overall agreement: 99.86%** — 28,747 of 28,786 compared headline cells, across
17 metrics.

| metric | agree / compared | % |
|---|---|---|
| LSAT 25 / 50 / 75 | 2934/2937 · 2933/2937 · 2934/2937 | 99.86–99.90% |
| uGPA 25 / 50 / 75 | 2931/2935 (each) | 99.86% |
| Acceptance rate | 1169/1169 | 100.00% |
| Applications | 588/588 | 100.00% |
| Offers | 588/588 | 100.00% |
| 1L enrollment | 588/588 | 100.00% |
| First-time bar % | 1761/1766 | 99.72% |
| State bar avg % | 1764/1766 | 99.89% |
| First-time takers | 1762/1767 | 99.72% |
| First-time passers | 1762/1767 | 99.72% |
| Bar graduates | 779/779 | 100.00% |
| Resident tuition | 196/196 | 100.00% |
| Non-resident tuition | 196/196 | 100.00% |

**Where the 0.14% sits:** the disagreements are not scattered — they concentrate
on **`rutgers-university`**, the known **adjudicated identity case** (the ABA
filings split Camden vs Newark in some years; the two compilations make different
roll-up choices). This is the same case flagged in `pipeline/FLAGS.md` (F2), not a
data error. No other school contributes a material share of the mismatches.

## Coverage — Historic roster vs Exhibit

262 listed → **253 (96.6%)** resolve straight to the Exhibit dataset. The 9
unmatched are **name-format variants of schools already present** (Charlotte,
Hamline, William Mitchell, Indiana Tech, Penn State, UMass Dartmouth, UNLV, New
England Law | Boston) plus one placeholder row ("Generic University") — i.e.
crosswalk-spelling gaps, not missing schools.

## Takeaway

Two independently-built compilations of the same primary source agree on
**99.86%** of comparable cells, with the residual fully explained by a single
adjudicated identity case. That is the cross-validation Exhibit leans on instead
of testimonials.
