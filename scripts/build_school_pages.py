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
DATA_PATH = os.path.join(ROOT, "data", "exhibit-data.js")
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


def esc(t):
    return (str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            if t is not None else "")


# Well-known schools whose common search brand differs from the generic
# "{University} School of Law" construction. Keyed by school id.
LAW_NAME_OVERRIDES = {
    "harvard-university": "Harvard Law School",
    "yale-university": "Yale Law School",
    "stanford-university": "Stanford Law School",
    "columbia-university": "Columbia Law School",
    "cornell-university": "Cornell Law School",
    "chicago-the-university-of": "University of Chicago Law School",
    "michigan-university-of": "University of Michigan Law School",
    "georgetown-university": "Georgetown University Law Center",
    "northwestern-university": "Northwestern Pritzker School of Law",
    "vanderbilt-university": "Vanderbilt Law School",
    "pennsylvania-university-of": "University of Pennsylvania Carey Law School",
    "california-berkeley-university-of": "UC Berkeley School of Law",
    "california-los-angeles-university-of": "UCLA School of Law",
    "ucla": "UCLA School of Law",
}


def law_name(s):
    """A query-friendly law-school name: 'University of Akron School of Law',
    'Harvard Law School', etc. Searchers use 'X law school', not the bare
    parent-university name, so we reconstruct + append 'School of Law'."""
    if s["id"] in LAW_NAME_OVERRIDES:
        return LAW_NAME_OVERRIDES[s["id"]]
    raw = (s.get("full") or s.get("name") or "").strip()
    aba = (s.get("aba_name") or "").strip()
    base = raw
    # The inline dataset stores "Akron, The University of" in `full`; the gz uses
    # `aba_name`. Reconstruct "University of X" / "University at X" from whichever
    # candidate carries the comma form.
    for cand in (aba, raw):
        if not cand:
            continue
        m = re.match(r"^(.*?),\s*(the\s+)?university of\s*$", cand, re.I)
        if m:
            base = "University of " + m.group(1).strip()
            break
        m2 = re.match(r"^(.*?),\s*(the\s+)?university at\s*$", cand, re.I)
        if m2:
            base = "University at " + m2.group(1).strip()
            break
    low = base.lower()
    if "law" in low or "college of law" in low:
        return base
    return base + " School of Law"


def state_slug(state):
    s = (state or "").lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s


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


