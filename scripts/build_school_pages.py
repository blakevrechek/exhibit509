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
import gzip
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_PATH = os.path.join(ROOT, "index.html")
DATA_PATH = os.path.join(ROOT, "data", "exhibit-data.js")
GZ_PATH = os.path.join(ROOT, "data", "exhibit_data.json.gz")
OUT_DIR = os.path.join(ROOT, "school")
STATE_DIR = os.path.join(ROOT, "state")
RANK_DIR = os.path.join(ROOT, "rankings")
SITEMAP_PATH = os.path.join(ROOT, "sitemap.xml")
DATASET_PATH = os.path.join(ROOT, "exhibit-dataset.json")
SITE_URL = "https://exhibit509.com"
SYNCED = "May 31, 2026"
LASTMOD = "2026-05-31"


def state_slug(state):
    return re.sub(r"[^a-z0-9]+", "-", (state or "").lower()).strip("-")


def load_history():
    """Return {school_id: {year(int): {field: value}}} from the gz, for the static
    trajectory tables. The gz is the only crawl-invisible store of the 15-yr series."""
    if not os.path.exists(GZ_PATH):
        return {}
    try:
        with gzip.open(GZ_PATH) as fh:
            H = json.load(fh)
    except Exception as e:
        print(f"  ! could not read gz history: {e}")
        return {}
    out = {}
    for sc in H.get("schools", []):
        hist = sc.get("history") or {}
        yrs = {}
        for y, obj in hist.items():
            if re.match(r"^\d{4}$", str(y)) and isinstance(obj, dict):
                yrs[int(y)] = obj
        if yrs:
            out[sc.get("id")] = yrs
    return out


HISTORY = {}  # populated in main()


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

# Columns for the static 15-year trajectory table: (gz field, header, formatter)
TRAJ_COLS = [
    ("lsat50", "LSAT 50", lambda v: str(int(v)) if v is not None else "—"),
    ("gpa50", "uGPA 50", lambda v: f"{v:.2f}" if v is not None else "—"),
    ("acc", "Acceptance", lambda v: f"{v}%" if v is not None else "—"),
    ("bar", "1st-time bar", lambda v: f"{v}%" if v is not None else "—"),
    ("bar_2yr", "2-yr bar", lambda v: f"{v}%" if v is not None else "—"),
    ("ftlt_pct", "FTLT empl.", lambda v: f"{v}%" if v is not None else "—"),
    ("tui_ft_res", "Res. tuition", lambda v: f"${int(v):,}" if v else "—"),
    ("grant_med_ft", "Median grant", lambda v: f"${int(v):,}" if v else "—"),
]


def trajectory_table(sid, full):
    """Visible, crawlable 15-year history table from the gz series (P0 differentiator)."""
    yrs = HISTORY.get(sid)
    if not yrs:
        return "", []
    years = sorted(yrs.keys())
    head = "".join(f'<th scope="col">{h}</th>' for _, h, _ in TRAJ_COLS)
    body = []
    for y in years:
        obj = yrs[y]
        cells = "".join(f"<td>{fmt(obj.get(k))}</td>" for k, _, fmt in TRAJ_COLS)
        body.append(f'<tr><th scope="row">{y}</th>{cells}</tr>')
    table = (
        '<details open class="traj"><summary>15-year trajectory (2011–2025) — the data behind every chart</summary>'
        '<div class="traj-scroll"><table>'
        f'<caption>{full} — key ABA 509 metrics by year, 2011–2025</caption>'
        f'<thead><tr><th scope="col">Year</th>{head}</tr></thead>'
        f'<tbody>{"".join(body)}</tbody></table></div></details>'
    )
    return table, years


def build_dataset_ld(s, full, slug, canonical, years):
    cov = f"{years[0]}/{years[-1]}" if years else "2025/2025"
    return {
        "@type": "Dataset",
        "@id": f"{canonical}#dataset",
        "name": f"{full} — ABA Standard 509 data, {cov.replace('/', '–')}",
        "description": f"Year-by-year ABA 509 disclosures for {full}: LSAT/uGPA percentiles, acceptance, tuition, scholarships, first-time and two-year ultimate bar passage, and FTLT employment.",
        "url": canonical,
        "isAccessibleForFree": True,
        "creator": {"@type": "Organization", "name": "509α", "url": SITE_URL + "/"},
        "isBasedOn": "https://abarequireddisclosures.org/",
        "license": SITE_URL + "/terms.html",
        "temporalCoverage": cov,
        "dateModified": LASTMOD,
        "variableMeasured": [
            "LSAT 25/50/75", "uGPA 25/50/75", "Acceptance rate",
            "First-time bar passage", "Two-year ultimate bar passage",
            "FTLT employment rate", "Resident tuition", "Non-resident tuition", "Median grant",
        ],
    }


