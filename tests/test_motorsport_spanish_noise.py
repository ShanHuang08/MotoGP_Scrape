"""西班牙文推廣尾段即使與正文同一行，也必須排除。"""
import pytest

from motogp_scraper.extractors import clean_article_text_for_site, remove_motorsport_tail_noise
from motogp_scraper.models import ExtractedContent


@pytest.mark.parametrize("separator", [" ", "\n", "\n\n"])
@pytest.mark.parametrize("tail", [
    "Comparte o guarda este artículo Mejores comentarios Suscríbete y accede a Motorsport.com con tu ad-blocker.",
    "Suscríbete y accede a Motorsport.com con tu ad-blocker. Desde la Fórmula 1 hasta MotoGP, informamos directamente desde el paddock.",
    "Desde la Fórmula 1 hasta MotoGP, informamos directamente desde el paddock porque amamos nuestro deporte, igual que tú.",
    "Comparte\u00a0o guarda este artículo Más información.",
])
def test_spanish_promotion_tail(separator, tail):
    body = '"Encaro este fin de semana como si fuera cualquier otro", remachó el chico de Rimini.'
    assert remove_motorsport_tail_noise(body + separator + tail) == body


def test_preserves_ordinary_motorsport_mentions():
    body = "Bezzecchi explicó a Motorsport.com sus comentarios sobre MotoGP y la Fórmula 1."
    assert remove_motorsport_tail_noise(body) == body


def test_spanish_source_cleanup_keeps_method():
    content = ExtractedContent(text="Noticia. Comparte o guarda este artículo Mejores comentarios", method="test")
    result = clean_article_text_for_site(content, url="https://es.motorsport.com/motogp/news/example/")
    assert result.text == "Noticia."
    assert result.method == "test"
    assert clean_article_text_for_site(content, url="https://www.gpone.com/en/example/") == content
