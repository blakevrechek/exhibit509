# Exhibit — Session Handoff

**Last updated:** 2026-05-31
**Repo:** `blakevrechek/exhibit509`
**Live:** https://exhibit509.com (Cloudflare Pages, auto-deploys from `main`)
**Current version:** `1.18.1` (see `VERSION`)
**`main` HEAD:** `57a21e3` — *Fix map down: leaflet.css SRI (CRLF→LF)*

---

## Roadmap / sequence (do these in order)

1. **Finalize the desktop** ← *we are here.* Last desktop items from the recent
   rounds are shipped; remaining desktop polish + the two live-browser checks
   below.
2. **Mobile.** Full mobile pass — layout, touch targets, the mobile menu/tab bar,
   panels, charts, and performance on a phone. Not started.
3. **Final data sweep.** Accuracy + integrity review of the dataset. **The user is
   currently rebuilding a "bulletproof" dataset in a separate Claude chat** — when
   that lands it replaces/validates the data files below, and this is the closing
   step. Hold major data-accuracy work until that arrives.

> Keep this order. Don't start mobile until desktop is signed off; don't do the
> data sweep until the user's rebuilt dataset is in hand.

---

## What this project is

A free, public viewer of **ABA Standard 509** disclosure data for every
ABA-accredited U.S. law school. Single-page app (vanilla JS, Leaflet map) plus
208 static per-school pages for SEO. Positioned around **"is law school worth
it?"** — outcomes, true cost, and 15-year trajectory.

Built by **509α**. Independent; not affiliated with the ABA.

---

## Architecture / where things live

| Path | What it is |
|---|---|
| `index.html` | The whole app — inline CSS + JS. ~376 KB raw / ~105 KB gzip. One big `<script>`. |
| `data/exhibit-data.js` | **Inline dataset** (`const S`, `BLS`, `RPP`, `FMR`). Loaded as a classic `<script src>` *before* the app script, so the globals are synchronously available. Current-cycle (2025) values + trends. 208 schools. |
| `data/exhibit_data.json.gz` | **Full 15-yr history**, lazy-loaded on first deep-dive (`loadFullDataset()` → `fetch` → `DecompressionStream('gzip')` → JSON, client-side). ~6 MB. |
| `vendor/leaflet/` | **Self-hosted Leaflet 1.9.4** (js, css, 5 marker images). Referenced with **SRI** + `crossorigin`. No more cdnjs. |
| `fonts/` | **Self-hosted** Nunito / Playfair Display / Geist Mono (latin woff2, content-hashed) + `fonts.css`. No Google Fonts. |
| `school/*.html` | 208 generated static pages (title/desc/canonical/OG/JSON-LD, indexable). |
| `scripts/build_school_pages.py` | Regenerates `school/*.html`, `sitemap.xml`, and injects the A–Z crawlable directory into `index.html`'s `<noscript>`. Reads `S` from `data/exhibit-data.js`. |
| `scripts/stamp_version.py` | **Single-source version stamper.** Reads `VERSION`, stamps `v<x.y.z>` into all HTML + the `sw.js` CACHE const. Run after bumping `VERSION`. |
| `_headers` | Cloudflare headers: CSP, HSTS, X-Frame-Options, cache rules. |
| `_redirects` | SPA rewrites (`/school/*`, `/compare/*`, `/match/*` → index 200) + legacy `/Exhibit/*` redirects. |
| `sw.js` | Service worker. App-shell precache (incl. data.js, fonts, Leaflet). Cache name carries the version. |
| `VERSION` | Single source of truth for the visible version string. |
| `manifest.json`, `robots.txt`, `sitemap.xml`, `llms.txt` | PWA + SEO/crawler metadata. |

### Build commands
```bash
python3 scripts/build_school_pages.py   # after any data change
python3 scripts/stamp_version.py        # after bumping VERSION
```

---

## Conventions / guardrails (learned the hard way)

- **Branch:** work on a `claude/desktop-round-N` branch, then fast-forward `main`
  (Cloudflare deploys `main`). User merges per round.
- **SRI + line endings:** `.gitattributes` now has `vendor/** -text` so EOL
  normalization can't silently change SRI-pinned bytes. **If you change any
  `vendor/` file, recompute its `sha512` and update the `integrity=` attr in
  `index.html`, then verify the *git-stored* blob hash matches** (not just the
  working tree). This is exactly what took the map down — see below.
