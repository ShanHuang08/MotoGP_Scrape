"""
translator.py - On-demand article translation.

Translation intentionally runs as a separate step from scraping:
read an existing latest-news Markdown report, extract one article by index,
send only that article to the OpenAI Responses API, and write a translated
HTML report.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import platform
from pathlib import Path
import re
import subprocess
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .reporter import build_report_html


DEFAULT_TRANSLATION_MODEL = "gpt-5"
DEFAULT_API_KEY_FILE = "API_SECRET_KEY.txt"
DEFAULT_PROMPT_FILE = "AI_translator_prompt.md"


class TranslationError(RuntimeError):
    """Raised when a translation request or report parse fails."""


@dataclass(frozen=True)
class MarkdownArticle:
    index: int
    title: str
    metadata: dict[str, str]
    body: str


@dataclass(frozen=True)
class TranslatedArticle:
    article: MarkdownArticle
    translated_text: str


def load_api_key(path: str | Path = DEFAULT_API_KEY_FILE) -> str:
    """Read API key from OPENAI_API_KEY or a local secret file."""
    import os

    env_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if env_key:
        return env_key

    secret_path = Path(path)
    if not secret_path.exists():
        raise TranslationError(
            f"API key not found. Set OPENAI_API_KEY or create {secret_path}."
        )

    key = secret_path.read_text(encoding="utf-8").strip()
    if not key:
        raise TranslationError(f"API key file is empty: {secret_path}")
    return key


def load_translation_prompt(path: str | Path = DEFAULT_PROMPT_FILE) -> str:
    prompt_path = Path(path)
    if not prompt_path.exists():
        raise TranslationError(f"Translation prompt file not found: {prompt_path}")
    prompt = prompt_path.read_text(encoding="utf-8").strip()
    if not prompt:
        raise TranslationError(f"Translation prompt file is empty: {prompt_path}")
    return prompt


def parse_markdown_articles(markdown: str) -> list[MarkdownArticle]:
    """Parse article sections from the generated latest-news Markdown report."""
    heading_pattern = re.compile(r"^##\s+(\d+)\.\s+(.+?)\s*$", re.MULTILINE)
    matches = list(heading_pattern.finditer(markdown))
    articles: list[MarkdownArticle] = []

    for position, match in enumerate(matches):
        index = int(match.group(1))
        title = match.group(2).strip()
        start = match.end()
        end = matches[position + 1].start() if position + 1 < len(matches) else len(markdown)
        section = markdown[start:end].strip()
        metadata, body = _split_article_section(section)
        articles.append(
            MarkdownArticle(index=index, title=title, metadata=metadata, body=body)
        )

    return articles


def extract_markdown_article(markdown: str, article_index: int) -> MarkdownArticle:
    for article in parse_markdown_articles(markdown):
        if article.index == article_index:
            return article
    raise TranslationError(f"Article #{article_index} was not found in the Markdown report.")


def translate_article_from_markdown(
    markdown_path: str | Path,
    *,
    article_index: int,
    model: str = DEFAULT_TRANSLATION_MODEL,
    api_key_file: str | Path = DEFAULT_API_KEY_FILE,
    prompt_file: str | Path = DEFAULT_PROMPT_FILE,
    output_dir: str | Path | None = None,
) -> Path:
    """Translate one article from a latest-news Markdown file and write HTML."""
    source_path = Path(markdown_path)
    markdown = source_path.read_text(encoding="utf-8")
    article = extract_markdown_article(markdown, article_index)
    prompt = load_translation_prompt(prompt_file)
    api_key = load_api_key(api_key_file)

    translated_text = OpenAIArticleTranslator(
        api_key=api_key,
        model=model,
        prompt=prompt,
    ).translate(article)

    html_text = build_translation_html(
        source_path=source_path,
        article=article,
        translated_text=translated_text,
        model=model,
    )

    destination_dir = Path(output_dir) if output_dir else source_path.parent
    destination_dir.mkdir(parents=True, exist_ok=True)
    output_path = destination_dir / _translation_filename(source_path, article.index)
    output_path.write_text(html_text, encoding="utf-8-sig")
    return output_path


def translate_articles_from_markdown(
    markdown_path: str | Path,
    *,
    article_indexes: list[int],
    model: str = DEFAULT_TRANSLATION_MODEL,
    api_key_file: str | Path = DEFAULT_API_KEY_FILE,
    prompt_file: str | Path = DEFAULT_PROMPT_FILE,
    output_dir: str | Path | None = None,
) -> Path:
    """Translate multiple articles one by one and write one combined HTML file."""
    if not article_indexes:
        raise TranslationError("At least one article index is required.")

    source_path = Path(markdown_path)
    markdown = source_path.read_text(encoding="utf-8")
    prompt = load_translation_prompt(prompt_file)
    api_key = load_api_key(api_key_file)
    translator = OpenAIArticleTranslator(api_key=api_key, model=model, prompt=prompt)

    translated_articles: list[TranslatedArticle] = []
    for article_index in article_indexes:
        article = extract_markdown_article(markdown, article_index)
        translated_articles.append(
            TranslatedArticle(
                article=article,
                translated_text=translator.translate(article),
            )
        )

    html_text = build_translations_html(
        source_path=source_path,
        translated_articles=translated_articles,
        model=model,
    )

    destination_dir = Path(output_dir) if output_dir else source_path.parent
    destination_dir.mkdir(parents=True, exist_ok=True)
    output_path = destination_dir / _translations_filename(source_path, article_indexes)
    output_path.write_text(html_text, encoding="utf-8-sig")
    return output_path


class OpenAIArticleTranslator:
    """Small stdlib-only OpenAI Responses API client."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str = DEFAULT_TRANSLATION_MODEL,
        prompt: str,
        timeout: int = 120,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.prompt = prompt
        self.timeout = timeout

    def translate(self, article: MarkdownArticle) -> str:
        payload = {
            "model": self.model,
            "instructions": self.prompt,
            "input": self._build_input(article),
        }
        if platform.system() == "Windows":
            response_data = self._request_with_curl(payload)
            return _extract_response_text(response_data)

        data = json.dumps(payload).encode("utf-8")
        request = Request(
            "https://api.openai.com/v1/responses",
            data=data,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urlopen(request, timeout=self.timeout) as response:
                response_data = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise TranslationError(f"OpenAI API error {exc.code}: {detail}") from exc
        except (URLError, TimeoutError) as exc:
            raise TranslationError(f"OpenAI API request failed: {exc}") from exc

        return _extract_response_text(response_data)

    def _request_with_curl(self, payload: dict[str, Any]) -> dict[str, Any]:
        command = [
            "curl.exe",
            "--location",
            "--silent",
            "--show-error",
            "--ssl-no-revoke",
            "--insecure",
            "--max-time",
            str(self.timeout),
            "--header",
            f"Authorization: Bearer {self.api_key}",
            "--header",
            "Content-Type: application/json",
            "--data-binary",
            "@-",
            "https://api.openai.com/v1/responses",
        ]
        completed = subprocess.run(
            command,
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if completed.returncode != 0:
            detail = completed.stderr.strip() or completed.stdout.strip()
            raise TranslationError(f"OpenAI API request failed: {detail}")

        try:
            response_data = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise TranslationError(
                f"OpenAI API returned invalid JSON: {completed.stdout[:500]}"
            ) from exc

        if "error" in response_data:
            raise TranslationError(f"OpenAI API error: {response_data['error']}")
        return response_data

    @staticmethod
    def _build_input(article: MarkdownArticle) -> str:
        metadata_lines = [f"{key}: {value}" for key, value in article.metadata.items()]
        metadata = "\n".join(metadata_lines)
        return "\n".join(
            [
                "請翻譯以下 MotoGP 新聞文章。",
                "",
                f"Title: {article.title}",
                metadata,
                "",
                "Article text:",
                article.body,
            ]
        ).strip()


def build_translation_html(
    *,
    source_path: Path,
    article: MarkdownArticle,
    translated_text: str,
    model: str,
) -> str:
    metadata_lines = [
        f"Source Markdown: {source_path.name}",
        f"Original Article: #{article.index} {article.title}",
        f"Translation Model: {model}",
    ]
    for key in ("Source", "URL", "Published At (UTC+8)", "Image"):
        value = article.metadata.get(key, "")
        if value:
            metadata_lines.append(f"{key}: {value}")

    markdown = "\n".join(
        [
            "# MotoGP Translation",
            "",
            *metadata_lines,
            "",
            f"## {article.index}. {article.title}",
            "",
            translated_text.strip(),
            "",
        ]
    )
    return build_report_html(markdown, title=f"Translated - {article.title}")


def build_translations_html(
    *,
    source_path: Path,
    translated_articles: list[TranslatedArticle],
    model: str,
) -> str:
    article_numbers = ", ".join(str(item.article.index) for item in translated_articles)
    metadata_lines = [
        f"Source Markdown: {source_path.name}",
        f"Translated Articles: {article_numbers}",
        f"Translation Model: {model}",
    ]
    article_sections: list[str] = []
    for item in translated_articles:
        article = item.article
        section_lines = [
            f"## {article.index}. {article.title}",
            "",
        ]
        for key in ("Source", "URL", "Published At (UTC+8)", "Image"):
            value = article.metadata.get(key, "")
            if value:
                section_lines.append(f"{key}: {value}")
        section_lines.extend(["", item.translated_text.strip(), ""])
        article_sections.append("\n".join(section_lines))

    markdown = "\n".join(
        [
            "# MotoGP Translations",
            "",
            *metadata_lines,
            "",
            *article_sections,
        ]
    )
    return build_report_html(markdown, title=f"Translated Articles {article_numbers}")


def _split_article_section(section: str) -> tuple[dict[str, str], str]:
    lines = section.splitlines()
    metadata: dict[str, str] = {}
    body_start = 0

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            body_start = i + 1
            continue
        if _is_article_metadata_line(stripped):
            key, value = stripped.split(":", 1)
            metadata[key.strip()] = value.strip()
            body_start = i + 1
            continue
        body_start = i
        break

    body = "\n".join(lines[body_start:]).strip()
    return metadata, body


def _is_article_metadata_line(line: str) -> bool:
    return line.startswith(("Source:", "URL:", "Published At", "Extraction:", "Image:"))


def _extract_response_text(response_data: dict[str, Any]) -> str:
    output_text = response_data.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    chunks: list[str] = []
    for item in response_data.get("output", []):
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []):
            if not isinstance(content, dict):
                continue
            text = content.get("text")
            if isinstance(text, str):
                chunks.append(text)

    text = "\n".join(chunks).strip()
    if not text:
        raise TranslationError("OpenAI API response did not contain translated text.")
    return text


def _translation_filename(source_path: Path, article_index: int) -> str:
    stem = source_path.stem
    return f"{stem} article {article_index} translated.html"


def _translations_filename(source_path: Path, article_indexes: list[int]) -> str:
    stem = source_path.stem
    suffix = "-".join(str(index) for index in article_indexes)
    return f"{stem} articles {suffix} translated.html"