def build_faq(s, full):
    """Visible <dl> + FAQPage entities (the format LLMs/answer-boxes lift most readily)."""
    def g(k):
        return s.get(k)
    qa = []
    if g("lsat50") is not None:
        qa.append((
            f"What LSAT and GPA do I need for {full}?",
            f"The most recent entering class had a median LSAT of {g('lsat50')} "
            f"(25th–75th percentile {g('lsat25') or '—'}–{g('lsat75') or '—'}) and a median uGPA of "
            f"{fmt_gpa(g('gpa50'))} ({fmt_gpa(g('gpa25'))}–{fmt_gpa(g('gpa75'))})."))
    if g("bar") is not None:
        sa = f", versus a {g('bar_state_avg')}% state average on the same exam" if g("bar_state_avg") is not None else ""
        qa.append((
            f"What is {full}'s bar passage rate?",
            f"The first-time bar passage rate was {g('bar')}% for the most recent graduating cohort{sa}."))
    if g("tui"):
        ng = f"; {g('schol_none_pct')}% of students receive no grant" if g("schol_none_pct") is not None else ""
        gm = f", and the median grant is {fmt_usd(g('grant_med'))}" if g("grant_med") else ""
        qa.append((
            f"How much does {full} cost?",
            f"Sticker resident tuition is {fmt_usd(g('tui'))} per year{gm}{ng}."))
    if g("ftlt_pct") is not None:
        qa.append((
            f"What are employment outcomes at {full}?",
            f"{g('ftlt_pct')}% of graduates were in full-time, long-term, JD-required or JD-advantage jobs "
            f"about ten months after graduation."))
    return qa


def seo_title(s, full):
    """Bake the standout stat(s) into <title> for higher search CTR + cleaner LLM
    extraction. Falls back gracefully when the headline numbers are missing."""
    bits = []
    if s.get("bar") is not None:
        bits.append(f"{s['bar']}% bar pass")
    if s.get("ftlt_pct") is not None:
        bits.append(f"{s['ftlt_pct']}% employed")
    if not bits and s.get("lsat50") is not None:
        bits.append(f"LSAT {s['lsat50']}")
    if bits:
        return f"{full}: {', '.join(bits[:2])} — ABA 509 data"
    return f"{full} — ABA 509 data (2011–2025) · Exhibit"


def md_table_traj(sid, full):
    yrs = HISTORY.get(sid)
    if not yrs:
        return ""
    years = sorted(yrs.keys())
    hdr = "| Year | " + " | ".join(h for _, h, _ in TRAJ_COLS) + " |"
    sep = "|---" * (len(TRAJ_COLS) + 1) + "|"
    rows = []
    for y in years:
        obj = yrs[y]
        cells = " | ".join(fmt(obj.get(k)) for k, _, fmt in TRAJ_COLS)
        rows.append(f"| {y} | {cells} |")
    return "## 15-year trajectory (2011–2025)\n\n" + hdr + "\n" + sep + "\n" + "\n".join(rows) + "\n"


