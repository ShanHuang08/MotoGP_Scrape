"""Source weighting knobs for latest-news selection.

These settings are intentionally separate from runner.py so source priority can
be adjusted without reading the scraper workflow.
"""

from __future__ import annotations

from datetime import timedelta


# Keep RSS and non-RSS sources balanced so GPone still has room in each report.
RSS_SHARE = 0.5

# Lower-priority sources stay eligible, but they are sorted as if they were a bit
# older than high-priority sources in the same RSS/non-RSS bucket.
SOURCE_PRIORITY_DELAYS = {
    "MotoGPNews": timedelta(hours=8),
    "The Race MotoGP": timedelta(hours=8),
}

# Per-source caps for lower-priority sources. For a 10-article report, keep each
# of these sources to one article. For a 20-article report, allow up to three if
# their articles are recent enough.
SOURCE_CAPS_BY_REPORT_LIMIT = {
    "MotoGPNews": (
        (10, 1),
        (19, 2),
        (999, 3),
    ),
    "The Race MotoGP": (
        (10, 1),
        (19, 2),
        (999, 3),
    ),
}


def source_article_cap(source_name: str, report_limit: int) -> int:
    """Return the max articles allowed for a source at a report size."""
    for max_report_limit, cap in SOURCE_CAPS_BY_REPORT_LIMIT.get(source_name, ()):
        if report_limit <= max_report_limit:
            return cap
    return report_limit

