from nonebot import logger
import pytest


@pytest.mark.asyncio
async def test_common_render():
    """测试使用 WeiboParser 解析链接并用 CommonRenderer 渲染"""
    import aiofiles

    from nonebot_plugin_parser import pconfig
    from nonebot_plugin_parser.parsers import WeiBoParser
    from nonebot_plugin_parser.renders.common import CommonRenderer

    parser = WeiBoParser()
    renderer = CommonRenderer()

    url_dict = {
        "video_fid": "https://video.weibo.com/show?fid=1034:514561539984589",
        "video_weibo": "https://weibo.com/7207262816/O70aCbjnd",
        "video_mweibo": "http://m.weibo.cn/status/5112672433738061",
        "image_album": "https://weibo.com/7207262816/P5kWdcfDe",
        "image_album_9": "https://weibo.com/7207262816/P2AFBk387",
        "image_album_single": "https://weibo.com/7207262816/Q6YCbtAn8",
        "image_album_single_repost": "https://weibo.com/7207262816/Q617WgOm4",
        "image_album_two": "https://weibo.com/7207262816/PsFzpzUX2",
        "image_album_three": "https://weibo.com/7207262816/P2rJE157H",
        "text": "https://mapp.api.weibo.cn/fx/8102df2b26100b2e608e6498a0d3cfe2.html",
        "repost": "https://mapp.api.weibo.cn/fx/77eaa5c2f741894631a87fc4806a1f05.html",
        "video_weibo_repost": "https://weibo.com/1694917363/Q0KtXh6z2",
    }

    async def parse_and_render(url: str, name: str) -> None:
        """解析并渲染单个 URL"""
        matched = parser.search_url(url)
        assert matched, f"无法匹配 URL: {url}"

        logger.info(f"{url} | 开始解析微博")
        parse_result = await parser.parse(matched)
        logger.debug(f"{url} | 解析结果: \n{parse_result}")

        logger.info(f"{url} | 开始渲染")
        image_raw = await renderer.draw_common_image(parse_result)
        assert image_raw, f"没有生成图片: {url}"
        image_path = pconfig.cache_dir / "aaaaaaa" / f"{name}.png"
        # 创建文件
        image_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(image_path, "wb+") as f:
            await f.write(image_raw)
        logger.success(f"{url} | 渲染成功，图片已保存到 {image_path}")

    failed_count = 0
    for name, url in url_dict.items():
        try:
            await parse_and_render(url, name)
        except Exception:
            logger.exception(f"{url} | 渲染失败")
            failed_count += 1
    logger.success(f"渲染完成，失败数量: {failed_count}")
