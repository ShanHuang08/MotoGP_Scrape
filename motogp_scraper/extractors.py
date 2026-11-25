"""
extractors.py - HTML 內容提取器

負責從 HTML 網頁中提取所需的內容，包含三大功能：

1. 提取新聞連結：extract_links_with_lxml() - 用 XPath 規則從 HTML 中提取連結
2. 提取文章內文：
   - extract_article_text()             - 主入口，自動選擇最佳提取方式
   - extract_article_with_trafilatura() - 用 trafilatura 庫提取（預設優先）
   - extract_gpone_article_sections()   - GPone 專用提取器
   - extract_article_with_lxml_fallback() - 用 lxml 提取 <p> 段落（備用）
3. 提取發佈日期：
   - extract_published_at_with_lxml()   - 從 meta 標籤、JSON-LD、URL 路徑提取日期
4. 網站專用清理：
   - clean_article_text_for_site()      - 依網站清理雜訊（目前針對 Motorsport.com）
   - remove_motorsport_tail_noise()     - 截斷 Motorsport.com 照片集/訂閱尾巴

提取策略：GPone 專用 → trafilatura → lxml 段落備用 → 空字串

依賴關係：
- 被 sources.py 調用（提取連結、標題、日期）
- 被 runner.py 調用（提取文章內文）
"""

from __future__ import annotations

from datetime import datetime
import json
import re
from typing import Iterable
from urllib.parse import urljoin, urlparse

from lxml import html
from trafilatura.core import extract as trafilatura_extract

from .datetime_utils import parse_datetime
from .models import ExtractedContent


BLOCKED_PAGE_MARKERS = (
    "just a moment...",
    "enable javascript and cookies to continue",
    "checking if the site connection is secure",
    "cf-browser-verification",
    "challenge-platform",
)


def is_blocked_page(markup_or_text: str) -> bool:
    """Return True when a site serves a bot-protection page instead of an article."""
    normalized = " ".join((markup_or_text or "").casefold().split())
    return any(marker in normalized for marker in BLOCKED_PAGE_MARKERS)


# ============================================================
# normalize_url - 將 URL 正規化
# ============================================================
# 將相對 URL 轉為絕對 URL，過濾掉 #, mailto:, javascript: 等無效連結。
# ============================================================
def normalize_url(base_url: str, href: str) -> str | None:
    href = (href or "").strip()
    if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
        return None

    absolute = urljoin(base_url, href)
    parsed = urlparse(absolute)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return absolute


def parse_html_document(markup: str) -> html.HtmlElement:
    """
    parse_html_document - 解析 HTML 內容為 HtmlElement

    :param markup: HTML 網頁內容
    :return: HtmlElement
    """
    return html.fromstring(markup)


# ============================================================
# extract_links_with_lxml - 用 XPath 規則從 HTML 中提取連結
# ============================================================
# 遍歷多個 XPath 規則，自動去重，將相對 URL 轉為絕對 URL。
# ============================================================
def extract_links_with_lxml(
    markup: str,
    *,
    base_url: str,
    xpaths: Iterable[str],
    limit: int | None = None,
) -> list[str]:
    """
    extract_links_with_lxml - 用 XPath 規則從 HTML 中提取連結

    :param markup: HTML 網頁內容
    :param base_url: 網頁的基底 URL，用於將相對 URL 轉為絕對 URL
    :param xpaths: 用於提取連結的 XPath 規則列表
    :param limit: 最多提取的連結數量限制
    :return: 連結清單
    """
    document = parse_html_document(markup)
    links: list[str] = []
    seen: set[str] = set()

    for xpath in xpaths:
        for raw_value in document.xpath(xpath):
            href = raw_value if isinstance(raw_value, str) else raw_value.get("href", "")
            url = normalize_url(base_url, href)
            if not url or url in seen:
                continue
            seen.add(url)
            links.append(url)
            if limit and len(links) >= limit:
                return links

    return links


