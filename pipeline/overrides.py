#!/usr/bin/env python3
"""
Identity overrides + adjudicated corrections — the human-decided layer that sits
ABOVE the gz-derived crosswalk. This is where we record decisions about schools
that opened, closed, split, or merged across 2011-2025 (the gz collapsed some of
these; the primary-source rebuild preserves them separately).

NAME_OVERRIDES  ABA workbook SchoolName  -> slug. Highest precedence in the
                resolver (beats gz aba_name and the meta name_aliases). Use to
                split schools the gz merged, or pin a new slug for a school the
                gz never had.

ADJUDICATED     slugs whose EXISTING gz values are known-wrong per an adjudicated
                FLAGS.md decision. The oracle reports them separately and excludes
                them from the parser-fidelity match rate (a mismatch here is a
                correction we intend, not a parser bug). The gz rebuild will write
                the corrected values.
"""

# --- F1: Penn State — keep the two ABA schools separate (decided 2026-06) ------
# Dickinson Law (Carlisle) stays on the historical slug; Penn State Law
# (University Park) gets its own. The gz had merged UP's numbers onto the
# Dickinson slug, so penn-state-dickinson-law is adjudicated (gz = wrong).
NAME_OVERRIDES = {
    "Penn State Dickinson Law": "penn-state-dickinson-law",
    "Penn State University": "penn-state-law",
    "Pennsylvania State University - Dickinson Law": "penn-state-dickinson-law",
    "Pennsylvania State University - Penn State Law": "penn-state-law",
}

ADJUDICATED = {
    "penn-state-dickinson-law",  # F1 — gz carries University Park figures
}

# New slugs introduced by overrides that the gz does not yet have. Metadata
# (name/state/lat/lng) is filled in at the gz-rebuild step; listed here so the
# crosswalk treats them as valid resolution targets.
NEW_SLUGS = {
    "penn-state-law": {
        "name": "Penn State Law",
        "full": "Pennsylvania State University (University Park)",
        "state": "Pennsylvania",
    },
}
