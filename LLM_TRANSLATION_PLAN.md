# LLM Translation Feature Planning

> 此文件為 LLM 翻譯功能的規劃紀錄，供後續開發參考。

---

## 架構建議

### 1. Prompt 存放位置

建議在 `config.py` 新增一個區塊，或獨立成 `prompts.py`：

```python
# config.py 新增區塊
TRANSLATION_PROMPTS = {
    "article": """你是一位專業的 MotoGP 賽事翻譯編輯。
請將以下英文新聞翻譯成繁體中文，要求：
- 保留車手、車隊、賽道的原文名稱（可加註中文）
- 使用台灣常用的賽車術語
- 語氣自然流暢，像體育新聞的風格

原文：
{text}

翻譯：""",

    "title": """請將以下 MotoGP 新聞標題翻譯成繁體中文，簡潔有力：
原文：{text}
翻譯：""",
}
```

### 2. API Keys 存放

建議用**環境變數**，不要硬編碼在 code 裡：

```python
# config.py
import os

LLM_API_KEYS = {
    "openai": os.environ.get("OPENAI_API_KEY"),
    "anthropic": os.environ.get("ANTHROPIC_API_KEY"),
    "deepseek": os.environ.get("DEEPSEEK_API_KEY"),
}
```

使用時：
```powershell
$env:OPENAI_API_KEY = "sk-xxx"
$env:DEEPSEEK_API_KEY = "sk-xxx"
python main.py --limit 5 --translate
```

### 3. CLI 參數設計

```powershell
# 基本翻譯（用預設模型）
python main.py --limit 10 --translate

# 指定翻譯模型
python main.py --limit 10 --translate --translate-model gpt-4o-mini
```

---

## LLM 模型推薦（翻譯外電新聞 → 繁體中文）

### 第一梯隊：性價比首選

| 模型 | 優點 | 缺點 | 價格（每篇約） |
|------|------|------|--------------|
| **GPT-5 mini** | 翻譯品質穩定、遵守術語規則能力強、成本低 | 文筆略遜於頂級模型 | ~$0.0002 |
| **DeepSeek-V3** | 中文表現優秀、價格極低、速度快 | 偶爾過度意譯，API 穩定性略有波動 | ~$0.0001 |
| **Gemini Flash** | 速度快、價格低、適合大量批次翻譯 | 專業術語與中文語感略弱 | ~$0.0002 |

### 第二梯隊：品質優先

| 模型 | 優點 | 缺點 | 價格（每篇約） |
|------|------|------|--------------|
| **GPT-5** | 翻譯品質頂尖、術語理解能力強、穩定性高 | 成本較高 | ~$0.003 |
| **Claude Sonnet** | 中文最自然、新聞語感佳、上下文理解強 | 成本較高 | ~$0.003~0.005 |
| **Gemini Pro** | 長文處理能力優秀、長 Context 表現佳 | 中文自然度略遜於 GPT 與 Claude | ~$0.002 |

### 第三梯隊：舊世代但仍可使用

| 模型 | 優點 | 缺點 | 適用情境 |
|------|------|------|---------|
| **GPT-4o-mini** | 穩定、成本低 | 已被 GPT-5 mini 超越 | 舊系統相容 |
| **GPT-4o** | 品質穩定 | 性價比不如 GPT-5 系列 | 舊專案維護 |
| **Claude 3.5 Haiku** | 成本低、速度快 | 已被新一代模型取代 | 舊專案維護 |
| **Claude 3.5 Sonnet** | 文筆優秀 | 已被 Sonnet 新版取代 | 舊專案維護 |

### MotoGP / F1 / 科技新聞翻譯建議

實務上，最終翻譯品質的影響因素通常為：

1. Prompt Template
2. 術語表（Glossary）
3. 翻譯後處理規則
4. 模型本身

若已建立完整術語規則，例如：

- Sprint → 衝刺賽
- Grand Prix → 正賽
- slipstream → 真空帶
- Long Lap penalty → 跑長圈
- two tenths of a second → 0.2秒

則 **GPT-5 mini** 或 **DeepSeek-V3** 通常已能達到接近人工翻譯的品質，性價比最高。

### 推薦組合

```python
# 建議的優先順序
DEFAULT_TRANSLATE_MODEL = "deepseek-v3"  # 首選：便宜又強
FALLBACK_MODELS = ["gpt-4o-mini", "claude-3.5-haiku"]  # 備用
```

**理由：**
- DeepSeek-V3 是中國公司開發，繁體中文翻譯品質非常好
- 每篇新聞翻譯成本約 $0.0001，10 篇才 $0.001
- 速度極快，10 篇新聞翻譯 < 30 秒

---

## 潛在問題提醒

### 1. Rate Limiting

大部分 LLM API 都有 rate limit，建議加上：

```python
import time
time.sleep(0.1)  # 每篇翻譯後等一下
```

### 2. 術語一致性

MotoGP 有很多專有名詞，建議在 prompt 中加一個術語表：

```python
MOTOGP_TERMS = {
    "MotoGP": "MotoGP",  # 不翻譯
    "Marc Marquez": "Marc Marquez",  # 或 "馬克·馬奎斯"
    "Ducati": "Ducati",  # 或 "杜卡迪"
    "pole position": "桿位",
    "podium": "頒獎台",
}
```

### 3. 錯誤處理

翻譯失敗時要有 fallback，不要讓整個程式掛掉：

```python
try:
    translated = translate(text)
except Exception:
    translated = text  # 失敗就用原文
```

---

## 檔案結構建議

```text
motogp_scraper/
  translator.py      # 翻譯邏輯（Translator 類別）
  prompts.py         # Prompt 模板（新增）
  config.py          # 加上 LLM_API_KEYS 設定
  cli.py             # 加上 --translate 參數
  models.py          # Article 加上 translated_text 欄位
```

---

## 總結：起步方案

1. **先用 GPT-5** — 翻譯品質頂尖、術語理解能力強、穩定性高
2. **Prompt 放 `prompts.py`** — 一個檔案放所有 prompt 模板
3. **API Key 用環境變數** — 不要硬編碼
4. **`--translate` 參數** — 預設不翻譯，加上才會翻譯
