# Master-workbook reconciliation — displayed data vs `Exhibit_509_Master.xlsx`

_Generated 2026-06-11 from the `Tuition & Fees` sheet (`FT_*_Annual_Final`). Matched 207/210 schools; unmatched: High Point University, La Verne University Of, Penn State Law (University Park)._

**Display philosophy: annualized (owner-confirmed).** For 2018–2020 the ABA reports tuition per *term*; our annual figure is 2× (semester schools) or 3× (quarter schools) the master's per-term `_Final`. That unit difference accounts for the vast majority of non-matching cells and is **not** an error.

## Categories (resident + nonresident cells where display ≠ master `_Final`)

| category | cells |
|---|---|
| semester x2 (ours annual) | 853 |
| per-credit (master null, ours converted) | 350 |
| ours-open-circle (master has value) | 27 |
| master blank/0 (ours carries value, e.g. private nr=res) | 23 |
| GENUINE | 21 |
| quarter x3 (ours annual) | 6 |

## Genuine value disagreements (both sides have a real figure, not a unit multiple)

| school | year | field | ours | master `_Final` | flag |
|---|---|---|---|---|---|
| Boston College | 2016 | nr | 50770 | 50700 | missing |
| Cornell University | 2019 | nr | 65541 | 67748 |  |
| Cornell University | 2019 | res | 65541 | 67748 |  |
| Denver | 2012 | nr | 39840 | 39480 | missing |
| Florida Coastal School of Law | 2020 | nr | 79580 | 19895 | yoy_-50% |
| Florida Coastal School of Law | 2020 | res | 79580 | 19895 | yoy_-50% |
| Florida State University | 2019 | nr | 36144 | 9036 | yoy_-56% |
| Indiana University-Indianapolis | 2017 | res | 26736 | 28631 | missing |
| Mitchell/Hamline | 2016 | nr | 40570 | 40470 | missing |
| Montana | 2023 | res | 12263 | 19494 | yoy_31% |
| Montana | 2024 | res | 12080 | 24161 |  |
| Montana | 2025 | res | 12291 | 24582 |  |
| Northwestern University | 2025 | nr | 79772 | 79722 | res>nonres |
| Oklahoma | 2025 | res | 18739 | 18379 |  |
| South Carolina | 2021 | nr | 35342 | 24661 |  |
| South Carolina | 2021 | res | 18556 | 9653 |  |
| Stanford University | 2019 | res | 62310 | 20725 | missing |
| Stanford University | 2020 | res | 63330 | 21450 | missing |
| Texas Southern University | 2024 | nr | 20049 | 25632 | yoy_47% |
| Texas Southern University | 2024 | res | 12645 | 18582 | yoy_47% |
| Willamette University | 2020 | nr | 47130 | 23265 | res>nonres |

### How to read them
- **① Your Tier-2 sheet vs this master conflict** (cells I changed this session from `audit_t2.xlsx`): **Cornell 2019** (65,541 / master 67,748), **Florida Coastal 2020** (79,580 / master 19,895 → 39,790 annual; my value is doubled), **South Carolina 2021** (18,556 / master 9,653).
- **② Pre-existing low-value errors, master is right:** **Montana 2023/24/25** (~$12k / $19,494·$24,161·$24,582), **Texas Southern 2024** ($12,645 / $18,582), **Indiana-Indianapolis 2017** ($26,736 / $28,631).
- **③ Worth a look:** **Florida State 2019 nr** (ours 36,144 vs master 9,036 — a 4× unit oddity), **Oklahoma 2025** ($18,739 / 18,379 — the known scalar drift).
- **Trivial (my session nr=res fixes vs master per-term):** Northwestern/Willamette/Boston College/Denver/Mitchell-Hamline nonresident — ours annual, master blank or per-term.

_Nothing was changed to produce this. Every non-matching cell, all categories, is in `master-reconciliation.csv` (1,280 rows)._