# ============================================================
# extract_title_with_lxml - 用 XPath 規則提取文章標題
# ============================================================
# 先嘗試提供的 XPath，找不到則退回到 <title> 標籤。
# ============================================================
def extract_title_with_lxml(markup: str, xpaths: Iterable[str] = ()) -> str | None:
    # Challenge pages can contain a stale/embedded article fragment; never use
    # their generic page title as the article headline.
    if is_blocked_page(markup):
        return None
    document = parse_html_document(markup)
    for xpath in xpaths:
        values = document.xpath(xpath)
        for value in values:
            text = value if isinstance(value, str) else value.text_content()
            text = " ".join(text.split())
            if text:
                return text

    title_values = document.xpath("//title/text()")
    if title_values:
        title = " ".join(title_values[0].split())
        return title or None
    return None


def extract_image_url_with_lxml(markup: str, *, base_url: str) -> str | None:
    """Extract the primary image URL from supported article pages."""
    document = parse_html_document(markup)
    host = urlparse(base_url).netloc.lower()

    if host in {"motosan.es", "www.motosan.es"}:
        site_xpaths = ("//*[@id='content-wrapper']/div/div[1]/img",)
    elif "crash.net" in host:
        site_xpaths = ("//*[@id='lbs-content']/div[1]/div[1]/div/figure/picture/img",)
    elif "gpone.com" in host:
        site_xpaths = ("//*[@id='block-gpone-content']/article/figure/a/picture/img",)
    elif "the-race.com" in host:
        site_xpaths = ("//*[@id='lt-user-email']/div[1]/main/article/header/figure/img",)
    elif "motorsport.com" in host:
        site_xpaths = (
            "//*[@id='main-content']/div[3]/article/div/div/div[2]/div[1]/picture/img",
            "//*[@id='main-content']//article//picture/img",
        )
    else:
        site_xpaths = ()

    fallback_xpaths = (
        "//meta[@property='og:image']/@content",
        "//meta[@name='twitter:image']/@content",
    )
    for xpath in site_xpaths + fallback_xpaths:
        for raw_value in document.xpath(xpath):
            if isinstance(raw_value, str):
                candidates = (raw_value,)
            else:
                candidates = (
                    raw_value.get("src", ""),
                    raw_value.get("data-src", ""),
                    _first_srcset_url(raw_value.get("srcset", "")),
                    _first_srcset_url(raw_value.get("data-srcset", "")),
                )

            for candidate in candidates:
                url = normalize_url(base_url, candidate)
                if url:
                    return url

    return None


def _first_srcset_url(srcset: str) -> str:
    first_candidate = (srcset or "").split(",", 1)[0].strip()
    if not first_candidate:
        return ""
    return first_candidate.split(maxsplit=1)[0]


# ============================================================
# extract_published_at_with_lxml - 從 HTML 中提取文章發佈日期
# ============================================================
# 嘗試順序：
# 1. 各種 <meta> 標籤（article:published_time, og:published_time 等）
# 2. JSON-LD 結構化資料中的 datePublished 等欄位
# 3. URL 路徑中的日期模式（如 /2024/06/01/）
# ============================================================
def extract_published_at_with_lxml(
    markup: str,
    *,
    url: str | None = None,
    default_timezone: str = "UTC",
) -> datetime | None:
    document = parse_html_document(markup)
    xpaths = (
        "//meta[@property='article:published_time']/@content",
        "//meta[@property='og:published_time']/@content",
        "//meta[@name='pubdate']/@content",
        "//meta[@name='publishdate']/@content",
        "//meta[@name='date']/@content",
        "//meta[@itemprop='datePublished']/@content",
        "//time/@datetime",
        "//time/text()",
        "//*[contains(concat(' ', normalize-space(@class), ' '), ' date ')]/text()",
        "//*[contains(concat(' ', normalize-space(@class), ' '), ' submitted ')]/text()",
    )

    for xpath in xpaths:
        for raw_value in document.xpath(xpath):
            value = raw_value if isinstance(raw_value, str) else raw_value.text_content()
            parsed = parse_datetime(value, default_timezone=default_timezone)
            if parsed:
                return parsed

    for script in document.xpath("//script[@type='application/ld+json']/text()"):
        parsed = _extract_date_from_json_ld(script, default_timezone=default_timezone)
        if parsed:
            return parsed

    if url:
        match = re.search(r"/(20\d{2})/(\d{2})/(\d{2})/", url)
        if match:
            return parse_datetime("-".join(match.groups()), default_timezone=default_timezone)

    return None


