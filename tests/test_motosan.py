"""MotoSan 的正文邊界、來源配額與日期排序回歸測試。"""
from datetime import datetime, timedelta, timezone

import pytest

from motogp_scraper.extractors import extract_article_text, extract_image_url_with_lxml
from motogp_scraper.models import NewsItem
from motogp_scraper.runner import MotoGPScraper


def test_body_stops_at_author():
    markup = """<div id="content-wrapper"><div class="entry-content">
    <div><img src="/cover.jpg"></div>
    <h3>Introducción</h3><p>Texto <strong>importante</strong>.</p>
    <div class="advert"><p>Advertisement</p></div>
    <h3>Final</h3><p>Último párrafo.</p>
    <div class="saboxplugin-wrap"><p>Author biography</p></div>
    <p>Related article</p></div></div>"""
    result = extract_article_text(markup, url="https://www.motosan.es/motogp/test/")
    assert result.text == "Introducción\n\nTexto importante.\n\nFinal\n\nÚltimo párrafo."
    assert extract_image_url_with_lxml(markup, base_url="https://www.motosan.es") == "https://www.motosan.es/cover.jpg"


@pytest.mark.parametrize("promotion", [
    "<p>¿TE GUSTAN LAS MOTOS ❤️? Pídele aquí a Google que te enseñe más de Motosan para tener siempre las últimas noticias. &#x20;</p>",
    "<h3>¿TE GUSTAN LAS MOTOS ❤?</h3><p><a>Pídele aquí a Google</a> que te enseñe más de Motosan para tener siempre las últimas noticias.&nbsp;</p>",
    "<p>¿TE GUSTAN LAS MOTOS? Pídele aquí a Google que te enseñe más de Motosan para tener siempre las últimas noticias.</p>",
])
def test_body_removes_google_promotion(promotion):
    # 宣傳句即使拆成標題與段落也要排除，但不能誤刪前面的正文。
    markup = '<div class="entry-content"><p>Último párrafo sobre Google y Motosan.</p>' + promotion + '</div>'
    result = extract_article_text(markup, url="https://www.motosan.es/motogp/test/")
    assert result.text == "Último párrafo sobre Google y Motosan."


def test_body_keeps_text_around_inline_promotion():
    markup = '''<div class="entry-content"><p>Antes. ¿TE GUSTAN LAS MOTOS ❤️?
    Pídele aquí a Google que te enseñe más de Motosan para tener siempre las últimas noticias. Después.</p></div>'''
    result = extract_article_text(markup, url="https://www.motosan.es/motogp/test/")
    assert " ".join(result.text.split()) == "Antes. Después."


def test_twenty_articles_reserve_and_cap():
    now = datetime(2026, 9, 30, tzinfo=timezone.utc)
    for offset in (-100, 100):
        items = [
            NewsItem("MotoSan MotoGP" if i < 6 else "Other", str(i), f"https://example.com/{i}",
                     now + timedelta(hours=offset if i < 6 else i),
                     raw_meta={"discovery_method": "rss"})
            for i in range(36)
        ]
        selected = MotoGPScraper()._select_weighted_latest(items, limit=20)
        assert len(selected) == 20
        assert 1 <= sum(item.source == "MotoSan MotoGP" for item in selected) <= 2
        assert selected == sorted(selected, key=lambda item: item.published_at, reverse=True)
        missing = MotoGPScraper()._select_weighted_latest(items[6:], limit=20)
        assert len(missing) == 20


def test_shortage_does_not_relax_motosan_cap():
    items = [NewsItem("MotoSan MotoGP", str(i), f"https://example.com/{i}") for i in range(6)]
    assert len(MotoGPScraper()._select_weighted_latest(items, limit=20)) == 2
