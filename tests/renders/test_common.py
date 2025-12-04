from typing import TYPE_CHECKING
from dataclasses import dataclass

import pytest
from nonebot import logger

if TYPE_CHECKING:
    from nonebot_plugin_parser.parsers import ParseResult


@dataclass
class Result:
    """存储解析结果的数据类"""

    url: str
    url_type: str
    parse_result: "ParseResult"


@pytest.fixture(scope="module")
def result_collections():
    """收集所有解析结果的 fixture"""
    return list[Result]()


@pytest.fixture(scope="module", autouse=True)
async def render_collected_results(result_collections: list[Result]):
    """在所有测试完成后，并发渲染收集到的结果"""
    yield

    if not result_collections:
        logger.warning("没有收集到任何解析结果")
        return

    # 导入渲染相关的模块
    import time
    import asyncio

    import aiofiles

    from nonebot_plugin_parser import pconfig
    from nonebot_plugin_parser.renders import CommonRenderer

    renderer = CommonRenderer()
    result_file = "render_result.md"

    # 写入表头
    async with aiofiles.open(result_file, "w") as f:
        await f.write("| 类型 | 耗时(秒) | 渲染所用图片总大小(MB) | 导出图片大小(MB) |\n")
        await f.write("| --- | --- | --- | --- |\n")

    async def render_single(item: Result) -> dict | None:
        """渲染单个结果"""
        try:
            logger.info(f"{item.url} | 开始渲染")

            # 下载媒体资源
            total_size = await _download_all_media(item.parse_result)

            # 渲染图片
            start_time = time.time()
            image_raw = await renderer.render_image(item.parse_result)
            cost_time = time.time() - start_time

            # 保存图片
            image_path = pconfig.cache_dir / "test_renders" / f"{item.url_type}.png"
            image_path.parent.mkdir(parents=True, exist_ok=True)
            async with aiofiles.open(image_path, "wb") as f:
                await f.write(image_raw)

            render_size = image_path.stat().st_size / 1024 / 1024

            logger.success(f"{item.url} | 渲染成功，耗时: {cost_time:.5f} 秒")
            return {
                "url": item.url,
                "url_type": item.url_type,
                "cost": cost_time,
                "media_size": total_size,
                "render_size": render_size,
            }
        except Exception:
            logger.exception(f"{item.url} | 渲染失败")
            return None

    # 并发渲染所有结果
    logger.info(f"开始并发渲染 {len(result_collections)} 个结果")
    render_results = await asyncio.gather(*[render_single(item) for item in result_collections])
    render_data = [r for r in render_results if r is not None]

    # 按耗时排序并写入结果
    if render_data:
        sorted_data = sorted(render_data, key=lambda x: x["cost"])
        async with aiofiles.open(result_file, "a") as f:
            for item in sorted_data:
                await f.write(f"| [{item['url_type']}]({item['url']}) | {item['cost']:.5f} ")
                await f.write(f"| {item['media_size']:.5f} | {item['render_size']:.5f} |\n")
        logger.success(f"所有测试结果已写入 {result_file}")


async def _download_all_media(result) -> float:
    """并发下载所有媒体资源并返回总大小(MB)"""
    import asyncio
    from pathlib import Path

    from nonebot_plugin_parser.parsers import ParseResult

    assert isinstance(result, ParseResult)
    assert result.author, f"没有作者: {result.url}"

    # 准备所有下载任务
    download_tasks = []

    # 添加头像和封面下载任务
    download_tasks.append(result.author.get_avatar_path())
    download_tasks.append(result.cover_path)

    # 添加内容下载任务
    for content in result.contents:
        download_tasks.append(content.get_path())

    # 并发下载所有资源
    paths = await asyncio.gather(
        *download_tasks,
        return_exceptions=True,
    )

    # 处理转发内容（递归）
    total_size: float = 0
    if result.repost:
        total_size += await _download_all_media(result.repost)

    # 计算大小（跳过异常结果）
    for path in paths:
        if isinstance(path, Exception):
            # 跳过异常
            continue
        if path and isinstance(path, Path):
            try:
                total_size += path.stat().st_size / 1024 / 1024
            except (AttributeError, OSError):
                # 跳过无效路径或文件不存在的情况
                pass

    return total_size


