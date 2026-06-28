"""
test_extractors.py - HTML 內容提取器的單元測試 (pytest)

測試範圍（第一 + 第二梯隊）：
- normalize_url()                 : 相對 URL 轉絕對 URL + 過濾無效連結
- extract_published_at_with_lxml(): 從 HTML meta/JSON-LD/URL 路徑提取日期
- remove_motorsport_tail_noise()  : Motorsport.com 尾部雜訊截斷

執行方式：
    python main.py --unit-test
    或
    pytest tests/test_extractors.py -v
"""

from __future__ import annotations

import pytest

from motogp_scraper.extractors import (
    normalize_url,
    extract_links_with_lxml,
    extract_image_url_with_lxml,
    extract_published_at_with_lxml,
    remove_motorsport_tail_noise,
    extract_article_text,
    clean_article_text_for_site,
    is_blocked_page,
)
from motogp_scraper.models import ExtractedContent


# ============================================================
# normalize_url 測試
# ============================================================
class TestNormalizeUrl:
    """normalize_url - URL 正規化與過濾"""

    # ---- 正常情況 ----

    def test_absolute_url_passthrough(self) -> None:
        """絕對 URL 原樣回傳"""
        url = normalize_url("https://example.com", "https://other.com/path")
        assert url == "https://other.com/path"

    def test_relative_url_resolved(self) -> None:
        """相對 URL 轉為絕對 URL"""
        url = normalize_url("https://example.com/news/", "/motogp/article")
        assert url == "https://example.com/motogp/article"

    def test_relative_path_resolved(self) -> None:
        """相對路徑轉為絕對 URL"""
        url = normalize_url("https://example.com/news/index.html", "article.html")
        assert url == "https://example.com/news/article.html"

    def test_http_scheme_preserved(self) -> None:
        """http:// scheme 保留"""
        url = normalize_url("https://example.com", "http://other.com/page")
        assert url == "http://other.com/page"

    # ---- 過濾無效連結（parametrize）----

    @pytest.mark.parametrize(
        "href",
        ["#section", "mailto:foo@bar.com", "javascript:void(0)", "tel:+1234567890",
         "", None, "   "],
        ids=["hash", "mailto", "javascript", "tel", "empty", "none", "whitespace"],
    )
    def test_invalid_hrefs_return_none(self, href) -> None:
        """無效連結（#/mailto/javascript/tel/空/None/空白）全部回傳 None"""
        assert normalize_url("https://example.com", href) is None

    # ---- 空白清理 ----

    def test_leading_trailing_whitespace_stripped(self) -> None:
        """前後空白被清理"""
        url = normalize_url("https://example.com", "  /path  ")
        assert url == "https://example.com/path"

    # ---- 更多 parametrize 測試 ----

    @pytest.mark.parametrize(
        "base, href, expected",
        [
            ("https://a.com/page/", "other.html", "https://a.com/page/other.html"),
            ("https://a.com/dir/file.html", "../other.html", "https://a.com/other.html"),
            ("https://a.com", "//cdn.example.com/script.js", "https://cdn.example.com/script.js"),
        ],
        ids=["relative-sibling", "parent-dir", "protocol-relative"],
    )
    def test_url_resolution_variants(self, base: str, href: str, expected: str) -> None:
        """參數化測試：多種 URL 解析情境"""
        assert normalize_url(base, href) == expected


class TestExtractLinksWithLxml:
    """extract_links_with_lxml - listing link extraction."""

    def test_the_race_listing_xpaths(self) -> None:
        markup = """
        <div id="lt-user-email"><div><section><div>
          <div></div>
          <div>
            <article><a href="/motogp/lead-story/"><div><h3>Lead story</h3></div></a></article>
          </div>
          <div>
            <article><a href="/motogp/second-story/"><div><h3>Second story</h3></div></a></article>
            <article><a href="/motogp/third-story/"><div><h3>Third story</h3></div></a></article>
          </div>
        </div></section></div></div>
        """
        links = extract_links_with_lxml(
            markup,
            base_url="https://www.the-race.com/motogp",
            xpaths=(
                "//*[@id='lt-user-email']/div/section/div[1]/div[2]/article/a/@href",
                "//*[@id='lt-user-email']/div/section/div[1]/div[3]/article[1]/a/@href",
                "//*[@id='lt-user-email']/div/section/div[1]/div[3]/article[2]/a/@href",
            ),
        )
        assert links == [
            "https://www.the-race.com/motogp/lead-story/",
            "https://www.the-race.com/motogp/second-story/",
            "https://www.the-race.com/motogp/third-story/",
        ]


