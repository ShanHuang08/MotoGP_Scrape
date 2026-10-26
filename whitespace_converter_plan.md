# 建立空白與換行轉換器

請建立一個可以將文章中的「連續空格」與「連續空白行」轉換為可保留排版格式的工具。

工具需要提供兩種操作方式：

1. HTML 網頁介面
2. CLI 命令列介面

核心原理是在連續空格或連續換行之間插入零寬空格：

```text
U+200B Zero Width Space
```

目的是避免 Facebook、Instagram、Threads 或其他平台自動壓縮連續空格與空白行。

---

## 一、技術要求

使用以下技術：

* Python 3.11+
* HTML
* CSS
* Vanilla JavaScript
* 不使用前端框架
* 不需要後端伺服器
* CLI 與 HTML 必須共用相同的轉換規則
* 所有檔案使用 UTF-8 編碼

建議專案結構：

```text
whitespace-converter/
├── index.html
├── style.css
├── app.js
├── converter.py
├── cli.py
├── tests/
│   └── test_converter.py
└── README.md
```

---

## 二、核心轉換規則

定義：

```python
ZERO_WIDTH_SPACE = "\u200B"
```

轉換前必須先移除輸入內容中已存在的 `U+200B`，避免使用者重複轉換時持續累加零寬空格。

### 規則 1：單一空格保持不變

輸入：

```text
Hello World
```

輸出：

```text
Hello World
```

單一普通空格不能插入零寬空格。

---

### 規則 2：連續兩個以上空格

在每個普通空格之間插入 `U+200B`。

輸入：

```text
Hello    World
```

實際輸出：

```text
Hello \u200B \u200B \u200B World
```

畫面上仍應顯示為四個空格。

轉換邏輯概念：

```python
converted = ZERO_WIDTH_SPACE.join(spaces)
```

只處理普通半形空格：

```text
U+0020
```

不要自動轉換 Tab、全形空格或其他 Unicode 空格。

---

### 規則 3：連續換行

當出現兩個以上連續換行時，在換行之間插入 `U+200B`。

輸入字串：

```python
"第一段\n\n第二段"
```

輸出字串：

```python
"第一段\n\u200B\n第二段"
```

輸入：

```python
"第一段\n\n\n第二段"
```

輸出：

```python
"第一段\n\u200B\n\u200B\n第二段"
```

也就是每個原本的空白行中，都放入一個零寬空格。

單一換行不需要轉換。

---

### 規則 4：支援 Windows 換行

輸入可能包含：

```text
\r\n
```

內部處理前，先統一換行格式：

```python
text = text.replace("\r\n", "\n").replace("\r", "\n")
```

輸出預設使用：

```text
\n
```

CLI 可額外提供參數，允許輸出 Windows 換行格式。

---

### 規則 5：重複執行結果必須一致

以下操作：

```python
convert(convert(text))
```

結果必須等於：

```python
convert(text)
```

也就是轉換函式必須具備冪等性。

---

## 三、Python 核心模組

在 `converter.py` 建立：

```python
ZERO_WIDTH_SPACE = "\u200B"


def convert_whitespace(text: str) -> str:
    """
    將連續空格與連續空白行轉換為含有零寬空格的文字。

    規則：
    1. 移除既有的 U+200B。
    2. 單一空格維持不變。
    3. 兩個以上連續普通空格，在空格之間插入 U+200B。
    4. 兩個以上連續換行，在換行之間插入 U+200B。
    5. 將 CRLF 與 CR 正規化為 LF。
    """
```

另外建立：

```python
def remove_zero_width_spaces(text: str) -> str:
    """
    移除所有 U+200B，還原為一般文字。
    """
```

要求：

* 函式不可修改外部狀態
* 必須有 type hints
* 必須有 docstring
* 不要使用過度複雜的正則表示式
* 優先考慮可讀性
* 不要使用 `except Exception`
* 空字串必須正常回傳空字串

---

## 四、CLI 功能

建立 `cli.py`。

支援以下使用方式。

### 1. 互動模式

執行：

```bash
python cli.py
```

