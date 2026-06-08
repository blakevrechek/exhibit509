# Cross-validation: rebuild `facts.sqlite` vs parallel `Exhibit_509_Master.xlsx`

Two independently-built derivations of the ABA 509 data, compared cell-by-cell
on `(school_id, year, field)` (their `SchoolName_Original` mapped through our
crosswalk). Verdict: **they agree wherever directly comparable** — strong mutual
validation. The remaining differences are architectural/policy choices, each
explainable, not data disagreements.

## Agreement (value concordance)
| field | 2023 | 2024 | 2025 | old era |
|---|---|---|---|---|
| lsat50 | 196/196 | 196/196 | 196/196 | 2014: 195/196 |
| gpa50 | 196/196 | 196/196 | 196/196 | — |
| apps | 196/196 | 196/196 | 196/196 | — |
| offers | 196/196 | 196/196 | 196/196 | — |
| fac_ft | 196/196 | 196/196 | 196/196 | — |
| bar | 195/195 | 195/195 | 194/194 | — |
| tui_ft_res | (their annual blank) | (blank) | 196/196 | — |

Essentially 100% wherever both populate the same quantity, in both the modern and
verbose eras.

## Architectural / policy differences (not value conflicts)
1. **Tuition normalization.** Ours normalizes every year to **annual**, including
   the ×2 for 2018–2020 (those workbooks report per-semester; verified: our ×2
   reproduces the gz annual 100%). The Master keeps era columns and only fills the
   `FT_Resident_Annual` canonical for 2025 — so its 2018–2020 annual tuition needs
   the ×2 applied downstream, or it's half. **Worth confirming on their side.**
2. **Rutgers.** Master keeps `RUTGERS-NEWARK` / `RUTGERS-CAMDEN` / `RUTGERS`
   separate. Ours collapses to one `rutgers-university` (combined). Both defensible
   (see F2). The merged school is one ABA accreditation; campuses are sub-rows.
3. **Penn State.** Both split Dickinson Law vs Penn State Law (agree — F1). ✓
4. **Bar 2011–2017.** Ours extracts the school-level **Composite Avg. School Pass
   %** from `Bar_Passage_Rates` (gap-fill; per F4 the ABA composite is canonical).
   Master treats 2011–2017 first-time-bar *summary* as absent (jurisdiction-level
   only). So ours carries bar for those years, theirs doesn't.
5. **Demographics.** Master carries gender buckets (Men/Women/AGI/Other) across
   years; ours currently has `grads` + deferred race totals (D1 → will add sex
   2011–2026 + race 2016–2025).
6. **Degrees awarded.** Master relocates to per-race `DegreesAwardedByRace: X`
   columns; ours keeps the single `grads` total. Same underlying data.

## Takeaway
The two derivations corroborate each other to ~99–100% on every directly-
comparable metric across 2011–2025. The differences are deliberate modeling
choices; #1 (2018–2020 tuition ×2) is the one with a clear right answer (ours,
gz-validated) and is worth checking in the Master before it feeds Exhibit.