def render_markdown(s):
    """A clean Markdown twin of each school page — the cleanest possible LLM input,
    generated from the same data. Served at /school/<slug>.md."""
    sid = s["id"]
    slug = slugify(sid)
    full = s.get("full") or s.get("name") or "Unknown"
    state = s.get("state") or ""
    canonical = f"{SITE_URL}/school/{slug}.html"

    def g(k):
        return s.get(k)

    def line(label, val):
        return f"- **{label}:** {val}"

    lines = [f"# {full} — ABA Standard 509 data", ""]
    if s.get("closed_status"):
        lines.append(f"> Status: {s['closed_status']}. Final reported disclosures + full historical record below.\n")
    lines.append(
        f"{full}{f' ({state})' if state else ''} — ABA 509 disclosure data, 2011–2025. "
        f"Synced {SYNCED}. Source: ABA Required Disclosures (abarequireddisclosures.org). "
        f"Canonical: {canonical}\n"
    )
    lines.append("## Admissions (most recent cycle)\n")
    lines += [
        line("LSAT (25/50/75)", f"{g('lsat25') or '—'} / {g('lsat50') or '—'} / {g('lsat75') or '—'}"),
        line("uGPA (25/50/75)", f"{fmt_gpa(g('gpa25'))} / {fmt_gpa(g('gpa50'))} / {fmt_gpa(g('gpa75'))}"),
        line("Acceptance rate", fmt_pct(g("acc"))),
        line("Applications / offers", f"{fmt_int(g('apps'))} / {fmt_int(g('offers'))}"),
        line("1L / total JD enrollment", f"{fmt_int(g('enr_1l'))} / {fmt_int(g('enr'))}"),
    ]
    lines.append("\n## Cost & scholarships\n")
    lines += [
        line("Resident / non-resident tuition", f"{fmt_usd(g('tui'))} / {fmt_usd(g('nrt'))}"),
        line("Median grant", fmt_usd(g("grant_med"))),
        line("No-grant share", fmt_pct(g("schol_none_pct"))),
    ]
    lines.append("\n## Bar passage & employment\n")
    lines += [
        line("First-time bar (most recent cohort)", fmt_pct(g("bar"))),
        line("Two-year ultimate bar", fmt_pct(g("bar_2yr"))),
        line("State average (same exam)", fmt_pct(g("bar_state_avg"))),
        line("FTLT employment", fmt_pct(g("ftlt_pct"))),
        line("BigLaw + MegaLaw (251+ attys)", fmt_pct((g("emp_biglaw_pct") or 0) + (g("emp_megalaw_pct") or 0)) if (g("emp_biglaw_pct") is not None or g("emp_megalaw_pct") is not None) else "—"),
    ]
    lines.append("\n> Note: bar passage / employment describe graduates who entered ~3 years before the admissions figures above — different cohorts.\n")
    traj = md_table_traj(sid, full)
    if traj:
        lines.append("\n" + traj)
    faq = build_faq(s, full)
    if faq:
        lines.append("\n## Common questions\n")
        for q, a in faq:
            lines.append(f"**{q}**\n\n{a}\n")
    lines.append(f"\n---\nSource: ABA Standard 509 Required Disclosure for {full}. "
                 f"Methodology: {SITE_URL}/methodology.html. Cite: Exhibit, \"ABA 509 data for {full},\" "
                 f"exhibit509.com, synced {SYNCED}.\n")
    return "\n".join(lines)


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
    title = seo_title(s, full)

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
    ld["@id"] = f"{canonical}#school"

    # 15-year trajectory (visible table) + the years it spans
    traj_html, traj_years = trajectory_table(sid, full)
    # FAQ (visible <dl> + entities)
    faq_qa = build_faq(s, full)

    # Combined JSON-LD @graph: institution + dataset + FAQ + breadcrumb
    graph = [ld, build_dataset_ld(s, full, slug, canonical, traj_years)]
    if faq_qa:
        graph.append({
            "@type": "FAQPage",
            "@id": f"{canonical}#faq",
            "mainEntity": [
                {"@type": "Question", "name": q,
                 "acceptedAnswer": {"@type": "Answer", "text": a}}
                for q, a in faq_qa
            ],
        })
    crumb = [
        {"@type": "ListItem", "position": 1, "name": "All schools", "item": SITE_URL + "/"},
    ]
    if state:
        crumb.append({"@type": "ListItem", "position": 2, "name": state,
                      "item": f"{SITE_URL}/state/{state_slug(state)}.html"})
    crumb.append({"@type": "ListItem", "position": len(crumb) + 1, "name": full, "item": canonical})
    graph.append({"@type": "BreadcrumbList", "@id": f"{canonical}#breadcrumb", "itemListElement": crumb})
    ld_json = json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False)

    # ── Body sections ───────────────────────────────────────────
    closed_banner = (
        f'<div class="closed-banner">{closed} — historical data shown below</div>'
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

    # Visible FAQ <dl>
    faq_html = ""
    if faq_qa:
        dts = "".join(f"<dt>{q}</dt><dd>{a}</dd>" for q, a in faq_qa)
        faq_html = f'<h2>Common questions about {full}</h2><dl class="faq">{dts}</dl>'

    # Breadcrumb (visible) + closed-school prose lede
    crumb_html = (
        '<nav class="crumb" aria-label="Breadcrumb"><a href="/">All schools</a> › '
        + (f'<a href="/state/{state_slug(state)}.html">{state}</a> › ' if state else "")
        + f"<span>{full}</span></nav>"
    )
    closed_lede = ""
    if closed:
        closed_lede = (
            f'<p class="lede"><strong>Status: {closed}.</strong> {full} is no longer enrolling new '
            f"students; the figures below are its final reported ABA 509 disclosures and full historical record.</p>"
        )

    # Cite + report-a-data-error (citation hygiene + liability)
    cite_html = (
        '<div class="cite"><strong>Cite this page:</strong> '
        f'Exhibit, “ABA 509 data for {full},” exhibit509.com, synced {SYNCED}. '
        f'<a href="{canonical}">{canonical}</a><br>'
        f'<a href="mailto:blake@exhibit509.com?subject=Data%20correction%20—%20{slug}">Report a data error on this page →</a></div>'
    )
    bar_caveat = (
        '<p class="caveat">Note: bar passage and employment describe graduates who <em>entered ~3 years '
        "before</em> the admissions figures above — they are different cohorts. Compare across years using the "
        "trajectory table, not within a single row.</p>"
    )

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
  caption{{text-align:left;font-family:var(--mono);font-size:11px;color:var(--dimmer);letter-spacing:0.4px;padding:0 0 6px;caption-side:top;}}
  .crumb{{font-family:var(--mono);font-size:11.5px;letter-spacing:0.4px;color:var(--dimmer);margin-bottom:14px;}}
  .crumb a{{color:var(--dim);text-decoration:none;}} .crumb a:hover{{color:var(--orange);}} .crumb span{{color:var(--dim);}}
  .lede{{font-size:16px;color:var(--dim);margin:6px 0 18px;}}
  details.traj{{margin:6px 0 26px;border:1px solid rgba(74,122,155,0.22);border-radius:5px;background:rgba(74,122,155,0.04);}}
  details.traj summary{{cursor:pointer;font-family:var(--mono);font-size:12.5px;letter-spacing:1px;text-transform:uppercase;color:var(--orange);font-weight:700;padding:12px 14px;}}
  .traj-scroll{{overflow-x:auto;padding:0 6px 6px;}}
  details.traj table{{min-width:640px;}}
  details.traj th[scope=col],details.traj th[scope=row]{{white-space:nowrap;}}
  dl.faq dt{{font-family:'Nunito',var(--serif);font-weight:800;font-size:16px;color:var(--white);margin-top:16px;}}
  dl.faq dd{{margin:4px 0 0;color:var(--dim);font-size:15px;}}
  .caveat{{font-family:var(--mono);font-size:11.5px;line-height:1.6;color:var(--dimmer);background:rgba(255,167,38,0.06);border-left:2px solid rgba(255,167,38,0.4);padding:8px 12px;margin:4px 0 8px;}}
  .cite{{font-family:var(--mono);font-size:11.5px;line-height:1.7;color:var(--dim);background:rgba(74,122,155,0.06);border:1px solid rgba(74,122,155,0.18);border-radius:4px;padding:12px 14px;margin:28px 0 0;}}
  .cite a{{color:var(--blue);word-break:break-all;}}
</style>
</head>
<body>
<div class="wrap">
  <nav class="nav"><a href="/">All schools</a><a href="/methodology.html">Methodology</a><a href="/about.html">About</a><a href="/contact.html">Contact</a></nav>
  {crumb_html}
  {closed_banner}
  <div class="eyebrow">ABA Standard 509 · 2025 cycle · Last synced {SYNCED}</div>
  <h1>{full}</h1>
  <div class="meta">{state}{f' · {school_type}' if school_type else ''} · School ID: {sid}</div>
  {closed_lede}
  <a class="cta" href="{spa_url}">Open interactive map &amp; comparison view</a>

  {traj_html}

  <h2>Admissions</h2>
  <table><caption>{full} — admissions, most recent cycle</caption>{adm_rows}</table>

  <h2>Cost &amp; scholarships</h2>
  <table>{cost_rows}</table>

  <h2>Bar passage</h2>
  <table>{bar_rows}</table>
  {bar_caveat}

  <h2>Job outcomes (10 months after graduation)</h2>
  <table>{job_rows}</table>

  {place_html}

  <h2>Demographics (current JD enrollment)</h2>
  <table>{demo_rows}</table>

  <h2>Faculty</h2>
  <table>{fac_rows}</table>

  {f'<h2>State market context</h2><table>{market_rows}</table>' if market_rows else ''}

  {faq_html}

  {cite_html}

  <div class="src">
    Source: ABA Standard 509 Required Disclosure for {full}, published by the American Bar Association at <a href="https://abarequireddisclosures.org/" rel="noopener">abarequireddisclosures.org</a>. State attorney salary data from U.S. Bureau of Labor Statistics OEWS 2024 (occupation code 23-1011). Cost-of-living from U.S. BEA Regional Price Parities. Methodology: <a href="/methodology.html">/methodology.html</a>.
  </div>
  <footer>Exhibit — Free law school data, built by 509α. Hosted on Cloudflare Pages. Independent project, not affiliated with the ABA.</footer>
</div>
</body>
</html>
"""


# ─────────────────────────────────────────────────────────────────
# Answer-shaped pages: per-state hubs + ranked "best of" lists
# (P0 — the prose lede + ranked table is what an LLM lifts to answer
#  "best value law school in Texas?" / "highest bar passage?")
# ─────────────────────────────────────────────────────────────────
LIST_CSS = """  caption{text-align:left;font-family:var(--mono);font-size:11px;color:var(--dimmer);padding:0 0 6px;}
  .crumb{font-family:var(--mono);font-size:11.5px;color:var(--dimmer);margin-bottom:14px;}
  .crumb a{color:var(--dim);text-decoration:none;} .crumb a:hover{color:var(--orange);}
  .lede{font-size:17px;color:var(--dim);line-height:1.7;margin:6px 0 22px;}
  .lede strong{color:var(--white);}
  table.rank{width:100%;border-collapse:collapse;margin:8px 0 26px;}
  table.rank th,table.rank td{text-align:left;padding:9px 10px;border-bottom:1px solid rgba(74,122,155,0.16);font-size:14px;font-family:var(--mono);}
  table.rank thead th{color:var(--orange);font-size:11px;letter-spacing:1px;text-transform:uppercase;}
  table.rank td{color:var(--white);font-variant-numeric:tabular-nums;}
  table.rank td a{color:var(--blue);text-decoration:none;font-family:var(--serif);} table.rank td a:hover{color:var(--orange);}
  table.rank td.rk{color:var(--dimmer);width:34px;}
  .xlinks{margin:26px 0;font-family:var(--mono);font-size:12px;line-height:2;}
  .xlinks a{color:var(--blue);text-decoration:none;margin-right:14px;} .xlinks a:hover{color:var(--orange);}
  dl.faq dt{font-family:'Nunito',var(--serif);font-weight:800;font-size:16px;color:var(--white);margin-top:16px;}
  dl.faq dd{margin:4px 0 0;color:var(--dim);font-size:15px;}"""


def list_page(slug, subdir, h1, eyebrow, lede_html, crumb_html, table_html, ld_blocks, xlinks="", faq_html=""):
    base = "../" if subdir else ""
    canonical = f"{SITE_URL}/{subdir + '/' if subdir else ''}{slug}.html"
    desc = re.sub("<[^>]+>", "", lede_html)[:300]
    ld = "\n".join(f'<script type="application/ld+json">{json.dumps(b, ensure_ascii=False)}</script>' for b in ld_blocks)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{h1} · Exhibit</title>
<meta name="description" content="{desc}">
<meta name="robots" content="index,follow">
<link rel="canonical" href="{canonical}">
<meta property="og:type" content="article">
<meta property="og:title" content="{h1}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{canonical}">
<meta property="og:site_name" content="Exhibit by 509α">
{ld}
<link rel="icon" type="image/png" href="{FAVICON}">
<style>
  :root{{--navy:#06111E;--orange:#D97757;--white:#F4F8FB;--dim:#A4C8DD;--dimmer:#7AAAC8;--blue:#5AABCB;--mono:'JetBrains Mono',ui-monospace,SFMono-Regular,Menlo,monospace;--serif:Georgia,'Times New Roman',serif;}}
  *{{box-sizing:border-box;}} body{{margin:0;background:var(--navy);color:var(--white);font-family:var(--serif);line-height:1.7;}}
  .wrap{{max-width:900px;margin:0 auto;padding:40px 22px 80px;}}
  .nav{{font-family:var(--mono);font-size:12px;letter-spacing:1px;margin-bottom:18px;}} .nav a{{color:var(--dim);text-decoration:none;margin-right:14px;}} .nav a:hover{{color:var(--orange);}}
  .eyebrow{{font-family:var(--mono);font-size:11px;letter-spacing:2px;text-transform:uppercase;color:var(--orange);}}
  h1{{font-family:'Nunito',var(--serif);font-size:34px;line-height:1.07;letter-spacing:-1px;margin:8px 0 12px;font-weight:800;}}
  h2{{font-family:var(--mono);font-size:14px;letter-spacing:1.8px;color:var(--orange);text-transform:uppercase;margin:34px 0 8px;}}
  a{{color:var(--orange);}}
  .src{{font-family:var(--mono);font-size:11px;color:var(--dimmer);margin-top:30px;padding-top:16px;border-top:1px solid rgba(74,122,155,0.2);line-height:1.7;}}
  .src a{{color:var(--blue);}}
{LIST_CSS}
</style>
</head>
<body>
<div class="wrap">
  <nav class="nav"><a href="{base}index.html">Map</a><a href="{base}methodology.html">Methodology</a><a href="{base}about.html">About</a></nav>
  {crumb_html}
  <div class="eyebrow">{eyebrow}</div>
  <h1>{h1}</h1>
  <p class="lede">{lede_html}</p>
  {table_html}
  {xlinks}
  {faq_html}
  <div class="src">Source: ABA Standard 509 Required Disclosures (2011–2025), via <a href="https://abarequireddisclosures.org/" rel="noopener">abarequireddisclosures.org</a>; attorney-wage context from U.S. BLS OEWS 2024. Figures are the most recent reported cycle unless noted. Full methodology: <a href="{base}methodology.html">/methodology.html</a>. Synced {SYNCED}.</div>
</div>
</body>
</html>
"""


def _rank_table(rows, value_header, value_fn):
    head = (
        '<table class="rank"><thead><tr><th>#</th><th>School</th><th>State</th>'
        f'<th>{value_header}</th><th>1st-time bar</th><th>FTLT</th><th>Res. tuition</th></tr></thead><tbody>'
    )
    body = []
    for i, s in enumerate(rows, 1):
        slug = slugify(s["id"])
        body.append(
            f'<tr><td class="rk">{i}</td>'
            f'<td><a href="{SITE_URL}/school/{slug}.html">{s.get("full") or s.get("name")}</a></td>'
            f'<td>{s.get("state") or "—"}</td>'
            f'<td>{value_fn(s)}</td>'
            f'<td>{fmt_pct(s.get("bar"))}</td>'
            f'<td>{fmt_pct(s.get("ftlt_pct"))}</td>'
            f'<td>{fmt_usd(s.get("tui"))}</td></tr>'
        )
    return head + "".join(body) + "</tbody></table>"


def _item_list_ld(slug, subdir, name, lede, rows):
    canonical = f"{SITE_URL}/{subdir + '/' if subdir else ''}{slug}.html"
    return {
        "@context": "https://schema.org", "@type": "ItemList", "@id": canonical + "#list",
        "name": name, "description": re.sub("<[^>]+>", "", lede)[:300],
        "itemListOrder": "https://schema.org/ItemListOrderDescending",
        "numberOfItems": len(rows),
        "itemListElement": [
            {"@type": "ListItem", "position": i,
             "url": f"{SITE_URL}/school/{slugify(s['id'])}.html",
             "name": s.get("full") or s.get("name")}
            for i, s in enumerate(rows, 1)
        ],
    }


def net3(s):
    if not s.get("tui"):
        return None
    g = s.get("grant_med") or 0
    return (s["tui"] - g) * 3


RANK_XLINKS = (
    '<div class="xlinks"><strong style="color:var(--dim);font-family:var(--serif);">More rankings:</strong> '
    '<a href="/rankings/highest-bar-passage.html">Highest bar passage</a>'
    '<a href="/rankings/best-value-law-schools.html">Best value</a>'
    '<a href="/rankings/cheapest-law-schools.html">Cheapest</a>'
    '<a href="/rankings/highest-biglaw-placement.html">Most BigLaw</a></div>'
)


def build_ranking_pages(S):
    os.makedirs(RANK_DIR, exist_ok=True)
    active = [s for s in S if not s.get("closed_status")]
    pages = []  # (slug, school_rows) for sitemap
    crumb = '<nav class="crumb" aria-label="Breadcrumb"><a href="/">All schools</a> › <span>Rankings</span></nav>'

    def write(slug, h1, lede, rows, vheader, vfn):
        tbl = _rank_table(rows, vheader, vfn)
        ld = [_item_list_ld(slug, "rankings", h1, lede, rows),
              {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
                  {"@type": "ListItem", "position": 1, "name": "All schools", "item": SITE_URL + "/"},
                  {"@type": "ListItem", "position": 2, "name": h1, "item": f"{SITE_URL}/rankings/{slug}.html"}]}]
        html = list_page(slug, "rankings", h1, "Exhibit · ranked from ABA 509 data", lede, crumb, tbl, ld, RANK_XLINKS)
        open(os.path.join(RANK_DIR, f"{slug}.html"), "w").write(html)
        pages.append(slug)

    # Highest bar passage
    r = sorted([s for s in active if s.get("bar") is not None], key=lambda s: -s["bar"])[:50]
    lede = (f"Across {len([s for s in active if s.get('bar') is not None])} ABA-accredited law schools reporting first-time "
            f"bar passage, <strong>{r[0].get('full')}</strong> leads at <strong>{r[0]['bar']}%</strong>. "
            "Bar passage reflects the most recent graduating cohort; rates move year to year, so each school page shows the full 2011–2025 trajectory.")
    write("highest-bar-passage", "Law schools with the highest bar passage", lede, r, "1st-time bar", lambda s: fmt_pct(s.get("bar")))

    # Cheapest (resident tuition)
    r = sorted([s for s in active if s.get("tui")], key=lambda s: s["tui"])[:50]
    lede = (f"The lowest resident sticker tuition among reporting ABA-accredited schools is "
            f"<strong>{r[0].get('full')}</strong> at <strong>{fmt_usd(r[0]['tui'])}</strong> per year. "
            "Sticker is before scholarships — see each school's median grant and net cost on its page.")
    write("cheapest-law-schools", "Cheapest law schools by resident tuition", lede, r, "Res. tuition", lambda s: fmt_usd(s.get("tui")))

    # Most BigLaw (megalaw + biglaw)
    def blaw(s):
        return (s.get("emp_megalaw_pct") or 0) + (s.get("emp_biglaw_pct") or 0)
    r = sorted([s for s in active if (s.get("emp_megalaw_pct") is not None or s.get("emp_biglaw_pct") is not None)],
               key=lambda s: -blaw(s))[:50]
    lede = (f"By share of graduates placed in large firms (251+ attorneys), <strong>{r[0].get('full')}</strong> leads, "
            f"sending <strong>{blaw(r[0]):.1f}%</strong> of its class to BigLaw or MegaLaw. "
            "Large-firm placement is a proxy for the highest-salary private outcomes.")
    write("highest-biglaw-placement", "Law schools with the most BigLaw placement", lede,
          r, "BigLaw+ (251+)", lambda s: f"{blaw(s):.1f}%")

    # Best value: FTLT employment per dollar of 3-yr net tuition, gated on solid outcomes
    cand = [s for s in active if s.get("ftlt_pct") and net3(s) and s.get("bar") and s["bar"] >= 60]
    def value(s):
        return s["ftlt_pct"] / max(net3(s) / 100000.0, 0.05)
    r = sorted(cand, key=lambda s: -value(s))[:50]
    lede = ("Best value ranks employment per dollar: full-time, long-term JD employment rate divided by 3-year net "
            f"tuition (sticker − median grant), among schools with first-time bar ≥ 60%. <strong>{r[0].get('full')}</strong> "
            "tops it — strong outcomes at a low net cost. This is a transparent ratio, not a weighted ranking.")
    write("best-value-law-schools", "Best-value law schools (outcomes per dollar)", lede,
          r, "Net 3-yr tuition", lambda s: fmt_usd(net3(s)))
    return pages


