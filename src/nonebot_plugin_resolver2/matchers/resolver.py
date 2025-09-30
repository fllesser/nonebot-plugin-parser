"""通用解析器"""

import re

from nonebot.matcher import Matcher

from ..exception import handle_exception
from ..parsers.data import ImageContent, ParseResult, VideoContent
from .preprocess import KeyPatternMatched, Keyword, on_keyword_regex
from .render import Renderer

# 定义所有支持的平台和对应的正则表达式
PLATFORM_PATTERNS: list[tuple[str, str]] = [
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

# 创建统一的 matcher
resolver = on_keyword_regex(*PLATFORM_PATTERNS)


@resolver.handle()
@handle_exception()
async def _(
    matcher: Matcher,
    searched: re.Match[str] = KeyPatternMatched(),
    keyword: str = Keyword(),
):
    """统一的解析处理器"""
    from ..download import DOWNLOADER
    from ..parsers import DouyinParser, KuaishouParser, WeiBoParser, XiaoHongShuParser

    url = searched.group(0)

    result: ParseResult | None = None

    # 根据匹配到的关键词判断平台并调用对应的 parser
    if keyword in ("v.douyin", "douyin"):
        parser = DouyinParser()
        result = await parser.parse_and_download(url)

    elif keyword in ("xiaohongshu.com", "xhslink.com"):
        parser = XiaoHongShuParser()
        parse_result = await parser.parse_url(url)
        # 手动下载（临时方案）
        if parse_result.cover_url:
            parse_result.cover_path = await DOWNLOADER.download_img(parse_result.cover_url)
        if parse_result.content:
            if isinstance(parse_result.content, VideoContent) and parse_result.content.video_url:
                parse_result.content.video_path = await DOWNLOADER.download_video(parse_result.content.video_url)
            elif isinstance(parse_result.content, ImageContent) and parse_result.content.pic_urls:
                parse_result.content.pic_paths = await DOWNLOADER.download_imgs_without_raise(
                    parse_result.content.pic_urls
                )
        result = parse_result

    elif keyword in ("v.kuaishou.com", "kuaishou", "chenzhongtech"):
        parser = KuaishouParser()
        parse_result = await parser.parse_url(url)
        # 手动下载（临时方案）
        if parse_result.cover_url:
            parse_result.cover_path = await DOWNLOADER.download_img(parse_result.cover_url)
        if parse_result.content:
            if isinstance(parse_result.content, VideoContent) and parse_result.content.video_url:
                parse_result.content.video_path = await DOWNLOADER.download_video(parse_result.content.video_url)
            elif isinstance(parse_result.content, ImageContent) and parse_result.content.pic_urls:
                parse_result.content.pic_paths = await DOWNLOADER.download_imgs_without_raise(
                    parse_result.content.pic_urls
                )
        result = parse_result

    elif keyword in ("weibo.com", "m.weibo.cn"):
        parser = WeiBoParser()
        parse_result = await parser.parse_share_url(url)
        # 手动下载（临时方案）
        if parse_result.content:
            if isinstance(parse_result.content, VideoContent) and parse_result.content.video_url:
                parse_result.content.video_path = await DOWNLOADER.download_video(
                    parse_result.content.video_url, ext_headers=parser.ext_headers
                )
            elif isinstance(parse_result.content, ImageContent) and parse_result.content.pic_urls:
                parse_result.content.pic_paths = await DOWNLOADER.download_imgs_without_raise(
                    parse_result.content.pic_urls, ext_headers=parser.ext_headers
                )
        result = parse_result

    if result:
        # 发送初始消息
        initial_msg = Renderer.render_initial_message(result)
        await matcher.send(initial_msg)

        # 渲染内容消息并发送
        messages = Renderer.render_content_messages(result)
        for message in messages:
            await message.send()
