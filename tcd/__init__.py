"""
tcd — Thunderbird Commander Desktop, Google-native front-end (Phase 0).

Repurposes the Wing's existing Python as the engine that PUSHES its data into a
Google Sheet (the shared data plane). Google's own tools then render it:
AppSheet for the interactive P-D-T-A-C board, Looker Studio for read-only
dashboards. No custom HTML/tunnel/Basic-Auth to maintain.

Phase 0 scope (this package): collect the current TCD dataset, give every item
a real source deep-link, and write it to a Google Sheet pre-structured so
AppSheet auto-generates a clean app. See docs/TCD_APPSHEET_PILOT.md.
"""

__all__ = ["permalink", "item_model", "staging", "collectors", "sheet_sync"]