def build_state_pages(S):
    os.makedirs(STATE_DIR, exist_ok=True)
    by_state = {}
    for s in S:
        st = s.get("state")
        if st:
            by_state.setdefault(st, []).append(s)
    pages = []
    for st, schools in sorted(by_state.items()):
        slug = state_slug(st)
        active = [s for s in schools if not s.get("closed_status")]
        ranked = sorted(active, key=lambda s: (-(s.get("bar") or -1)))
        if not ranked:
            ranked = schools
        crumb = f'<nav class="crumb" aria-label="Breadcrumb"><a href="/">All schools</a> › <span>{st}</span></nav>'
        top = ranked[0]
        barpart = (f"By first-time bar passage, <strong>{top.get('full')}</strong> leads at "
                   f"<strong>{top['bar']}%</strong>. " if top.get("bar") is not None else "")
        lede = (f"{st} has <strong>{len(schools)}</strong> ABA-accredited law school{'s' if len(schools)!=1 else ''} "
                f"({len(active)} currently operating). {barpart}"
                "Each is ranked below on the metrics that drive the decision — bar passage, employment, and cost — "
                "with the full 15-year history on every school's page.")
        tbl = _rank_table(ranked, "1st-time bar", lambda s: fmt_pct(s.get("bar")))
        h1 = f"Law schools in {st}"
        ld = [_item_list_ld(slug, "state", h1, lede, ranked),
              {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
                  {"@type": "ListItem", "position": 1, "name": "All schools", "item": SITE_URL + "/"},
                  {"@type": "ListItem", "position": 2, "name": st, "item": f"{SITE_URL}/state/{slug}.html"}]}]
        html = list_page(slug, "state", h1, f"Exhibit · {st} · ABA 509 data", lede, crumb, tbl, ld, RANK_XLINKS)
        open(os.path.join(STATE_DIR, f"{slug}.html"), "w").write(html)
        pages.append(slug)
    return pages


