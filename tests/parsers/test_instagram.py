import pytest


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "url,keyword",
    [
        ("https://www.instagram.com/reel/DBOC0Z4hOR1/", "instagram.com"),
        ("https://www.instagram.com/reels/DBOC0Z4hOR1/", "instagram.com"),
        ("https://instagram.com/p/DBOC0Z4hOR1/", "instagram.com"),
        ("https://www.instagram.com/kiran.mazumder/reel/DBOC0Z4hOR1/", "instagram.com"),
        ("https://www.instagram.com/share/reel/DBOC0Z4hOR1/", "instagram.com"),
        ("https://www.instagram.com/share/p/DBOC0Z4hOR1/", "instagram.com"),
        ("https://instagr.am/p/DBOC0Z4hOR1/", "instagr.am"),
        ("https://m.instagram.com/p/DBOC0Z4hOR1/", "instagram.com"),
        ("https://ig.me/reel/DBOC0Z4hOR1/", "ig.me"),
        (
            "https://l.instagram.com/?u=https%3A%2F%2Fwww.instagram.com%2Freel%2FDBOC0Z4hOR1%2F",
            "l.instagram.com",
        ),
    ],
)
async def test_instagram_url_match(url: str, keyword: str):
    from nonebot_plugin_parser.parsers import InstagramParser

    matched_keyword, searched = InstagramParser.search_url(url)
    assert matched_keyword == keyword
    assert searched


def test_instagram_url_normalize():
    from nonebot_plugin_parser.parsers.instagram import _extract_instagram_target

    assert (
        _extract_instagram_target("https://www.instagram.com/kiran.mazumder/reel/DBOC0Z4hOR1/")
        == "https://www.instagram.com/reel/DBOC0Z4hOR1/"
    )
    assert (
        _extract_instagram_target("https://www.instagram.com/share/p/DBOC0Z4hOR1/")
        == "https://www.instagram.com/p/DBOC0Z4hOR1/"
    )
    assert (
        _extract_instagram_target("https://instagr.am/p/DBOC0Z4hOR1/")
        == "https://www.instagram.com/p/DBOC0Z4hOR1/"
    )
    assert (
        _extract_instagram_target("https://ig.me/reel/DBOC0Z4hOR1/")
        == "https://www.instagram.com/reel/DBOC0Z4hOR1/"
    )
    assert (
        _extract_instagram_target(
            "https://l.instagram.com/?u=https%3A%2F%2Fwww.instagram.com%2Freel%2FDBOC0Z4hOR1%2F"
        )
        == "https://www.instagram.com/reel/DBOC0Z4hOR1/"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "url",
    [
        "https://www.instagram.com/reel/DBOC0Z4hOR1/",
        "https://www.instagram.com/p/DBOC0Z4hOR1/",
        "https://www.instagram.com/kiran.mazumder/reel/DBOC0Z4hOR1/",
        "https://www.instagram.com/share/reel/DBOC0Z4hOR1/",
        "https://instagr.am/p/DBOC0Z4hOR1/",
    ],
)
async def test_instagram_parse_network(url: str):
    from nonebot_plugin_parser.parsers import InstagramParser

    parser = InstagramParser()
    keyword, searched = parser.search_url(url)
    try:
        result = await parser.parse(keyword, searched)
    except Exception as exc:
        pytest.skip(f"Instagram 网络或 yt-dlp 不可用: {exc}")

    assert result.contents
    assert result.author
    if result.video:
        assert result.video.cover
