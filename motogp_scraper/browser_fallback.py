"""Optional browser-based fallback fetchers for bot-protected pages."""

from __future__ import annotations

import sys
from pathlib import Path


GPONE_BROWSER_PROFILE_DIR = Path(".gpone_browser_profile")
GPONE_BROWSER_TIMEOUT_MS = 30_000


def fetch_gpone_article_with_playwright(url: str) -> str | None:
    """Fetch a GPone article with a real browser when normal HTTP gets blocked."""
    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        print(f"[WARN] Playwright fallback unavailable for GPone: {exc}", file=sys.stderr)
        return None

    try:
        with sync_playwright() as playwright:
            context = _launch_gpone_context(playwright)
            page = context.new_page()
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=GPONE_BROWSER_TIMEOUT_MS)
                _wait_for_gpone_article(page, PlaywrightTimeoutError)
                markup = page.content()
            finally:
                context.close()
    except Exception as exc:
        print(f"[WARN] Playwright fallback failed for GPone {url}: {exc}", file=sys.stderr)
        return None

    return markup


def _launch_gpone_context(playwright):
    kwargs = {
        "user_data_dir": str(GPONE_BROWSER_PROFILE_DIR),
        "headless": False,
        "locale": "en-US",
        "viewport": {"width": 1366, "height": 900},
    }
    try:
        return playwright.chromium.launch_persistent_context(channel="chrome", **kwargs)
    except Exception:
        return playwright.chromium.launch_persistent_context(**kwargs)


def _wait_for_gpone_article(page, timeout_error_type) -> None:
    selectors = (
        "#block-gpone-content article",
        "#block-gpone-content",
        "article",
    )
    for selector in selectors:
        try:
            page.wait_for_selector(selector, timeout=10_000)
            return
        except timeout_error_type:
            continue
    page.wait_for_timeout(5_000)
