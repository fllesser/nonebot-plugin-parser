from dataclasses import dataclass
import time
from typing import Any

import aiofiles
from nonebot import logger


@dataclass
class RenderDataItem:
    url: str
    url_type: str
    cost: float
    media_size: float
    render_size: float


DATA_COLLECTION: list[RenderDataItem] = []


async def download_all_media(result: Any):
    """下载所有媒体资源"""
    from nonebot_plugin_parser.parsers import ParseResult

    assert isinstance(result, ParseResult), "result 类型错误"

    total_size = 0
    assert result.author, f"没有作者: {result.url}"
    avatar_path = await result.author.get_avatar_path()
    cover_path = await result.cover_path
    for content in result.contents:
        await content.get_path()
    if result.repost:
        repost_size = await download_all_media(result.repost)
        total_size += repost_size

    if avatar_path:
        total_size += avatar_path.stat().st_size / 1024 / 1024
    if cover_path:
        total_size += cover_path.stat().st_size / 1024 / 1024
    # content 取前9项
    for content in result.contents[:9]:
        total_size += (await content.get_path()).stat().st_size / 1024 / 1024

    return total_size


async def test_render_with_emoji():
    """测试使用 BilibiliParser 解析链接并用 CommonRenderer 渲染"""

    from nonebot_plugin_parser import pconfig
    from nonebot_plugin_parser.parsers import BilibiliParser
    from nonebot_plugin_parser.renders import CommonRenderer

    parser = BilibiliParser()
    renderer = CommonRenderer()

    opus_url = "https://b23.tv/GwiHK6N"
    keyword, searched = parser.search_url(opus_url)
    assert searched, f"无法匹配 URL: {opus_url}"
    logger.info(f"{opus_url} | 开始解析哔哩哔哩动态")
    parse_result = await parser.parse(keyword, searched)
    logger.debug(f"{opus_url} | 解析结果: \n{parse_result}")

    total_size = await download_all_media(parse_result)

    logger.info(f"{opus_url} | 开始渲染")
    start_time = time.time()
    image_raw = await renderer.render_image(parse_result)
    end_time = time.time()
    cost_time = end_time - start_time

    image_path = pconfig.cache_dir / "aaaaaaa" / "bilibili_opus_emoji.png"
    # 创建文件
    image_path.parent.mkdir(parents=True, exist_ok=True)
    async with aiofiles.open(image_path, "wb+") as f:
        await f.write(image_raw)
    render_size = image_path.stat().st_size / 1024 / 1024
    logger.success(f"{opus_url} | 渲染成功，图片已保存到 {image_path}")
    DATA_COLLECTION.append(RenderDataItem(opus_url, "哔哩哔哩动态", cost_time, total_size, render_size))


async def test_graphics_content():
    """测试使用 BilibiliParser 解析链接并用 CommonRenderer 渲染"""
    import aiofiles

    from nonebot_plugin_parser import pconfig
    from nonebot_plugin_parser.parsers import BilibiliParser
    from nonebot_plugin_parser.renders import CommonRenderer

    parser = BilibiliParser()
    renderer = CommonRenderer()

    # url = "https://www.bilibili.com/opus/1122430505331982343"
    # url = "https://www.bilibili.com/opus/1040093151889457152"
    url = "https://www.bilibili.com/opus/658174132913963042"
    keyword, searched = parser.search_url(url)
    assert searched, f"无法匹配 URL: {url}"
    logger.info(f"{url} | 开始解析哔哩哔哩 opus")
    parse_result = await parser.parse(keyword, searched)
    logger.debug(f"{url} | 解析结果: \n{parse_result}")

    # await 所有资源下载，计算渲染时间
    total_size = await download_all_media(parse_result)

    logger.info(f"{url} | 开始渲染")
    start_time = time.time()
    image_raw = await renderer.render_image(parse_result)
    end_time = time.time()
    cost_time = end_time - start_time
    logger.success(f"{url} | 渲染成功，耗时: {cost_time} 秒")

    image_path = pconfig.cache_dir / "aaaaaaa" / f"blibili_opus_{url.split('/')[-1]}.png"
    # 创建文件
    image_path.parent.mkdir(parents=True, exist_ok=True)
    async with aiofiles.open(image_path, "wb+") as f:
        await f.write(image_raw)
    render_size = image_path.stat().st_size / 1024 / 1024
    DATA_COLLECTION.append(RenderDataItem(url, "bilibili-opus", cost_time, total_size, render_size))
    logger.success(f"{url} | 渲染成功，图片已保存到 {image_path}")


