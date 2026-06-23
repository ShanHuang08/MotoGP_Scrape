from __future__ import annotations

from pathlib import Path

import pytest

from motogp_scraper.translator import (
    TranslatedArticle,
    TranslationError,
    build_translation_html,
    build_translations_html,
    extract_markdown_article,
    parse_markdown_articles,
    _extract_response_text,
)


SAMPLE_MARKDOWN = """
# MotoGP Latest News

Generated at: 2026-06-20T10:00:00

## Latest News

| # | Title | Link | Published At (UTC+8) |
|---:|---|---|---|
| 1 | First title | https://example.com/1 | 2026-06-20T09:00:00+08:00 |
| 2 | Second title | https://example.com/2 | 2026-06-20T08:00:00+08:00 |

## Article Text

## 1. First title

Source: Test Source
URL: https://example.com/1
Published At (UTC+8): 2026-06-20T09:00:00+08:00
Extraction: trafilatura
Image: https://example.com/1.jpg

First paragraph.

Second paragraph.

## 2. Second title

Source: Test Source
URL: https://example.com/2
Published At (UTC+8): 2026-06-20T08:00:00+08:00
Extraction: gpone-lxml-sections
Image:

Second article body.
""".strip()


def test_parse_markdown_articles() -> None:
    articles = parse_markdown_articles(SAMPLE_MARKDOWN)

    assert len(articles) == 2
    assert articles[0].index == 1
    assert articles[0].title == "First title"
    assert articles[0].metadata["URL"] == "https://example.com/1"
    assert articles[0].body == "First paragraph.\n\nSecond paragraph."


def test_extract_markdown_article_by_index() -> None:
    article = extract_markdown_article(SAMPLE_MARKDOWN, 2)

    assert article.title == "Second title"
    assert article.metadata["Extraction"] == "gpone-lxml-sections"
    assert article.body == "Second article body."


def test_extract_markdown_article_missing_index_raises() -> None:
    with pytest.raises(TranslationError):
        extract_markdown_article(SAMPLE_MARKDOWN, 9)


def test_extract_response_text_prefers_output_text() -> None:
    assert _extract_response_text({"output_text": " translated "}) == "translated"


def test_extract_response_text_from_output_content() -> None:
    response = {
        "output": [
            {
                "content": [
                    {"type": "output_text", "text": "hello"},
                    {"type": "output_text", "text": "world"},
                ]
            }
        ]
    }

    assert _extract_response_text(response) == "hello\nworld"


def test_build_translation_html_contains_translated_text() -> None:
    article = extract_markdown_article(SAMPLE_MARKDOWN, 1)

    html = build_translation_html(
        source_path=Path("2026-06-20 latest news.md"),
        article=article,
        translated_text="Translated article body.",
        model="gpt-5",
    )

    assert "MotoGP Translation" in html
    assert "Translated article body." in html
    assert "Translation Model:" in html
    assert "gpt-5" in html


def test_build_translations_html_combines_multiple_articles() -> None:
    article_1 = extract_markdown_article(SAMPLE_MARKDOWN, 1)
    article_2 = extract_markdown_article(SAMPLE_MARKDOWN, 2)

    html = build_translations_html(
        source_path=Path("2026-06-20 latest news.md"),
        translated_articles=[
            TranslatedArticle(article=article_1, translated_text="Translated first."),
            TranslatedArticle(article=article_2, translated_text="Translated second."),
        ],
        model="gpt-5",
    )

    assert "MotoGP Translations" in html
    assert "Translated Articles:" in html
    assert "1, 2" in html
    assert "1. First title" in html
    assert "2. Second title" in html
    assert "Translated first." in html
    assert "Translated second." in html