# ============================================================
# extract_published_at_with_lxml 測試
# ============================================================
class TestExtractPublishedAt:
    """extract_published_at_with_lxml - 從 HTML 提取發佈日期"""

    def test_meta_article_published_time(self) -> None:
        """從 <meta property='article:published_time'> 提取 ISO 日期"""
        html = """
        <html>
        <head>
            <meta property="article:published_time" content="2024-06-01T12:00:00Z">
        </head>
        <body></body>
        </html>
        """
        result = extract_published_at_with_lxml(html)
        assert result is not None
        assert (result.year, result.month, result.day) == (2024, 6, 1)
        assert (result.hour, result.minute, result.second) == (12, 0, 0)

    def test_meta_pubdate(self) -> None:
        """從 <meta name='pubdate'> 提取日期"""
        html = """
        <html>
        <head>
            <meta name="pubdate" content="2024-06-01T12:00:00+02:00">
        </head>
        <body></body>
        </html>
        """
        result = extract_published_at_with_lxml(html)
        assert result is not None
        assert (result.year, result.month, result.day) == (2024, 6, 1)

    def test_time_element_datetime(self) -> None:
        """從 <time datetime='...'> 提取日期"""
        html = """
        <html>
        <body>
            <time datetime="2024-06-01T10:30:00Z">June 1, 2024</time>
        </body>
        </html>
        """
        result = extract_published_at_with_lxml(html)
        assert result is not None
        assert result.hour == 10

    def test_json_ld_date_published(self) -> None:
        """從 JSON-LD script 的 datePublished 提取日期"""
        html = """
        <html>
        <head>
            <script type="application/ld+json">
            {"@type": "NewsArticle", "datePublished": "2024-06-01T12:00:00Z"}
            </script>
        </head>
        <body></body>
        </html>
        """
        result = extract_published_at_with_lxml(html)
        assert result is not None
        assert (result.year, result.month, result.day) == (2024, 6, 1)

    def test_json_ld_graph_array(self) -> None:
        """JSON-LD 含 @graph 陣列時能遞迴找到日期"""
        html = """
        <html>
        <head>
            <script type="application/ld+json">
            {
                "@context": "https://schema.org",
                "@graph": [
                    {"@type": "WebPage"},
                    {"@type": "NewsArticle", "datePublished": "2024-06-15T08:00:00Z"}
                ]
            }
            </script>
        </head>
        <body></body>
        </html>
        """
        result = extract_published_at_with_lxml(html)
        assert result is not None
        assert result.day == 15

    def test_url_date_pattern(self) -> None:
        """從 URL 路徑 /2024/06/01/ 提取日期"""
        html = "<html><body></body></html>"
        result = extract_published_at_with_lxml(
            html, url="https://example.com/2024/06/01/some-article"
        )
        assert result is not None
        assert (result.year, result.month, result.day) == (2024, 6, 1)

    def test_no_date_returns_none(self) -> None:
        """HTML 中無任何日期資訊回傳 None"""
        html = "<html><body><p>No date here</p></body></html>"
        assert extract_published_at_with_lxml(html) is None

    def test_invalid_json_ld_returns_none(self) -> None:
        """JSON-LD 格式錯誤不會崩潰，回傳 None"""
        html = """
        <html>
        <head>
            <script type="application/ld+json">
            {invalid json content
            </script>
        </head>
        <body></body>
        </html>
        """
        assert extract_published_at_with_lxml(html) is None

    def test_default_timezone_applied(self) -> None:
        """無時區的日期套用指定的預設時區"""
        html = """
        <html>
        <head>
            <meta property="article:published_time" content="2024-06-01T12:00:00">
        </head>
        <body></body>
        </html>
        """
        result = extract_published_at_with_lxml(html, default_timezone="Europe/Rome")
        assert result is not None
        assert result.tzinfo is not None

    # ---- 新增：parametrize 測試多種 meta 標籤 ----

    @pytest.mark.parametrize(
        "meta_tag",
        [
            '<meta property="article:published_time" content="2024-06-01T12:00:00Z">',
            '<meta property="og:published_time" content="2024-06-01T12:00:00Z">',
            '<meta name="pubdate" content="2024-06-01T12:00:00Z">',
            '<meta name="publishdate" content="2024-06-01T12:00:00Z">',
            '<meta name="date" content="2024-06-01T12:00:00Z">',
            '<meta itemprop="datePublished" content="2024-06-01T12:00:00Z">',
        ],
        ids=["article:published_time", "og:published_time", "pubdate",
             "publishdate", "date", "datePublished"],
    )
    def test_various_meta_tags(self, meta_tag: str) -> None:
        """參數化測試：所有支援的 meta 標籤格式都能提取日期"""
        html = f"<html><head>{meta_tag}</head><body></body></html>"
        result = extract_published_at_with_lxml(html)
        assert result is not None
        assert result.year == 2024


