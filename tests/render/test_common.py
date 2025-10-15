import time

import aiofiles
from nonebot import logger


async def test_render_with_emoji():
    """测试使用 BilibiliParser 解析链接并用 CommonRenderer 渲染"""

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

    image_path = pconfig.cache_dir / "aaaaaaa" / "bilibili_opus_emoji.png"
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

    # url = "https://www.bilibili.com/opus/1122430505331982343"
    # url = "https://www.bilibili.com/opus/1040093151889457152"
    url = "https://www.bilibili.com/opus/658174132913963042"
    matched = parser.search_url(url)
    assert matched, f"无法匹配 URL: {url}"
    logger.info(f"{url} | 开始解析哔哩哔哩视频")
    parse_result = await parser.parse(matched)
    logger.debug(f"{url} | 解析结果: \n{parse_result}")

    # await 所有资源下载，计算渲染时间
    assert parse_result.author, "没有作者信息"
    await parse_result.author.get_avatar_path()
    for content in parse_result.contents:
        await content.get_path()

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
    logger.success(f"{url} | 渲染成功，图片已保存到 {image_path}")
    assert image_raw, f"没有生成图片: {url}"


async def test_read():
    """测试使用 BilibiliParser 解析链接并用 CommonRenderer 渲染"""
    import aiofiles

    from nonebot_plugin_parser import pconfig
    from nonebot_plugin_parser.parsers import BilibiliParser
    from nonebot_plugin_parser.renders import _COMMON_RENDERER

    parser = BilibiliParser()
    renderer = _COMMON_RENDERER

    url = "https://www.bilibili.com/read/cv523868"
    matched = parser.search_url(url)
    assert matched, f"无法匹配 URL: {url}"
    logger.info(f"{url} | 开始解析哔哩哔哩图文")
    parse_result = await parser.parse(matched)
    logger.debug(f"{url} | 解析结果: \n{parse_result}")

    # await 所有资源下载，计算渲染时间
    assert parse_result.author, "没有作者信息"
    await parse_result.author.get_avatar_path()
    for content in parse_result.contents:
        await content.get_path()

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
    logger.success(f"{url} | 渲染成功，图片已保存到 {image_path}")
    assert image_raw, f"没有生成图片: {url}"


async def test_common_render():
    """测试使用 WeiboParser 解析链接并用 CommonRenderer 渲染"""

    from nonebot_plugin_parser import pconfig
    from nonebot_plugin_parser.parsers import ParseResult, WeiBoParser
    from nonebot_plugin_parser.renders import _COMMON_RENDERER

    parser = WeiBoParser()
    renderer = _COMMON_RENDERER

    async def download_all_media(parse_result: ParseResult):
        """下载所有媒体资源"""
        assert parse_result.author, f"没有作者: {parse_result.url}"
        avatar_path = await parse_result.author.get_avatar_path()
        cover_path = await parse_result.cover_path
        for content in parse_result.contents:
            await content.get_path()
        if parse_result.repost:
            await download_all_media(parse_result.repost)

        # 计算用于绘制的图片总大小 MB
        total_size = 0
        if avatar_path:
            total_size += avatar_path.stat().st_size / 1024 / 1024
        if cover_path:
            total_size += cover_path.stat().st_size / 1024 / 1024
        # content 取前9项
        for content in parse_result.contents[:9]:
            total_size += (await content.get_path()).stat().st_size / 1024 / 1024
        return total_size

    url_dict = {
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
    # 总耗时
    total_time: float = 0
    # 各链接耗时
    data_collection: dict[str, tuple[str, float, float, float]] = {}

    async def parse_and_render(url: str, name: str) -> None:
        """解析并渲染单个 URL"""
        matched = parser.search_url(url)
        assert matched, f"无法匹配 URL: {url}"

        logger.info(f"{url} | 开始解析微博")
        parse_result = await parser.parse(matched)
        logger.debug(f"{url} | 解析结果: \n{parse_result}")

        # await 所有资源下载，利用计算渲染时间
        total_size = await download_all_media(parse_result)

        logger.info(f"{url} | 开始渲染")
        #  渲染图片，并计算耗时
        start_time = time.time()
        image_raw = await renderer.render_image(parse_result)
        end_time = time.time()
        cost_time = end_time - start_time

        nonlocal total_time, data_collection
        total_time += cost_time

        logger.success(f"{url} | 渲染成功，耗时: {cost_time} 秒")
        assert image_raw, f"没有生成图片: {url}"
        image_path = pconfig.cache_dir / "aaaaaaa" / f"{name}.png"
        # 创建文件
        image_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(image_path, "wb+") as f:
            await f.write(image_raw)
        data_collection[name] = (url, cost_time, total_size, image_path.stat().st_size / 1024 / 1024)
        logger.success(f"{url} | 渲染成功，图片已保存到 {image_path}")

    failed_count = 0
    for name, url in url_dict.items():
        try:
            await parse_and_render(url, name)
        except Exception:
            logger.exception(f"{url} | 渲染失败")
            failed_count += 1

    result_markdown = "### 渲染结果\n"
    result_markdown += f"失败数量: {failed_count}\n"
    result_markdown += f"总耗时: {total_time} 秒\n"
    result_markdown += f"平均耗时: {total_time / len(url_dict)} 秒\n"
    result_markdown += "### 详细结果\n"
    # 按时间排序
    sorted_url_time_mapping = sorted(data_collection.items(), key=lambda x: x[1][1])
    result_markdown += "| 类型 | 耗时(秒) | 渲染所用图片总大小(MB) | 导出图片大小(MB)\n"
    result_markdown += "| --- | --- | --- | --- |\n"
    for name, (url, cost, total_size, image_size) in sorted_url_time_mapping:
        result_markdown += f"| [{name}]({url}) | {cost:.5f} | {total_size:.5f} | {image_size:.5f} |\n"
