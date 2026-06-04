# Exhibit 509 — Session Handoff

**Last updated:** 2026-06-03
**Repo:** `blakevrechek/exhibit509`
**Live:** https://exhibit509.com (Cloudflare Pages, auto-deploys from `main`)
**Current version:** `1.29.0` (see `VERSION`)
**`main` HEAD:** `3cb8579` — *Rebrand to "Exhibit 509", trust/funding line, mobile fix*
**Working branch:** `claude/elegant-lovelace-0awdY` (fast-forward merged into `main`)

**Brand:** the product is **"Exhibit 509"**; **509α** is the publisher ("by 509α").
The domain is `exhibit509.com`, so the brand and domain now match.

---

## Roadmap / sequence

1. **Desktop** — ✅ done. Map layers/filters reworked, header/footer cleaned,
   gray-map bug root-caused and fixed. Optional live audits below remain (not blocking).
2. **Data check** — ✅ landed. Counts are now build-generated (208 / 197 / 11) and
   stamped, so index + methodology can't drift. See **DATA notes**.
3. **Mobile** — in progress, iterating on real-device reports. Latest: school
   overview now renders in front of the fixed header so its exit button isn't
   covered (v1.29.0). Keep an eye out for similar z-index/overlap issues on phones.
4. **Content / correctness + brand** — review-driven fixes (OBBBA loan cliff,
   year-span, bar caveat) shipped in v1.28.0; rebrand to "Exhibit 509" + a
   trust/funding line on About shipped in v1.29.0.

> Versions advanced 1.19.5 → 1.28.0 across intervening sessions not detailed in
> this doc; this session covered **1.28.0** (review items) and **1.29.0**
> (rebrand + trust line + mobile fix).

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
  `claude/elegant-lovelace-0awdY`), then fast-forward merge into `main` and push —
  Cloudflare deploys `main`. After merging, verify `main`'s tree == branch tip's.
- **No em dashes** in user-facing prose — use commas/colons. (House style; checked
  each ship with `grep -c "—"`.)
- **Brand strings:** product = "Exhibit 509", publisher = "509α". Generated school
  pages get `| Exhibit 509`; don't hand-edit `school/*.html` — change the template
  in `build_school_pages.py` and rebuild.
- **Counts are generated, never hand-typed** — edit the dataset, run `build.sh`,
  let `stamp_counts()` propagate to index + methodology.
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

## What shipped THIS session (on `main`, → 1.28.0, → 1.29.0)

**v1.28.0 — review items 1–5 (content / correctness)**

1. **OBBBA federal-loan cliff is now modeled, not just mentioned.** Net Price calc
   fires a live warning when modeled federal borrowing exceeds the 2026 caps
   (**$50k/yr, $200k lifetime**), showing the overflow that spills to private loans
   (no PSLF/IDR on it). Borrow tile relabeled **"federal"**; both stale "confirm
   Grad PLUS rates" lines refreshed to explain the cap regime.
2. **"0 schools" cold load — verified NOT a bug** (pins paint from inline `S`;
   nothing gates first paint). Seeded the static placeholder with the real count
   (207) so the pre-JS crawl snapshot doesn't read "0".
3. **15- vs 8-year span mismatch** — school-page template corrected to 15-year
   (2011–2025), matching the homepage.
4. **Count drift** — new `stamp_counts()` build step derives 208/197/11 from the
   dataset and stamps index + methodology; they can't disagree again.
5. **Bar-passage temporal caveat** — every school page now carries a visible
   "different cohorts" note under Bar passage.

**v1.29.0 — rebrand + trust + mobile**

6. **Rebrand to "Exhibit 509"** (509α = publisher) across titles, OG/Twitter,
   JSON-LD, header/footer wordmarks, hero `<h1>`, share text, and all 208 generated
   school pages + directory + pillars (`| Exhibit 509`).
7. **Trust / funding line** — new About section *"Why you can trust it, and how it
   stays free"*: data free + ungated, no money from rankings/ads/sponsorship/data-
   sales, no first-party tracking, run independently by Blake Vrechek, Skool + email
   sustain the work but nothing is gated behind them. *Only verifiable facts.*
8. **Mobile fix** — the full-screen school overview now sits in front of the fixed
   header on phones (`@media ≤640px`: `top:0`, `z-index:1001`, safe-area top
   padding), so its "Back to Exhibit" exit button is no longer covered.

Validation: inline JS `node --check` OK; all JSON-LD valid; version drift clean
(`v1.29.0`); no em dashes reintroduced.

### Open follow-ups from this session
- **Wordmark redundancy (low priority).** Header reads "Exhibit 509 · by 509α" —
  `509`/`509α` sit close together. If it looks redundant live, drop the wordmark to
  just "Exhibit 509" and keep "by 509α" in footer/About only. One-string change.
- **Trust-line specifics.** The funding paragraph states only what's verifiable;
  if the real business model has nameable specifics (e.g., whether Skool is paid),
  add them. I deliberately did not assert what I couldn't confirm.
- **Deploy + IndexNow.** Confirm deploy is live, then run `indexnow_ping.py` so the
  rebranded titles/pages get recrawled.

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

1. `git fetch && git checkout main && git pull` — confirm HEAD is `3cb8579` (or later),
   `VERSION` is `1.29.0`.
2. Confirm the v1.29.0 deploy is live; if data/titles changed, run
   `python3 scripts/indexnow_ping.py` to ping for recrawl.
3. **Mobile pass** continues — sweep for other header/overlay z-index issues on
   phones; verify the school-overview fix on a real device.
4. Any data refresh: edit the dataset, run `bash scripts/build.sh` (regen + counts +
   version), bump `VERSION` first if shipping. Update the "Last synced …" date
   string (NOT auto-stamped).
5. Ship: session branch → fast-forward merge into `main` → push. Hard-reload the
   live site once to install any new SW.
