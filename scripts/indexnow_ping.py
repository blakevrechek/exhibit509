#!/usr/bin/env python3
"""
IndexNow post-deploy ping — tells Bing, Yandex, Brave, DuckDuckGo (et al.) to
crawl new/updated URLs within hours instead of waiting for a natural crawl.

Run this AFTER the site is deployed (the key file must be live at the host root):

    python3 scripts/indexnow_ping.py

Reads every <loc> from sitemap.xml and submits them in one batch. The key file
(<key>.txt at the site root) must contain exactly the key below.
"""
import json, os, re, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOST = "exhibit509.com"
KEY = "c3040eb549d49a2eded93c8011acfffe"
SITEMAP = os.path.join(ROOT, "sitemap.xml")
ENDPOINT = "https://api.indexnow.org/indexnow"


def main():
    xml = open(SITEMAP).read()
    urls = re.findall(r"<loc>([^<]+)</loc>", xml)
    if not urls:
        raise SystemExit("No URLs found in sitemap.xml")
    payload = {
        "host": HOST,
        "key": KEY,
        "keyLocation": f"https://{HOST}/{KEY}.txt",
        "urlList": urls,
    }
    req = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            print(f"IndexNow: submitted {len(urls)} URLs → HTTP {r.status}")
    except Exception as e:
        print(f"IndexNow ping failed: {e}")
        print("(The key file must be live at the host root first; safe to retry.)")


if __name__ == "__main__":
    main()