def write_bulk_dataset(S):
    """One canonical open-data file for LLM retrieval/training pipelines (P1).
    Current-cycle record per school; the full 2011–2025 series ships in the gz and
    in each school page's trajectory table."""
    payload = {
        "name": "Exhibit — ABA Standard 509 law school dataset",
        "description": "Current-cycle ABA 509 disclosure data for every ABA-accredited U.S. law school, "
                       "plus BLS/BEA/HUD context. Full 2011–2025 history per school at /school/<slug>.html.",
        "source": "https://abarequireddisclosures.org/",
        "publisher": "Exhibit by 509α (exhibit509.com)",
        "license": SITE_URL + "/terms.html",
        "synced": SYNCED,
        "temporalCoverage": "2011/2025",
        "school_count": len(S),
        "schools": S,
    }
    with open(DATASET_PATH, "w") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
    print(f"Wrote bulk open dataset: exhibit-dataset.json ({len(S)} schools).")


def update_sitemap(schools, rank_slugs=None, state_slugs=None):
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
    for slug in (rank_slugs or []):
        body_lines.append(
            f'  <url>\n    <loc>https://exhibit509.com/rankings/{slug}.html</loc>\n    <changefreq>monthly</changefreq>\n    <priority>0.7</priority>\n    <lastmod>2026-05-31</lastmod>\n  </url>'
        )
    for slug in (state_slugs or []):
        body_lines.append(
            f'  <url>\n    <loc>https://exhibit509.com/state/{slug}.html</loc>\n    <changefreq>monthly</changefreq>\n    <priority>0.7</priority>\n    <lastmod>2026-05-31</lastmod>\n  </url>'
        )
    body = "\n".join(body_lines)
    tail = "\n</urlset>\n"
    with open(SITEMAP_PATH, "w") as f:
        f.write(head + body + tail)


