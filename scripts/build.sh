#!/usr/bin/env bash
# One-command rebuild of every generated artifact. Run after editing the dataset
# (data/exhibit-data.js) or bumping the VERSION file:
#   0. VALIDATE the dataset — aborts the build on data-integrity errors so a
#      generation bug (constant fields, truncated trends, impossible values,
#      inline/trend drift) can never be regenerated into the static pages.
#   1. regenerate per-school pages, /schools.html directory, pillar pages, sitemap
#   2. re-stamp the canonical version across the HTML pages + service worker
#
# This is the single source of truth for build order — both humans and CI
# (.github/workflows/seo-build.yml) call it, so they can never drift.
set -euo pipefail
cd "$(dirname "$0")/.."

python3 scripts/validate_data.py
python3 scripts/build_school_pages.py
python3 scripts/stamp_version.py

echo
echo "Build complete. Review 'git status', then commit & push."
echo "After the deploy is live, run: python3 scripts/indexnow_ping.py"