# ============================================================
# _extract_date_from_json_ld - 從 JSON-LD 腳本中提取日期（私有函數）
# ============================================================
# 解析 <script type="application/ld+json"> 中的結構化資料，
# 找尋 datePublished/dateCreated/dateModified/uploadDate 等欄位。
# 支援 @graph 陣列的遞迴搜尋。
# ============================================================
def _extract_date_from_json_ld(script: str, *, default_timezone: str) -> datetime | None:
    try:
        payload = json.loads(script)
    except json.JSONDecodeError:
        return None

    candidates = payload if isinstance(payload, list) else [payload]
    while candidates:
        current = candidates.pop(0)
        if isinstance(current, dict):
            for key in ("datePublished", "dateCreated", "dateModified", "uploadDate"):
                parsed = parse_datetime(str(current.get(key) or ""), default_timezone=default_timezone)
                if parsed:
                    return parsed
            graph = current.get("@graph")
            if isinstance(graph, list):
                candidates.extend(graph)
        elif isinstance(current, list):
            candidates.extend(current)

    return None


# ============================================================
# extract_article_with_trafilatura - 用 trafilatura 庫提取文章內文
# ============================================================
# trafilatura 能智能識別文章主體，過濾廣告/導航欄。
# ============================================================
def extract_article_with_trafilatura(
    markup: str,
    *,
    url: str | None = None,
    include_comments: bool = False,
    include_tables: bool = False,
) -> ExtractedContent | None:
    text = trafilatura_extract(
        markup, # 原始 HTML 字串
        url=url, # 可選，該頁面的 URL（trafilatura 會用來輔助判斷連結）
        include_comments=include_comments, # 不要留言 
        include_tables=include_tables, # 不要表格 
        output_format="txt", # 輸出格式為純文字
        favor_recall=True, # 偏向「多抽」，寧可多保留內容也不要漏掉
    )
    if not text:
        return None

    cleaned = text.strip()
    if not cleaned:
        return None
    if is_blocked_page(cleaned):
        return ExtractedContent(text="", method="blocked-page")
    return ExtractedContent(text=cleaned, method="trafilatura")


# ============================================================
# extract_gpone_article_sections - GPone 專用文章提取器
# ============================================================
# GPone 的文章內文分散在 article/div[1]/section[*]/div[2]，
# trafilatura 無法完整處理，所以用專用 XPath 提取。
# ============================================================
def extract_gpone_article_sections(markup: str) -> ExtractedContent | None:
    """GPone 正文分散在 article/div[1]/section[*]/div[2]，先用專用 XPath 抽完整段落。"""
    document = parse_html_document(markup)
    section_nodes = document.xpath(
        "//*[@id='block-gpone-content']/article/div[1]/section/div[2]"
    )
    paragraphs: list[str] = []

    for section_node in section_nodes:
        # Instagram 嵌入區屬於社群內容，不是記者正文；保留區塊後的文字。
        for embed in section_node.xpath(
            ".//*[contains(concat(' ', normalize-space(@class), ' '), ' instagram-media ')]"
        ):
            embed.drop_tree()
        # GPone 的大字體重點常放在 h2/strong，正文在 p；照 DOM 順序一起保留。
        content_nodes = section_node.xpath(".//h2 | .//p")
        if content_nodes:
            candidates = [" ".join(node.text_content().split()) for node in content_nodes]
        else:
            candidates = [" ".join(section_node.text_content().split())]

        for candidate in candidates:
            # 僅排除獨立署名段落，不截斷後續正文，也不限定帳號或攝影師姓名。
            if re.match(
                r"^(?:Un post condiviso da\s+|A post shared by\s+|"
                r"Una publicación compartida por\s+|Photo\s*credit\s*[:@])",
                candidate, flags=re.IGNORECASE,
            ):
                continue
            if candidate and candidate not in paragraphs:
                paragraphs.append(candidate)

    text = "\n\n".join(paragraphs).strip()
    if not text:
        return None
    return ExtractedContent(text=text, method="gpone-lxml-sections")


def extract_the_race_article_section(markup: str) -> ExtractedContent | None:
    """Extract The Race article body and skip the embedded latest-stories block."""
    document = parse_html_document(markup)
    content_nodes = document.xpath(
        "//*[@id='lt-user-email']/div[1]/main/article/section"
        "//*[self::h2 or self::h3 or self::p or self::li or self::blockquote]"
        "[not(ancestor::section[contains(concat(' ', normalize-space(@class), ' '), ' latest-stories ')])]"
    )
    paragraphs: list[str] = []

    for node in content_nodes:
        text = " ".join(node.text_content().split())
        if text and text not in paragraphs:
            paragraphs.append(text)

    body = "\n\n".join(paragraphs).strip()
    if not body:
        return None
    return ExtractedContent(text=body, method="the-race-lxml-section")


