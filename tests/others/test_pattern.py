from pathlib import Path

from nonebot import logger
import pytest


def test_pattern_matching():
    from nonebot_plugin_parser.parsers import BaseParser

    parser_classes = BaseParser.get_all_subclass()
    patterns = [p for _cls in parser_classes for p in _cls._patterns]
    patterns.sort(key=lambda x: len(x[0]), reverse=True)  # 按关键字长度降序排序

    urls_file = Path(__file__).parent / "urls.txt"
    with urls_file.open("r", encoding="utf-8") as f:
        urls = f.readlines()
    urls = [url.strip() for url in urls if url.strip()]
    urls = [url.removeprefix("- ").strip() for url in urls if url.startswith("- ")]

    def match_url(url: str):
        for keyword, pattern in patterns:
            if keyword not in url:
                continue
            if pattern.search(url):
                logger.success(f"URL 匹配成功: {url} 关键词: {keyword}")
                return True
            logger.debug(f"keyword '{keyword}' is in '{url}', but not matched")
        return False

    # 统计匹配结果
    failed_urls: list[str] = []
    for url in urls:
        if not match_url(url):
            failed_urls.append(url)

    if failed_urls:
        logger.error("以下 URL 未能匹配成功:")
        for url in failed_urls:
            logger.error(f"- {url}")
        pytest.fail(f"共有 {len(failed_urls)} 个 URL 未能匹配成功，请检查日志。")