async def test_read():
    """测试使用 BilibiliParser 解析链接并用 CommonRenderer 渲染"""
    import aiofiles

    from nonebot_plugin_parser import pconfig
    from nonebot_plugin_parser.parsers import BilibiliParser
    from nonebot_plugin_parser.renders import CommonRenderer

    parser = BilibiliParser()
    renderer = CommonRenderer()

    url = "https://www.bilibili.com/read/cv523868"
    keyword, searched = parser.search_url(url)
    assert searched, f"无法匹配 URL: {url}"
    logger.info(f"{url} | 开始解析哔哩哔哩图文")
    parse_result = await parser.parse(keyword, searched)
    logger.debug(f"{url} | 解析结果: \n{parse_result}")

    # await 所有资源下载，计算渲染时间
    total_size = await download_all_media(parse_result)

    logger.info(f"{url} | 开始渲染")
    start_time = time.time()
    image_raw = await renderer.render_image(parse_result)
    end_time = time.time()
    cost_time = end_time - start_time
    logger.success(f"{url} | 渲染成功，耗时: {cost_time} 秒")

    image_path = pconfig.cache_dir / "aaaaaaa" / "bilibili_read.png"
    # 创建文件
    image_path.parent.mkdir(parents=True, exist_ok=True)
    async with aiofiles.open(image_path, "wb+") as f:
        await f.write(image_raw)

    render_size = image_path.stat().st_size / 1024 / 1024
    DATA_COLLECTION.append(RenderDataItem(url, "bilibili-read", cost_time, total_size, render_size))

    logger.success(f"{url} | 渲染成功，图片已保存到 {image_path}")


async def test_common_render():
    """测试使用 WeiboParser 解析链接并用 CommonRenderer 渲染"""

    from nonebot_plugin_parser import pconfig
    from nonebot_plugin_parser.parsers import WeiBoParser
    from nonebot_plugin_parser.renders import CommonRenderer

    parser = WeiBoParser()
    renderer = CommonRenderer()

    urls = {
        "微博视频": "https://weibo.com/3800478724/Q9ectF6yO",
        "微博视频2": "https://weibo.com/3800478724/Q9dXDkrul",
        "微博图集(超过9张)": "https://weibo.com/7793636592/Q96aMs3dG",
        "微博图集(9张)": "https://weibo.com/6989461668/Q3bmxf778",
        "微博图集(2张)": "https://weibo.com/7983081104/Q98U3sDmH",
        "微博图集(3张)": "https://weibo.com/7299853661/Q8LXh1X74",
        "微博图集(4张)": "https://weibo.com/6458148211/Q3Cdb5vgP",
        "微博纯文": "https://mapp.api.weibo.cn/fx/8102df2b26100b2e608e6498a0d3cfe2.html",
        "微博纯文2": "https://weibo.com/5647310207/Q9c0ZwW2X",
        "微博转发纯文": "https://weibo.com/2385967842/Q9epfFLvQ",
        "微博转发(横图)": "https://weibo.com/7207262816/Q6YCbtAn8",
        "微博转发(竖图)": "https://weibo.com/7207262816/Q617WgOm4",
        "微博转发(两张)": "https://mapp.api.weibo.cn/fx/77eaa5c2f741894631a87fc4806a1f05.html",
        "微博转发(视频)": "https://weibo.com/1694917363/Q0KtXh6z2",
    }

    async def parse_and_render(url_type: str, url: str) -> None:
        """解析并渲染单个 URL"""
        keyword, searched = parser.search_url(url)
        assert searched, f"无法匹配 URL: {url}"

        logger.info(f"{url} | 开始解析微博")
        parse_result = await parser.parse(keyword, searched)
        logger.debug(f"{url} | 解析结果: \n{parse_result}")

        # await 所有资源下载，利用计算渲染时间
        total_size = await download_all_media(parse_result)

        logger.info(f"{url} | 开始渲染")
        #  渲染图片，并计算耗时
        start_time = time.time()
        image_raw = await renderer.render_image(parse_result)
        end_time = time.time()
        cost_time = end_time - start_time

        logger.success(f"{url} | 渲染成功，耗时: {cost_time} 秒")
        image_path = pconfig.cache_dir / "aaaaaaa" / f"{url_type}.png"
        # 创建文件
        image_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(image_path, "wb+") as f:
            await f.write(image_raw)

        render_size = image_path.stat().st_size / 1024 / 1024
        DATA_COLLECTION.append(RenderDataItem(url, url_type, cost_time, total_size, render_size))

    for url_type, url in urls.items():
        try:
            await parse_and_render(url_type, url)
        except Exception:
            logger.exception(f"{url} | 渲染失败")


def test_write_result():
    # 按时间排序
    sorted_data_collection = sorted(DATA_COLLECTION, key=lambda x: x.cost)
    result = "| 类型 | 耗时(秒) | 渲染所用图片总大小(MB) | 导出图片大小(MB)\n"
    result += "| --- | --- | --- | --- |\n"
    for item in sorted_data_collection:
        result += (
            f"| [{item.url_type}]({item.url}) | {item.cost:.5f} | {item.media_size:.5f} | {item.render_size:.5f} |\n"
        )

    with open("render_result.md", "w+") as f:
        f.write(result)