def extract_motogpnews_article(markup: str) -> ExtractedContent | None:
    """Extract MotoGPNews body from article[id^='post-'] without related/newsletter blocks."""
    document = parse_html_document(markup)
    article_nodes = document.xpath("//*[@id='main-content']/div[4]//*[starts-with(@id, 'post-')]")
    if not article_nodes:
        article_nodes = document.xpath("//article[starts-with(@id, 'post-')]")
    if not article_nodes:
        return None

    paragraphs: list[str] = []
    for node in article_nodes[0].xpath("./p | ./h2 | ./h3 | ./blockquote"):
        text = " ".join(node.text_content().split())
        if text and text not in paragraphs:
            paragraphs.append(text)

    body = "\n\n".join(paragraphs).strip()
    if not body:
        return None
    return ExtractedContent(text=body, method="motogpnews-lxml-article")


def extract_motosan_article(markup: str) -> ExtractedContent | None:
    """保留正文直屬段落與小標，遇到作者介紹或底部分享區停止。"""
    document = parse_html_document(markup)
    roots = document.xpath("//*[contains(concat(' ', normalize-space(@class), ' '), ' entry-content ')]")
    if not roots:
        return None
    paragraphs: list[str] = []
    for node in roots[0].iterdescendants():
        classes = set((node.get("class") or "").split())
        if classes & {"saboxplugin-wrap", "addtoany_content_bottom"}:
            break
        # 排除巢狀廣告、圖說和推薦區塊，只擷取文章層級的文字。
        if node.getparent() is roots[0] and node.tag in {"p", "h2", "h3", "blockquote", "ul", "ol"}:
            text = " ".join(node.text_content().split())
            if text:
                paragraphs.append(text)
    # 只移除 Google 追蹤宣傳句；允許愛心符號、換行及連結標籤造成的空白差異。
    body = "\n\n".join(paragraphs)
    promotion = (
        r"¿TE\s+GUSTAN\s+LAS\s+MOTOS\s*[❤\ufe0f]*\s*\?\s*"
        r"Pídele\s+aquí\s+a\s+Google\s+que\s+te\s+enseñe\s+más\s+de\s+Motosan\s+"
        r"para\s+tener\s+siempre\s+las\s+últimas\s+noticias\."
    )
    body = re.sub(promotion, "", body, flags=re.IGNORECASE).strip()
    return ExtractedContent(text=body, method="motosan-lxml-article")


def can_extract_with_trafilatura(markup: str, *, url: str | None = None) -> bool:
    extracted = extract_article_with_trafilatura(markup, url=url)
    return bool(extracted and extracted.text)


# ============================================================
# extract_article_with_lxml_fallback - 備用方案：用 lxml 提取段落文字
# ============================================================
# 從 <article>/<main>/<p> 標籤中提取，只保留長度超過 40 字元的段落。
# ============================================================
def extract_article_with_lxml_fallback(markup: str) -> ExtractedContent | None:
    document = parse_html_document(markup)
    paragraphs = [
        " ".join(node.text_content().split())
        for node in document.xpath("//article//p | //main//p | //p")
    ]
    text = "\n\n".join(paragraph for paragraph in paragraphs if len(paragraph) > 40)
    if not text.strip():
        return None
    return ExtractedContent(text=text.strip(), method="lxml-paragraph-fallback")


# ============================================================
# extract_article_text - 提取文章內文的主入口函數
# ============================================================
# 提取策略（優先順序）：
# 1. GPone 專用提取器（如果是 gpone.com 的網址）
# 2. trafilatura（效果最好）
# 3. lxml 段落備用
# 4. 回傳空字串 method="empty"
# ============================================================
def remove_motorsport_image_blocks(markup: str) -> str:
    """先移除圖片區塊，避免圖說與攝影署名被抽取器合併進正文。"""
    document = parse_html_document(markup)
    # 主圖與內文圖片的容器不同；使用網站結構，不比對車手或攝影師姓名。
    nodes = document.xpath(
        "//*[@data-widget='image'] | "
        "//*[contains(concat(' ', normalize-space(@class), ' '), ' ms-entity-promo ')] | "
        "//figcaption | //script"
    )
    for node in nodes:
        # JSON-LD 的 articleBody 也含圖說，移除腳本以免備援抽取重新帶回雜訊。
        # drop_tree 會保留節點後的 tail，避免圖片後方正文被一併刪除。
        if node.getparent() is not None:
            node.drop_tree()
    return html.tostring(document, encoding="unicode")


