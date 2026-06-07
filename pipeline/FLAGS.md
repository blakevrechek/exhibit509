# Rebuild adjudication flags

Discrepancies surfaced by the primary-source rebuild. Per the data-integrity
rule (v1.54.0) these are **called out, not silently corrected** — each needs a
decision before any edit to `data/exhibit-data.js` or the gz.

## RESOLVED

### F1 — Penn State: two ABA schools collapsed to one slug (identity) ✅
- **Decision (2026-06, Blake):** keep the two schools separate — opening/closing
  recurs across the dataset and both are to be preserved.
- **Implemented:** `pipeline/overrides.py` —
  `Penn State University` → new slug **`penn-state-law`** (University Park);
  `Penn State Dickinson Law` → **`penn-state-dickinson-law`** (Carlisle).
  The gz's existing `penn-state-dickinson-law` carries University Park figures,
  so it is marked ADJUDICATED (excluded from the oracle match rate; the gz
  rebuild will write the corrected Carlisle values + add `penn-state-law`).
- **General mechanism:** future split/merge/open/close identity decisions go in
  `overrides.py` (`NAME_OVERRIDES` / `NEW_SLUGS`); the extractor's collision
  detector surfaces new ones automatically.

---

## OPEN

_(none)_

<!-- template for future flags
### F2 — <title>
- **Where:** ...
- **What:** ...
- **Decision needed:** ...
-->

## (history)

### F1 detail — Penn State: two ABA schools collapse to one slug (identity)
- **Where:** 2024 (and likely every year both reported). All ~21 JD/bar/tuition
  fields for `penn-state-dickinson-law`.
- **What:** the ABA workbooks list **two** rows — `Penn State Dickinson Law`
  (Carlisle) and `Penn State University` (= Penn State Law, University Park).
  The meta `name_aliases` maps `Penn State University` → `penn-state-dickinson-law`,
  so both collapse to one slug; the extractor now flags this instead of letting
  one silently overwrite the other.
- **Key fact:** the existing gz `penn-state-dickinson-law` 2024 values match the
  **`Penn State University`** row (enr 385, white 268, grads 140), NOT the
  `Penn State Dickinson Law` row (enr 304, white 169, grads 89). So the slug
  named "Dickinson" is currently carrying Penn State **Law** (University Park)
  figures.
- **Decision needed:** which entity is `penn-state-dickinson-law` supposed to be?
  Options: (a) keep it as Dickinson Law (Carlisle) and re-point the alias / add a
  second slug for University Park; (b) accept it as the merged Penn State and use
  the University Park row (status quo of the gz); (c) treat University Park as a
  closed/teach-out school. Penn State Law (UP) wound down and merged into
  Dickinson Law ~2020–22, so teach-out years overlap.
- **Status:** awaiting decision. Extractor keeps the Dickinson Law row; gz keeps
  the University Park row → shows as 21 mismatches until resolved.
