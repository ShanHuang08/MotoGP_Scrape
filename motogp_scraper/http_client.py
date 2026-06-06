"""
http_client.py - HTTP 客戶端（負責下載網頁的工具）

這個檔案封裝了所有 HTTP 請求的邏輯，負責去網站下載網頁內容。

主要功能：
1. fetch_bytes() - 下載原始 bytes 資料（自動偵測平台，Windows 用 curl，其他用 urllib）
2. fetch_text()  - 下載網頁並解碼為文字字串
3. decode_response_bytes() - 將 bytes 解碼為文字（自動偵測編碼）

為什麼 Windows 要用 curl？
因為 Windows 上的 Python urllib 有時會有 SSL 憑證問題，
所以改用 Windows 內建的 curl.exe 來避免這個問題。

依賴關係：
- 被 sources.py 和 runner.py 調用，用來下載網頁和 RSS 內容
"""

from __future__ import annotations

import platform
import subprocess
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


# ============================================================
# 預設的 HTTP 請求標頭（模仿瀏覽器，避免被網站擋掉）
# ============================================================
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0 Safari/537.36 MotoGPNewsScraper/1.0"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
}


# ============================================================
# FetchError - 自定義例外
# ============================================================
# 當 HTTP 請求失敗時擲出此例外
# ============================================================
class FetchError(RuntimeError):
    """當無法取得 HTTP 資源時擲出的例外"""


# ============================================================
# fetch_bytes - 下載網頁原始 bytes
# ============================================================
# 自動偵測作業系統：
# - Windows：使用 curl.exe 下載（避免 SSL 問題）
# - 其他系統：使用 Python 內建的 urllib 下載
#
# 參數：
#   url           - 要下載的網址
#   timeout       - 超時秒數（預設 20 秒）
#   retries       - 失敗時重試次數（預設 2 次）
#   delay_seconds - 重試間隔秒數（預設 1.0 秒，每次重試會加長）
#   headers       - 額外的 HTTP 標頭（可選）
#
# 回傳：下載到的 bytes 資料
# ============================================================
def fetch_bytes(
    url: str,
    *,
    timeout: int = 20,
    retries: int = 2,
    delay_seconds: float = 1.0,
    headers: dict[str, str] | None = None,
) -> bytes:
    # Windows 系統改用 curl.exe 下載
    if platform.system() == "Windows":
        return _fetch_bytes_with_curl(
            url,
            timeout=timeout,
            retries=retries,
            delay_seconds=delay_seconds,
            headers=headers,
        )

    # 合併預設標頭和自訂標頭
    request_headers = DEFAULT_HEADERS | (headers or {})
    last_error: Exception | None = None

    # 嘗試重試機製：失敗後等待並重試
    for attempt in range(retries + 1):
        try:
            request = Request(url, headers=request_headers)
            with urlopen(request, timeout=timeout) as response:
                return response.read()
        except (HTTPError, URLError, TimeoutError) as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(delay_seconds * (attempt + 1))

    raise FetchError(f"Could not fetch {url}: {last_error}") from last_error


# ============================================================
# fetch_text - 下載網頁並回傳文字字串
# ============================================================
# 與 fetch_bytes 類似，但會自動將 bytes 解碼為文字。
# Windows 系統同樣使用 curl.exe。
# ============================================================
def fetch_text(
    url: str,
    *,
    timeout: int = 20,
    retries: int = 2,
    encoding: str = "utf-8",
    headers: dict[str, str] | None = None,
) -> str:
    if platform.system() == "Windows":
        data = _fetch_bytes_with_curl(
            url,
            timeout=timeout,
            retries=retries,
            delay_seconds=1.0,
            headers=headers,
        )
        return decode_response_bytes(data, fallback_encoding=encoding)

    data = fetch_bytes(url, timeout=timeout, retries=retries, headers=headers)
    return decode_response_bytes(data, fallback_encoding=encoding)


