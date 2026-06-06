from __future__ import annotations

from xml.etree import ElementTree

from .datetime_utils import parse_datetime
from .models import NewsItem


def _text(
    element: ElementTree.Element,
    path: str,
    namespaces: dict[str, str] | None = None,
) -> str | None:
    found = element.find(path, namespaces or {})
    if found is None or found.text is None:
        return None
    value = found.text.strip()
    return value or None


def parse_rss_items(
    markup: str,
    *,
    source_name: str,
    default_timezone: str = "UTC",
) -> list[NewsItem]:
    root = ElementTree.fromstring(markup)
    items: list[NewsItem] = []

    for element in root.findall(".//item"):
        title = _text(element, "title")
        link = _text(element, "link")
        if not title or not link:
            continue

        published = parse_datetime(
            _text(element, "pubDate")
            or _text(element, "published")
            or _text(element, "updated"),
            default_timezone=default_timezone,
        )
        items.append(
            NewsItem(
                source=source_name,
                title=title,
                url=link,
                published_at=published,
                summary=_text(element, "description"),
                raw_meta={"discovery_method": "rss"},
            )
        )

    atom_namespace = {"atom": "http://www.w3.org/2005/Atom"}
    for entry in root.findall(".//atom:entry", atom_namespace):
        title = _text(entry, "atom:title", atom_namespace)
        link = None
        for link_element in entry.findall("atom:link", atom_namespace):
            href = link_element.attrib.get("href")
            rel = link_element.attrib.get("rel", "alternate")
            if href and rel == "alternate":
                link = href
                break
        if not title or not link:
            continue

        items.append(
            NewsItem(
                source=source_name,
                title=title,
                url=link,
                published_at=parse_datetime(
                    _text(entry, "atom:published", atom_namespace)
                    or _text(entry, "atom:updated", atom_namespace),
                    default_timezone=default_timezone,
                ),
                summary=_text(entry, "atom:summary", atom_namespace),
                raw_meta={"discovery_method": "rss"},
            )
        )

    return items
