from nonebot import logger
import pytest


@pytest.mark.asyncio
async def test_common_render():
    """测试使用 WeiboParser 解析链接并用 CommonRenderer 渲染"""
    import time

    import aiofiles

    from nonebot_plugin_parser import pconfig
    from nonebot_plugin_parser.parsers import WeiBoParser
    from nonebot_plugin_parser.renders import _COMMON_RENDERER

    parser = WeiBoParser()
    renderer = _COMMON_RENDERER

    url_dict = {
        "video_fid": "https://video.weibo.com/show?fid=1034:5145615399845897",
        "video_weibo": "https://weibo.com/7207262816/O70aCbjnd",
        "video_mweibo": "http://m.weibo.cn/status/5112672433738061",
        "image_album_many": "https://weibo.com/7207262816/P5kWdcfDe",
        "image_album_9": "https://weibo.com/7207262816/P2AFBk387",
        "image_album_2": "https://weibo.com/7207262816/PsFzpzUX2",
        "image_album_3": "https://weibo.com/7207262816/P2rJE157H",
        "many_text": "https://mapp.api.weibo.cn/fx/8102df2b26100b2e608e6498a0d3cfe2.html",
        "repost_single_horizontal_image": "https://weibo.com/7207262816/Q6YCbtAn8",
        "repost_single_upright_image": "https://weibo.com/7207262816/Q617WgOm4",
        "repost_2_image": "https://mapp.api.weibo.cn/fx/77eaa5c2f741894631a87fc4806a1f05.html",
        "repost_video": "https://weibo.com/1694917363/Q0KtXh6z2",
    }
    # 总耗时
    total_time: float = 0
    # 各链接耗时
    name_cost_dict: dict[str, float] = {}

    async def parse_and_render(url: str, name: str) -> None:
        """解析并渲染单个 URL"""
        matched = parser.search_url(url)
        assert matched, f"无法匹配 URL: {url}"

        logger.info(f"{url} | 开始解析微博")
        parse_result = await parser.parse(matched)
        logger.debug(f"{url} | 解析结果: \n{parse_result}")

        # await 所有资源下载，利用计算渲染时间
        assert parse_result.author, f"没有作者: {url}"
        await parse_result.author.get_avatar_path()
        await parse_result.cover_path
        for content in parse_result.contents:
            await content.get_path()

        logger.info(f"{url} | 开始渲染")
        #  渲染图片，并计算耗时
        start_time = time.time()
        image_raw = await renderer.render_image(parse_result)
        end_time = time.time()
        cost_time = end_time - start_time

        nonlocal total_time, name_cost_dict
        total_time += cost_time
        name_cost_dict[name] = cost_time

        logger.success(f"{url} | 渲染成功，耗时: {cost_time} 秒")
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
    logger.success(f"渲染完成，失败数量: {failed_count}, 总耗时: {total_time} 秒")
    logger.success(f"平均耗时: {total_time / len(url_dict)} 秒")
    # 按时间排序
    sorted_url_time_mapping = sorted(name_cost_dict.items(), key=lambda x: x[1])
    for name, cost in sorted_url_time_mapping:
        logger.success(f"耗时: {cost:.5f} 秒 | {name}")


async def test_render_with_emoji():
    """测试使用 BilibiliParser 解析链接并用 CommonRenderer 渲染"""

    import aiofiles

    from nonebot_plugin_parser import pconfig
    from nonebot_plugin_parser.parsers import BilibiliParser
    from nonebot_plugin_parser.renders import _COMMON_RENDERER

    parser = BilibiliParser()
    renderer = _COMMON_RENDERER

    opus_url = "https://b23.tv/GwiHK6N"
    matched = parser.search_url(opus_url)
    assert matched, f"无法匹配 URL: {opus_url}"
    logger.info(f"{opus_url} | 开始解析哔哩哔哩动态")
    parse_result = await parser.parse(matched)
    logger.debug(f"{opus_url} | 解析结果: \n{parse_result}")

    logger.info(f"{opus_url} | 开始渲染")
    image_raw = await renderer.render_image(parse_result)

    assert image_raw, "没有生成图片"

    image_path = pconfig.cache_dir / "aaaaaaa" / "bilibili_opus.png"
    # 创建文件
    image_path.parent.mkdir(parents=True, exist_ok=True)
    async with aiofiles.open(image_path, "wb+") as f:
        await f.write(image_raw)
    logger.success(f"{opus_url} | 渲染成功，图片已保存到 {image_path}")
    assert image_raw, f"没有生成图片: {opus_url}"


async def test_graphics_content():
    """测试使用 BilibiliParser 解析链接并用 CommonRenderer 渲染"""
    import aiofiles

    from nonebot_plugin_parser import pconfig
    from nonebot_plugin_parser.parsers import BilibiliParser
    from nonebot_plugin_parser.renders import _COMMON_RENDERER

    parser = BilibiliParser()
    renderer = _COMMON_RENDERER

    url = "https://www.bilibili.com/opus/1122430505331982343"
    matched = parser.search_url(url)
    assert matched, f"无法匹配 URL: {url}"
    logger.info(f"{url} | 开始解析哔哩哔哩视频")
    parse_result = await parser.parse(matched)
    logger.debug(f"{url} | 解析结果: \n{parse_result}")

    logger.info(f"{url} | 开始渲染")
    image_raw = await renderer.render_image(parse_result)
    assert image_raw, "没有生成图片"

    image_path = pconfig.cache_dir / "aaaaaaa" / "bilibili_graphics_content.png"
    # 创建文件
    image_path.parent.mkdir(parents=True, exist_ok=True)
    async with aiofiles.open(image_path, "wb+") as f:
        await f.write(image_raw)
    logger.success(f"{url} | 渲染成功，图片已保存到 {image_path}")
    assert image_raw, f"没有生成图片: {url}"
