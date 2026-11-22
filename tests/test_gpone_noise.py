"""GPone 社群署名與照片來源的清理回歸測試。"""

import pytest

from motogp_scraper.extractors import extract_article_text


@pytest.mark.parametrize("noise", [
    "<p>Un post condiviso da GPOne.com (@gponedotcom)</p>",
    "<p>Photocredit: Pier Luca Brunetti</p>",
    "<p>Photo credit: Another photographer</p>",
    "<p>A post shared by GPOne.com (@gponedotcom)</p>",
    "<p>Una publicación compartida por GPOne.com</p>",
    '<blockquote class="instagram-media"><p>View this post on Instagram</p><p>Social caption</p></blockquote>',
    "<p>Un post <a>condiviso da GPOne.com</a> (@gponedotcom)</p><p>Photocredit:&nbsp;Pier Luca Brunetti</p>",
])
def test_gpone_removes_noise_without_truncating_body(noise):
    markup = '<div id="block-gpone-content"><article><div><section><div></div><div>'
    markup += '<h2>Race analysis</h2><p>Alex was fast.</p>' + noise
    markup += '<p>Bezzecchi was faster.</p></div></section></div></article></div>'
    result = extract_article_text(markup, url="https://www.gpone.com/en/motogp/test.html")
    assert result.method == "gpone-lxml-sections"
    assert result.text == "Race analysis\n\nAlex was fast.\n\nBezzecchi was faster."


def test_gpone_preserves_credit_mentioned_in_body():
    markup = '''<div id="block-gpone-content"><article><div><section><div></div><div>
    <p>Alex gave credit to his team.</p><p>The Photocredit: field identifies the photographer.</p>
    </div></section></div></article></div>'''
    result = extract_article_text(markup, url="https://www.gpone.com/en/motogp/test.html")
    assert result.text == "Alex gave credit to his team.\n\nThe Photocredit: field identifies the photographer."
