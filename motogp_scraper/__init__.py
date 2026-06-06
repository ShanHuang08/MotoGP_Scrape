"""
motogp_scraper 套件入口

將 MotoGPScraper 類別匯出，讓外部可以直接從套件匯入使用：
  from motogp_scraper import MotoGPScraper
"""

# 匯出主控制器類別，讓外部可以直接使用
from .runner import MotoGPScraper

# __all__ 定義了 "from motogp_scraper import *" 時會匯出哪些名稱
__all__ = ["MotoGPScraper"]