class TestExtractImageUrl:
    """extract_image_url_with_lxml - article hero image extraction."""

    def test_crash_xpath_image(self) -> None:
        markup = """
        <div id="lbs-content"><div><div><div>
          <figure><picture><img src="/images/crash.jpg"></picture></figure>
        </div></div></div></div>
        """
        result = extract_image_url_with_lxml(
            markup,
            base_url="https://www.crash.net/motogp/news/test",
        )
        assert result == "https://www.crash.net/images/crash.jpg"

    def test_gpone_xpath_image(self) -> None:
        markup = """
        <div id="block-gpone-content">
          <article><figure><a><picture><img src="https://cdn.gpone.com/main.jpg"></picture></a></figure></article>
        </div>
        """
        result = extract_image_url_with_lxml(
            markup,
            base_url="https://www.gpone.com/en/news/test",
        )
        assert result == "https://cdn.gpone.com/main.jpg"

    def test_motorsport_xpath_srcset_image(self) -> None:
        markup = """
        <main id="main-content"><div></div><div></div><div>
          <article><div><div><div></div><div><picture>
            <img srcset="/photo-small.jpg 400w, /photo-large.jpg 1200w">
          </picture></div></div></div></article>
        </div></main>
        """
        result = extract_image_url_with_lxml(
            markup,
            base_url="https://www.motorsport.com/motogp/news/test",
        )
        assert result == "https://www.motorsport.com/photo-small.jpg"

    def test_the_race_xpath_image(self) -> None:
        markup = """
        <div id="lt-user-email"><div>
          <main><article><header>
            <figure><img src="/cdn-cgi/image/width=1200/images/hero.jpg"></figure>
          </header></article></main>
        </div></div>
        """
        result = extract_image_url_with_lxml(
            markup,
            base_url="https://www.the-race.com/motogp/test-story/",
        )
        assert result == "https://www.the-race.com/cdn-cgi/image/width=1200/images/hero.jpg"

    def test_falls_back_to_open_graph_image(self) -> None:
        markup = '<html><head><meta property="og:image" content="/fallback.jpg"></head></html>'
        result = extract_image_url_with_lxml(markup, base_url="https://example.com/article")
        assert result == "https://example.com/fallback.jpg"