def extract_article_text(markup: str, *, url: str | None = None) -> ExtractedContent:
    # Check before site-specific extractors, since stale article DOM can remain
    # inside an interstitial page and otherwise be mistaken for a real article.
    if is_blocked_page(markup):
        return ExtractedContent(text="", method="blocked-page")

    if url:
        host = urlparse(url).netloc
        if host.lower() in {"motosan.es", "www.motosan.es"}:
            motosan_extracted = extract_motosan_article(markup)
            if motosan_extracted is not None:
                return motosan_extracted
        # GPone 的主文不適合完全依賴 trafilatura，優先使用站內固定 section 結構。
        if "gpone.com" in host:
            gpone_extracted = extract_gpone_article_sections(markup)
            if gpone_extracted:
                return gpone_extracted
        if "the-race.com" in host:
            the_race_extracted = extract_the_race_article_section(markup)
            if the_race_extracted:
                return the_race_extracted
        if "motogpnews.com" in host:
            motogpnews_extracted = extract_motogpnews_article(markup)
            if motogpnews_extracted:
                return motogpnews_extracted

    if url:
        host = (urlparse(url).hostname or "").lower()
        if host == "motorsport.com" or host.endswith(".motorsport.com"):
            markup = remove_motorsport_image_blocks(markup)

    extracted = extract_article_with_trafilatura(markup, url=url)
    if extracted:
        return clean_article_text_for_site(extracted, url=url)

    fallback = extract_article_with_lxml_fallback(markup)
    if fallback:
        return clean_article_text_for_site(fallback, url=url)

    return ExtractedContent(text="", method="empty")


def clean_article_text_for_site(content: ExtractedContent, *, url: str | None = None) -> ExtractedContent:
    """依網站清理抽取雜訊，目前主要處理 Motorsport.com 的照片集和訂閱尾巴。"""
    if not url or "motorsport.com" not in urlparse(url).netloc:
        return content

    cleaned = remove_motorsport_tail_noise(content.text)
    return ExtractedContent(text=cleaned, method=content.method)


def remove_motorsport_tail_noise(text: str) -> str:
    """Motorsport.com 文章後段常接照片集、留言、訂閱提示，遇到這些段落就截斷。"""
    # 西班牙文推廣區可能被合併到正文同一行，因此用完整提示定位。
    # 不以 Motorsport.com、comentarios 等一般單字判斷，避免誤刪新聞內容。
    spanish_tail = re.search(
        r"(?<!\w)(?:Comparte\s+o\s+guarda\s+este\s+artículo|"
        r"Suscríbete\s+y\s+accede\s+a\s+Motorsport\.com|"
        r"Desde\s+la\s+Fórmula\s+1\s+hasta\s+MotoGP,\s+informamos\s+"
        r"directamente\s+desde\s+el\s+paddock)\b",
        text, flags=re.IGNORECASE,
    )
    if spanish_tail:
        text = text[:spanish_tail.start()].rstrip()
    stop_prefixes = (
        "Photos from ",
        "We want your opinion!",
        "What would you like to see on Motorsport.com?",
        "Share Or Save This Story",
        "Top Comments",
        "Latest news",
        "Feature",
        "Subscribe and access Motorsport.com",
        "Become a subscriber.",
        "Disable your adblocker.",
        "Mejores comentarios",
    )
    cleaned_lines: list[str] = []

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            cleaned_lines.append(line)
            continue
        if any(stripped.startswith(prefix) for prefix in stop_prefixes):
            break
        # 例如 "Hungarian GP - Friday, in photos"，賽站名稱會變，所以用結尾判斷。
        if stripped.endswith(", in photos"):
            break
        cleaned_lines.append(line)

    return "\n".join(cleaned_lines).strip()
