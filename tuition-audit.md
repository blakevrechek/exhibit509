# Tuition anomaly audit — `tui_trend` scan

Scanned all 208 schools' year-by-year tuition for moves outside normal inflation
(flag: any YoY change **> +18%** or **< −10%**, and ≥ $2k). Real tuition almost
never moves that fast, so each flag is a candidate for the **semester-reported-as-
annual** (or vice-versa) error you called out — or a transcription glitch.

**Nothing was auto-changed.** Verify each against the original ABA 509 disclosure,
then tell me which to correct and I'll patch `tui_trend` (and rebuild).

Legend: `'YY:$NNk` is that year's reported full-time tuition.

---

## A. High confidence — looks like a real error

| School | Bad year | What I see | Likely truth |
|---|---|---|---|
| **Chicago, University of** | **2018 = $44k** | `'16:$61k '17:$63k '18:$44k … '23:$76k` | A drop to $44k between $63k and $76k is not real — likely a mis-keyed/partial figure. Should be ~$64–66k. |
| **Indiana U–Indianapolis** | **2017 = $14k** | `'16:$26k '17:$14k … '24:$29k` | Single-year halving that reverts → classic **semester figure**. Should be ~$27k. |
| **Detroit Mercy** | **2025 = $28k** | `'23:$53k '24:$55k '25:$28k` | −49% in one year → likely **one semester reported**. Should be ~$56k. |
| **Baylor University** | **2018 = $42k**, **2024 = $65k**, **2025 = $47k** | `'17:$60k '18:$42k … '23:$43k '24:$65k '25:$47k` | Multiple swings; the whole 2018–2025 run looks inconsistent (semester/annual mixed). Needs a full re-pull. |
| **Texas Southern** | **2023–24 = $13k** | `'18:$20k '23:$13k '24:$13k '25:$19k` | The $13k years look like a **semester/partial** dip; ~$19–20k is the trend. |
| **Tulsa, University of** | **2017 = $25k** (persists) | `'16:$38k '17:$25k '18:$25k … '23:$29k` | $38k→$25k step that stays — could be a real tuition reset OR a switch to a different rate. Verify. |

## B. Medium — single-year dip that reverts (probable error)

| School | Bad year | Series |
|---|---|---|
| **Ohio Northern** | 2014 = $25k (from $34k, persists low then back to $34k) | `'13:$34k '14:$25k … '23:$34k` |
| **Roger Williams** | 2014 = $34k | `'13:$42k '14:$34k '15:$35k …` |
| **Brooklyn Law** | 2015 = $46k | `'14:$54k '15:$46k '16:$46k '17:$51k` |
| **Montana, University of** | 2023 = $19k (spike) | `'18:$13k '23:$19k '24:$12k '25:$12k` — the **2023 $19k** is the outlier, not 2024 |
| **Iowa, University of** | 2014 = $24k | `'13:$28k '14:$24k '15:$24k …` |
| **Texas A&M** | 2016 = $28k | `'15:$33k '16:$28k '17:$29k …` |

## C. Lower — abnormal but possibly real (rapid increases, new schools)

| School | Year(s) | Note |
|---|---|---|
| North Carolina Central | 2015 (+28%), 2016 (+20%) | public school ramp; could be real |
| Mississippi | 2013 (+19%) | public; plausible |
| Elon | 2015 (−12%), 2018 (+21%) | volatile; verify |
| Howard | 2017 (−10%) | mild |
| Toledo | 2015 (−12%) | mild |
| Arizona | 2013 (−11%) | mild |
| North Texas–Dallas | 2025 (−15%) | new school, short series |

---

### Method note
Scan logic: for each school, walk consecutive reported years (skipping multi-year
gaps); flag a year when tuition ÷ prior-year ≥ 1.18 or ≤ 0.90 with an absolute
change ≥ $2,000. Tightening to the strict "≈2× / ≈½" swap (the textbook
semester/annual error) yields just three: **Indiana–Indianapolis 2017**,
**Detroit Mercy 2025**, **Montana 2024** — those are the safest auto-fix
candidates if you want to start there.
