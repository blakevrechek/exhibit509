# Exhibit 509 — Session Handoff

**Last updated:** 2026-06-11
**Repo:** `blakevrechek/exhibit509` · **Live:** https://exhibit509.com (Cloudflare Pages, auto-deploys from `main`)
**On `main`:** `v1.94.0` (HEAD `1dd02e3`, squash of PR #70) — the full June 2026 tuition audit is LIVE.
**Working branch:** `claude/wonderful-pasteur-uxl4qq` — re-stacked clean on `origin/main` after the merge.
**Version sync:** `VERSION` is the single source of truth; `stamp_version.py` propagates it to the chrome HTML + `sw.js`.

## Session 2026-06-11 (v1.93.2 → v1.94.0) — tuition audit, master reconciliation, corrections framework

**Shipped to `main` in PR #70 (squash-merged).** All gated through `bash scripts/build.sh` (validator 0 errors).

### Data integrity
- **Parser fix** — `pipeline/extract.py` `clean_int`/`clean_float` now strip a leading straight/curly apostrophe (Excel text-marker) before parsing, so `'34073`-style cells coerce to a number instead of dropping to `$0`. Takes effect on the next source re-extract.
- **Per-term annualization** — the ABA switched to per-*term* tuition reporting ~2018. We display **annual** = ×2 (semester) or ×3 (quarter) of the per-term figure. De-oscillated Baylor (per-quarter ×3; 2022/23 nulled; +2026 $69,510), Texas, Cincinnati, Stanford. Confirmed display philosophy (owner ruling).
- **De-doubling** — Cornell, Ohio State, Campbell, Nevada-Las Vegas (Priority-2/Tier-2 from `audit_t2.xlsx`).
- **Master reconciliation** — cross-checked every tuition cell vs `Exhibit_509_Master.xlsx` (`Tuition & Fees` sheet, `FT_*_Annual_Final`). 207/210 matched; **>99% faithful** once the per-term unit is accounted for. Resolved the **21 genuine** discrepancies to owner/ABA values (Montana 2023–25, Texas Southern 2024, Indiana-Indianapolis 2017, Cornell 2019 → 67,748, Florida Coastal 2020 → 19,895 [was a doubling], South Carolina 2021 → 9,653, Florida State 2019, Oklahoma 2025). Evidence committed: **`master-reconciliation.md` / `.csv`**.
- **Detroit Mercy** — tuition cut: 2025 → $27,800 (res=nr); nonresident series mirrored to resident. *2023 & 2024 still carry the old ~$53–54k sticker — pending owner values.*
- Cleared the Montana/Oklahoma scalar-vs-trend **drift warnings**.

### Transparency framework (the visible "we correct and show our work" system)
- **Correction rings** — adjudicated chart points get an **amber hollow ring + hover note**. Driven by the `FIXES` registry in `index.html` (school id → trendKey → year → note), read by `lineChart` (wired on the panel tuition+enrollment and deep-dive enrollment charts).
- **Open-circle missing data** — a missing interior year is stored as an explicit `null` key (not omitted), so `lineChart` draws a dashed bridge + hollow "not reported" circle. Swept all schools (15 omitted gaps filled). `$0` years already render a floor open-circle via `zeroAsMissing`.
- **⚠ "Data corrected" banner** — on the school full page (in-app deep-dive `dp-corr` + static `school/*.html` `corr-banner`) for the **28** substantively-corrected schools. Sets: `CORRECTED` in `index.html`, `CORRECTED_IDS` in `scripts/build_school_pages.py` — **keep both in sync with `corrections.md`**.
- **Ledger** — every change logged old→new with reason in **`corrections.md`**.
- **Methodology** — `methodology.html#data-corrections` rewritten from "all edits reverted / mirrors ABA exactly" to the new **"correct, ring, and log"** policy (raw gz keeps the original).

### Content
- New **Explained** post (`blog.html#tuition-holes`): *"The holes in 15 years of 509 tuition data — and how we patched them."*
- **Nebraska** grant > resident tuition explained in methodology (grants are residency-pooled, scaled to the non-resident sticker — not a bug).

### Gotchas learned this session
- The owner's **`audit_t2.xlsx` (Tier-2 sheet) and `Exhibit_509_Master.xlsx` disagree** on a few cells (Cornell, Florida Coastal, South Carolina). The **master won** every time. Reconcile new audit sheets against the master before applying.
- The master's `FT_*_Annual_Final` holds **per-term** values for 2018–2020 — a naive diff shows ~1,200 false "mismatches" that are just the annual-vs-term unit. The reconciliation script's classifier handles this (`semester x2` / `quarter x3` / `per-credit`).

### Open / next
- **Detroit Mercy 2023 & 2024** — need owner values (cut era; currently ~$53–54k stale).
- **Bulk apostrophe recovery** — parser fix is in; awaiting the ABA 509 **source re-upload + re-extract** to recover the open-school $0 cells (Dayton, Washburn, UIC, Widener ×2, etc. — currently nulled/open-circle).
- **Closed schools** (Arizona Summit, Whittier, Valparaiso, Florida Coastal $0 years) stay missing — no recoverable source.
- If the `CORRECTED`/`FIXES` lists grow, regenerate the id set via a value-level diff vs `origin/main`.

## Prior session (v1.90.1 → v1.93.2)

### Live on `main` (PR #67 → 1.92.2, PR #68 → 1.92.3)
- **Data — "Cond. Schl. Offered"** raw conditional-scholarship count row (falls back to latest `cond_enter_trend` year).
- **Methodology — dataset-scale breakdown** ("How big is the dataset, exactly": ~2.44M non-null facts).
- **Direct-to-data links** — every key chart/section has a permanent `/school/<id>/<chart>` URL; 🔗 copy buttons; router scrolls + flashes the anchor.
- **Embeddable widgets** — standalone **`/embed.html`** renders one branded trend chart per school; `</>` button → iframe snippet with live preview. `_headers` scopes a framing relaxation to `/embed*` (detaches global `X-Frame-Options: DENY`, opens `frame-ancestors *`); `_redirects` adds `/embed/<school>/<chart>`.
- **Bluebook "Cite this data"** — page-level + per-chart citation popover.
- **Three value-add data modules** — `pipeline/add_outcome_metrics.py` promotes derived fields into `data/exhibit-data.js`:
  1. **Splitter index** — `splitter_lean` = national pctile rank(median LSAT) − rank(median GPA); per-school module w/ 15-yr trend + ranked `splitter-friendly-law-schools.html` pillar. HONEST framing: ABA data is *marginal, not joint* → NOT a measured admit rate (caveats on module, pillar, `methodology#splitter`).
  2. **Conditional-scholarship risk** — stripped % over recent window + Risk Factor badge (moderate ≥15%, high ≥33%). Drops impossible rows (`elim>enter`, e.g. SMU 2023), caps 100%, shows year span.
  3. **Real-world employment** — `emp_adj_pct` = reported FTLT − school-funded (`raw_emp.Funded_*` in the gz), charted vs reported.
- **consultants.html** — full **"Exhibit A"** rewrite; softened competitive absolutes; "Book a call" → `cal.com/blakev`.
- **terms.html §3.1** — Consultant / Exhibit A report limitation (informational, not advice; advisor verifies figures).
- **Consultant gate (server-side)** — **`functions/_middleware.js`** (Cloudflare Pages Function) does HTTP Basic Auth on `/consultants*`; HTML not served until authed. Password `sell` fallback; override via `CONSULTANTS_PASSWORD` env var. Page auto-reveals once past auth.

### Branch only — draft PR #69 (v1.93.0 → 1.93.2), NOT yet on `main`
- **Chart "Enlarge" affordance** — a `MutationObserver` wraps every `svg.lc` / `.st-wrap` chart and attaches an "⤢ Enlarge" badge — only on charts that actually zoom (div infographics excluded by design, so no false affordances).
- **Enlarge modal** actions: **Save · Print · Embed · Copy link · Close** (Embed/Copy-link appear when the chart has a per-school key; `window.__schoolId` set in `renderSchoolPage`).
- **Nav / IA** — removed **Methodology + Glossary** from the global header (standalone + SPA desktop + mobile drawer; footer/body links kept). New **"Reference & data indexes"** hub on the Blog. Data-index links KEPT in the SEO-page nav (PILLAR_NAV) for internal linking, per decision.
- **Header logo → map** — `logoHome()` tears down a school/compare overlay then shows the map (fixes `showMap()` leaving the school page on top).
- **"Blog" renamed to "Explained"** (label only; URL stays `/blog.html`).

## Open items / next session
- **Merge PR #69** to ship 1.93.x (chart enlarge, nav restructure, Explained) — currently draft, stacked on `main` @ 1.92.3.
- **Splitter caveat tone** — owner to confirm it's conservative enough; one wording call flagged: kept "a widely-used transparency tool" vs the deck's "best-known".
- **Embed framing** — verify a cross-origin `/embed.html` iframe actually loads on the live deploy (depends on Cloudflare honoring `! X-Frame-Options`).
- **Consultant password** — set `CONSULTANTS_PASSWORD` in Cloudflare to keep it out of the repo, then drop the `'sell'` fallback in `functions/_middleware.js`.
- **Cloudflare Web Analytics** — enable via dashboard automatic setup (cookieless, no code; chosen earlier this session).
- **Tuition audit** — list of schools to verify against source 509s handed off this session (see `tuition-audit.md` for prior cell-by-cell detail; the app already flags these as "under review" via `TUI_IRREGULAR` + the rule-based `tuiAnomalyReason`).
- Carried from before: F2 Rutgers identity case; the ~12 genuine tuition gaps; `enr_trend` ~1yr offset.

## Build / deploy quick-ref
- Bump `VERSION` → `bash scripts/build.sh` (validate_data → build_school_pages → stamp_version). Gate = `validate_data.py` 0 errors + inline-JS syntax (`vm.Script` per `<script>`).
- Data injectors (run with `--write` before build when data changes): `pipeline/build_curated_records.py`, `pipeline/add_outcome_metrics.py`.
- Push branch → draft PR → merge to `main` triggers the Cloudflare Pages deploy; SW cache-busts on the version bump.
- **Squash-merge norm** → a commit pushed *after* a PR merges needs its own PR (that's why the gate became PR #68 after #67).

---

## Prior session notes (2026-06-05)

**Last updated:** 2026-06-05
**Repo:** `blakevrechek/exhibit509`
**Live:** https://exhibit509.com (Cloudflare Pages, auto-deploys from `main`)
**Current version:** `1.49.0` (see `VERSION`)
**`main` HEAD:** `fbd5892` — *HANDOFF + version sync* (on top of `ea2c781`, per-state pages)
**Working branch:** `claude/sharp-maxwell-owNOk` (fast-forward merged into `main`)
**Version sync:** `VERSION` is the single source of truth; `stamp_version.py` propagates
it to all chrome HTML + `sw.js` (cache name + `?v=` dataset bust). Verified aligned at
`1.49.0` across index/methodology/terms/about/contact/glossary/blog + sw.js. Generated
SEO pages (school/state/pillar/directory) carry no version string by design.
**Tag pending:** `v1.49.0` is created locally but the CI sandbox can't push tags
(proxy 403). Owner: `git fetch && git push origin v1.49.0` (or cut a Release) so git
carries the version too. PRs #4/#5 closed 2026-06-05; ~12 stale `claude/*` branches
still need deleting by the owner (see Open follow-ups).

**Brand:** the product is **"Exhibit 509"**; **509α** is the publisher ("by 509α").
The domain is `exhibit509.com`, so brand and domain match.

> ⚠️ **Heads-up for next session — main auto-regenerates.** A CI job commits
> `chore: regenerate SEO static pages + sitemap [skip ci]` onto `main` after pushes.
> So `main` will be **ahead of your branch** when you go to merge. Workflow that
> worked: push branch → `git fetch origin main` → `git checkout main && git reset
> --hard origin/main` → `git merge --ff-only <branch>`; if ff fails, `git checkout
> <branch> && git rebase origin/main && git push --force-with-lease`, then ff main.

---

## Roadmap / sequence

Desktop, data check, mobile, brand all ✅. The product is now feature-rich; recent
work has been the **school full-page experience** (charts, projections, calculators,
glossary) and **polish**. The map/desktop foundations are stable.

> This doc tracks 1.28.0 → **1.49.0**. The detailed per-version log is under
> **"What shipped"** below; earlier sessions (≤1.27.x) are summarized at the bottom.

### Backlog / future ideas (not started)

- **Our own school ranking — S/A/B/C/D/F tier list** (owner idea, publicity hook;
  "everyone wants to rank everything," à la US News + tiermaker). Intended as a
  *later* project, likely a **blog post / shareable artifact** rather than a core
  app feature. Notes for whoever picks it up:
  - We already have every input to do it transparently: bar pass + vs-state, FTLT
    employment, BigLaw/clerkship mix, 3-yr net cost, $/outcome ratios, selectivity,
    trajectory. A composite tier score is very doable from `S`.
  - **Positioning tension to resolve first:** the site is explicitly *anti-opaque-
    rankings* (About: "We don't sell rankings… trajectory is information"). Any
    Exhibit 509 ranking must be the opposite of US News — **fully transparent
    methodology, free, reproducible, no paid placement** — or it undercuts the
    trust pitch. Frame as "here's the math, change the weights yourself" (an
    interactive weighted tiermaker) rather than a handed-down authority list.
  - Natural home: a `/rankings` or blog page + a shareable S–F tier graphic.

---

## What this project is

A free, public viewer of **ABA Standard 509** disclosure data for every
ABA-accredited U.S. law school. Single-page app (vanilla JS, Leaflet map) plus
208 static per-school pages for SEO. Positioned around **"is law school worth
it?"** — outcomes, true cost, and 15-year trajectory.

Brand: **Exhibit 509**, published by **509α**. Independent; not affiliated with the ABA.

---

## Architecture / where things live

| Path | What it is |
|---|---|
| `index.html` | The whole app — inline CSS + JS. One big `<script>`. ~217 KB of inline JS. |
| `data/exhibit-data.js` | **Inline dataset** (`const S`, `BLS`, `RPP`, `FMR`). Loaded as a classic `<script src>` *before* the app script, so the globals are synchronously available. Current-cycle (2025) values + trends. 208 schools. |
| `data/exhibit_data.json.gz` | **Full 15-yr history**, lazy-loaded on first deep-dive (`loadFullDataset()` → `fetch` → `DecompressionStream('gzip')` → JSON, client-side). ~6 MB. |
| `vendor/leaflet/` | **Self-hosted Leaflet 1.9.4** (js, css, 5 marker images). Referenced with **SRI** + `crossorigin`. No cdnjs. |
| `fonts/` | **Self-hosted** Nunito / Geist Mono (latin woff2) + `fonts.css`. No Google Fonts. **Playfair Display was PURGED (v1.30.6)** — `--serif` now points at the Nunito stack; don't reintroduce Playfair (owner disliked it). |
| `glossary.html` | Standalone crawlable glossary (43 terms, 5 sections). Generated once from the methodology chrome; hand-edit directly now. Linked in nav + sitemap. |
| `school/*.html` | 208 generated static pages (title/desc/canonical/OG/JSON-LD, indexable). |
| `scripts/validate_data.py` | **Data-integrity gate** (v1.48.2). Runs FIRST in `build.sh` + its own CI workflow (`validate.yml`); aborts on data-gen bug classes that have shipped before: constant-collapse (faculty=25), truncated trends vs gz, impossible values, inline↔trend drift. ERRORS fail the build; sentinel-0s / high-tuition are WARNINGS. |
| `scripts/build_school_pages.py` | Regenerates `school/*.html`, `sitemap.xml`, injects the A–Z crawlable directory into `index.html`'s `<noscript>`. Reads `S` from `data/exhibit-data.js`. |
| `scripts/stamp_version.py` | **Single-source version stamper.** Reads `VERSION`, stamps `v<x.y.z>` into all HTML + the `sw.js` CACHE const. Run after bumping `VERSION`. |
| `_headers` | Cloudflare headers: CSP, HSTS, X-Frame-Options, cache rules. |
| `_redirects` | SPA rewrites (`/school/*`, `/compare/*`, `/match/*` → index 200) + legacy `/Exhibit/*` redirects. |
| `sw.js` | Service worker. **HTML = network-first; same-origin assets = stale-while-revalidate; cross-origin = NOT intercepted** (see guardrails). Cache name carries the version. |
| `VERSION` | Single source of truth for the visible version string. |
| `manifest.json`, `robots.txt`, `sitemap.xml`, `llms.txt` | PWA + SEO/crawler metadata. Icons are `icon192.png` / `icon512.png` (NO hyphen). |

### Build commands
```bash
bash scripts/build.sh                   # one-shot: regen school pages + sitemap,
                                        # stamp_counts(), stamp_version() — run after
                                        # ANY data/content/VERSION change
python3 scripts/indexnow_ping.py        # AFTER the deploy is live (recrawl ping)
```
`build.sh` wraps the individual steps; you rarely need them alone:
```bash
python3 scripts/build_school_pages.py   # regen school/*.html + sitemap from data
python3 scripts/stamp_version.py        # stamp v<x.y.z> across HTML + sw.js
# stamp_counts() (inside build.sh) derives 208/197/11 from the dataset and stamps
# index.html + methodology.html so the totals can never disagree.
```

---

## Conventions / guardrails (learned the hard way)

- **Branch + ship:** work on the session branch (this session:
  `claude/sharp-maxwell-owNOk`), then fast-forward merge into `main` and push —
  Cloudflare deploys `main`. After merging, verify `main`'s tree == branch tip's.
  Tag each release `git tag -a vX.Y.Z` + `git push origin vX.Y.Z` so git, `VERSION`,
  and the stamped files agree (tag push must run outside the CI sandbox — proxy 403).
- **No em dashes** in user-facing prose — use commas/colons. (House style; checked
  each ship with `grep -c "—"`.)
- **Brand strings:** product = "Exhibit 509", publisher = "509α". Generated school
  pages get `| Exhibit 509`; don't hand-edit `school/*.html` — change the template
  in `build_school_pages.py` and rebuild.
- **Counts are generated, never hand-typed** — edit the dataset, run `build.sh`,
  let `stamp_counts()` propagate to index + methodology.
- **Data integrity over completeness.** We do NOT fabricate values: impossible 0s
  are nulled (Belmont fix), ambiguous tuition is flagged not invented, projections
  are clearly labeled model output (logit/CAGR/OLS), not forecasts. Keep that bar.
- **No Playfair Display** — purged in 1.30.6; `--serif` = Nunito stack. Owner
  dislikes the decorative serif. Don't reintroduce it.
- **Charts are click-delegated.** A single document-level `chartZoom` opens any
  `svg.lc`/`.st-wrap` in a branded modal. New trend charts get zoom + projection
  for free via `lineChart`/`bandChart` (pass `project:{n:4,mode:'rate'|'mult'|
  'linear'}`); they're touch-aware via `lcTip`.
- **Service worker, cross-origin:** **the SW must NEVER intercept cross-origin
  requests.** It returns early when `url.origin !== location.origin`. Leaflet map
  tiles (`*.basemaps.cartocdn.com`) are `no-cors`/opaque; routing them through the
  SW caused `NS_ERROR_INTERCEPTION_FAILED` in Firefox and a **gray basemap**. This
  was THE root cause of the whole gray-map saga — not sizing, not CSP. Don't
  reintroduce cross-origin handling in `sw.js`.
- **Service worker, HTML:** HTML navigations are **network-first** so a refresh
  always gets the live shell (avoids serving a stale page). Versioned same-origin
  assets stay stale-while-revalidate. Any SW change needs **one hard-reload** on
  the live site to install before it takes effect.
- **stamp_version.py SVG safety:** the version-token regex has a negative
  lookbehind `(?<![A-Za-z0-9.])` so it can't rewrite SVG path coords like `v1.7`.
  Before that fix it silently corrupted the LinkedIn/Facebook share-icon paths on
  every bump. If you touch the stamper, keep that guard. Sanity check after
  stamping: `grep -c "h3v1.7c" index.html contact.html` should stay `1` each.
- **SRI + line endings:** `.gitattributes` has `vendor/** -text` so EOL
  normalization can't change SRI-pinned bytes. If you change any `vendor/` file,
  recompute its `sha512`, update `integrity=` in `index.html`, and verify the
  *git-stored* blob hash matches (not just the working tree). This took the map
  down once (CRLF→LF).
- **No external CDNs.** Fonts + Leaflet self-hosted. CSP only allows Carto tile
  *images* externally (`img-src ... https://*.basemaps.cartocdn.com`). The CSP is
  correct — it was wrongly suspected during the gray-map debugging.
- **Validate JS after editing `index.html`:** extract the big inline script and
  `node --check` it. (One-liner used all session: regex out the largest
  `<script>` without `src`, write to /tmp, `node --check`.)
- **No headless browser in this sandbox** and **no outbound network** (egress is
  blocked — even curling Carto/example.com returns 403). Static checks only;
  **the owner must confirm anything visual/behavioral on the live deploy.**
- **Version drift:** never hand-type a version. Bump `VERSION`, run the stamper.

---

## What shipped (1.28.0 → 1.49.0)

**1.49.0** — **per-state SEO landing pages** (`build_state_pages`): 51
`{state}-law-schools.html`, ranked by first-time bar (FTLT + tuition), current
chrome + "E" favicon, CollectionPage/ItemList + breadcrumb JSON-LD; linked from the
`/schools.html` directory + sitemap. Re-implemented cleanly instead of merging the
stale PR #4. Stale PRs #4/#5 closed; dead branches flagged for deletion.
**1.48.x** — **data-validation CI gate** (`validate_data.py`, runs first in
`build.sh` + `validate.yml`: constant-collapse, truncated-trend, impossible-value,
inline↔trend-drift; it caught + fixed 127 faculty-trend gaps); **projection refine**
(cone half-width capped 35%, money floored at 0, dashed edges); **global tuition
Y-scale** (0 → 98th-pct ceiling so all schools compare); **compare composition bars**
(sex/race/faculty) + **Letter (8.5×11) print/share**; **outcome-funnel + faculty
100% stacks**; LSAT/uGPA + tuition/scholarship history backfilled from gz.
**1.46.x** — full-width school page + bigger charts + click-to-enlarge prompt;
10/5/3/2-yr trailing-change badges; absolute employment head-count stack.
**1.45.x** — **dataset cache-bust** (`?v=<VERSION>` on `exhibit-data.js`, the fix
for stale faculty/LSAT persisting via the SW); Trends/history loader hardened
(handles CDN-decompressed gz); funny 404; **"E" monogram favicon**; global header
split (features vs writings); blueprint bg; print readout rebuilt; `blog.html`.

**1.28.0** — review fixes: OBBBA federal-loan cliff modeled in Net Price (live
warning at 2026 caps $50k/yr·$200k lifetime); "0 schools" verified not-a-bug;
school pages corrected to 15-yr; `stamp_counts()` (208/197/11) so counts can't
drift; bar-passage "different cohorts" caveat on every school page.
**1.29.0** — rebrand to **Exhibit 509** (509α = publisher) everywhere; About
trust/funding section; mobile fix (school overview above the fixed header).
**1.29.1–.3** — removed the orange accent bar atop "Match Me"; map color-metric
caption (`.ms-eyebrow`) → readable sans (was mono-caps); `.sp-intro` de-italicized.
**1.29.2** — chart Y-axis headroom (`niceTicks` padded ~7%) so peak points/labels
never clip.
**1.30.0** — **dense grouped compare mega-table** (`CMP_GROUPS`, ~58 rows × 6
sections) + the **LSAT/uGPA 0-sentinel fix** (impossible 0s nulled at load AND in
the generator: Belmont 2012, Arizona Summit, Whittier, Florida Coastal, Valparaiso).
**1.30.1–.8** — desktop-density on the school view; tiles fill width (`auto-fill`→
`auto-fit`); graph crosshair tooltip (hover **+ touch** via `lcTip`, all series);
**Playfair purged → Nunito** (1.30.6, `@font-face` removed too); dotted-grid bg on
standalone pages; **orange "Back to Exhibit" buttons**; sticky school-view top bar.
**1.31.0** — **tuition corrections**: 4 unambiguous semester/annual errors fixed in
data (Chicago 2018, Indiana–Indianapolis 2017, Detroit Mercy 2025, Montana 2023);
15 schools flagged `TUI_IRREGULAR` ("under review" callout) instead of fabricating;
documented in `methodology.html#data-corrections`. (Audit: `tuition-audit.md`.)
**1.32.0 / 1.33.0** — **band charts** (`bandChart`): LSAT/uGPA 25–75 percentile
bands; bar-passage first-time→ultimate band; tuition resident→non-resident band.
"At a glance" compressed.
**1.34.0** — **employment over time**: big stacked composition (gz history) + a
**dropdown** to chart any single category (`empCatPaint`, defaults FTLT).
**1.35.0** — compare gets an **employment-over-time** dropdown (`paintCompareEmpEvo`/
`cmpEmpCatPaint`); single-school **demographics dropdown**; **print padding** fix
(16/14mm + reflow so nothing clips).
**1.36.0** — **state legal-market** pulled into its own section (`sec('market',…)`):
BLS salary band + RPP + rent.
**1.37.0** — **4-year projections on all trend charts** (`projectFit` + `project`
hook on lineChart/bandChart): logit-linear for rates, CAGR for money, OLS else;
dashed line + uncertainty cone + "projected →" divider; caveat + `methodology.html
#projections`. Framed as model output, NOT fact.
**1.38.0** — **loan-payoff calculator** (`loanCalcWidget`/`loanPayoffUpdate`):
borrowed + monthly + rate sliders → payoff time, total paid, interest.
**1.39.0** — **bimodal salary** explainer (`salaryDist`): BLS percentile bar +
NALP two-hump context.
**1.40.0** — **glossary.html** (43 terms) + nav/sitemap.
**1.41.0** — chart sizes up; LSAT yellow → goldenrod `#D6A520` (legible both
themes) + adj-flag border removed; school column centered (`.dp-wrap` 1720→1360);
**version string in footers** (auto-stamped after "Last synced").
**1.42.0** — branded **"509α" no-school hero** (the empty overview state) + "At a
glance" cut to a single 7-tile row.
**1.43.0** — **#7 click-to-zoom charts**: event-delegated `chartZoom` → full-screen
branded modal with cited source; **"New tab"** (`openChartTab`) serializes the
chart to a standalone branded HTML page (blob URL).
**1.45.0** — **faculty-trend data fix**: every school's `fac_trend["2025"]` was a
corrupted constant `25` (the series is *full-time* faculty = gz `fac_ft`, not
total); repaired all 186 wrong values from the authoritative gz `fac_ft`, relabeled
the chart "Total faculty" → "Full-time faculty" (the 9 remaining 25s are genuinely
small schools). **Curriculum & program mix over time** (`CURRIC_BUCKETS` +
`curricYear`/`curricNormHistory`, painted into `#curric-evo-slot`; normalizes the
shifting ABA `raw_curric` schemas → clinics/field/simulation/seminars/co-curricular
stacked per year). **Blog** (`blog.html`, writings placeholder with 3 starter posts;
in sitemap + version stamper). **Global header split** — interactive *features* on
the left, the *writings* (Blog/Methodology/Glossary/About/Contact) pushed right
behind a hairline (`.h-nav-grp`/`.h-nav-writ`; mirrored on standalone pages'
`.gh-nav`). **Subtle blueprint grid** background on the school full page
(`#schoolPage`, 24px minor + 120px major, both themes). **Print readout rebuilt**
to match the story-sec/story-mod layout: collapses masonry to one column, keeps
charts whole, hides every interactive-only control (dropdowns, loan sliders, zoom),
and prints a branded `.dp-print-head`. (Sex/race historic stacks + per-year
employment stack + outcome funnel already shipped in 1.44.0.)
**1.44.0** — gender composition over time (`SEX_BUCKETS`); curriculum bars
(`curriculumBars`) + faculty-total trend; **transfers own module** (in/out + net +
transfer-GPA band + trend); always-on **"JD jobs over time"** line under the
employment bars.

### Key functions added (all in `index.html` inline JS)
`bandChart` · `projectFit` + `projDrawSeries` (projection engine) · `lcTip`
(chart touch) · `chartZoom`/`openChartTab` (chart modal, delegated on document
click) · `empCatPaint` + `paintEmpEvolution` · `demoCatPaint` · `cmpEmpCatPaint`/
`paintCompareEmpEvo` · `loanCalcWidget`/`loanPayoffUpdate` · `salaryDist` ·
`curriculumBars` · `schoolSnapshot` (now one concise row). Buckets: `EMP_BUCKETS`,
`EMP_CAT_LIST`, `RACE_BUCKETS`, `DEMO_CAT_LIST`, `SEX_BUCKETS`. `TUI_IRREGULAR` map.

### Open follow-ups
- **Owner actions pending (sandbox can't do these — proxy 403):**
  (1) **Push tag `v1.49.0`** — created locally, not on origin. `git push origin v1.49.0`
  or cut a Release. (2) **Delete dead branches** — PRs #4/#5 are CLOSED, but the ~12
  stale `claude/*` branches still exist; delete from the GitHub Branches page (keep
  `main` + the active session branch).
- **3 validation warnings** (non-blocking, surfaced by `validate_data.py`): 54
  LSAT/uGPA 0-sentinels still stored (nulled at runtime — could null in data);
  1 high tuition (Cornell 2019 ~$126k historic outlier); 2 schools' current `tui`
  differ slightly from their `tui_trend` latest (oklahoma, montana). Owner can
  verify/clean when convenient.
- **Improvement backlog (proposed, not started):** SW "update available" toast;
  a small test suite (chart helpers + data invariants) in CI; Lighthouse perf +
  axe a11y pass; render key figures into static pages for SEO; real blog content;
  the transparent reweightable S–F tier-ranking.
- **`tuition-audit.md`** lists 15 flagged schools (multi-year level shifts, likely
  real 2014–15 resets) the owner is researching. When verified, correct in
  `data/exhibit-data.js` (object-scoped string replace; mind `"YYYY": N` spacing &
  private-school `nrt` mirrors) and drop from `TUI_IRREGULAR`.
- **Projections** are linear/CAGR/logistic on each school's own history — clearly
  labeled non-forecasts. If asked to harden, that's the place.
- **Backlog: S/A/B/C/D/F tier ranking** (see Backlog section) — still not started.
- Run `indexnow_ping.py` after deploys with new/changed pages (glossary etc.).

---

## Earlier session (on `main`, 1.18.1 → 1.19.5)

- **Map color layers (left panel).** Replaced the floating bottom-right legend
  (it kept colliding with the Overview panel) with a **"Color the map by"** control
  inside the left panel. Multi-select **up to 3** metric layers; `MAP_LAYERS[0]`
  is the **primary** and colors the pins (numbered badges on the rest). Clicking
  an active layer promotes it; × drops a secondary. `window.MAP_METRIC` is now a
  **getter aliasing the primary**, so legacy callers keep working. Pin tooltips
  list all active layers; the school Overview has an "Active map layers" readout.
  **Firm-size + sector groups are collapsed behind a "+ More metrics" expander**
  (only the 3 Outcomes metrics show by default) to keep the panel calm.
- **Subset filters = single-select.** All / National / Regional / Local / Bar≥90 /
  Under $35K / My Safeties / Targets / Reaches narrow the map one at a time
  (`currentMF`). (These briefly went multi-select+AND, then reverted per owner —
  the panel felt too busy.)
- **Removed** the "207 schools shown" map-count chip; tightened the hero subhead;
  hid the left-panel scrollbar (`.ip-body`).
- **Footer/header email cleanup:** removed the footer logo/"Exhibit by 509α"
  wordmark and the header + footer "Sign up for email updates" links; renamed the
  Google-form links to **"Email list"** (footer, full-profile modal, mobile menu).
- **Gray-map saga — fully fixed (the big one).** Symptoms ranged "partial on first
  load" → "gray on refresh". Tried `invalidateSize` timing + a `ResizeObserver`
  (both kept, both reasonable), but the **actual** root cause was the SW
  intercepting cross-origin Carto tiles → `NS_ERROR_INTERCEPTION_FAILED` → no
  tiles. Fix: SW returns early on cross-origin. Also made HTML network-first.
- **Icon 404s:** manifest / apple-touch-icon / JSON-LD referenced
  `icon-192/512.png` (hyphen) but files are `icon192/512.png`. Fixed.

---

## Optional desktop audits (NOT blocking — owner runs on live site)

- [ ] **axe DevTools + Lighthouse a11y** (WCAG 2.1 AA): contrast, focus order,
      ARIA. Static audit was clean. Keep native `<select>` for LSAT/GPA.
- [ ] **Lighthouse performance** — watch LCP (map tiles/hero) + HTML transfer size.
- [ ] **Confirm gray-map fix on live** — hard-reload once (to install the new SW),
      then plain-refresh a few times: basemap should load and stay. In Network,
      `cartocdn` tiles should be **200**, not `NS_ERROR_INTERCEPTION_FAILED`.

---

## DATA notes (for step 2, the data check — NEXT)

- **Two data layers must stay in sync:** inline `data/exhibit-data.js` (current
  year + the `*_trend` series, **2011–2025**) and `data/exhibit_data.json.gz`
  (`getSchoolHistory(id)` → `rec.history`, per-year, **~2018–2026**). Rebuild
  regenerates **both**, then `build_school_pages.py`.
- **gz `history` is RICH (corrected note):** earlier handoffs wrongly said it was
  "bar only" — that was from sampling the latest year (2026), which only has bar
  data (employment reporting lags ~1yr). Across all years it carries **employment
  mix, race, sex, grants $, resident/non-res tuition, faculty, transfers, etc. per
  year**. The employment/demographics/sex over-time charts read from it. It parses
  with `NaN`→null. The 15-yr `*_trend` series (LSAT/GPA/bar/tuition/acc/apps/enr/
  fac/trans) live inline; richer composition history is gz-only (≈2018+).
- **Known seam:** ~4 inline-only **closed** schools (Charlotte, Hamline, Indiana
  Tech, William Mitchell-era) exist in `S` but **not** in the gz history —
  `getSchoolHistory(id)` returns null for them by design. Verify the new dataset
  preserves or documents this.
- **Counts:** 208 total · 207 with map coords · 11 closed → 197 active/reporting ·
  194 currently plotted. (The old ⓘ count tooltip was REMOVED this session, so
  there's no longer an on-map count to keep in sync — but the `S` array still
  drives `build_school_pages.py` and the `<noscript>` directory.)
- **"Adjusted" badge:** scholarship "no-grant" share is re-derived
  (100 − Σ grant buckets) because the 509 source value is unreliable;
  `scholAdjusted()` flags cells where source vs derived differ ≥0.6pp. Check new
  data against this logic.
- **"Last synced May 31, 2026"** appears in copy + school pages — update when data
  is refreshed (it's part of the version-stamp era but is NOT auto-stamped).
- Sources: ABA 509 (2011–2025), BLS OEWS attorney wages, BEA RPP, HUD Small Area FMR.

---

## Quick start for the next chat

1. `git fetch && git checkout main && git reset --hard origin/main` — confirm HEAD
   is `66ca857` (or later, incl. the CI auto-regen commit), `VERSION` is `1.49.0`.
2. **Edit `index.html` inline JS → `node --check` it** (extract largest `<script>`
   without `src`). Bump `VERSION`, run `bash scripts/build.sh` — which now runs
   `validate_data.py` FIRST (aborts on data errors), then regen + counts + stamp.
   Validate JSON-LD if you touched it. No em dashes. Tag the release + push it.
3. **Ship + reconcile main** (it auto-regenerates — see the heads-up box at top):
   push branch; `git checkout main && git reset --hard origin/main`; `git merge
   --ff-only <branch>`; if ff fails, rebase branch on origin/main, force-with-lease,
   then ff main. Hard-reload live once to install the new SW.
4. After deploys with new/changed pages: `python3 scripts/indexnow_ping.py`.
5. **Real-device pass recommended** on a rich school (e.g. Michigan): projection
   cones, click-to-zoom charts (+ New tab), loan sliders, bimodal bar, employment/
   demographics dropdowns, the 509α no-school hero.
6. Owner to verify the **15 flagged tuition schools** (`tuition-audit.md`) against
   the 509 source, then patch + de-flag.
