# Part-Time JD — feature spec

_Status: proposed (data confirmed available, not yet implemented). Owner-requested
after the tuition/fees audit._

## Why
Part-time JD is **not a niche**: **~86 of 211 schools (~41%)** enrolled part-time 1Ls
in 2025 (87 ever since 2018). Today the site reports full-time figures only, so for
nearly half the catalog a whole enrollment track — with its own tuition, admissions
profile, and (often weaker) outcomes — is invisible. Historically the PT track is also
where a lot of access/affordability and bar-risk signal lives, so it is worth first-class
treatment.

## Data — already in the ABA master, no new sourcing needed
| Domain | Full-time (current) | Part-time (to add) | Master source |
|---|---|---|---|
| Enrollment | `enr_1l` | `enr_1l_pt` (already in gz) + total PT | First Year Class `PTEnrollees`; JD Enrollment PT cols |
| Tuition | `tui` / `nrt` | `tui_pt` / `nrt_pt` | Tuition & Fees `PT_Resident_Annual`, `PT_NonResident_Annual` |
| Fees | `ft_fee` / `fee_nrt` | `pt_fee` / `pt_fee_nrt` | `PTRS_AnnualFees`, `PTNRS_AnnualFees` |
| LSAT 25/50/75 | `lsat25/50/75` | `lsat_pt_25/50/75` | `PT{25,50,75}thPercentileLSAT` |
| UGPA 25/50/75 | `gpa25/50/75` | `gpa_pt_25/50/75` | `PT{25,50,75}thPercentileUGPA` |
| GRE / JD-Next | present | PT variants exist | `GREPT*`, `JDNEXTPTEnrollees` |

Note: many schools that report a PT *program* report it per-credit, not annual — the
PT tuition needs the same per-credit×credits annualization discipline we just applied to
FT (and the same per-semester-vs-annual trap). Budget reconciliation time for that.

## Data-model changes
1. Add `pt_*` scalars + `_pt` trends to `data/exhibit-data.js` (and gz history) for the
   ~86 PT schools; leave null for FT-only schools.
2. Add a boolean `offers_pt` (derived: `PTEnrollees > 0` in the latest cycle) to every
   school — drives badges/filters cheaply without reading the full PT block.
3. Extend `scripts/validate_data.py` with PT range/consistency checks mirroring FT.

## UI / UX
1. **School card + full page:** an `FT | PT` toggle in the Cost and Admissions sections.
   Default FT. When a school is FT-only, hide the toggle and show a quiet "Full-time only"
   note. Reuse the existing tuition/fee/enrollment row + trend components — they just bind
   to the `_pt` series when PT is active.
2. **Directory / search:** a "Part-time available" filter chip and a small badge on
   schools that offer it (drives off `offers_pt`).
3. **Compare:** let the compare view pick FT or PT per metric so PT programs are
   comparable head-to-head.
4. **Trends (national):** optional later — PT vs FT national medians (tuition, LSAT,
   enrollment) is a strong story given the historic state of affairs.

## Effort estimate
- **Data/pipeline (PT extract + annualization reconciliation + validator):** the largest
  piece, because PT per-credit annualization will surface the same unit-mismatch errors we
  just cleaned in FT. ~½–1 day of audited extraction.
- **Data-model + `offers_pt` + gz sync:** small.
- **UI (toggle + badge + filter + compare):** moderate; mostly rebinding existing
  components to `_pt` fields rather than net-new widgets.

## Phasing
1. **Phase 1 (visibility):** `offers_pt` badge + filter + a single "Part-time: tuition,
   enrollment, LSAT/GPA" block on the school page. Ships the 41% coverage fast.
2. **Phase 2 (parity):** full FT/PT toggle across Cost + Admissions + trends, compare
   support.
3. **Phase 3 (analysis):** national PT-vs-FT trends.

## Open questions for owner
- Per-credit PT schools: annualize to a notional full PT load, or display per-credit?
- Should PT outcomes (bar/employment) be split out, or do the ABA disclosures only break
  those out by track for some schools? (needs a coverage check before promising it.)
