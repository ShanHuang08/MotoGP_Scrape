"""
test_reporter.py - 報告生成器輔助函數的單元測試 (pytest)

測試範圍（第一梯隊）：
- _split_markdown_table_row() : Markdown 表格行切割 + escaped pipe 支援
- _normalize_row()            : 確保每列欄位數一致

執行方式：
    python main.py --unit-test
    或
    pytest tests/test_reporter.py -v
"""

from __future__ import annotations

import pytest

from motogp_scraper.reporter import (
    _split_markdown_table_row,
    _normalize_row,
    _format_table_cell,
    build_report_html,
)


# ============================================================
# _split_markdown_table_row 測試
# ============================================================
class TestSplitMarkdownTableRow:
    """_split_markdown_table_row - 切開 Markdown 表格行"""

    def test_basic_row(self) -> None:
        """基本三欄位切割"""
        row = "| Title | Link | Date |"
        assert _split_markdown_table_row(row) == ["Title", "Link", "Date"]

    def test_single_column(self) -> None:
        """單欄位"""
        row = "| Title |"
        assert _split_markdown_table_row(row) == ["Title"]

    def test_escaped_pipe_preserved(self) -> None:
        """被 escape 的 \\| 不會被當作欄位分隔符"""
        row = "| A \\| B | C |"
        assert _split_markdown_table_row(row) == ["A | B", "C"]

    def test_multiple_escaped_pipes(self) -> None:
        """多個 escaped pipe 都能正確處理"""
        row = "| A \\| B \\| C | D |"
        assert _split_markdown_table_row(row) == ["A | B | C", "D"]

    def test_empty_cells(self) -> None:
        """空欄位保留為空字串"""
        row = "| A | | C |"
        assert _split_markdown_table_row(row) == ["A", "", "C"]

    def test_whitespace_trimmed(self) -> None:
        """欄位前後空白被去除"""
        row = "|  A  |  B  |"
        assert _split_markdown_table_row(row) == ["A", "B"]

    def test_without_leading_trailing_pipe(self) -> None:
        """沒有前後 pipe 也能正常處理"""
        row = "A | B | C"
        assert _split_markdown_table_row(row) == ["A", "B", "C"]

    def test_separator_row(self) -> None:
        """分隔線行（---）"""
        row = "|---:|---|---|"
        assert _split_markdown_table_row(row) == ["---:", "---", "---"]

    def test_url_in_cell(self) -> None:
        """包含 URL 的欄位"""
        row = "| Title | https://example.com/news | 2024-06-01 |"
        result = _split_markdown_table_row(row)
        assert result[1] == "https://example.com/news"

    def test_markdown_link_in_cell(self) -> None:
        """包含 Markdown 連結的欄位"""
        row = "| Title | [link](https://example.com) |"
        result = _split_markdown_table_row(row)
        assert result[1] == "[link](https://example.com)"

    # ---- parametrize 測試 ----

    @pytest.mark.parametrize(
        "row, expected_count",
        [
            ("| A | B | C | D |", 4),
            ("| X |", 1),
            ("| 1 | 2 | 3 | 4 | 5 | 6 |", 6),
        ],
        ids=["4-col", "1-col", "6-col"],
    )
    def test_column_count(self, row: str, expected_count: int) -> None:
        """參數化測試：不同欄位數量的表格行"""
        assert len(_split_markdown_table_row(row)) == expected_count


# ============================================================
# _normalize_row 測試
# ============================================================
class TestNormalizeRow:
    """_normalize_row - 確保每列欄位數與表頭一致"""

    def test_exact_width_unchanged(self) -> None:
        """欄位數等於 width 時不改變"""
        row = ["A", "B", "C"]
        assert _normalize_row(row, 3) == ["A", "B", "C"]

    def test_too_few_padded_with_empty(self) -> None:
        """欄位數少於 width 時補空字串"""
        row = ["A"]
        assert _normalize_row(row, 3) == ["A", "", ""]

    def test_too_many_truncated(self) -> None:
        """欄位數多於 width 時截斷"""
        row = ["A", "B", "C", "D", "E"]
        assert _normalize_row(row, 3) == ["A", "B", "C"]

    def test_empty_row_padded(self) -> None:
        """空列表補滿空字串"""
        assert _normalize_row([], 2) == ["", ""]

    def test_width_one(self) -> None:
        """width=1 只保留第一個欄位"""
        row = ["A", "B"]
        assert _normalize_row(row, 1) == ["A"]

    # ---- parametrize 測試 ----

    @pytest.mark.parametrize(
        "row, width, expected_len",
        [
            (["A"], 5, 5),
            (["A", "B", "C", "D"], 2, 2),
            ([], 3, 3),
        ],
        ids=["pad-3", "truncate-2", "empty-pad-3"],
    )
    def test_normalize_length(self, row: list[str], width: int, expected_len: int) -> None:
        """參數化測試：normalize 後長度一定等於 width"""
        assert len(_normalize_row(row, width)) == expected_len


def test_table_url_cell_uses_source_label() -> None:
    url = (
        "https://es.motorsport.com/motogp/news/martin-vuelve-pole-position-assen-resultados-"
        "clasificacion-motogp/10833862/?utm_source=RSS&utm_medium=referral"
    )

    rendered = _format_table_cell(url)

    assert 'href="https://es.motorsport.com/motogp/news/' in rendered
    assert "utm_source=RSS&amp;utm_medium=referral" in rendered
    assert ">motorsport es</a>" in rendered
    assert "utm_source=RSS" not in rendered.split(">", 1)[1]


def test_html_table_has_compact_link_and_single_line_published_column() -> None:
    markdown = """
# MotoGP Latest News

Generated at: 2026-06-27T10:00:00

## Latest News

| # | Title | Link | Published At (UTC+8) |
|---:|---|---|---|
| 1 | Test title | https://www.crash.net/motogp/news/1099562/1/example | 2026-06-27T18:00:00+08:00 |

## Article Text
""".strip()

    rendered = build_report_html(markdown)

    assert '<col class="col-title">' in rendered
    assert '<col class="col-link">' in rendered
    assert '<col class="col-published">' in rendered
    assert '<td class="col-link"><a href="https://www.crash.net/motogp/news/1099562/1/example"' in rendered
    assert ">crash.net</a>" in rendered
    assert 'td class="col-published"' in rendered


def test_html_report_includes_motogp_favicons() -> None:
    rendered = build_report_html("# MotoGP Latest News")

    assert (
        '<link rel="icon" type="image/png" sizes="16x16" '
        'href="https://static.dorna.com/assets/logos/mgp/brand/mgp-favicon-16x16.png">'
        in rendered
    )
    assert (
        '<link rel="icon" type="image/png" sizes="32x32" '
        'href="https://static.dorna.com/assets/logos/mgp/brand/mgp-favicon-32x32.png">'
        in rendered
    )