- **No external CDNs.** Fonts + Leaflet are self-hosted; CSP only allows Carto
  tile images externally. Don't reintroduce cdnjs/Google Fonts.
- **Validate JS after editing `index.html`:** extract inline scripts and
  `node --check`. The dataset split means `S/BLS/RPP/FMR` come from
  `data/exhibit-data.js` — verify both load in a same-realm test if you touch boot.
- **No headless browser in this sandbox** — can't run axe/Lighthouse or render the
  map. Static checks only; **the user must confirm visual/behavioral things on the
  live deploy.**
- **Version drift:** never hand-type a version. Bump `VERSION`, run the stamper.

---

## Open items for DESKTOP (step 1)

**Needs a real browser (the user must run these on the live site):**
- [ ] **axe DevTools + Lighthouse a11y**, target **WCAG 2.1 AA**. Static audit was
      clean (all imgs now have alt; buttons/selects/inputs have names). Still need
      rendered-state checks: **contrast ratios, focus order, ARIA**. Keep the native
      `<select>` dropdowns for LSAT/GPA (intentional).
- [ ] **Lighthouse performance**, watch **LCP** (likely the map tiles or hero) and
      **HTML transfer size**. Measured gzip sizes: index ~105 KB, inline dataset
      ~272 KB (loads before app), Leaflet js 41 KB, 3× woff2 ~105 KB. No LCP number
      yet (no headless Chrome here).
- [ ] **Confirm the map fix deployed** — map renders with pins, console clean (no
      SRI/CSP errors). *This was just fixed; verify it's actually green.*

**Optional desktop polish (discuss with user):** none outstanding/blocking.

---

## Recent work (rounds 4–5, all merged to `main`)

Round 5 (latest):
- Self-hosted **Leaflet 1.9.4 + SRI**, dropped cdnjs; tightened CSP.
- Fixed yellow **LSAT/uGPA** chart lines unreadable on white in light mode.
- a11y: **alt text** on all images.
- **School-count reconciliation** — ⓘ tooltip by the map count (194 plotted ·
  197 reporting · 208 total incl. 11 closed/historical).
- **Single-source version** (`VERSION` + `stamp_version.py`) — killed v1.13/v1.16/
  v1.16.2 drift.
- **Map-down hotfix** (`57a21e3`): leaflet.css was committed CRLF, `* text=auto`
  normalized it to LF on commit, so served bytes ≠ the SRI hash (computed from the
  CRLF copy) → browser blocked the stylesheet → map collapsed. Fixed the hash,
  added `.gitattributes vendor/** -text`, bumped to 1.18.1.

Round 4: top-bar reposition, header style unification, removed AI tells (`//`
labels, arrows), light-mode yellow outlines, font globalization across themes,
footer trim, CSP + X-Frame-Options, print/copy-link on school pages, crawlable
A–Z directory, **dataset split out of HTML**, **"adjusted" trust badge** on
auto-sanitized cells, DOM-escape the search input, repositioning copy.

---

## DATA notes (for the final sweep, step 3)

- **Two data layers** must stay in sync: inline `data/exhibit-data.js` (current
  year) and `data/exhibit_data.json.gz` (full history). The user's rebuilt
  dataset should regenerate **both**.
- **Known seam:** ~4 inline-only **closed** schools (Charlotte, Hamline, Indiana
  Tech, William Mitchell-era) exist in `S` but **not** in the gz history —
  `getSchoolHistory(id)` returns null for them by design. Verify the new dataset
  preserves or documents this.
- **Counts:** 208 total · 207 with map coords · 11 closed → 197 active/reporting ·
  194 currently plotted (the ⓘ tooltip explains the subsets — keep it accurate if
  counts change).
- **"Adjusted" badge:** the scholarship "no-grant" share is re-derived
  (100 − Σ grant buckets) because the 509 source value is unreliable;
  `scholAdjusted()` flags cells where source vs derived differ ≥0.6pp. New data
  should be checked against this logic.
- **"Last synced May 31, 2026"** appears in copy — update when data is refreshed.
- Sources: ABA 509 (2011–2025), BLS OEWS attorney wages, BEA RPP, HUD Small Area FMR.

---

## Quick start for the next chat

1. `git fetch && git checkout main && git pull` — confirm HEAD is `57a21e3` (or later).
2. Confirm the map is live (user check).
3. We're on **step 1 (desktop)** → finish the two Lighthouse/axe checks above.
4. Then **step 2 (mobile)**.
5. Then **step 3 (final data sweep)** once the user's rebuilt dataset is ready.
