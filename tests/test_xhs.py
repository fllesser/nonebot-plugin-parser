from nonebot.log import logger


async def test_xiaohongshu():
    """
    xiaohongshu:
    - https://xhslink.com/a/zGL52ubtpJ20
    - https://www.xiaohongshu.com/discovery/item/6469c95c0000000012031f3c?source=webshare&xhsshare=pc_web&xsec_token=ABkMJSd3a0BPMgj5BMkZcggIq1FxU8vYNcNW_-MhfDyq0=&xsec_source=pc_share
    """
    urls = [
        "https://xhslink.com/a/zGL52ubtpJ20",
        "https://www.xiaohongshu.com/discovery/item/6469c95c0000000012031f3c?source=webshare&xhsshare=pc_web&xsec_token=ABkMJSd3a0BPMgj5BMkZcggIq1FxU8vYNcNW_-MhfDyq0=&xsec_source=pc_share",
    ]
    from nonebot_plugin_resolver2.parsers.xiaohongshu import parse_url

    for url in urls:
        try:
            title_desc, urls, video_url = await parse_url(url)
            logger.debug(f"title_desc: {title_desc}")
            logger.debug(f"urls: {urls}")
            logger.debug(f"video_url: {video_url}")
        except Exception:
            continue
