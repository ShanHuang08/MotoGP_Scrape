"""
run_tests.py - 單元測試執行入口 (pytest)

使用 pytest 自動發現並執行 tests/ 資料夾下所有 test_*.py 測試檔案。

使用方式：
    python run_tests.py            # 執行所有測試
    python run_tests.py -v         # 詳細輸出模式
    或透過 CLI：
    python main.py --unit-test     # 透過命令行介面執行
"""

from __future__ import annotations

import sys

import pytest


def run_all_tests(verbosity: int = 2) -> bool:
    """
    使用 pytest 執行 tests/ 資料夾下所有單元測試。

    :param verbosity: 輸出詳細程度（1=簡潔, 2=詳細）
    :return: 所有測試是否全部通過
    """
    args = [
        "tests",
        f"-{'v' * verbosity}",       # -v 或 -vv
        "--tb=short",                 # 失敗時只顯示簡短 traceback
        "--no-header",                # 不顯示 pytest 標頭
        "-p", "no:cacheprovider",     # 不使用 .pytest_cache
    ]
    exit_code = pytest.main(args)
    return exit_code == 0


if __name__ == "__main__":
    verbose = "-v" in sys.argv
    success = run_all_tests(verbosity=2 if verbose else 1)
    sys.exit(0 if success else 1)
