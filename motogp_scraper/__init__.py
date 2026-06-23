"""MotoGP scraper package."""

from __future__ import annotations

__all__ = ["MotoGPScraper"]


def __getattr__(name: str):
    if name == "MotoGPScraper":
        from .runner import MotoGPScraper

        return MotoGPScraper
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