@pytest.mark.asyncio
async def test_bilibili_opus_with_emoji(result_collections: list[Result]):
    """测试解析哔哩哔哩动态（包含 emoji）"""
    from nonebot_plugin_parser.parsers import BilibiliParser

    parser = BilibiliParser()
    url = "https://b23.tv/GwiHK6N"

    keyword, searched = parser.search_url(url)
    assert searched, f"无法匹配 URL: {url}"

    logger.info(f"{url} | 开始解析")
    try:
        parse_result = await parser.parse(keyword, searched)
        logger.debug(f"{url} | 解析成功")

        # 收集解析结果
        result_collections.append(Result(url, "哔哩哔哩动态", parse_result))
    except Exception as e:
        pytest.skip(str(e))


@pytest.mark.asyncio
async def test_bilibili_opus_graphics(result_collections: list[Result]):
    """测试解析哔哩哔哩图文动态"""
    from nonebot_plugin_parser.parsers import BilibiliParser

    parser = BilibiliParser()
    url = "https://www.bilibili.com/opus/658174132913963042"

    keyword, searched = parser.search_url(url)
    assert searched, f"无法匹配 URL: {url}"

    logger.info(f"{url} | 开始解析")
    try:
        parse_result = await parser.parse(keyword, searched)
        logger.debug(f"{url} | 解析成功")

        # 收集解析结果
        result_collections.append(Result(url, "bilibili-opus", parse_result))
    except Exception as e:
        pytest.skip(str(e))


@pytest.mark.asyncio
async def test_bilibili_read(result_collections: list[Result]):
    """测试解析哔哩哔哩专栏"""
    from nonebot_plugin_parser.parsers import BilibiliParser

    parser = BilibiliParser()
    url = "https://www.bilibili.com/read/cv523868"

    keyword, searched = parser.search_url(url)
    assert searched, f"无法匹配 URL: {url}"

    logger.info(f"{url} | 开始解析")
    parse_result = await parser.parse(keyword, searched)
    logger.debug(f"{url} | 解析成功")

    # 收集解析结果
    result_collections.append(Result(url, "bilibili-read", parse_result))


@pytest.mark.asyncio
async def test_weibo_urls(result_collections: list[Result]):
    """并发测试解析多个微博链接"""
    import asyncio

    from nonebot_plugin_parser.parsers import WeiBoParser

    parser = WeiBoParser()

    urls = {
        "微博视频": "https://weibo.com/3800478724/Q9ectF6yO",
        "微博视频2": "https://weibo.com/3800478724/Q9dXDkrul",
        "微博图集(超过9张)": "https://weibo.com/7793636592/Q96aMs3dG",
        "微博图集(9张)": "https://weibo.com/6989461668/Q3bmxf778",
        "微博图集(2张)": "https://weibo.com/7983081104/Q98U3sDmH",
        "微博图集(3张)": "https://weibo.com/7299853661/Q8LXh1X74",
        "微博图集(4张)": "https://weibo.com/6458148211/Q3Cdb5vgP",
        "微博纯文2": "https://weibo.com/5647310207/Q9c0ZwW2X",
        "微博转发纯文": "https://weibo.com/2385967842/Q9epfFLvQ",
        "微博转发(横图)": "https://weibo.com/7207262816/Q6YCbtAn8",
        "微博转发(竖图)": "https://weibo.com/7207262816/Q617WgOm4",
        "微博转发(视频)": "https://weibo.com/1694917363/Q0KtXh6z2",
    }

    async def parse_single(url_type: str, url: str) -> Result | None:
        """解析单个微博链接"""
        try:
            keyword, searched = parser.search_url(url)
            assert searched, f"无法匹配 URL: {url}"

            logger.info(f"{url} | 开始解析")
            parse_result = await parser.parse(keyword, searched)
            logger.debug(f"{url} | 解析成功")

            return Result(url, url_type, parse_result)
        except Exception:
            logger.exception(f"{url} | 解析失败")
            return None

    # 并发解析所有微博链接
    logger.info(f"开始并发解析 {len(urls)} 个微博链接")
    results = await asyncio.gather(*[parse_single(url_type, url) for url_type, url in urls.items()])

    # 收集成功的解析结果
    for result in results:
        if result is not None:
            result_collections.append(result)