# ============================================================
# decode_response_bytes - 將 bytes 解碼為文字
# ============================================================
# 嘗試順序：
# 1. 先用 charset_normalizer 庫自動偵測編碼
# 2. 如果失敗，嘗試多種常見編碼（utf-8, utf-8-sig, cp1252, latin-1）
# 3. 最後用 fallback 編碼 + errors="replace" 強制解碼
# ============================================================
def decode_response_bytes(data: bytes, *, fallback_encoding: str = "utf-8") -> str:
    try:
        from charset_normalizer import from_bytes

        best = from_bytes(data).best()
        if best is not None:
            return str(best)
    except Exception:
        pass

    for encoding in (fallback_encoding, "utf-8-sig", "cp1252", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode(fallback_encoding, errors="replace")


# ============================================================
# _fetch_bytes_with_curl - 使用 Windows curl.exe 下載（私有函數）
# ============================================================
# 在 Windows 上，Python 的 urllib 可能會有 SSL 憑證問題，
# 所以改用 Windows 10+ 內建的 curl.exe 來下載。
# 使用 --insecure 和 --ssl-no-revoke 來避免 SSL 驗證問題。
# ============================================================
def _fetch_bytes_with_curl(
    url: str,
    *,
    timeout: int,
    retries: int,
    delay_seconds: float = 1.0,
    headers: dict[str, str] | None = None,
) -> bytes:
    request_headers = DEFAULT_HEADERS | (headers or {})
    command = [
        "curl.exe",
        "--location",
        "--silent",
        "--show-error",
        "--ssl-no-revoke",
        "--insecure",
        "--max-time",
        str(timeout),
    ]
    for key, value in request_headers.items():
        command.extend(["--header", f"{key}: {value}"])
    command.append(url)

    last_error: Exception | None = None
    for attempt in range(retries + 1):
        completed = subprocess.run(command, capture_output=True)
        if completed.returncode == 0 and completed.stdout:
            return completed.stdout

        error_text = completed.stderr.decode("utf-8", errors="replace").strip()
        last_error = FetchError(error_text or f"curl exited with {completed.returncode}")
        if attempt < retries:
            time.sleep(delay_seconds * (attempt + 1))

    raise FetchError(f"Could not fetch {url}: {last_error}") from last_error


# ============================================================
# _fetch_text_with_powershell - 使用 PowerShell 下載（私有函數，目前未使用）
# ============================================================
# 備用方案：使用 PowerShell 的 Invoke-WebRequest 下載網頁。
# 目前程式碼中沒有被調用，但保留作為未來的備用選項。
# ============================================================
def _fetch_text_with_powershell(
    url: str,
    *,
    timeout: int,
    retries: int,
    delay_seconds: float = 1.0,
    headers: dict[str, str] | None = None,
) -> str:
    request_headers = DEFAULT_HEADERS | (headers or {})
    quoted_url = _powershell_single_quote(url)
    header_literal = "@{" + "; ".join(
        f"{_powershell_single_quote(key)}={_powershell_single_quote(value)}"
        for key, value in request_headers.items()
    ) + "}"
    script = (
        "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
        f"$headers = {header_literal}; "
        f"$response = Invoke-WebRequest -Uri {quoted_url} -UseBasicParsing "
        f"-Headers $headers -TimeoutSec {int(timeout)}; "
        "$response.Content"
    )

    last_error: Exception | None = None
    for attempt in range(retries + 1):
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if completed.returncode == 0:
            return completed.stdout

        last_error = FetchError(completed.stderr.strip() or completed.stdout.strip())
        if attempt < retries:
            time.sleep(delay_seconds * (attempt + 1))

    raise FetchError(f"Could not fetch {url}: {last_error}") from last_error


# ============================================================
# _powershell_single_quote - PowerShell 字串轉義（私有輔助函數）
# ============================================================
# 將字串用 PowerShell 的單引號包起來，
# 並將字串內的單引號轉換為兩個單引號來轉義。
# ============================================================
def _powershell_single_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"
