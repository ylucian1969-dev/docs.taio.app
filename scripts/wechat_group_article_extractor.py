#!/usr/bin/env python3
"""从微信群聊天记录中提取公众号文章链接并抓取文章信息。"""

from __future__ import annotations

import argparse
import json
import re
import time
from dataclasses import asdict, dataclass
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

WECHAT_URL_RE = re.compile(r'https?://mp\.weixin\.qq\.com/s\?[^\s\u3000<>"\']+')


@dataclass
class Article:
    url: str
    title: str
    account_name: str
    content: str


class _DivTextExtractor(HTMLParser):
    """抽取指定 div 内的可读文本。"""

    def __init__(self, target_id: str) -> None:
        super().__init__()
        self.target_id = target_id
        self._stack: list[bool] = []
        self._buffer: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_map = dict(attrs)
        inside_parent = self._stack[-1] if self._stack else False
        is_target = tag == "div" and attrs_map.get("id") == self.target_id
        now_inside = inside_parent or is_target
        self._stack.append(now_inside)

        if now_inside and tag in {"p", "br", "li", "h1", "h2", "h3"}:
            self._buffer.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if self._stack:
            self._stack.pop()

    def handle_data(self, data: str) -> None:
        if self._stack and self._stack[-1]:
            stripped = data.strip()
            if stripped:
                self._buffer.append(stripped + " ")

    def text(self) -> str:
        content = "".join(self._buffer)
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        return "\n".join(lines)


def extract_wechat_urls(chat_text: str) -> list[str]:
    """从聊天文本提取去重后的微信公众号文章链接。"""
    seen: set[str] = set()
    urls: list[str] = []
    for match in WECHAT_URL_RE.finditer(chat_text):
        raw = match.group(0)
        cleaned = raw.rstrip("),.;!?]}>。！？；，")
        if cleaned not in seen:
            seen.add(cleaned)
            urls.append(cleaned)
    return urls


def fetch_html(url: str, timeout: int = 15) -> str:
    """下载网页 HTML。"""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/123.0 Safari/537.36"
        )
    }
    req = Request(url, headers=headers)
    with urlopen(req, timeout=timeout) as resp:
        encoding = resp.headers.get_content_charset() or "utf-8"
        return resp.read().decode(encoding, errors="replace")


def _first_match(pattern: str, html: str) -> str:
    m = re.search(pattern, html, flags=re.IGNORECASE | re.DOTALL)
    return unescape(m.group(1).strip()) if m else ""


def parse_wechat_article(url: str, html: str, max_content_chars: int = 5000) -> Article:
    """解析公众号文章标题、公众号名和正文。"""
    title = _first_match(r'<meta\s+property="og:title"\s+content="(.*?)"', html)
    if not title:
        title = _first_match(r"var\s+msg_title\s*=\s*'(.*?)'", html)

    account = _first_match(r"var\s+nickname\s*=\s*'(.*?)'", html)
    if not account:
        account = _first_match(r'<meta\s+name="author"\s+content="(.*?)"', html)

    extractor = _DivTextExtractor("js_content")
    extractor.feed(html)
    content = extractor.text()

    if max_content_chars > 0 and len(content) > max_content_chars:
        content = content[:max_content_chars].rstrip() + "…"

    return Article(
        url=url,
        title=title or "(未解析到标题)",
        account_name=account or "(未解析到公众号名称)",
        content=content or "(未解析到正文内容)",
    )


def process_urls(urls: Iterable[str], max_content_chars: int, sleep_seconds: float) -> tuple[list[Article], list[dict[str, str]]]:
    """抓取和解析多个 URL。"""
    url_list = list(urls)
    articles: list[Article] = []
    failures: list[dict[str, str]] = []

    for idx, url in enumerate(url_list, start=1):
        try:
            html = fetch_html(url)
            articles.append(parse_wechat_article(url, html, max_content_chars=max_content_chars))
        except (HTTPError, URLError, TimeoutError, ValueError) as exc:
            failures.append({"url": url, "error": str(exc)})
        if sleep_seconds > 0 and idx < len(url_list):
            time.sleep(sleep_seconds)

    return articles, failures


def write_jsonl(path: Path, records: Iterable[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="从微信群聊天记录提取微信公众号文章链接并抓取内容")
    parser.add_argument("--chat-file", required=True, type=Path, help="微信群聊天记录文本文件")
    parser.add_argument("--output", type=Path, default=Path("wechat_articles.jsonl"), help="输出 JSONL 文件路径")
    parser.add_argument("--errors", type=Path, default=Path("wechat_article_errors.jsonl"), help="错误日志 JSONL 文件路径")
    parser.add_argument("--encoding", default="utf-8", help="聊天记录编码")
    parser.add_argument("--max-content-chars", type=int, default=5000, help="正文最大长度，默认 5000")
    parser.add_argument("--sleep", type=float, default=0.0, help="每次请求间隔秒数，避免请求过快")
    return parser


def main() -> int:
    args = build_parser().parse_args()

    chat_text = args.chat_file.read_text(encoding=args.encoding)
    urls = extract_wechat_urls(chat_text)

    if not urls:
        print("未找到任何微信公众号文章链接。")
        return 1

    articles, failures = process_urls(
        urls=urls,
        max_content_chars=args.max_content_chars,
        sleep_seconds=args.sleep,
    )

    write_jsonl(args.output, (asdict(article) for article in articles))
    if failures:
        write_jsonl(args.errors, failures)

    print(f"链接总数: {len(urls)}")
    print(f"成功解析: {len(articles)}")
    print(f"失败数量: {len(failures)}")
    print(f"输出文件: {args.output}")
    if failures:
        print(f"错误日志: {args.errors}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
