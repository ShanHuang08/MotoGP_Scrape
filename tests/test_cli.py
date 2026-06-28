from __future__ import annotations

from datetime import datetime, timezone

from motogp_scraper.cli import format_capture_summary
from motogp_scraper.models import NewsItem


def test_format_capture_summary_groups_sources_by_count() -> None:
    items = [
        NewsItem("Crash.net MotoGP", "A", "https://crash.net/a", datetime(2024, 1, 1, tzinfo=timezone.utc)),
        NewsItem("GPone MotoGP EN", "B", "https://gpone.com/b", datetime(2024, 1, 1, tzinfo=timezone.utc)),
        NewsItem("GPone MotoGP EN", "C", "https://gpone.com/c", datetime(2024, 1, 1, tzinfo=timezone.utc)),
    ]

    assert (
        format_capture_summary(items)
        == "2 GPone MotoGP EN news, 1 Crash.net MotoGP news have been captured."
    )


def test_format_capture_summary_handles_empty_items() -> None:
    assert format_capture_summary([]) == "No news captured."

