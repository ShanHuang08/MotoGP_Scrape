from __future__ import annotations

from datetime import datetime, timezone

from motogp_scraper.cli import build_parser, format_capture_summary, main
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


def test_cli_help_uses_global_command_name() -> None:
    help_text = build_parser().format_help()

    assert help_text.startswith("usage: gpnews")
    assert "[-l LIMIT]" in help_text
    assert "Examples:\n  gpnews -l 10" in help_text
    assert "python main.py" not in help_text


def test_limit_short_option_matches_long_option() -> None:
    parser = build_parser()

    assert parser.parse_args(["-l", "7"]).limit == 7
    assert parser.parse_args(["--limit", "7"]).limit == 7


def test_cli_help_examples_are_valid_dry_runs() -> None:
    parser = build_parser()
    example_arguments = [
        ["-l", "10"],
        ["--limit", "10", "--no-open"],
        ["--limit", "10", "--skip-articles"],
        ["--limit", "10", "--output-dir", "reports"],
        ["--limit", "10", "--no-organize"],
        ["--limit", "5", "--skip-articles", "--no-open"],
        ["--unit-test"],
        [
            "--translate-report",
            r"latest_news_reports\2026-06-20 101500 latest news.md",
            "--translate-article",
            "3",
        ],
    ]

    for arguments in example_arguments:
        parser.parse_args(arguments)


def test_latest_news_run_writes_html_only(tmp_path, monkeypatch) -> None:
    class FakeScraper:
        def latest_news(self, *, limit: int) -> list[NewsItem]:
            return [
                NewsItem(
                    "Crash.net MotoGP",
                    "Test title",
                    "https://www.crash.net/motogp/news/test",
                    datetime(2024, 1, 1, tzinfo=timezone.utc),
                    raw_meta={"discovery_method": "rss"},
                )
            ][:limit]

    monkeypatch.setattr("motogp_scraper.runner.MotoGPScraper", FakeScraper)

    result = main(
        [
            "--limit",
            "1",
            "--skip-articles",
            "--format",
            "markdown",
            "--no-open",
            "--no-organize",
            "--output-dir",
            str(tmp_path),
        ]
    )

    assert result == 0
    assert len(list(tmp_path.glob("*.html"))) == 1
    assert list(tmp_path.glob("*.md")) == []
