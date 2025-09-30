"""统一的解析器 matcher"""

import re

from nonebot import logger
from nonebot.matcher import Matcher

from ..config import rconfig
from ..download import DOWNLOADER
from ..exception import handle_exception
from ..parsers import DouyinParser, KuaishouParser, WeiBoParser, XiaoHongShuParser
from ..parsers.data import ImageContent, ParseResult, VideoContent
from .preprocess import KeyPatternMatched, Keyword, on_keyword_regex
from .render import Renderer

# 定义所有支持的平台和对应的正则表达式
ALL_PLATFORM_PATTERNS: list[tuple[str, str]] = [
    # 抖音
    ("v.douyin", r"https://v\.douyin\.com/[a-zA-Z0-9_\-]+"),
    (
        "douyin",
        r"https://www\.(?:douyin|iesdouyin)\.com/(?:video|note|share/(?:video|note|slides))/[0-9]+",
    ),
    # 小红书
    ("xiaohongshu.com", r"https?://(?:www\.)?xiaohongshu\.com/[A-Za-z0-9._?%&+=/#@-]*"),
    ("xhslink.com", r"https?://xhslink\.com/[A-Za-z0-9._?%&+=/#@-]*"),
    # 快手
    ("v.kuaishou.com", r"https?://v\.kuaishou\.com/[A-Za-z\d._?%&+\-=/#]+"),
    ("kuaishou", r"https?://(?:www\.)?kuaishou\.com/[A-Za-z\d._?%&+\-=/#]+"),
    ("chenzhongtech", r"https?://(?:v\.m\.)?chenzhongtech\.com/fw/[A-Za-z\d._?%&+\-=/#]+"),
    # Twitter/X
    ("x.com", r"https?://x.com/[0-9-a-zA-Z_]{1,20}/status/([0-9]+)"),
    # 微博
    ("weibo.com", r"https?://(?:www\.|m\.)?weibo\.com/[A-Za-z\d._?%&+\-=/#@]+"),
    ("m.weibo.cn", r"https?://m\.weibo\.cn/[A-Za-z\d._?%&+\-=/#@]+"),
]

# 关键词到平台名称的映射
KEYWORD_TO_PLATFORM = {
    "v.douyin": "douyin",
    "douyin": "douyin",
    "xiaohongshu.com": "xiaohongshu",
    "xhslink.com": "xiaohongshu",
    "v.kuaishou.com": "kuaishou",
    "kuaishou": "kuaishou",
    "chenzhongtech": "kuaishou",
    "x.com": "twitter",
    "weibo.com": "weibo",
    "m.weibo.cn": "weibo",
}


def _get_enabled_patterns() -> list[tuple[str, str]]:
    """根据配置获取启用的平台正则表达式列表"""
    # 获取禁用的平台列表
    disabled_platforms = set(rconfig.r_disable_resolvers)

    # 如果未配置小红书 cookie，也禁用小红书
    if not rconfig.r_xhs_ck:
        disabled_platforms.add("xiaohongshu")
        logger.warning("未配置小红书 cookie, 小红书解析已关闭")

    # 过滤掉被禁用的平台
    enabled_patterns = [
        (keyword, pattern)
        for keyword, pattern in ALL_PLATFORM_PATTERNS
        if KEYWORD_TO_PLATFORM.get(keyword) not in disabled_platforms
    ]
    logger.info(f"启用的平台: {', '.join({KEYWORD_TO_PLATFORM[k] for k, _ in enabled_patterns})}")

    return enabled_patterns


async def _download_resources(result: ParseResult, ext_headers: dict[str, str] | None = None) -> None:
    """统一的资源下载函数

    Args:
        result: 解析结果
        ext_headers: 额外的请求头（用于某些需要特殊headers的平台，如微博）
    """
    # 下载封面
    if result.cover_url:
        result.cover_path = await DOWNLOADER.download_img(result.cover_url)

    # 下载内容
    if result.content:
        if isinstance(result.content, VideoContent):
            # 下载视频
            if result.content.video_url:
                result.content.video_path = await DOWNLOADER.download_video(
                    result.content.video_url, ext_headers=ext_headers
                )
        elif isinstance(result.content, ImageContent):
            # 下载图片
            if result.content.pic_urls:
                result.content.pic_paths = await DOWNLOADER.download_imgs_without_raise(
                    result.content.pic_urls, ext_headers=ext_headers
                )


# 平台解析器映射
PLATFORM_PARSERS = {
    "douyin": DouyinParser,
    "xiaohongshu": XiaoHongShuParser,
    "kuaishou": KuaishouParser,
    "weibo": WeiBoParser,
}

# 根据配置创建只包含启用平台的 matcher
resolver = on_keyword_regex(*_get_enabled_patterns())


@resolver.handle()
@handle_exception()
async def _(
    keyword: str = Keyword(),
    searched: re.Match[str] = KeyPatternMatched(),
):
    """统一的解析处理器"""
    url = searched.group(0)
    platform = KEYWORD_TO_PLATFORM.get(keyword)
    if not platform:
        logger.warning(f"未找到关键词 {keyword} 对应的平台")
        return

    # 获取对应平台的解析器
    parser_class = PLATFORM_PARSERS.get(platform)
    if not parser_class:
        logger.warning(f"未找到平台 {platform} 的解析器")
        return

    # 创建解析器并解析 URL（只获取元数据，不下载）
    parser = parser_class()
    result = await parser.parse_url(url)

    if result:
        # 1. 先发送初始消息（快速反馈给用户）
        initial_msg = Renderer.render_initial_message(result)
        await resolver.send(initial_msg)

        # 2. 下载资源
        ext_headers = getattr(parser, "ext_headers", None)  # 微博等平台需要特殊请求头
        await _download_resources(result, ext_headers)

        # 3. 渲染内容消息并发送
        messages = Renderer.render_content_messages(result)
        for message in messages:
            await message.send()
