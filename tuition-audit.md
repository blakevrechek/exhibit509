# Tuition anomaly audit — `tui_trend` downward-jump scan (workbook cross-referenced)

Scan of all 208 schools' resident `tui_trend` for year-over-year drops **> 10%**
and **>= $2,000** (real tuition rarely falls that fast). Each flag is now
cross-referenced against the **authoritative `Exhibit_Data.xlsx`** (column `ABA src`),
so you can adjudicate case by case. **Nothing was auto-changed.** Tell me which to
patch and I'll edit `tui_trend` (+ `nrt` mirrors) and rebuild.

Last refreshed 2026-06-05 against the uploaded workbook. 51 downward jumps flagged.

## Patched in v1.51.2 (decisive cases only)

Corrected to the ABA source where the evidence was unambiguous (isolated 2x
spike bracketed by correct years on both sides, scalar-confirmed, or 0-sentinel):

- Cornell 2019 res $135,496 -> $67,748 (isolated spike)
- Ohio State 2019 res $62,900 -> $31,450 (isolated spike)
- Campbell 2019 res $85,200 -> $42,600 (isolated spike)
- Nevada-Las Vegas 2020 res $53,800 -> $26,900, nr $78,600 -> $39,300 (isolated spike)
- Montana 2023-25 res $12k -> $19,494 / $24,161 / $24,582 (matches the school's own 2025 scalar)
- Florida State 2020-22 res & nr were 0-sentinels -> ABA ($17,487/$17,487/$17,458; nr $35,902/$35,902/$35,873)

The remaining flags below are LEFT AS-IS: they are genuine semester-vs-annual
ambiguities where the direction varies by school (for several, the site value
already fits the trajectory and the ABA cell is the per-semester figure).
Verify these against the original 509 disclosure before changing.



## $0-tuition sweep, patched in v1.51.3

Separate from the semester/annual flags below. 239 garbage tuition cells (mostly
stored `$0`, a few truncated like `$70`/`$120`/`$550`) across 39 schools, almost
all 2018-2022. `$0` is never valid tuition, so:
- 205 cells filled from data consistent with the school's neighbors: the ABA
  workbook where present, and for PRIVATE schools the non-resident figure where
  only the resident cell was zeroed (Boston College 2019-20 -> $56,940/$59,220,
  Loyola Marymount 2019-23 -> ~$58-65k, UIC 2019-22 -> $34,800, Kansas ->
  $21,779, Santa Clara -> ~$54k, Detroit Mercy -> $43,297).
- 34 cells DELETED (rendered as MISSING, not $0) where no trustworthy source
  exists: Stanford 2018, the closed schools (Arizona Summit, Whittier,
  Valparaiso, Florida Coastal), and double-garbage 2018 cells (Washburn $70,
  Widener $120, UIC $550, Dayton $418, Indiana $1,094).

## D. Likely SITE error — ABA source has a normal/higher value (best fix candidates)

| School | Year | Site prev → year | Drop | ABA src (prev → year) | Assessment |
|---|---|---|---|---|---|
| Montana, University of | 2023 | $14,838 → $12,263 | −17% | $14,838 → $19,494 | site below ABA source — likely site error; ABA = $19,494 |

## C. Prior-year looks DOUBLED — the drop is a correction; fix the earlier cell instead

| School | Year | Site prev → year | Drop | ABA src (prev → year) | Assessment |
|---|---|---|---|---|---|
| South Carolina, University of | 2021 | $19,306 → $9,653 | −50% | $9,653 → $9,653 | prior year ($19,306) looks doubled vs ABA ($9,653); flagged year matches ABA — fix the PRIOR cell |
| Nevada-Las Vegas, University of | 2021 | $53,800 → $26,900 | −50% | $26,900 → $26,900 | prior year ($53,800) looks doubled vs ABA ($26,900); flagged year matches ABA — fix the PRIOR cell |
| Cincinnati, University of | 2021 | $24,010 → $12,005 | −50% | $12,005 → $12,005 | prior year ($24,010) looks doubled vs ABA ($12,005); flagged year matches ABA — fix the PRIOR cell |
| Mississippi College | 2021 | $34,800 → $17,400 | −50% | $17,400 → $17,400 | prior year ($34,800) looks doubled vs ABA ($17,400); flagged year matches ABA — fix the PRIOR cell |
| Brigham Young University | 2021 | $13,860 → $7,104 | −49% | $6,930 → $7,104 | prior year ($13,860) looks doubled vs ABA ($6,930); flagged year matches ABA — fix the PRIOR cell |
| The Ohio State University | 2020 | $62,900 → $32,060 | −49% | $31,450 → $32,060 | prior year ($62,900) looks doubled vs ABA ($31,450); flagged year matches ABA — fix the PRIOR cell |
| Cornell University | 2020 | $135,496 → $70,188 | −48% | $67,748 → $70,188 | prior year ($135,496) looks doubled vs ABA ($67,748); flagged year matches ABA — fix the PRIOR cell |
| Campbell University | 2020 | $85,200 → $44,950 | −47% | $42,600 → $44,950 | prior year ($85,200) looks doubled vs ABA ($42,600); flagged year matches ABA — fix the PRIOR cell |
| Pontifical Catholic University of Puerto Rico | 2021 | $15,000 → $8,000 | −47% | $7,500 → $8,000 | prior year ($15,000) looks doubled vs ABA ($7,500); flagged year matches ABA — fix the PRIOR cell |
| South Dakota, University of | 2020 | $17,000 → $11,620 | −32% | $8,500 → $11,620 | prior year ($17,000) looks doubled vs ABA ($8,500); flagged year matches ABA — fix the PRIOR cell |
| Southern University | 2019 | $16,530 → $11,338 | −31% | $8,265 → $11,338 | prior year ($16,530) looks doubled vs ABA ($8,265); flagged year matches ABA — fix the PRIOR cell |
| North Carolina Central University | 2019 | $18,738 → $13,444 | −28% | $9,369 → $13,444 | prior year ($18,738) looks doubled vs ABA ($9,369); flagged year matches ABA — fix the PRIOR cell |
| Oklahoma, University of | 2020 | $21,504 → $15,720 | −27% | $10,752 → $15,720 | prior year ($21,504) looks doubled vs ABA ($10,752); flagged year matches ABA — fix the PRIOR cell |
| Southern Illinois University | 2019 | $22,564 → $17,504 | −22% | $11,282 → $17,504 | prior year ($22,564) looks doubled vs ABA ($11,282); flagged year matches ABA — fix the PRIOR cell |
| Louisiana State University | 2019 | $23,660 → $19,750 | −17% | $11,830 → $19,750 | prior year ($23,660) looks doubled vs ABA ($11,830); flagged year matches ABA — fix the PRIOR cell |
| Texas Tech University | 2019 | $26,840 → $22,590 | −16% | $13,420 → $22,590 | prior year ($26,840) looks doubled vs ABA ($13,420); flagged year matches ABA — fix the PRIOR cell |
| Tennessee, University of | 2019 | $19,674 → $16,696 | −15% | $9,837 → $16,696 | prior year ($19,674) looks doubled vs ABA ($9,837); flagged year matches ABA — fix the PRIOR cell |
| Florida State University | 2019 | $20,694 → $18,072 | −13% | $10,347 → $18,072 | prior year ($20,694) looks doubled vs ABA ($10,347); flagged year matches ABA — fix the PRIOR cell |

## A. ABA source CONFIRMS the drop — real reset or a source-level semester error (verify the original 509 disclosure)

| School | Year | Site prev → year | Drop | ABA src (prev → year) | Assessment |
|---|---|---|---|---|---|
| Washburn University | 2018 | $21,588 → $70 | −100% | $21,588 → $35 | ABA source shows the same drop ($21,588→$35) — real reset or source semester error; verify disclosure |
| Dayton, University of | 2018 | $33,739 → $418 | −99% | $33,739 → $209 | ABA source shows the same drop ($33,739→$209) — real reset or source semester error; verify disclosure |
| Tulsa, The University of | 2017 | $38,030 → $25,254 | −34% | $38,030 → $25,254 | ABA source shows the same drop ($38,030→$25,254) — real reset or source semester error; verify disclosure |
| Texas Southern University | 2023 | $19,201 → $12,645 | −34% | $19,201 → $12,645 | ABA source shows the same drop ($19,201→$12,645) — real reset or source semester error; verify disclosure |
| Baylor University | 2025 | $64,544 → $46,574 | −28% | $64,544 → $46,574 | ABA source shows the same drop ($64,544→$46,574) — real reset or source semester error; verify disclosure |
| Ohio Northern University | 2014 | $33,684 → $24,800 | −26% | $33,684 → $24,800 | ABA source shows the same drop ($33,684→$24,800) — real reset or source semester error; verify disclosure |
| Roger Williams University | 2014 | $42,130 → $33,792 | −20% | $42,130 → $33,792 | ABA source shows the same drop ($42,130→$33,792) — real reset or source semester error; verify disclosure |
| William & Mary | 2020 | $35,000 → $28,724 | −18% | $35,000 → $28,724 | ABA source shows the same drop ($35,000→$28,724) — real reset or source semester error; verify disclosure |
| Texas A&M University | 2016 | $33,092 → $28,000 | −15% | $33,092 → $28,000 | ABA source shows the same drop ($33,092→$28,000) — real reset or source semester error; verify disclosure |
| Iowa, University of | 2014 | $28,047 → $23,760 | −15% | $28,047 → $23,760 | ABA source shows the same drop ($28,047→$23,760) — real reset or source semester error; verify disclosure |
| Brooklyn Law School | 2015 | $54,246 → $46,176 | −15% | $54,246 → $46,176 | ABA source shows the same drop ($54,246→$46,176) — real reset or source semester error; verify disclosure |
| North Texas at Dallas, University of | 2025 | $19,126 → $16,298 | −15% | $19,126 → $16,298 | ABA source shows the same drop ($19,126→$16,298) — real reset or source semester error; verify disclosure |
| Houston, University of | 2020 | $33,180 → $28,674 | −14% | $33,180 → $28,674 | ABA source shows the same drop ($33,180→$28,674) — real reset or source semester error; verify disclosure |
| North Carolina, University of | 2019 | $24,172 → $21,142 | −13% | $24,172 → $21,142 | ABA source shows the same drop ($24,172→$21,142) — real reset or source semester error; verify disclosure |
| Oklahoma City University | 2019 | $35,630 → $30,886 | −13% | $35,630 → $30,886 | ABA source shows the same drop ($35,630→$30,886) — real reset or source semester error; verify disclosure |
| Florida, University of | 2020 | $21,802 → $19,140 | −12% | $21,802 → $19,140 | ABA source shows the same drop ($21,802→$19,140) — real reset or source semester error; verify disclosure |
| Elon University | 2015 | $37,924 → $33,334 | −12% | $37,924 → $33,334 | ABA source shows the same drop ($37,924→$33,334) — real reset or source semester error; verify disclosure |
| Toledo, The University of | 2015 | $22,203 → $19,612 | −12% | $22,203 → $19,612 | ABA source shows the same drop ($22,203→$19,612) — real reset or source semester error; verify disclosure |
| Georgia, University of | 2019 | $19,708 → $17,604 | −11% | $19,708 → $17,604 | ABA source shows the same drop ($19,708→$17,604) — real reset or source semester error; verify disclosure |
| Arizona, The University of | 2013 | $27,272 → $24,396 | −11% | $27,272 → $24,396 | ABA source shows the same drop ($27,272→$24,396) — real reset or source semester error; verify disclosure |
| Memphis, The University of | 2020 | $19,218 → $17,116 | −11% | $19,218 → $17,116 | ABA source shows the same drop ($19,218→$17,116) — real reset or source semester error; verify disclosure |
| California-Berkeley, University of | 2022 | $62,979 → $56,500 | −10% | $62,979 → $56,500 | ABA source shows the same drop ($62,979→$56,500) — real reset or source semester error; verify disclosure |
| George Mason University | 2019 | $25,354 → $22,702 | −10% | $25,354 → $22,702 | ABA source shows the same drop ($25,354→$22,702) — real reset or source semester error; verify disclosure |
| California-San Francisco, University of | 2021 | $49,758 → $44,728 | −10% | $49,758 → $44,728 | ABA source shows the same drop ($49,758→$44,728) — real reset or source semester error; verify disclosure |
| Howard University | 2017 | $37,534 → $33,630 | −10% | $37,534 → $33,630 | ABA source shows the same drop ($37,534→$33,630) — real reset or source semester error; verify disclosure |

## B. Other / no clean ABA comparison

| School | Year | Site prev → year | Drop | ABA src (prev → year) | Assessment |
|---|---|---|---|---|---|
| Indiana University-Indianapolis | 2018 | $26,736 → $1,094 | −96% | $28,631 → $547 | differs from ABA ($547) |
| FLORIDA COASTAL SCHOOL OF LAW | 2020 | $79,580 → $39,790 | −50% | $39,790 → $19,895 | differs from ABA ($19,895) |
| South Carolina, University of | 2019 | $29,608 → $19,306 | −35% | $14,804 → $9,653 | differs from ABA ($9,653) |
| Washington, University of | 2019 | $35,988 → $23,970 | −33% | $35,988 → $11,985 | differs from ABA ($11,985) |
| Chicago, The University of | 2019 | $65,134 → $44,434 | −32% | $21,766 → $22,217 | differs from ABA ($22,217) |
| Baylor University | 2018 | $60,050 → $41,614 | −31% | $60,050 → $20,807 | differs from ABA ($20,807) |
| Elon University | 2019 | $44,550 → $30,760 | −31% | $44,550 → $15,380 | differs from ABA ($15,380) |