顯示提示：

```text
請輸入文章。
輸入完成後：
- Windows：按 Ctrl+Z，再按 Enter
- macOS/Linux：按 Ctrl+D
```

讀取多行文字後，自動轉換並輸出。

---

### 2. 直接輸入文字

```bash
python cli.py --text "Hello    World"
```

---

### 3. 從檔案讀取

```bash
python cli.py --input article.txt
```

---

### 4. 輸出至檔案

```bash
python cli.py --input article.txt --output converted.txt
```

---

### 5. 直接複製到剪貼簿

```bash
python cli.py --input article.txt --copy
```

剪貼簿功能可使用：

```text
pyperclip
```

如果沒有安裝 `pyperclip`，顯示清楚錯誤訊息：

```text
剪貼簿功能需要安裝 pyperclip：
pip install pyperclip
```

不可讓程式直接顯示 Python traceback。

---

### 6. 還原零寬空格

```bash
python cli.py --input converted.txt --clean
```

`--clean` 模式只移除 `U+200B`，不執行轉換。

---

### 7. 顯示不可見字元

提供：

```bash
python cli.py --input converted.txt --debug
```

Debug 模式輸出時，將零寬空格顯示成：

```text
<ZWSP>
```

例如：

```text
Hello <ZWSP> <ZWSP> World
```

這只用於檢查，實際儲存或複製時仍須使用真正的 `U+200B`。

---

### CLI 參數

使用 `argparse`：

```text
--text
--input
--output
--copy
--clean
--debug
--windows-newline
```

輸入來源優先順序：

```text
--text
↓
--input
↓
stdin
```

若同時傳入 `--text` 與 `--input`，顯示錯誤並結束。

CLI 必須使用合理的 exit code：

```text
0：成功
1：一般執行錯誤
2：參數錯誤
```

---

## 五、HTML 網頁版

建立單頁網頁。

頁面內容包括：

### 標題

```text
空白與換行轉換器
```

### 輸入區

使用：

```html
<textarea id="inputText"></textarea>
```

placeholder：

```text
在這裡貼上文章……
```

### 按鈕

提供以下按鈕：

```text
轉換
轉換並複製
複製結果
清除
還原零寬空格
```

### 輸出區

使用：

```html
<textarea id="outputText" readonly></textarea>
```

### 狀態提示

例如：

```text
轉換完成
文字已複製
內容已清除
沒有可轉換的文字
瀏覽器不支援自動複製
```

狀態訊息顯示後，約 2 秒自動消失。

---

## 六、前端轉換邏輯

在 `app.js` 建立：

```javascript
const ZERO_WIDTH_SPACE = "\u200B";

function convertWhitespace(text) {
    // 與 Python convert_whitespace 完全相同的規則
}

function removeZeroWidthSpaces(text) {
    return text.replaceAll(ZERO_WIDTH_SPACE, "");
}
```

要求：

* 不依賴 jQuery
* 不依賴 ClipboardJS
* 使用現代瀏覽器 API
* 使用 `navigator.clipboard.writeText()`
* 若 Clipboard API 不可用，使用 fallback
* fallback 可建立畫面外的 `<textarea>`，選取後執行複製
* 複製失敗時顯示錯誤訊息
* 不可使用 `innerHTML` 顯示使用者輸入
* 避免 XSS 風險

---

## 七、網頁操作流程

### 轉換

```text
讀取 inputText.value
↓
執行 convertWhitespace()
↓
寫入 outputText.value
```

### 轉換並複製

```text
讀取輸入
↓
轉換
↓
寫入輸出區
↓
複製轉換結果
↓
顯示「文字已複製」
```

### 複製結果

直接複製輸出區內容。

若輸出區是空的，顯示：

```text
沒有可複製的內容
```

### 清除

清空輸入區、輸出區及狀態訊息。

### 還原零寬空格

讀取輸入區內容，移除所有 `U+200B` 後寫入輸出區。

---

## 八、快捷鍵

網頁版支援：

```text
Ctrl + Enter
```

或 macOS：

```text
Cmd + Enter
```

