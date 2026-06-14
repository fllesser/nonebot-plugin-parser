"""卡片标题/正文大模型翻译（国外社交平台解析结果）。"""

from __future__ import annotations

import json
import re
from typing import Any

import httpx
from nonebot import logger

from .config import pconfig
from .constants import PlatformEnum
from .parsers.data import ParseResult

_DEFAULT_FOREIGN: frozenset[PlatformEnum] = frozenset(
    {
        PlatformEnum.REDDIT,
        PlatformEnum.TWITTER,
        PlatformEnum.TIKTOK,
        PlatformEnum.YOUTUBE,
    }
)

_DEFAULT_SYSTEM_PROMPT = """你是翻译助手。将用户 JSON 中的 title、text 翻译成简体中文。
要求：保留 @用户名、r/子版块、URL、emoji；不要加解释。
只输出 JSON：{"title":"...","text":"..."}，无内容字段用空字符串。"""


def _platforms_enabled() -> frozenset[PlatformEnum]:
    raw = (pconfig.parser_llm_translate_platforms or "").strip()
    if not raw:
        return _DEFAULT_FOREIGN
    out: set[PlatformEnum] = set()
    for part in raw.replace("，", ",").split(","):
        name = part.strip().lower()
        if not name:
            continue
        try:
            out.add(PlatformEnum(name))
        except ValueError:
            logger.warning("忽略未知翻译平台: %s", name)
    return frozenset(out) if out else _DEFAULT_FOREIGN


def should_translate_card(result: ParseResult) -> bool:
    if not pconfig.parser_llm_translate_enable:
        return False
    if not (pconfig.parser_llm_translate_api_url or "").strip():
        return False
    return result.platform.name in _platforms_enabled()


def _parse_json_content(text: str) -> dict[str, Any] | None:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", text)
        if not m:
            return None
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            return None


async def translate_card_text(
    title: str | None, text: str | None
) -> tuple[str | None, str | None]:
    url = (pconfig.parser_llm_translate_api_url or "").strip().rstrip("/")
    if not url or (not title and not text):
        return title, text

    model = (pconfig.parser_llm_translate_model or "gpt-4o-mini").strip()
    system = (pconfig.parser_llm_translate_prompt or _DEFAULT_SYSTEM_PROMPT).strip()
    api_key = (pconfig.parser_llm_translate_api_key or "").strip()
    chat_url = (
        url if url.endswith("/chat/completions") else f"{url}/chat/completions"
    )
    timeout = max(5.0, float(pconfig.parser_llm_translate_timeout or 60))

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": json.dumps(
                    {"title": title or "", "text": text or ""},
                    ensure_ascii=False,
                ),
            },
        ],
        "temperature": 0.2,
    }
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        async with httpx.AsyncClient(timeout=timeout, verify=False) as client:
            resp = await client.post(chat_url, headers=headers, json=payload)
            resp.raise_for_status()
            body = resp.json()
        content = (
            (body.get("choices") or [{}])[0]
            .get("message", {})
            .get("content", "")
        )
        parsed = _parse_json_content(str(content))
        if not parsed:
            logger.warning("LLM 翻译 JSON 解析失败")
            return title, text
        nt = parsed.get("title")
        nx = parsed.get("text")
        return (
            str(nt) if nt is not None else title,
            str(nx) if nx is not None else text,
        )
    except Exception as exc:
        logger.warning("卡片 LLM 翻译失败，使用原文: %s", exc)
        return title, text


async def apply_card_translation(result: ParseResult) -> None:
    """渲染卡片前就地翻译 title / text。"""
    if not should_translate_card(result):
        return
    result.title, result.text = await translate_card_text(result.title, result.text)
