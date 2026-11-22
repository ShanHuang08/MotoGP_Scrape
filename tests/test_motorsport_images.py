"""確保 Motorsport 圖說清理不刪除相鄰正文，且涵蓋兩種抽取路徑。"""
import pytest
from unittest.mock import patch

from motogp_scraper.extractors import extract_article_text, remove_motorsport_image_blocks
from lxml import html


MARKUP = '''<html><body><article>
<script type="application/ld+json">{"articleBody":"Photo by: Hidden credit"}</script>
<div class="ms-entity-promo relative"><p>Alex Marquez, Gresini Racing</p><p>Photo by: Another photographer</p></div>
<p>Alex Marquez said Marco Bezzecchi was the fastest rider during Friday practice.</p>
<section data-widget="image"><p class="title">Marco Bezzecchi, Aprilia Racing</p><p class="photographer">Photo by: Gold and Goose Photography / Getty Images</p></section>
<p>Bezzecchi, who won the Portuguese Grand Prix last year, was fastest in the morning.</p>
</article></body></html>'''


def test_removes_image_blocks_and_keeps_following_text():
    cleaned = remove_motorsport_image_blocks(MARKUP)
    text = html.fromstring(cleaned).text_content()
    assert "Photo by:" not in text
    assert "Marco Bezzecchi, Aprilia Racing" not in text
    assert "Bezzecchi, who won" in text
    assert "Alex Marquez said" in text


@pytest.mark.parametrize("host", ["www.motorsport.com", "es.motorsport.com"])
def test_fallback_receives_clean_markup(host):
    with patch("motogp_scraper.extractors.extract_article_with_trafilatura", return_value=None):
        result = extract_article_text(MARKUP, url=f"https://{host}/motogp/news/test/")
    assert "Photo by:" not in result.text
    assert "Bezzecchi, who won" in result.text


def test_trafilatura_receives_clean_markup():
    with patch("motogp_scraper.extractors.extract_article_with_trafilatura", return_value=None) as extract:
        extract_article_text(MARKUP, url="https://www.motorsport.com/motogp/news/test/")
    assert "Photo by:" not in extract.call_args.args[0]


def test_image_tail_survives():
    cleaned = remove_motorsport_image_blocks('<article><section data-widget="image">Caption</section>Following body.</article>')
    assert html.fromstring(cleaned).text_content() == "Following body."
