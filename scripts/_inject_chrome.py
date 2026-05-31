#!/usr/bin/env python3
"""One-off: inject a consistent global header + footer bar into the standalone
content pages (about / contact / methodology / terms) so the whole site shares
the same chrome as the app shell. Idempotent — re-running is a no-op."""
import re, sys, pathlib

FORM = ("https://docs.google.com/forms/d/e/"
        "1FAIpQLScvkEp7vEwHAtpbMbk06AmtdUqHTy595OiQFcNBanSBXm0qDA/viewform?usp=publish-editor")

CSS = """
<style id="ghfChrome">
/* ── Global site chrome: fixed header + footer bar, shared with the app shell.
   Self-contained (literal colors) so it does not depend on each page's vars. ── */
body{padding-top:52px;padding-bottom:42px;}
#floatBack{display:none!important;}
.gh{position:fixed;top:0;left:0;right:0;z-index:1000;height:52px;display:flex;align-items:center;background:rgba(4,13,23,0.97);border-bottom:1px solid rgba(74,122,155,0.3);-webkit-backdrop-filter:blur(16px);backdrop-filter:blur(16px);}
.gh-logo{display:flex;align-items:center;gap:10px;padding:0 18px;height:100%;text-decoration:none;border-right:1px solid rgba(74,122,155,0.2);white-space:nowrap;}
.gh-logo b{font-family:Georgia,'Times New Roman',serif;font-size:18px;font-weight:700;color:#F4F8FB;letter-spacing:-0.5px;}
.gh-logo b em{font-style:normal;color:#D97757;font-size:12px;font-family:ui-monospace,Menlo,monospace;font-weight:600;letter-spacing:1.6px;margin-left:7px;text-transform:uppercase;}
.gh-nav{display:flex;align-items:center;height:100%;overflow-x:auto;scrollbar-width:none;}
.gh-nav::-webkit-scrollbar{display:none;}
.gh-nav a{display:flex;align-items:center;height:100%;padding:0 14px;font-family:ui-monospace,Menlo,monospace;font-size:12px;letter-spacing:1px;text-transform:uppercase;color:#A4C8DD;text-decoration:none;white-space:nowrap;transition:color .15s;}
.gh-nav a:hover{color:#F4F8FB;}
.gh-nav a.on{color:#F4F8FB;box-shadow:inset 0 -2px 0 #D97757;}
.gh-cta{margin-left:auto;display:flex;align-items:center;gap:6px;background:#D97757;color:#06111E;padding:6px 14px;margin-right:12px;font-family:ui-monospace,Menlo,monospace;font-size:11px;letter-spacing:1px;text-transform:uppercase;text-decoration:none;border-radius:3px;font-weight:700;white-space:nowrap;flex-shrink:0;}
.gh-cta:hover{background:#E68660;}
.gf{position:fixed;bottom:0;left:0;right:0;z-index:1000;height:36px;display:flex;align-items:center;background:rgba(4,13,23,0.97);border-top:1px solid rgba(74,122,155,0.2);overflow-x:auto;scrollbar-width:none;}
.gf::-webkit-scrollbar{display:none;}
.gf-brand{display:flex;align-items:center;padding:0 14px;height:100%;border-right:1px solid rgba(74,122,155,0.15);white-space:nowrap;flex-shrink:0;}
.gf-brand b{font-family:Georgia,'Times New Roman',serif;font-size:14px;font-weight:700;color:#F4F8FB;}
.gf-brand b em{font-style:normal;color:#D97757;font-size:10px;font-family:ui-monospace,Menlo,monospace;font-weight:400;margin-left:3px;}
.gf a{display:flex;align-items:center;padding:0 13px;height:100%;border-right:1px solid rgba(74,122,155,0.12);font-family:ui-monospace,Menlo,monospace;font-size:12px;color:#A4C8DD;text-decoration:none;letter-spacing:0.4px;white-space:nowrap;transition:color .15s;flex-shrink:0;}
.gf a:hover{color:#F4F8FB;}
.gf a.gf-accent{color:#D97757;font-weight:600;}
.gf a.gf-accent:hover{color:#E68660;}
.gf-src{padding:0 14px;font-family:ui-monospace,Menlo,monospace;font-size:11px;color:#7AAAC8;white-space:nowrap;margin-left:auto;letter-spacing:0.3px;flex-shrink:0;}
.gf-src a{display:inline;padding:0;border:none;height:auto;color:#5AABCB;}
@media(max-width:640px){.gh-nav a{padding:0 10px;font-size:11px;}.gf-src{display:none;}}
</style>
"""

def nav(active):
    items = [("Map", "index.html", None),
             ("Schools", "index.html#view=profiles", None),
             ("States", "index.html#view=states", None),
             ("Transfers", "index.html#view=transfers", None),
             ("Net price", "index.html#view=calc", None),
             ("Methodology", "methodology.html", "methodology"),
             ("About", "about.html", "about"),
             ("Contact", "contact.html", "contact")]
    out = []
    for label, href, key in items:
        on = ' class="on"' if key and key == active else ''
        out.append(f'<a href="{href}"{on}>{label}</a>')
    return "".join(out)

def header(active):
    return (f'<header class="gh"><a class="gh-logo" href="index.html">'
            f'<b>Exhibit <em>by 509α</em></b></a>'
            f'<nav class="gh-nav">{nav(active)}</nav>'
            f'<a class="gh-cta" href="{FORM}" target="_blank" rel="noopener">→ Email updates</a>'
            f'</header>')

FOOTER = (f'<div class="gf">'
          f'<span class="gf-brand"><b>Exhibit <em>by 509α</em></b></span>'
          f'<a class="gf-accent" href="{FORM}" target="_blank" rel="noopener">→ Sign up for email updates</a>'
          f'<a href="methodology.html">Methodology</a>'
          f'<a href="about.html">About</a>'
          f'<a href="contact.html">Contact</a>'
          f'<a href="terms.html">Terms · Privacy</a>'
          f'<a class="gf-accent" href="https://skool.com/509alpha" target="_blank" rel="noopener">Join 509α on Skool</a>'
          f'<span class="gf-src"><span style="color:#4A9B6B;">●</span> Sourced from official ABA Standard 509 disclosures '
          f'· <span style="color:#D97757;">Last synced May 2026</span> '
          f'· <a href="https://abarequireddisclosures.org/" target="_blank" rel="noopener">Source</a></span>'
          f'</div>')

PAGES = {"about.html": "about", "contact.html": "contact",
         "methodology.html": "methodology", "terms.html": None}

root = pathlib.Path(__file__).resolve().parent.parent
for fname, active in PAGES.items():
    p = root / fname
    html = p.read_text(encoding="utf-8")
    if 'class="gh-nav"' in html:
        print(f"skip {fname} (already injected)"); continue
    html = html.replace("</head>", CSS + "</head>", 1)
    html = re.sub(r"<body>", "<body>\n" + header(active), html, count=1)
    html = html.replace("</body>", FOOTER + "\n</body>", 1)
    p.write_text(html, encoding="utf-8")
    print(f"injected {fname} (active={active})")
