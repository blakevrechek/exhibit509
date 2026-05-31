#!/usr/bin/env python3
"""
Exhibit — per-school static HTML generator.

Reads the inline `const S` array from index.html, writes one
self-contained HTML page per school to /school/<slug>.html. The
goal is per-school indexable URLs that AI crawlers + Google read
without needing to execute the SPA's JS.

Each generated page contains:
  - Full content (admissions, cost, scholarships, bar, employment,
    demographics, faculty, state market, curriculum) as plain HTML.
  - Per-school schema.org JSON-LD (CollegeOrUniversity + nested
    Dataset, geo, hasCredential).
  - Open Graph + Twitter Card meta.
  - Canonical URL pointing to /school/<slug>.html on exhibit509.com.
  - A prominent "Open the interactive map view" CTA linking to the
    SPA at /#school/<id>.

Run:  python3 scripts/build_school_pages.py
Idempotent. Overwrites school/*.html on every run.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_PATH = os.path.join(ROOT, "index.html")
OUT_DIR = os.path.join(ROOT, "school")
SITEMAP_PATH = os.path.join(ROOT, "sitemap.xml")
SITE_URL = "https://exhibit509.com"


def slugify(school_id):
    """URL-safe slug: lowercase alphanumerics + hyphens only."""
    s = school_id.lower()
    s = re.sub(r"[^a-z0-9-]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s


def extract_S(html):
    """Walk brackets to extract the inline const S = [...] array."""
    marker = "const S = "
    i = html.find(marker)
    if i < 0:
        raise SystemExit("Could not find 'const S =' in index.html")
    start = i + len(marker)
    depth = 0
    in_str = False
    esc = False
    j = start
    while j < len(html):
        c = html[j]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        else:
            if c == '"':
                in_str = True
            elif c == "[":
                depth += 1
            elif c == "]":
                depth -= 1
                if depth == 0:
                    j += 1
                    break
        j += 1
    return json.loads(html[start:j])


def fmt_int(v):
    return f"{v:,}" if isinstance(v, (int, float)) and v is not None else "—"


def fmt_pct(v):
    return f"{v}%" if isinstance(v, (int, float)) and v is not None else "—"


def fmt_usd(v):
    return f"${int(v):,}" if isinstance(v, (int, float)) and v else "—"


def fmt_gpa(v):
    return f"{v:.2f}" if isinstance(v, (int, float)) and v is not None else "—"


def row(k, v, hint=""):
    """Render one key/value row for the static page."""
    h = f' title="{hint}"' if hint else ""
    return f'<tr{h}><th>{k}</th><td>{v}</td></tr>'


# ─────────────────────────────────────────────────────────────────
# Page template
# ─────────────────────────────────────────────────────────────────
def _favicon_data_uri():
    """Read the inlined PNG data URI from index.html's IMG const so every static
    page carries the brand favicon even before icon-192.png is uploaded. Falls
    back to /icon-192.png if extraction fails."""
    try:
        import re as _re
        h = open(INDEX_PATH).read()
        m = _re.search(r"const IMG=\{png:'(data:image/png;base64,[^']+)'", h)
        if m: return m.group(1)
    except Exception:
        pass
    return "/icon-192.png"

FAVICON = _favicon_data_uri()


def render_page(s):
    sid = s["id"]
    slug = slugify(sid)
    full = s.get("full") or s.get("name") or "Unknown"
    state = s.get("state") or ""
    school_type = s.get("school_type") or ""
    closed = s.get("closed_status")

    canonical = f"{SITE_URL}/school/{slug}.html"
    spa_url = f"{SITE_URL}/#school/{sid}"

    # ── Title + meta description ────────────────────────────────
    bar = s.get("bar")
    ftlt_pct = s.get("ftlt_pct")
    tui = s.get("tui")
    lsat50 = s.get("lsat50")
    desc_parts = [
        f"{full}",
        f"({state})" if state else "",
        "— ABA 509 data:",
        f"LSAT median {lsat50}," if lsat50 else "",
        f"acceptance {s.get('acc')}%," if s.get("acc") is not None else "",
        f"first-time bar {bar}%," if bar is not None else "",
        f"FTLT employment {ftlt_pct}%," if ftlt_pct is not None else "",
        f"tuition {fmt_usd(tui)}." if tui else "",
    ]
    desc = " ".join(x for x in desc_parts if x).strip()
    title = f"{full} — ABA 509 data · Exhibit"

    # ── Schema.org JSON-LD (CollegeOrUniversity) ────────────────
    ld = {
        "@context": "https://schema.org",
        "@type": "CollegeOrUniversity",
        "name": full,
        "url": canonical,
        "description": desc,
        "isAccessibleForFree": True,
        "sameAs": ["https://abarequireddisclosures.org/"],
    }
    if state:
        ld["address"] = {
            "@type": "PostalAddress",
            "addressRegion": state,
            "addressCountry": "US",
        }
    if s.get("lat") and s.get("lng"):
        ld["geo"] = {
            "@type": "GeoCoordinates",
            "latitude": s["lat"],
            "longitude": s["lng"],
        }
    ld["hasCredential"] = {
        "@type": "EducationalOccupationalCredential",
        "credentialCategory": "degree",
        "name": "Juris Doctor (JD)",
    }
    ld["subjectOf"] = {
        "@type": "Dataset",
        "name": f"ABA Standard 509 disclosure ({full})",
        "url": "https://abarequireddisclosures.org/",
    }
    ld_json = json.dumps(ld, ensure_ascii=False)

    # ── Body sections ───────────────────────────────────────────
    closed_banner = (
        f'<div class="closed-banner">// {closed} — historical data shown below</div>'
        if closed else ""
    )

    # Admissions
    adm_rows = "".join([
        row("LSAT (25 / 50 / 75)", f"{s.get('lsat25') or '—'} / {lsat50 or '—'} / {s.get('lsat75') or '—'}"),
        row("uGPA (25 / 50 / 75)", f"{fmt_gpa(s.get('gpa25'))} / {fmt_gpa(s.get('gpa50'))} / {fmt_gpa(s.get('gpa75'))}"),
        row("Acceptance rate", fmt_pct(s.get("acc"))),
        row("Applications received", fmt_int(s.get("apps"))),
        row("Offers extended", fmt_int(s.get("offers"))),
        row("1L enrollment", fmt_int(s.get("enr_1l"))),
        row("Total JD enrollment", fmt_int(s.get("enr"))),
        row("GRE-only takers", fmt_int(s.get("gre_takers"))),
        row("Transfers in / out", f"{fmt_int(s.get('trans_in'))} / {fmt_int(s.get('trans_out'))}"),
    ])

    # Cost & scholarships
    cost_rows = "".join([
        row("Resident tuition", fmt_usd(tui)),
        row("Non-resident tuition", fmt_usd(s.get("nrt"))),
        row("Mandatory fees", fmt_usd(s.get("ft_fee"))),
        row("Living-expense estimate", fmt_usd(s.get("living"))),
        row("Median grant", fmt_usd(s.get("grant_med"))),
        row("Grant 25 / 75 percentile", f"{fmt_usd(s.get('grant_p25'))} / {fmt_usd(s.get('grant_p75'))}"),
        row("No-grant share", fmt_pct(s.get("schol_none_pct"))),
        row("< half-tuition grants", fmt_pct(s.get("schol_lt_pct"))),
        row("Half-to-full grants", fmt_pct(s.get("schol_mt_pct"))),
        row("Full-tuition grants", fmt_pct(s.get("schol_full_pct"))),
        row("Above-full grants (stipend)", fmt_pct(s.get("schol_gt_pct"))),
        row("Conditional-scholarship loss rate", fmt_pct(s.get("cond"))),
    ])

    # Bar passage
    bar_rows = "".join([
        row("First-Time Bar (2024 cohort)", fmt_pct(s.get("bar"))),
        row("Two-Year Ultimate Bar", fmt_pct(s.get("bar_2yr"))),
        row("State average (same exam)", fmt_pct(s.get("bar_state_avg"))),
        row("Difference vs. state", f"{s.get('bar_state_diff'):+.1f} pts" if s.get("bar_state_diff") is not None else "—"),
    ])

    # Job outcomes
    job_rows = "".join([
        row("Total graduates", fmt_int(s.get("grads"))),
        row("FTLT (full-time, long-term, JD-required/advantage)", fmt_pct(s.get("ftlt_pct"))),
        row("Bar-required jobs", fmt_pct(s.get("emp_bar_pct"))),
        row("MegaLaw 500+", fmt_pct(s.get("emp_megalaw_pct"))),
        row("BigLaw 251–500", fmt_pct(s.get("emp_biglaw_pct"))),
        row("Mid 101–250", fmt_pct(s.get("emp_mid_pct"))),
        row("Small 2–100", fmt_pct(s.get("emp_small_pct"))),
        row("Solo", fmt_pct(s.get("emp_solo_pct"))),
        row("Clerkships", fmt_pct(s.get("emp_clk_pct"))),
        row("Government", fmt_pct(s.get("emp_gov_pct"))),
        row("Public interest", fmt_pct(s.get("emp_pi_pct"))),
        row("Business / industry", fmt_pct(s.get("emp_biz_pct"))),
        row("Academia", fmt_pct(s.get("emp_edu_pct"))),
        row("Seeking employment", fmt_pct(s.get("emp_seek_pct"))),
    ])

    # Demographics
    sex_men = s.get("sex_men") or 0
    sex_women = s.get("sex_women") or 0
    sex_total = sex_men + sex_women
    demo_rows = "".join([
        row("Male enrollment", f"{fmt_int(sex_men)} ({(sex_men/sex_total*100):.1f}%)" if sex_total else "—"),
        row("Female enrollment", f"{fmt_int(sex_women)} ({(sex_women/sex_total*100):.1f}%)" if sex_total else "—"),
        row("White", fmt_int(s.get("race_white"))),
        row("Black", fmt_int(s.get("race_black"))),
        row("Hispanic", fmt_int(s.get("race_hisp"))),
        row("Asian", fmt_int(s.get("race_asian"))),
        row("Two or more races", fmt_int(s.get("race_multi"))),
        row("Other / unreported", fmt_int(s.get("race_other"))),
    ])

    # Faculty
    fac_rows = "".join([
        row("Total faculty", fmt_int(s.get("fac_total"))),
        row("Full-time", fmt_int(s.get("fac_ft"))),
        row("Faculty of color", fmt_int(s.get("fac_poc"))),
    ])

    # State market
    bls_mean = s.get("bls_mean")
    market_rows = ""
    if bls_mean:
        market_rows = "".join([
            row("Mean attorney salary in state", fmt_usd(bls_mean), "U.S. BLS OEWS 2024"),
        ])

    # Top destination states
    place_html = ""
    if s.get("place_top3"):
        items = []
        for p in s["place_top3"]:
            if isinstance(p, dict) and p.get("st") and p.get("n"):
                items.append(f"<li><strong>{p['st']}</strong> — {p['n']} graduates</li>")
        if items:
            yr = s.get("place_top3_year") or ""
            place_html = f"<h2>Top destination states{f' ({yr})' if yr else ''}</h2><ul>{''.join(items)}</ul>"

    # ── Final page ──────────────────────────────────────────────
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta name="robots" content="index,follow">
<link rel="canonical" href="{canonical}">
<meta property="og:type" content="article">
<meta property="og:title" content="{full} — ABA 509 data">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{canonical}">
<meta property="og:site_name" content="Exhibit by 509α">
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="{full} — ABA 509 data">
<meta name="twitter:description" content="{desc}">
<script type="application/ld+json">{ld_json}</script>
<link rel="icon" type="image/png" href="{FAVICON}">
<link rel="apple-touch-icon" href="{FAVICON}">
<style>
  :root{{--navy:#06111E;--orange:#D97757;--white:#F4F8FB;--dim:#A4C8DD;--dimmer:#7AAAC8;--blue:#5AABCB;--mono:'JetBrains Mono',ui-monospace,SFMono-Regular,Menlo,monospace;--serif:Georgia,'Times New Roman',serif;}}
  *{{box-sizing:border-box;}}
  body{{margin:0;background:var(--navy);color:var(--white);font-family:var(--serif);line-height:1.7;}}
  .wrap{{max-width:860px;margin:0 auto;padding:40px 22px 80px;}}
  .nav{{font-family:var(--mono);font-size:12px;letter-spacing:1px;margin-bottom:24px;}}
  .nav a{{color:var(--dim);text-decoration:none;margin-right:14px;}}
  .nav a:hover{{color:var(--orange);}}
  .eyebrow{{font-family:var(--mono);font-size:11px;letter-spacing:2px;text-transform:uppercase;color:var(--orange);}}
  h1{{font-family:'Nunito',var(--serif);font-size:36px;line-height:1.05;letter-spacing:-1.2px;margin:8px 0 6px;font-weight:800;}}
  .meta{{font-family:var(--mono);font-size:12px;color:var(--dim);letter-spacing:1.5px;text-transform:uppercase;margin-bottom:28px;}}
  h2{{font-family:var(--mono);font-size:14px;letter-spacing:1.8px;color:var(--orange);text-transform:uppercase;margin:36px 0 8px;font-weight:700;}}
  table{{width:100%;border-collapse:collapse;margin:8px 0 16px;}}
  th,td{{text-align:left;padding:8px 10px;border-bottom:1px solid rgba(74,122,155,0.16);font-size:14px;}}
  th{{color:var(--dim);font-family:var(--mono);font-size:12px;font-weight:500;letter-spacing:0.2px;width:50%;}}
  td{{color:var(--white);font-family:var(--mono);font-size:14px;font-variant-numeric:tabular-nums;}}
  ul{{padding-left:22px;}}
  a{{color:var(--orange);}}
  .cta{{display:inline-block;background:var(--orange);color:#06111E;padding:12px 22px;font-family:var(--mono);font-size:13px;letter-spacing:1.5px;text-transform:uppercase;text-decoration:none;font-weight:700;margin:18px 0 30px;border-radius:3px;}}
  .cta:hover{{background:#E68660;}}
  .closed-banner{{background:rgba(255,167,38,0.12);border:1px solid rgba(255,167,38,0.4);padding:10px 14px;font-family:var(--mono);font-size:12px;letter-spacing:1px;color:#FFA726;margin-bottom:20px;}}
  .src{{font-family:var(--mono);font-size:11px;color:var(--dimmer);margin-top:36px;padding-top:16px;border-top:1px solid rgba(74,122,155,0.2);letter-spacing:0.4px;line-height:1.7;}}
  .src a{{color:var(--blue);}}
  footer{{margin-top:30px;font-family:var(--mono);font-size:10.5px;color:var(--dimmer);letter-spacing:0.4px;}}
</style>
</head>
<body>
<div class="wrap">
  <nav class="nav"><a href="/">← All schools</a><a href="/methodology.html">Methodology</a><a href="/about.html">About</a><a href="/contact.html">Contact</a></nav>
  {closed_banner}
  <div class="eyebrow">// ABA Standard 509 · 2025 cycle · Last synced May 31, 2026</div>
  <h1>{full}</h1>
  <div class="meta">{state}{f' · {school_type}' if school_type else ''} · School ID: {sid}</div>
  <a class="cta" href="{spa_url}">→ Open interactive map &amp; comparison view</a>

  <h2>Admissions</h2>
  <table>{adm_rows}</table>

  <h2>Cost &amp; scholarships</h2>
  <table>{cost_rows}</table>

  <h2>Bar passage</h2>
  <table>{bar_rows}</table>

  <h2>Job outcomes (10 months after graduation)</h2>
  <table>{job_rows}</table>

  {place_html}

  <h2>Demographics (current JD enrollment)</h2>
  <table>{demo_rows}</table>

  <h2>Faculty</h2>
  <table>{fac_rows}</table>

  {f'<h2>State market context</h2><table>{market_rows}</table>' if market_rows else ''}

  <div class="src">
    Source: ABA Standard 509 Required Disclosure for {full}, published by the American Bar Association at <a href="https://abarequireddisclosures.org/" rel="noopener">abarequireddisclosures.org</a>. State attorney salary data from U.S. Bureau of Labor Statistics OEWS 2024 (occupation code 23-1011). Cost-of-living from U.S. BEA Regional Price Parities. Methodology: <a href="/methodology.html">/methodology.html</a>.
  </div>
  <footer>Exhibit — Free law school data, built by 509α. Hosted on Cloudflare Pages. Independent project, not affiliated with the ABA.</footer>
</div>
</body>
</html>
"""