執行「轉換並複製」。

---

## 九、UI 設計

介面風格：

* 簡潔
* 支援桌面與手機
* 最大內容寬度約 900px
* textarea 使用等寬字型
* textarea 至少 12 行
* 保留使用者輸入中的換行與空格
* 按鈕在手機版可自動換行
* 使用清楚的 focus 樣式
* 支援系統深色模式
* 不使用外部 CSS library
* 不載入 CDN
* 不加入廣告、分析或追蹤程式

HTML 必須包含：

```html
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
```

---

## 十、單元測試

使用 `pytest` 建立 `tests/test_converter.py`。

至少測試以下情境。

### 空字串

```python
assert convert_whitespace("") == ""
```

### 單一空格

```python
assert convert_whitespace("A B") == "A B"
```

### 兩個空格

```python
assert convert_whitespace("A  B") == "A \u200B B"
```

### 四個空格

```python
assert convert_whitespace("A    B") == "A \u200B \u200B \u200B B"
```

### 單一換行

```python
assert convert_whitespace("A\nB") == "A\nB"
```

### 兩個換行

```python
assert convert_whitespace("A\n\nB") == "A\n\u200B\nB"
```

### 三個換行

```python
assert convert_whitespace("A\n\n\nB") == "A\n\u200B\n\u200B\nB"
```

### Windows 換行

```python
assert convert_whitespace("A\r\n\r\nB") == "A\n\u200B\nB"
```

### 混合空格與換行

```python
input_text = "A    B\n\nC"
expected = "A \u200B \u200B \u200B B\n\u200B\nC"

assert convert_whitespace(input_text) == expected
```

### 移除既有零寬空格

```python
assert convert_whitespace("A \u200B B") == "A \u200B B"
```

### 冪等性

```python
converted = convert_whitespace("A    B\n\nC")

assert convert_whitespace(converted) == converted
```

### 清除功能

```python
assert remove_zero_width_spaces("A\u200BB") == "AB"
```

---

## 十一、README

建立完整的 `README.md`，內容包括：

1. 工具用途
2. 零寬空格的原理
3. 專案結構
4. HTML 使用方式
5. CLI 使用方式
6. CLI 參數說明
7. 安裝方式
8. 執行測試方式
9. 範例輸入與輸出
10. 已知限制
11. Unicode `U+200B` 說明

安裝範例：

```bash
python -m venv .venv
```

Windows：

```bash
.venv\Scripts\activate
```

macOS/Linux：

```bash
source .venv/bin/activate
```

安裝：

```bash
pip install pytest pyperclip
```

執行測試：

```bash
pytest -v
```

啟動 HTML 可直接打開：

```text
index.html
```

也可以使用：

```bash
python -m http.server 8000
```

然後開啟：

```text
http://localhost:8000
```

---

## 十二、實作限制

請遵守：

* 不複製原網站的程式碼
* 只重現相同的公開功能與轉換原理
* 不加入網域驗證
* 不加入混淆程式碼
* 不加入重新導向
* 不加入追蹤程式
* 不加入廣告
* 不使用壓縮後或難以閱讀的程式碼
* 不在程式碼中直接寫不可辨識的零寬字元

零寬空格必須明確寫成：

```javascript
"\u200B"
```

或：

```python
"\u200B"
```

不要直接貼入肉眼不可見的字元，避免維護困難。

---

## 十三、驗收標準

完成後請確認：

* HTML 可直接在瀏覽器使用
* CLI 可處理多行文章
* CLI 可讀寫 UTF-8 文字檔
* 連續空格可以保留
* 連續空白行可以保留
* 單一空格與單一換行不受影響
* 重複轉換不會持續增加零寬空格
* 中文、英文、數字與 Emoji 都能正常處理
* JavaScript 與 Python 的輸出結果一致
* 所有 pytest 測試通過
* 所有按鈕與快捷鍵正常運作

完成實作後，請依序輸出：

1. 專案檔案結構
2. 各檔案完整內容
3. 安裝與執行方式
4. 測試結果
5. 一組中文文章的實際轉換範例
