import pytest
from nonebot import logger


@pytest.mark.asyncio
async def test_reddit_match():
    from nonebot_plugin_parser.parsers import RedditParser

    parser = RedditParser()
    url = "https://www.reddit.com/r/ClaudeAI/comments/1u4cyvh/fable_5_indefinitely_suspended/"
    keyword, searched = parser.search_url(url)
    assert searched
    assert keyword == "reddit.com"
    assert searched.group("post_id") == "1u4cyvh"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "url,share_id",
    [
        (
            "https://www.reddit.com/r/girlsmasturbating/s/Qda0641IXZ",
            "Qda0641IXZ",
        ),
        (
            "https://www.reddit.com/r/ChatGPT/s/yImeAVe1YW",
            "yImeAVe1YW",
        ),
        (
            "https://www.reddit.com/r/Seedance_v2/s/Hh1eyP8mND",
            "Hh1eyP8mND",
        ),
        (
            "https://old.reddit.com/r/ChatGPT/s/yImeAVe1YW",
            "yImeAVe1YW",
        ),
    ],
)
async def test_reddit_share_url_match(url: str, share_id: str):
    from nonebot_plugin_parser.parsers import RedditParser

    keyword, searched = RedditParser.search_url(url)
    assert keyword == "reddit.com"
    assert searched.group("share_id") == share_id
    assert "/s/" in searched.group(0)
    assert share_id in searched.group(0)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "url,expect",
    [
        (
            "https://www.reddit.com/r/Seedance_AI/comments/1u1taif/shooting_ai_fantasy/",
            "video",
        ),
        (
            "https://www.reddit.com/r/ClaudeAI/comments/1u4cyvh/fable_5_indefinitely_suspended/",
            "image",
        ),
        (
            "https://www.reddit.com/r/CheatingPOV/comments/1u4jidb/your_wife_doesnt_need_to_know/",
            "gallery",
        ),
    ],
)
async def test_reddit_parse_network(url: str, expect: str):
    from nonebot_plugin_parser.parsers import RedditParser

    parser = RedditParser()
    keyword, searched = parser.search_url(url)
    assert searched

    try:
        result = await parser.parse(keyword, searched)
    except Exception as exc:
        pytest.skip(f"Reddit 网络不可用: {exc}")

    logger.info("reddit result: %s", result)
    assert result.title
    assert result.author
    assert result.contents, "媒体列表为空"

    if expect == "video":
        assert result.video, "应为单视频以渲染卡片封面"
        assert result.video.cover, "视频应有封面"
    elif expect == "image":
        assert len(result.img_contents) >= 1
    elif expect == "gallery":
        assert len(result.img_contents) >= 2

    await result.ensure_downloads_complete(img_only=True)

    if expect == "video" and result.video and result.video.cover:
        cover = await result.video.cover.safe_get()
        assert cover and cover.exists()

    if expect in ("image", "gallery"):
        path = await result.img_contents[0].path_task.safe_get()
        assert path and path.exists()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "url",
    [
        "https://www.reddit.com/r/girlsmasturbating/s/Qda0641IXZ",
        "https://www.reddit.com/r/ChatGPT/s/yImeAVe1YW",
        "https://www.reddit.com/r/Seedance_v2/s/Hh1eyP8mND",
    ],
)
async def test_reddit_share_parse_network(url: str):
    from nonebot_plugin_parser.parsers import RedditParser

    import os
    from pathlib import Path
    parser = RedditParser()
    ck = os.environ.get("PARSER_REDDIT_CK", "").strip()
    if not ck:
        probe = Path(__file__).resolve().parents[2] / ".reddit_ck_probe"
        if probe.is_file():
            ck = probe.read_text(encoding="utf-8").strip()
    if ck:
        parser.headers["cookie"] = ck
    keyword, searched = parser.search_url(url)
    assert searched.group("share_id")

    try:
        result = await parser.parse(keyword, searched)
    except Exception as exc:
        pytest.skip(f"Reddit 网络不可用: {exc}")

    assert result.title
    assert result.contents, "分享链接应解析出媒体"
    if result.video:
        assert result.video.cover, "视频应有封面"
    elif result.img_contents:
        assert result.img_contents[0].path_task