def update_sitemap(schools):
    """Inject one <url> entry per school into sitemap.xml."""
    head = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://exhibit509.com/</loc>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
    <lastmod>2026-05-31</lastmod>
  </url>
  <url>
    <loc>https://exhibit509.com/about.html</loc>
    <changefreq>monthly</changefreq>
    <priority>0.6</priority>
  </url>
  <url>
    <loc>https://exhibit509.com/methodology.html</loc>
    <changefreq>monthly</changefreq>
    <priority>0.7</priority>
    <lastmod>2026-05-31</lastmod>
  </url>
  <url>
    <loc>https://exhibit509.com/contact.html</loc>
    <changefreq>monthly</changefreq>
    <priority>0.6</priority>
  </url>
  <url>
    <loc>https://exhibit509.com/terms.html</loc>
    <changefreq>yearly</changefreq>
    <priority>0.3</priority>
  </url>
"""
    body_lines = []
    for s in schools:
        slug = slugify(s["id"])
        body_lines.append(
            f'  <url>\n    <loc>https://exhibit509.com/school/{slug}.html</loc>\n    <changefreq>monthly</changefreq>\n    <priority>0.8</priority>\n    <lastmod>2026-05-31</lastmod>\n  </url>'
        )
    body = "\n".join(body_lines)
    tail = "\n</urlset>\n"
    with open(SITEMAP_PATH, "w") as f:
        f.write(head + body + tail)


def main():
    if not os.path.exists(INDEX_PATH):
        sys.exit(f"index.html not found at {INDEX_PATH}")
    html = open(INDEX_PATH).read()
    S = extract_S(html)
    print(f"Extracted {len(S)} schools from inline S array.")

    os.makedirs(OUT_DIR, exist_ok=True)
    written = 0
    for s in S:
        try:
            page = render_page(s)
            slug = slugify(s["id"])
            path = os.path.join(OUT_DIR, f"{slug}.html")
            with open(path, "w") as f:
                f.write(page)
            written += 1
        except Exception as e:
            print(f"  ! Failed {s.get('id')}: {e}")

    print(f"Wrote {written} static school pages to {OUT_DIR}/")
    update_sitemap(S)
    print(f"Updated sitemap.xml with {len(S)} school URLs (plus 4 site pages).")


if __name__ == "__main__":
    main()