def render_page(s, all_schools=None):
    sid = s["id"]
    slug = slugify(sid)
    full = s.get("full") or s.get("name") or "Unknown"
    lname = law_name(s)            # query-friendly "… School of Law" name
    state = s.get("state") or ""
    school_type = s.get("school_type") or ""
    closed = s.get("closed_status")

    canonical = f"{SITE_URL}/school/{slug}.html"
    spa_url = f"{SITE_URL}/#school/{sid}"

    # ── Title + meta description (tuned to real search queries) ──
    bar = s.get("bar")
    ftlt_pct = s.get("ftlt_pct")
    tui = s.get("tui")
    lsat50 = s.get("lsat50")
    acc = s.get("acc")
    grant_med = s.get("grant_med")
    desc_parts = [
        f"{lname}:",
        f"{bar}% first-time bar pass," if bar is not None else "",
        f"{ftlt_pct}% in full-time JD jobs," if ftlt_pct is not None else "",
        f"{fmt_usd(tui)} resident tuition," if tui else "",
        f"{lsat50} median LSAT." if lsat50 else "",
        "Full ABA Standard 509 outcomes, cost & 15-year trajectory.",
    ]
    desc = " ".join(x for x in desc_parts if x).strip()
    title = f"{lname}: Bar Passage, Cost & Employment (ABA 509) | Exhibit 509"

    # ── Schema.org JSON-LD (CollegeOrUniversity) ────────────────
    ld = {
        "@context": "https://schema.org",
        "@type": "CollegeOrUniversity",
        "name": lname,
        "alternateName": full if full != lname else None,
        "url": canonical,
        "description": desc,
        "isAccessibleForFree": True,
        "sameAs": ["https://abarequireddisclosures.org/"],
    }
    ld = {k: v for k, v in ld.items() if v is not None}
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

    # ── Unique lead paragraph (prose summary; unique body text up top) ──
    type_phrase = (school_type.lower() + " law school") if school_type else "law school"
    lead_bits = [f"<strong>{esc(lname)}</strong> is a {esc(type_phrase)}"
                 + (f" in {esc(state)}" if state else "") + "."]
    if bar is not None:
        sa = s.get("bar_state_avg")
        lead_bits.append(f" In the most recent ABA Standard 509 cycle it reported a <strong>{bar}% first-time bar passage rate</strong>"
                         + (f" (state average {sa}%)" if sa is not None else "") + ".")
    if ftlt_pct is not None:
        bl = (s.get("emp_biglaw_pct") or 0) + (s.get("emp_megalaw_pct") or 0)
        lead_bits.append(f" <strong>{ftlt_pct}%</strong> of graduates landed full-time, long-term JD-required or JD-advantage jobs"
                         + (f", and {bl:.1f}% joined large firms of 251+ attorneys" if bl else "") + ".")
    if tui:
        net = (tui - grant_med) if (grant_med is not None) else None
        lead_bits.append(f" Resident tuition is <strong>{fmt_usd(tui)}</strong> per year"
                         + (f"; a median grant of {fmt_usd(grant_med)} brings median net tuition to about {fmt_usd(net)}" if net is not None else "") + ".")
    if lsat50 or acc is not None:
        lead_bits.append(f" The median LSAT is <strong>{lsat50 or '—'}</strong>"
                         + (f" with a {acc}% acceptance rate" if acc is not None else "") + ".")
    lead_html = '<p class="lead">' + "".join(lead_bits) + "</p>"

    # ── FAQ (visible + FAQPage schema; question-query targeting) ──
    faqs = []
    if bar is not None:
        sa = s.get("bar_state_avg")
        faqs.append((f"What is the first-time bar passage rate at {lname}?",
                     f"{lname} reported a {bar}% first-time bar passage rate in the most recent ABA Standard 509 disclosure"
                     + (f", versus a {sa}% state average." if sa is not None else ".")))
    if tui:
        ans = f"Resident tuition at {lname} is {fmt_usd(tui)} per year (about {fmt_usd(tui * 3)} over three years)."
        if grant_med is not None:
            ans += f" The median grant is {fmt_usd(grant_med)}, bringing median net tuition to roughly {fmt_usd(tui - grant_med)} per year."
        faqs.append((f"How much does {lname} cost?", ans))
    if lsat50 or acc is not None:
        faqs.append((f"What LSAT and GPA do you need for {lname}?",
                     f"The median (50th-percentile) LSAT at {lname} is {lsat50 or 'not reported'} and the median GPA is {fmt_gpa(s.get('gpa50'))}"
                     + (f"; the acceptance rate is {acc}%." if acc is not None else ".")))
    if ftlt_pct is not None:
        seek = s.get("emp_seek_pct")
        bl = (s.get("emp_biglaw_pct") or 0) + (s.get("emp_megalaw_pct") or 0)
        ans = f"{ftlt_pct}% of {lname} graduates held full-time, long-term JD-required or JD-advantage jobs about ten months after graduation."
        if bl:
            ans += f" {bl:.1f}% joined large firms of 251+ attorneys."
        if seek is not None:
            ans += f" {seek}% were still seeking employment."
        faqs.append((f"What are the job outcomes at {lname}?", ans))
    faq_html, faq_ld_json = "", ""
    if faqs:
        faq_html = "<h2>Frequently asked questions</h2>" + "".join(
            f'<div class="faq-q">{esc(q)}</div><p class="faq-a">{esc(a)}</p>' for q, a in faqs)
        faq_ld = {"@context": "https://schema.org", "@type": "FAQPage",
                  "mainEntity": [{"@type": "Question", "name": q,
                                  "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faqs]}
        faq_ld_json = '<script type="application/ld+json">' + json.dumps(faq_ld, ensure_ascii=False) + "</script>"

    # ── Breadcrumb (visible + schema) ──
    crumbs = [("Home", f"{SITE_URL}/")]
    if state:
        crumbs.append((f"{state} law schools", f"{SITE_URL}/{state_slug(state)}-law-schools.html"))
    crumbs.append((lname, canonical))
    crumb_html = '<nav class="crumbs" aria-label="Breadcrumb">' + " › ".join(
        (f'<a href="{u}">{esc(t)}</a>' if i < len(crumbs) - 1 else f"<span>{esc(t)}</span>")
        for i, (t, u) in enumerate(crumbs)) + "</nav>"
    crumb_ld = {"@context": "https://schema.org", "@type": "BreadcrumbList",
                "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": t, "item": u}
                                    for i, (t, u) in enumerate(crumbs)]}
    crumb_ld_json = '<script type="application/ld+json">' + json.dumps(crumb_ld, ensure_ascii=False) + "</script>"

    # ── Interlinking: other law schools in the same state ──
    siblings_html = ""
    if all_schools and state:
        sibs = sorted((x for x in all_schools if x.get("state") == state and x["id"] != sid and not x.get("closed_status")),
                      key=lambda x: law_name(x).lower())
        if sibs:
            lis = "".join(f'<li><a href="/school/{slugify(x["id"])}.html">{esc(law_name(x))}</a></li>' for x in sibs)
            state_url = f"/{state_slug(state)}-law-schools.html"
            siblings_html = (f'<h2>Other law schools in <a href="{state_url}">{esc(state)}</a></h2>'
                             f'<ul class="sibs">{lis}</ul>')

    # ── Body sections ───────────────────────────────────────────
    closed_banner = (
        f'<div class="closed-banner">{closed}, historical data shown below</div>'
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
                items.append(f"<li><strong>{p['st']}</strong>, {p['n']} graduates</li>")
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
<meta property="og:title" content="{lname}: ABA 509 data">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{canonical}">
<meta property="og:site_name" content="Exhibit 509">
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="{lname}: ABA 509 data">
<meta name="twitter:description" content="{desc}">
<script type="application/ld+json">{ld_json}</script>
{faq_ld_json}
{crumb_ld_json}
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
  .crumbs{{font-family:var(--mono);font-size:11px;letter-spacing:0.5px;color:var(--dimmer);margin-bottom:14px;}}
  .crumbs a{{color:var(--dim);text-decoration:none;}}
  .crumbs a:hover{{color:var(--orange);}}
  .crumbs span{{color:var(--dimmer);}}
  .lead{{font-size:17px;line-height:1.6;color:#D6E4F0;margin:0 0 22px;}}
  .cohort-note{{font-family:var(--mono);font-size:12px;line-height:1.6;color:#FFB27A;background:rgba(217,119,87,0.08);border-left:2px solid var(--orange);padding:9px 12px;margin:0 0 14px;}}
  .lead strong{{color:var(--white);}}
  .faq-q{{font-family:'Nunito',var(--serif);font-weight:700;font-size:16px;color:var(--white);margin:16px 0 2px;}}
  .faq-a{{margin:0 0 8px;font-size:15px;color:#CFE0EC;}}
  .sibs{{columns:2;column-gap:28px;font-family:var(--mono);font-size:13px;}}
  .sibs li{{margin-bottom:5px;break-inside:avoid;}}
  @media(max-width:560px){{.sibs{{columns:1;}}}}
  .src{{font-family:var(--mono);font-size:11px;color:var(--dimmer);margin-top:36px;padding-top:16px;border-top:1px solid rgba(74,122,155,0.2);letter-spacing:0.4px;line-height:1.7;}}
  .src a{{color:var(--blue);}}
  footer{{margin-top:30px;font-family:var(--mono);font-size:10.5px;color:var(--dimmer);letter-spacing:0.4px;}}
</style>
</head>
<body>
<div class="wrap">
  <nav class="nav"><a href="/">Map</a><a href="/schools.html">All schools</a><a href="/law-school-bar-passage-rates.html">Bar passage</a><a href="/cheapest-law-schools.html">Tuition</a><a href="/law-school-employment-outcomes.html">Employment</a><a href="/methodology.html">Methodology</a></nav>
  {crumb_html}
  {closed_banner}
  <div class="eyebrow">ABA Standard 509 · 2025 cycle · Last synced May 31, 2026</div>
  <h1>{lname}</h1>
  <div class="meta">{state}{f' · {school_type}' if school_type else ''} · School ID: {sid}</div>
  {lead_html}
  <a class="cta" href="{spa_url}">Open interactive map &amp; comparison view</a>

  <h2>Admissions</h2>
  <table>{adm_rows}</table>

  <h2>Cost &amp; scholarships</h2>
  <table>{cost_rows}</table>

  <h2>Bar passage</h2>
  <table>{bar_rows}</table>
  <p class="cohort-note">Different cohorts: first-time bar passage reflects graduates who <strong>entered law school about three years before</strong> the current admissions class shown above. Read the two as separate snapshots, not a single pipeline.</p>

  <h2>Job outcomes (10 months after graduation)</h2>
  <table>{job_rows}</table>

  {place_html}

  <h2>Demographics (current JD enrollment)</h2>
  <table>{demo_rows}</table>

  <h2>Faculty</h2>
  <table>{fac_rows}</table>

  {f'<h2>State market context</h2><table>{market_rows}</table>' if market_rows else ''}

  {faq_html}

  {siblings_html}

  <div class="src">
    Source: ABA Standard 509 Required Disclosure for {full}, published by the American Bar Association at <a href="https://abarequireddisclosures.org/" rel="noopener">abarequireddisclosures.org</a>. State attorney salary data from U.S. Bureau of Labor Statistics OEWS 2024 (occupation code 23-1011). Cost-of-living from U.S. BEA Regional Price Parities. Methodology: <a href="/methodology.html">/methodology.html</a>.
  </div>
  <footer>Exhibit 509: free law school data, by 509α. Hosted on Cloudflare Pages. Independent project, not affiliated with the ABA.</footer>
</div>
</body>
</html>
"""


STYLE = """<style>
  :root{--navy:#06111E;--orange:#D97757;--white:#F4F8FB;--dim:#A4C8DD;--dimmer:#7AAAC8;--blue:#5AABCB;--mono:'JetBrains Mono',ui-monospace,SFMono-Regular,Menlo,monospace;--serif:Georgia,'Times New Roman',serif;}
  *{box-sizing:border-box;}
  body{margin:0;background:var(--navy);color:var(--white);font-family:var(--serif);line-height:1.7;}
  .wrap{max-width:980px;margin:0 auto;padding:40px 22px 80px;}
  .nav{font-family:var(--mono);font-size:12px;letter-spacing:1px;margin-bottom:18px;}
  .nav a{color:var(--dim);text-decoration:none;margin-right:14px;}
  .nav a:hover{color:var(--orange);}
  .crumbs{font-family:var(--mono);font-size:11px;letter-spacing:0.5px;color:var(--dimmer);margin-bottom:14px;}
  .crumbs a{color:var(--dim);text-decoration:none;} .crumbs a:hover{color:var(--orange);} .crumbs span{color:var(--dimmer);}
  h1{font-family:'Nunito',var(--serif);font-size:36px;line-height:1.05;letter-spacing:-1.2px;margin:6px 0 8px;font-weight:800;}
  .lead{font-size:17px;line-height:1.6;color:#D6E4F0;margin:0 0 24px;max-width:760px;}
  .lead strong{color:var(--white);}
  h2{font-family:var(--mono);font-size:14px;letter-spacing:1.8px;color:var(--orange);text-transform:uppercase;margin:30px 0 10px;font-weight:700;}
  a{color:var(--orange);}
  table.rank{width:100%;border-collapse:collapse;margin:8px 0 20px;font-family:var(--mono);}
  table.rank th,table.rank td{text-align:left;padding:7px 10px;border-bottom:1px solid rgba(74,122,155,0.16);font-size:13px;}
  table.rank th{color:var(--dim);font-size:11px;letter-spacing:1px;text-transform:uppercase;font-weight:600;}
  table.rank td{font-variant-numeric:tabular-nums;}
  table.rank td.num{color:var(--dimmer);width:42px;}
  table.rank td a{color:var(--white);text-decoration:none;border-bottom:1px solid rgba(217,119,87,0.4);}
  table.rank td a:hover{color:var(--orange);}
  table.rank td.v{color:var(--orange);font-weight:700;}
  .dir-state{font-family:'Nunito',var(--serif);font-size:18px;font-weight:800;color:var(--white);margin:24px 0 4px;border-bottom:1px solid rgba(74,122,155,0.2);padding-bottom:4px;}
  .dir-list{columns:3;column-gap:30px;font-family:var(--mono);font-size:13px;padding-left:0;list-style:none;}
  .dir-list li{margin-bottom:6px;break-inside:avoid;}
  .dir-list a{color:var(--dim);text-decoration:none;} .dir-list a:hover{color:var(--orange);}
  @media(max-width:760px){.dir-list{columns:2;}}
  @media(max-width:480px){.dir-list{columns:1;}}
  .src{font-family:var(--mono);font-size:11px;color:var(--dimmer);margin-top:36px;padding-top:16px;border-top:1px solid rgba(74,122,155,0.2);letter-spacing:0.4px;line-height:1.7;}
  .src a{color:var(--blue);}
  footer{margin-top:30px;font-family:var(--mono);font-size:10.5px;color:var(--dimmer);letter-spacing:0.4px;}
</style>"""

PILLAR_NAV = ('<nav class="nav"><a href="/">Map</a><a href="/schools.html">All schools</a>'
              '<a href="/law-school-bar-passage-rates.html">Bar passage</a>'
              '<a href="/cheapest-law-schools.html">Tuition</a>'
              '<a href="/law-school-employment-outcomes.html">Employment</a>'
              '<a href="/methodology.html">Methodology</a></nav>')


def page_shell(title, desc, canonical, body, ld_json=""):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<meta name="description" content="{esc(desc)}">
<meta name="robots" content="index,follow">
<link rel="canonical" href="{canonical}">
<meta property="og:type" content="website">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{canonical}">
<meta property="og:site_name" content="Exhibit 509">
<meta name="twitter:card" content="summary">
{f'<script type="application/ld+json">{ld_json}</script>' if ld_json else ''}
<link rel="icon" type="image/png" href="{FAVICON}">
{STYLE}
</head>
<body>
<div class="wrap">
{body}
  <div class="src">Source: ABA Standard 509 Required Disclosures (most recent cycle), via <a href="https://abarequireddisclosures.org/" rel="noopener">abarequireddisclosures.org</a>. State attorney-salary context from U.S. BLS OEWS 2024. Methodology: <a href="/methodology.html">/methodology.html</a>.</div>
  <footer>Exhibit 509: free law school data, by 509α. Independent project, not affiliated with the ABA.</footer>
</div>
</body>
</html>
"""


def build_directory_page(schools):
    """A crawlable /schools.html: every school grouped by state (anchored by
    state slug for breadcrumb deep-links). The internal hub that links all pages."""
    by_state = {}
    for s in schools:
        if s.get("closed_status"):
            continue
        by_state.setdefault(s.get("state") or "Other", []).append(s)
    states = sorted(by_state)
    body = [PILLAR_NAV,
            '<nav class="crumbs"><a href="/">Home</a> › <span>All law schools</span></nav>',
            "<h1>All ABA-accredited U.S. law schools</h1>",
            f'<p class="lead">Browse every ABA-accredited law school by state, each links to a full profile with '
            f'bar passage, employment outcomes, true cost, scholarships, and a 15-year trajectory from the official '
            f'ABA Standard 509 disclosures. {sum(len(v) for v in by_state.values())} schools across {len(states)} states.</p>']
    for st in states:
        sl = state_slug(st)
        sibs = sorted(by_state[st], key=lambda x: law_name(x).lower())
        lis = "".join(f'<li><a href="/school/{slugify(x["id"])}.html">{esc(law_name(x))}</a></li>' for x in sibs)
        heading = (f'<a href="/{sl}-law-schools.html">{esc(st)}</a>' if st != "Other" else esc(st))
        body.append(f'<div class="dir-state" id="{sl}">{heading} <span style="font-family:var(--mono);font-size:12px;color:var(--dimmer);font-weight:400;">· {len(sibs)}</span></div>'
                    f'<ul class="dir-list">{lis}</ul>')
    ld = {"@context": "https://schema.org", "@type": "CollectionPage",
          "name": "All ABA-accredited U.S. law schools",
          "url": f"{SITE_URL}/schools.html"}
    html = page_shell(
        "All ABA Law Schools by State: Bar Passage, Cost & Employment | Exhibit 509",
        "Directory of every ABA-accredited U.S. law school by state. Each profile shows bar passage, employment outcomes, tuition, scholarships and a 15-year trajectory from official ABA 509 disclosures.",
        f"{SITE_URL}/schools.html", "\n".join(body), json.dumps(ld, ensure_ascii=False))
    open(os.path.join(ROOT, "schools.html"), "w").write(html)
    print("Wrote schools.html directory page.")


def build_pillar(schools, *, fname, h1, title, desc, intro, key, fmt, reverse, znull=False, unit=""):
    """Generic ranked 'pillar' page targeting a head-term query, linking out to
    every ranked school page."""
    rows = []
    for s in schools:
        if s.get("closed_status"):
            continue
        v = s.get(key)
        if v is None or not isinstance(v, (int, float)):
            continue
        if znull and v <= 0:
            continue
        rows.append((v, s))
    rows.sort(key=lambda t: t[0], reverse=reverse)
    trs = []
    for i, (v, s) in enumerate(rows, 1):
        trs.append(
            f'<tr><td class="num">{i}</td>'
            f'<td><a href="/school/{slugify(s["id"])}.html">{esc(law_name(s))}</a></td>'
            f'<td>{esc(s.get("state") or "—")}</td>'
            f'<td class="v">{fmt(v)}</td>'
            f'<td>{fmt_pct(s.get("bar")) if key!="bar" else fmt_pct(s.get("ftlt_pct"))}</td>'
            f'<td>{fmt_usd(s.get("tui"))}</td></tr>')
    second_h = "FTLT" if key == "bar" else "Bar"
    body = [PILLAR_NAV,
            '<nav class="crumbs"><a href="/">Home</a> › <a href="/schools.html">All law schools</a> › <span>'
            + esc(h1) + "</span></nav>",
            f"<h1>{esc(h1)}</h1>",
            f'<p class="lead">{intro}</p>',
            f'<table class="rank"><tr><th>#</th><th>Law school</th><th>State</th><th>{esc(unit)}</th><th>{second_h}</th><th>Tuition</th></tr>'
            + "".join(trs) + "</table>",
            '<p style="font-family:var(--mono);font-size:12px;color:var(--dimmer);">Ranked from the most recent ABA Standard 509 cycle. '
            + str(len(rows)) + ' schools shown. Explore any school for full outcomes, cost and trajectory, or open the '
            '<a href="/">interactive map</a>.</p>']
    ld = {"@context": "https://schema.org", "@type": "ItemList", "name": h1,
          "numberOfItems": len(rows),
          "itemListElement": [{"@type": "ListItem", "position": i,
                               "url": f"{SITE_URL}/school/{slugify(s['id'])}.html",
                               "name": law_name(s)} for i, (v, s) in enumerate(rows[:50], 1)]}
    html = page_shell(title, desc, f"{SITE_URL}/{fname}", "\n".join(body), json.dumps(ld, ensure_ascii=False))
    open(os.path.join(ROOT, fname), "w").write(html)
    print(f"Wrote {fname} ({len(rows)} ranked).")


def build_pillar_pages(schools):
    build_pillar(schools, fname="law-school-bar-passage-rates.html",
                 h1="Law school bar passage rates",
                 title="Law School Bar Passage Rates, Ranked (2025 ABA 509) | Exhibit 509",
                 desc="Every ABA-accredited law school ranked by first-time bar passage rate, from the official ABA Standard 509 disclosures. Compare against employment and tuition.",
                 intro="Every ABA-accredited U.S. law school ranked by <strong>first-time bar passage rate</strong> from the latest ABA Standard 509 disclosures. Click any school for the full picture: 2-year ultimate pass rate, employment, cost and trajectory.",
                 key="bar", fmt=lambda v: f"{v}%", reverse=True, unit="First-time bar")
    build_pillar(schools, fname="cheapest-law-schools.html",
                 h1="Cheapest ABA-accredited law schools by tuition",
                 title="Cheapest Law Schools by Tuition, Ranked (2025 ABA 509) | Exhibit 509",
                 desc="ABA-accredited law schools ranked from lowest resident tuition, from official ABA Standard 509 data. See cost against bar passage and employment outcomes.",
                 intro="ABA-accredited law schools ranked from the <strong>lowest resident tuition</strong> upward (latest ABA Standard 509 cycle). Remember to weigh sticker price against scholarships, bar passage and employment. Click any school for net cost and outcomes.",
                 key="tui", fmt=lambda v: fmt_usd(v), reverse=False, znull=True, unit="Resident tuition")
    build_pillar(schools, fname="law-school-employment-outcomes.html",
                 h1="Law schools by employment outcomes",
                 title="Law School Employment Outcomes, Ranked (2025 ABA 509) | Exhibit 509",
                 desc="ABA-accredited law schools ranked by full-time, long-term JD-required/JD-advantage employment (FTLT) from official ABA Standard 509 disclosures.",
                 intro="ABA-accredited law schools ranked by <strong>full-time, long-term JD-required or JD-advantage employment</strong> (FTLT) about ten months after graduation, from the latest ABA Standard 509 disclosures.",
                 key="ftlt_pct", fmt=lambda v: f"{v}%", reverse=True, unit="FTLT employed")


def state_page_fname(state):
    """Standalone crawlable per-state landing URL: 'california-law-schools.html'."""
    return f"{state_slug(state)}-law-schools.html"


def build_state_pages(schools):
    """One standalone, indexable landing page per state ('[state] law schools' is
    high-intent search volume). Sits as a clean internal-linking tier between the
    homepage and the per-school pages: Home › [State] law schools › [School].
    Returns the sorted list of states it built, for the sitemap."""
    by_state = {}
    for s in schools:
        if s.get("closed_status"):
            continue
        st = s.get("state")
        if not st:
            continue
        by_state.setdefault(st, []).append(s)
    states = sorted(by_state)

    def bar_sort(x):
        v = x.get("bar")
        return (0, -v) if isinstance(v, (int, float)) else (1, 0)

    for st in states:
        sl = state_slug(st)
        fname = f"{sl}-law-schools.html"
        canonical = f"{SITE_URL}/{fname}"
        sibs = sorted(by_state[st], key=bar_sort)
        n = len(sibs)
        bls_mean = next((x.get("bls_mean") for x in sibs if x.get("bls_mean")), None)

        # Ranked table: school → first-time bar, FTLT employment, resident tuition, median LSAT.
        trs = []
        for i, x in enumerate(sibs, 1):
            trs.append(
                f'<tr><td class="num">{i}</td>'
                f'<td><a href="/school/{slugify(x["id"])}.html">{esc(law_name(x))}</a></td>'
                f'<td class="v">{fmt_pct(x.get("bar"))}</td>'
                f'<td>{fmt_pct(x.get("ftlt_pct"))}</td>'
                f'<td>{fmt_usd(x.get("tui"))}</td>'
                f'<td>{x.get("lsat50") or "—"}</td></tr>')
        table = ('<table class="rank"><tr><th>#</th><th>Law school</th>'
                 '<th>First-time bar</th><th>FTLT employed</th>'
                 '<th>Resident tuition</th><th>Median LSAT</th></tr>'
                 + "".join(trs) + "</table>")

        school_word = "law school" if n == 1 else "law schools"
        lead = (f"There {'is' if n == 1 else 'are'} <strong>{n}</strong> ABA-accredited {school_word} "
                f"in {esc(st)}. Each row links to a full profile with first-time and 2-year ultimate bar "
                f"passage, full-time JD employment, true cost after scholarships, and a 15-year trajectory "
                f"from the official ABA Standard 509 disclosures.")
        if bls_mean:
            lead += (f" The mean attorney salary in {esc(st)} is {fmt_usd(bls_mean)} "
                     f"(U.S. BLS OEWS 2024), useful context for weighing cost against outcomes.")

        body = [PILLAR_NAV,
                f'<nav class="crumbs"><a href="/">Home</a> › <a href="/schools.html">All law schools</a> › '
                f'<span>{esc(st)} law schools</span></nav>',
                f"<h1>{esc(st)} law schools</h1>",
                f'<p class="lead">{lead}</p>',
                table,
                '<p style="font-family:var(--mono);font-size:12px;color:var(--dimmer);">'
                'From the most recent ABA Standard 509 cycle. Open any school for full outcomes, cost and '
                'trajectory, browse <a href="/schools.html">every state</a>, or open the '
                '<a href="/">interactive map</a>.</p>']

        crumb_ld = {"@context": "https://schema.org", "@type": "BreadcrumbList",
                    "itemListElement": [
                        {"@type": "ListItem", "position": 1, "name": "Home", "item": f"{SITE_URL}/"},
                        {"@type": "ListItem", "position": 2, "name": "All law schools",
                         "item": f"{SITE_URL}/schools.html"},
                        {"@type": "ListItem", "position": 3, "name": f"{st} law schools",
                         "item": canonical}]}
        coll_ld = {"@context": "https://schema.org", "@type": "CollectionPage",
                   "name": f"{st} law schools: ABA 509 data", "url": canonical,
                   "mainEntity": {"@type": "ItemList", "numberOfItems": n,
                                  "itemListElement": [
                                      {"@type": "ListItem", "position": i,
                                       "url": f"{SITE_URL}/school/{slugify(x['id'])}.html",
                                       "name": law_name(x)} for i, x in enumerate(sibs, 1)]}}
        ld_block = (json.dumps(coll_ld, ensure_ascii=False)
                    + '</script>\n<script type="application/ld+json">'
                    + json.dumps(crumb_ld, ensure_ascii=False))

        title = (f"{st} Law Schools: Bar Passage, Cost & Employment (ABA 509) | Exhibit 509")
        desc = (f"All {n} ABA-accredited law {('school' if n == 1 else 'schools')} in {st}, ranked with "
                f"first-time bar passage, full-time JD employment, and resident tuition from official "
                f"ABA Standard 509 disclosures.")
        html = page_shell(title, desc, canonical, "\n".join(body), ld_block)
        open(os.path.join(ROOT, fname), "w").write(html)
    print(f"Wrote {len(states)} per-state landing pages.")
    return states


def update_sitemap(schools, states=None):
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
  <url>
    <loc>https://exhibit509.com/schools.html</loc>
    <changefreq>weekly</changefreq>
    <priority>0.9</priority>
    <lastmod>2026-05-31</lastmod>
  </url>
  <url>
    <loc>https://exhibit509.com/law-school-bar-passage-rates.html</loc>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
    <lastmod>2026-05-31</lastmod>
  </url>
  <url>
    <loc>https://exhibit509.com/cheapest-law-schools.html</loc>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
    <lastmod>2026-05-31</lastmod>
  </url>
  <url>
    <loc>https://exhibit509.com/law-school-employment-outcomes.html</loc>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
    <lastmod>2026-05-31</lastmod>
  </url>
"""
    body_lines = []
    # Per-state landing pages sit one tier above the school pages — give them a
    # slightly higher priority and list them first.
    for st in (states or []):
        body_lines.append(
            f'  <url>\n    <loc>https://exhibit509.com/{state_page_fname(st)}</loc>\n    <changefreq>monthly</changefreq>\n    <priority>0.8</priority>\n    <lastmod>2026-05-31</lastmod>\n  </url>'
        )
    for s in schools:
        slug = slugify(s["id"])
        body_lines.append(
            f'  <url>\n    <loc>https://exhibit509.com/school/{slug}.html</loc>\n    <changefreq>monthly</changefreq>\n    <priority>0.8</priority>\n    <lastmod>2026-05-31</lastmod>\n  </url>'
        )
    body = "\n".join(body_lines)
    tail = "\n</urlset>\n"
    with open(SITEMAP_PATH, "w") as f:
        f.write(head + body + tail)


def update_index_directory(schools):
    """Inject a crawlable A–Z <ul> of every school page into index.html's noscript
    block (between SCHOOL_INDEX markers) so the 208 static pages have an internal
    HTML link path, not just the sitemap."""
    html = open(INDEX_PATH).read()
    start = "<!-- SCHOOL_INDEX_START -->"
    end = "<!-- SCHOOL_INDEX_END -->"
    i, j = html.find(start), html.find(end)
    if i < 0 or j < 0:
        print("  ! SCHOOL_INDEX markers not found; skipping directory injection")
        return
    items = []
    for s in sorted(schools, key=lambda x: law_name(x).lower()):
        slug = slugify(s["id"])
        nm = esc(law_name(s))
        state = esc(s.get("state") or "")
        items.append(f'<li><a href="school/{slug}.html">{nm}</a>{(", " + state) if state else ""}</li>')
    block = start + '\n<ul class="ns-schools">\n' + "\n".join(items) + "\n</ul>\n" + end
    html = html[:i] + block + html[j + len(end):]
    open(INDEX_PATH, "w").write(html)
    print(f"Injected {len(items)}-school crawlable directory into index.html noscript.")


def stamp_counts(schools):
    """Derive the school counts from the dataset and stamp them everywhere they
    appear in prose / config, so 208 / 197 / 11 (and the map's default count) can
    never drift out of agreement. Single source of truth = the dataset itself."""
    T = len(schools)                                              # total entries
    C = sum(1 for s in schools if s.get("closed_status"))         # closed/transitioning
    A = T - C                                                     # currently accredited
    M = sum(1 for s in schools if s.get("lat") and s.get("lng"))  # default map markers

    idx = open(INDEX_PATH, encoding="utf-8").read()
    idx_subs = [
        # Seed the pre-JS / crawl placeholder with the real default map count so
        # the homepage never snapshots "0 schools on map" before hydration.
        (r'(id="msTotal">)\d+(<)', rf"\g<1>{M}\g<2>"),
        (r"(total_schools:\s*)\d+", rf"\g<1>{T}"),
        (r"(schools_inline:\s*)\d+", rf"\g<1>{T}"),
        (r"for \d+ schools \(\d+ currently accredited \+ \d+ closed",
         f"for {T} schools ({A} currently accredited + {C} closed"),
        (r"(years of data, )\d+( schools)", rf"\g<1>{T}\g<2>"),
        (r"(2011–2025\) for )\d+( schools)", rf"\g<1>{T}\g<2>"),
    ]
    for pat, rep in idx_subs:
        idx = re.sub(pat, rep, idx)
    open(INDEX_PATH, "w", encoding="utf-8").write(idx)

    meth = os.path.join(ROOT, "methodology.html")
    if os.path.exists(meth):
        m = open(meth, encoding="utf-8").read()
        m = re.sub(r"all \d+ reporting schools", f"all {A} reporting schools", m)
        open(meth, "w", encoding="utf-8").write(m)

    print(f"Stamped counts: total={T} accredited={A} closed={C} mapped={M}")


def main():
    if not os.path.exists(INDEX_PATH):
        sys.exit(f"index.html not found at {INDEX_PATH}")
    # Dataset now lives in data/exhibit-data.js (split out of the HTML). Read S from
    # there; fall back to index.html for older checkouts.
    data_src = DATA_PATH if os.path.exists(DATA_PATH) else INDEX_PATH
    S = extract_S(open(data_src).read())
    print(f"Extracted {len(S)} schools from {os.path.basename(data_src)}.")

    os.makedirs(OUT_DIR, exist_ok=True)
    written = 0
    for s in S:
        try:
            page = render_page(s, all_schools=S)
            slug = slugify(s["id"])
            path = os.path.join(OUT_DIR, f"{slug}.html")
            with open(path, "w") as f:
                f.write(page)
            written += 1
        except Exception as e:
            print(f"  ! Failed {s.get('id')}: {e}")

    print(f"Wrote {written} static school pages to {OUT_DIR}/")
    build_directory_page(S)
    build_pillar_pages(S)
    states = build_state_pages(S)
    update_sitemap(S, states)
    print(f"Updated sitemap.xml with {len(S)} school URLs + {len(states)} state pages "
          f"(plus site + directory + pillar pages).")
    update_index_directory(S)
    stamp_counts(S)


if __name__ == "__main__":
    main()
