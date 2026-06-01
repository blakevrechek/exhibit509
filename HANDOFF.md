# Exhibit — Session Handoff

**Last updated:** 2026-06-01
**Repo:** `blakevrechek/exhibit509`
**Live:** https://exhibit509.com (Cloudflare Pages, auto-deploys from `main`)
**Current version:** `1.19.5` (see `VERSION`)
**`main` HEAD:** `b1ef3a3` — *Merge: fix gray map (SW cross-origin) + icon 404s*
**Working branch:** `claude/vibrant-keller-IdnyW` (currently == `main`'s content)

---

## Roadmap / sequence (UPDATED — order changed by owner)

1. **Desktop** — ✅ effectively done. Map layers/filters reworked, footer/header
   cleaned, the gray-map bug is finally root-caused and fixed. Only the optional
   live-browser audits below remain (axe/Lighthouse), and they're not blocking.
2. **Data check** ← *NEXT.* Owner is doing an accuracy/integrity pass on the
   dataset. See **DATA notes** below. (Owner was rebuilding a "bulletproof"
   dataset in a separate chat — confirm whether that has landed before editing
   data by hand.)
3. **Mobile.** Full mobile pass — layout, touch targets, mobile menu/tab bar,
   the bottom-sheet school panel, charts, perf on a phone. Not started.

> Note: this reorders the old plan (was desktop → mobile → data). Owner now wants
> **data check before mobile.**

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
| `index.html` | The whole app — inline CSS + JS. One big `<script>`. ~217 KB of inline JS. |
| `data/exhibit-data.js` | **Inline dataset** (`const S`, `BLS`, `RPP`, `FMR`). Loaded as a classic `<script src>` *before* the app script, so the globals are synchronously available. Current-cycle (2025) values + trends. 208 schools. |
| `data/exhibit_data.json.gz` | **Full 15-yr history**, lazy-loaded on first deep-dive (`loadFullDataset()` → `fetch` → `DecompressionStream('gzip')` → JSON, client-side). ~6 MB. |
| `vendor/leaflet/` | **Self-hosted Leaflet 1.9.4** (js, css, 5 marker images). Referenced with **SRI** + `crossorigin`. No cdnjs. |
| `fonts/` | **Self-hosted** Nunito / Playfair Display / Geist Mono (latin woff2, content-hashed) + `fonts.css`. No Google Fonts. |
| `school/*.html` | 208 generated static pages (title/desc/canonical/OG/JSON-LD, indexable). |
| `scripts/build_school_pages.py` | Regenerates `school/*.html`, `sitemap.xml`, injects the A–Z crawlable directory into `index.html`'s `<noscript>`. Reads `S` from `data/exhibit-data.js`. |
| `scripts/stamp_version.py` | **Single-source version stamper.** Reads `VERSION`, stamps `v<x.y.z>` into all HTML + the `sw.js` CACHE const. Run after bumping `VERSION`. |
| `_headers` | Cloudflare headers: CSP, HSTS, X-Frame-Options, cache rules. |
| `_redirects` | SPA rewrites (`/school/*`, `/compare/*`, `/match/*` → index 200) + legacy `/Exhibit/*` redirects. |
| `sw.js` | Service worker. **HTML = network-first; same-origin assets = stale-while-revalidate; cross-origin = NOT intercepted** (see guardrails). Cache name carries the version. |
| `VERSION` | Single source of truth for the visible version string. |
| `manifest.json`, `robots.txt`, `sitemap.xml`, `llms.txt` | PWA + SEO/crawler metadata. Icons are `icon192.png` / `icon512.png` (NO hyphen). |

### Build commands
```bash
python3 scripts/build_school_pages.py   # after any data change
python3 scripts/stamp_version.py        # after bumping VERSION
```

---

## Conventions / guardrails (learned the hard way)

- **Branch + ship:** work on `claude/vibrant-keller-IdnyW`, then merge into `main`
  (`git merge --no-ff`) and push — Cloudflare deploys `main`. After merging,
  verify `main`'s tree == branch tip's tree exactly. (PR #2 is merged/closed; new
  work just goes branch → main directly per owner's "direct fast-forward".)
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

## What shipped THIS session (all on `main`, 1.18.1 → 1.19.5)

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
  year) and `data/exhibit_data.json.gz` (full history). A rebuilt dataset should
  regenerate **both**, then run `build_school_pages.py`.
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

1. `git fetch && git checkout main && git pull` — confirm HEAD is `b1ef3a3` (or later),
   `VERSION` is `1.19.5`.
2. Confirm the gray-map fix is green on live (hard-reload once, then refresh).
3. **Step 2: data check** — see DATA notes. Confirm whether the rebuilt dataset
   has landed before hand-editing. Regenerate both data layers + run
   `build_school_pages.py`, bump `VERSION`, run `stamp_version.py`.
4. **Step 3: mobile pass.**
5. Ship: branch → `git merge --no-ff` into `main` → push. Hard-reload to pick up
   any new SW.