def _median(vals):
    vals = sorted(v for v in vals if isinstance(v, (int, float)))
    if not vals:
        return None
    n = len(vals)
    return vals[n // 2] if n % 2 else (vals[n // 2 - 1] + vals[n // 2]) / 2


def update_aggregates(schools, state_slugs):
    """Inject national aggregates + an evidence-based 'is it worth it' answer + links
    to the ranked/state pages into the no-JS block (NS_AGG markers). This is the
    prose+numbers a text-only crawler/LLM actually reads."""
    html = open(INDEX_PATH).read()
    start, end = "<!-- NS_AGG_START -->", "<!-- NS_AGG_END -->"
    i, j = html.find(start), html.find(end)
    if i < 0 or j < 0:
        return html
    active = [s for s in schools if not s.get("closed_status")]
    med_bar = _median([s.get("bar") for s in active])
    med_ftlt = _median([s.get("ftlt_pct") for s in active])
    med_tui = _median([s.get("tui") for s in active])
    med_lsat = _median([s.get("lsat50") for s in active])
    states_sorted = sorted({s.get("state") for s in active if s.get("state")})
    state_links = " · ".join(f'<a href="state/{state_slug(st)}.html">{st}</a>' for st in states_sorted)
    block = (
        start
        + '\n<h2>Is law school worth it? The data</h2>'
        + f'<p>Across the {len(active)} currently-accredited ABA law schools, the median first-time bar '
        + f'passage rate is <strong>{med_bar:.0f}%</strong>, median full-time long-term JD employment is '
        + f'<strong>{med_ftlt:.0f}%</strong>, and median resident tuition is <strong>${int(med_tui):,}/year</strong> '
        + f'(median entering LSAT <strong>{med_lsat:.0f}</strong>). Whether a degree is "worth it" depends on the '
        + 'gap between a specific school\'s cost and its outcomes — which is exactly what Exhibit breaks out, per '
        + 'school, with 15 years of history. Start with the ranked lists or your state below.</p>'
        + '<h2>Ranked lists</h2><ul>'
        + '<li><a href="rankings/highest-bar-passage.html">Law schools with the highest bar passage</a></li>'
        + '<li><a href="rankings/best-value-law-schools.html">Best-value law schools (outcomes per dollar)</a></li>'
        + '<li><a href="rankings/cheapest-law-schools.html">Cheapest law schools by tuition</a></li>'
        + '<li><a href="rankings/highest-biglaw-placement.html">Law schools with the most BigLaw placement</a></li>'
        + '</ul>'
        + f'<h2>Browse by state</h2><p>{state_links}</p>'
        + end
    )
    html = html[:i] + block + html[j + len(end):]
    open(INDEX_PATH, "w").write(html)
    print("Injected national aggregates + ranked/state links into no-JS block.")
    return html


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
    for s in sorted(schools, key=lambda x: (x.get("full") or x.get("name") or "").lower()):
        slug = slugify(s["id"])
        full = (s.get("full") or s.get("name") or s["id"]).replace("&", "&amp;").replace("<", "&lt;")
        state = (s.get("state") or "").replace("&", "&amp;").replace("<", "&lt;")
        items.append(f'<li><a href="school/{slug}.html">{full}</a>{(" — " + state) if state else ""}</li>')
    block = start + '\n<ul class="ns-schools">\n' + "\n".join(items) + "\n</ul>\n" + end
    html = html[:i] + block + html[j + len(end):]
    open(INDEX_PATH, "w").write(html)
    print(f"Injected {len(items)}-school crawlable directory into index.html noscript.")


def main():
    if not os.path.exists(INDEX_PATH):
        sys.exit(f"index.html not found at {INDEX_PATH}")
    # Dataset now lives in data/exhibit-data.js (split out of the HTML). Read S from
    # there; fall back to index.html for older checkouts.
    data_src = DATA_PATH if os.path.exists(DATA_PATH) else INDEX_PATH
    S = extract_S(open(data_src).read())
    print(f"Extracted {len(S)} schools from {os.path.basename(data_src)}.")
    global HISTORY
    HISTORY = load_history()
    print(f"Loaded gz history for {len(HISTORY)} schools (15-yr trajectory tables).")

    os.makedirs(OUT_DIR, exist_ok=True)
    written = 0
    md_written = 0
    for s in S:
        try:
            slug = slugify(s["id"])
            with open(os.path.join(OUT_DIR, f"{slug}.html"), "w") as f:
                f.write(render_page(s))
            written += 1
            with open(os.path.join(OUT_DIR, f"{slug}.md"), "w") as f:
                f.write(render_markdown(s))
            md_written += 1
        except Exception as e:
            print(f"  ! Failed {s.get('id')}: {e}")

    print(f"Wrote {written} static school pages + {md_written} Markdown twins to {OUT_DIR}/")
    rank_slugs = build_ranking_pages(S)
    print(f"Wrote {len(rank_slugs)} ranked answer pages to {RANK_DIR}/")
    state_slugs = build_state_pages(S)
    print(f"Wrote {len(state_slugs)} per-state hub pages to {STATE_DIR}/")
    write_bulk_dataset(S)
    update_sitemap(S, rank_slugs, state_slugs)
    print(f"Updated sitemap.xml with {len(S)} school + {len(rank_slugs)} ranking + {len(state_slugs)} state URLs.")
    update_aggregates(S, state_slugs)
    update_index_directory(S)


if __name__ == "__main__":
    main()
