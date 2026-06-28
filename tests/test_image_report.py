from __future__ import annotations

from motogp_scraper.cli import render_articles
from motogp_scraper.reporter import build_report_html, markdown_report_to_html


def test_render_articles_places_image_after_extraction(make_article) -> None:
    article = make_article(image_url="https://example.com/very/long/image.jpg")

    markdown = render_articles([article])

    extraction_index = markdown.index("Extraction: trafilatura")
    image_index = markdown.index("Image: https://example.com/very/long/image.jpg")
    assert extraction_index < image_index


def test_markdown_report_to_html_renders_image_button() -> None:
    markdown = """
## 1. Test Article

Source: Test
URL: https://example.com/article
Published At (UTC+8): 2024-06-01T20:00:00+08:00
Extraction: trafilatura
Image: https://example.com/image.jpg

Article body.
""".strip()

    html = build_report_html(markdown)

    assert 'class="image-btn"' in html
    assert "\u67e5\u770b\u4e26\u4e0b\u8f09\u5716\u7247" in html
    assert 'data-image-url="https://example.com/image.jpg"' in html
    assert 'class="image-preview"' in html
    assert '<img src="https://example.com/image.jpg" alt="">' in html
    assert "downloadArticleImage" in html
    assert "fetch(url, { mode: 'cors'" in html
    assert "triggerImageDownload" in html


def test_copy_script_includes_article_title() -> None:
    markdown = """
## 2. Pedro Acosta says Brno MotoGP crash proves one-bike rule not a good idea

Source: Test
URL: https://example.com/article
Published At (UTC+8): 2024-06-01T20:00:00+08:00
Extraction: trafilatura
Image:

Article body.
""".strip()

    html = build_report_html(markdown)

    assert "findArticleHeading" in html
    assert "article-heading" in html
    assert "replace(/^\\d+\\.\\s*/, '')" in html
    assert "title + '\\n\\n' + bodyText" in html


def test_copy_url_button_uses_url_without_query_string() -> None:
    markdown = """
## 1. Test Article

Source: Motorsport
URL: https://es.motorsport.com/motogp/news/story/10833648/?utm_source=RSS&utm_medium=referral
Published At (UTC+8): 2024-06-01T20:00:00+08:00
Extraction: trafilatura
Image:

Article body.
""".strip()

    html = build_report_html(markdown)

    assert "copyArticleUrl" in html
    assert "Copy URL" in html
    assert (
        'data-url="https://es.motorsport.com/motogp/news/story/10833648/"'
        in html
    )
    assert 'data-url="https://es.motorsport.com/motogp/news/story/10833648/?' not in html