# ============================================================
# remove_motorsport_tail_noise 測試
# ============================================================
class TestRemoveMotorsportTailNoise:
    """remove_motorsport_tail_noise - Motorsport.com 尾部雜訊截斷"""

    # ---- parametrize：所有截斷觸發詞 ----

    @pytest.mark.parametrize(
        "noise_line",
        [
            "Photos from the race.",
            "We want your opinion!",
            "Subscribe and access Motorsport.com",
            "Top Comments",
            "Become a subscriber.",
            "Share Or Save This Story",
            "Latest news",
            "Disable your adblocker.",
        ],
        ids=["photos", "opinion", "subscribe", "comments",
             "subscriber", "share", "latest", "adblocker"],
    )
    def test_noise_triggers_cut(self, noise_line: str) -> None:
        """參數化測試：所有截斷觸發詞都能正確截斷"""
        text = f"Article body.\n{noise_line}\nShould be removed."
        result = remove_motorsport_tail_noise(text)
        assert result == "Article body."

    def test_in_photos_suffix_triggers_cut(self) -> None:
        """遇到 ', in photos' 結尾截斷"""
        text = "Article text.\nHungarian GP - Friday, in photos\nExtra."
        result = remove_motorsport_tail_noise(text)
        assert result == "Article text."

    def test_clean_text_unchanged(self) -> None:
        """乾淨的文字不受影響"""
        text = "This is a clean article.\nWith multiple paragraphs.\nAll good."
        assert remove_motorsport_tail_noise(text) == text

    def test_empty_lines_preserved(self) -> None:
        """文章中的空行被保留"""
        text = "First paragraph.\n\nSecond paragraph."
        assert remove_motorsport_tail_noise(text) == text

    def test_empty_input(self) -> None:
        """空字串回傳空字串"""
        assert remove_motorsport_tail_noise("") == ""

    def test_only_noise_returns_empty(self) -> None:
        """第一行就是噪音，回傳空字串"""
        text = "Photos from the race.\nMore noise."
        assert remove_motorsport_tail_noise(text) == ""

    def test_feature_prefix_triggers_cut(self) -> None:
        """遇到 'Feature' 前綴截斷"""
        text = "Good content.\nFeature: Best of 2024\nMore."
        assert remove_motorsport_tail_noise(text) == "Good content."

    def test_what_would_you_like_triggers_cut(self) -> None:
        """遇到 'What would you like to see on Motorsport.com?' 截斷"""
        text = "Race recap.\nWhat would you like to see on Motorsport.com?\nSurvey."
        assert remove_motorsport_tail_noise(text) == "Race recap."


# ============================================================
# extract_article_text 測試
# ============================================================
class TestExtractArticleText:
    """extract_article_text - 提取文章內文的主入口函數"""

    def test_returns_extracted_content(self) -> None:
        """回傳 ExtractedContent 物件"""
        html = "<html><body><article><p>This is a test article body with enough text.</p></article></body></html>"
        result = extract_article_text(html)
        assert isinstance(result, ExtractedContent)
        assert result.text
        assert result.method

    def test_empty_html_returns_empty_method(self) -> None:
        """空 HTML 回傳 method='empty'"""
        html = "<html><body></body></html>"
        result = extract_article_text(html)
        assert result.method == "empty"
        assert result.text == ""

    def test_blocked_page_returns_blocked_method(self) -> None:
        html = """
        <html>
          <head><title>Just a moment...</title></head>
          <body>Enable JavaScript and cookies to continue</body>
        </html>
        """
        result = extract_article_text(
            html,
            url="https://www.gpone.com/it/2026/06/23/motogp/example.html",
        )
        assert result.method == "blocked-page"
        assert result.text == ""

    def test_blocked_text_marker_detected(self) -> None:
        assert is_blocked_page("Enable JavaScript and cookies to continue")

    def test_article_with_paragraphs(self) -> None:
        """有 <article> 和 <p> 的 HTML 能提取內文"""
        html = """
        <html><body>
        <article>
            <p>This is the first paragraph of the MotoGP article with enough content.</p>
            <p>This is the second paragraph with more details about the race.</p>
        </article>
        </body></html>
        """
        result = extract_article_text(html)
        assert result.text
        assert result.method != "empty"

    def test_gpone_url_uses_gpone_extractor(self) -> None:
        """gpone.com 的 URL 使用 GPone 專用提取器"""
        html = """
        <html><body>
        <div id="block-gpone-content">
            <article><div>
                <section><div></div><div><p>GPone article paragraph one.</p></div></section>
                <section><div></div><div><p>GPone article paragraph two.</p></div></section>
            </div></article>
        </div>
        </body></html>
        """
        result = extract_article_text(html, url="https://www.gpone.com/en/news/article")
        assert result.method == "gpone-lxml-sections"

    def test_gpone_extractor_includes_h2_emphasis_text(self) -> None:
        """GPone 的大字體 h2/strong 內容也要被抽進正文。"""
        html = """
        <html><body>
        <div id="block-gpone-content">
            <article><div>
                <section><div></div><div>
                    <h2><strong>Large intro line one.</strong></h2>
                    <h2><strong>Large intro line two.</strong></h2>
                    <p>Regular paragraph one.</p>
                </div></section>
                <section><div></div><div>
                    <h2>Large section two line one.</h2>
                    <h2><strong>Large section two line two.</strong></h2>
                    <h2><strong>Large section two line three.</strong></h2>
                    <p>Regular paragraph two.</p>
                </div></section>
            </div></article>
        </div>
        </body></html>
        """
        result = extract_article_text(html, url="https://www.gpone.com/en/news/article")
        assert result.method == "gpone-lxml-sections"
        assert result.text.splitlines() == [
            "Large intro line one.",
            "",
            "Large intro line two.",
            "",
            "Regular paragraph one.",
            "",
            "Large section two line one.",
            "",
            "Large section two line two.",
            "",
            "Large section two line three.",
            "",
            "Regular paragraph two.",
        ]

    def test_non_gpone_url_skips_gpone_extractor(self) -> None:
        """非 gpone.com 的 URL 不使用 GPone 提取器"""
        html = "<html><body><article><p>Normal article text here.</p></article></body></html>"
        result = extract_article_text(html, url="https://crash.net/motogp/news")
        assert result.method != "gpone-lxml-sections"

    def test_the_race_url_uses_section_extractor(self) -> None:
        html = """
        <html><body>
        <div id="lt-user-email"><div>
          <main><article>
            <section>
              <p>First The Race paragraph with enough useful article content.</p>
              <h2>Technical background</h2>
              <p>Second The Race paragraph with the key MotoGP explanation.</p>
              <section class="latest-stories latest-stories-mid">
                <article><a><h3>Recommended story should not appear.</h3></a></article>
              </section>
            </section>
          </article></main>
        </div></div>
        </body></html>
        """
        result = extract_article_text(
            html,
            url="https://www.the-race.com/motogp/ducatis-trick-ride-height-device-addition-revealed/",
        )
        assert result.method == "the-race-lxml-section"
        assert "First The Race paragraph" in result.text
        assert "Technical background" in result.text
        assert "Recommended story" not in result.text

    def test_motogpnews_url_uses_article_extractor(self) -> None:
        html = """
        <html><body>
        <main id="main-content">
          <div></div><div></div><div></div>
          <div>
            <div>
              <article id="post-99999">
                <section>Talking point should not appear.</section>
                <p>First MotoGPNews paragraph with useful article text.</p>
                <ul><li>Read more should not appear.</li></ul>
                <h2>Important MotoGPNews subheading</h2>
                <p>Second MotoGPNews paragraph with more useful details.</p>
                <div>Newsletter should not appear.</div>
              </article>
            </div>
          </div>
        </main>
        </body></html>
        """
        result = extract_article_text(
            html,
            url="https://www.motogpnews.com/2026/06/26/example-story/",
        )
        assert result.method == "motogpnews-lxml-article"
        assert "First MotoGPNews paragraph" in result.text
        assert "Important MotoGPNews subheading" in result.text
        assert "Second MotoGPNews paragraph" in result.text
        assert "Talking point" not in result.text
        assert "Read more" not in result.text
        assert "Newsletter" not in result.text


