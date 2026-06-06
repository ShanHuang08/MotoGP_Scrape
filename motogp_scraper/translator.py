"""
translator.py - 文章翻譯器（預留模組）

這個檔案是為了未來的 LLM（大型語言模型）翻譯功能預留的接口。
目前尚未實作，只提供了一個 ArticleTranslator 類別的骨架。

未來可以在 translate() 方法中接入 OpenAI 或其他 LLM API，
來將英文/西班牙文新聞翻譯成中文。

目前狀態：尚未實作（調用會擲出 NotImplementedError）

依賴關係：
- 目前未被任何模組調用
"""

from __future__ import annotations


# ============================================================
# ArticleTranslator - 文章翻譯器（預留類別）
# ============================================================
# 未來可以在這裡接入 LLM API，實作翻譯功能。
# translate() 方法預期接收文章文字和目標語言，回傳翻譯結果。
# ============================================================
class ArticleTranslator:
    """未來 LLM 翻譯功能的預留接口"""

    def translate(self, text: str, *, target_language: str = "zh-TW") -> str:
        raise NotImplementedError(
            "LLM translation is intentionally not implemented yet. "
            "Plug an OpenAI/other LLM client in this method later."
        )