# ============================================================
# clean_article_text_for_site 測試
# ============================================================
class TestCleanArticleTextForSite:
    """clean_article_text_for_site - 依網站清理抽取雜訊"""

    def test_motorsport_url_cleans_noise(self, make_extracted) -> None:
        """motorsport.com 的 URL 會清理尾部雜訊"""
        content = make_extracted(text="Good article.\nPhotos from the race.\nNoise.")
        result = clean_article_text_for_site(content, url="https://www.motorsport.com/motogp/news/test")
        assert result.text == "Good article."
        assert result.method == content.method

    def test_non_motorsport_url_unchanged(self, make_extracted) -> None:
        """非 motorsport.com 的 URL 不清理"""
        content = make_extracted(text="Good article.\nPhotos from the race.\nMore.")
        result = clean_article_text_for_site(content, url="https://crash.net/news")
        assert result.text == content.text
        assert result.method == content.method

    def test_none_url_unchanged(self, make_extracted) -> None:
        """url=None 不清理"""
        content = make_extracted(text="Good article.\nPhotos from the race.")
        result = clean_article_text_for_site(content, url=None)
        assert result.text == content.text

    def test_method_preserved_after_cleaning(self, make_extracted) -> None:
        """清理後 method 不變"""
        content = make_extracted(text="Text.\nTop Comments\nNoise.", method="trafilatura")
        result = clean_article_text_for_site(content, url="https://www.motorsport.com/news")
        assert result.method == "trafilatura"
