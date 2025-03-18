import asyncio
from pathlib import Path
import re

import aiohttp
from bilibili_api import (
    HEADERS,
    video,
)
from bilibili_api.video import VideoDownloadURLDataDetecter
from nonebot.adapters.onebot.v11 import Bot, Message, MessageEvent, MessageSegment
from nonebot.adapters.onebot.v11.exception import ActionFailed
from nonebot.log import logger
from nonebot.params import CommandArg
from nonebot.plugin.on import on_command, on_message

from nonebot_plugin_resolver2.config import DURATION_MAXIMUM, NEED_UPLOAD, NICKNAME, plugin_cache_dir
from nonebot_plugin_resolver2.download import (
    download_file_by_stream,
    download_imgs_without_raise,
    merge_av,
    re_encode_video,
)
from nonebot_plugin_resolver2.download.utils import delete_boring_characters
from nonebot_plugin_resolver2.parsers.bilibili import CREDENTIAL, parse_favlist, parse_live, parse_opus, parse_read

from .filter import is_not_in_disabled_groups
from .preprocess import ExtractText, Keyword, r_keywords
from .utils import get_file_seg, get_video_seg, send_segments

bilibili = on_message(
    rule=is_not_in_disabled_groups & r_keywords("bilibili", "bili2233", "b23", "BV", "av"),
    priority=5,
)

bili_music = on_command(cmd="bm", block=True)

PATTERNS: dict[str, re.Pattern] = {
    "BV": re.compile(r"(BV[1-9a-zA-Z]{10})(?:\s)?(\d{1,3})?"),
    "av": re.compile(r"av(\d{6,})(?:\s)?(\d{1,3})?"),
    "/BV": re.compile(r"/(BV[1-9a-zA-Z]{10})()"),
    "/av": re.compile(r"/av(\d{6,})()"),
    "b23": re.compile(r"https?://b23\.tv/[A-Za-z\d\._?%&+\-=/#]+()()"),
    "bili2233": re.compile(r"https?://bili2233\.cn/[A-Za-z\d\._?%&+\-=/#]+()()"),
    "bilibili": re.compile(r"https?://(?:space|www|live|m|t)?\.?bilibili\.com/[A-Za-z\d\._?%&+\-=/#]+()()"),
}


@bilibili.handle()
async def _(bot: Bot, text: str = ExtractText(), keyword: str = Keyword()):
    share_prefix = f"{NICKNAME}解析 | 哔哩哔哩 - "
    match = PATTERNS[keyword].search(text)
    if not match:
        logger.info(f"{text} 中的链接或id无效, 忽略")
        return
    url, video_id, page_num = match.group(0), match.group(1), match.group(2)

    # 短链重定向地址
    if keyword in ("b23", "bili2233"):
        b23url = url
        async with aiohttp.ClientSession() as session:
            async with session.get(b23url, headers=HEADERS, allow_redirects=False) as resp:
                url = resp.headers.get("Location", b23url)
        if url == b23url:
            logger.info(f"链接 {url} 无效，忽略")
            return

    # 链接中是否包含BV，av号
    if url and (id_type := next((i for i in ("/BV", "/av") if i in url), None)):
        if match := PATTERNS[id_type].search(url):
            keyword = id_type
            video_id = match.group(1)
    # 预发送消息列表
    segs: list[Message | MessageSegment | str] = []
    # 如果不是视频
    if not video_id:
        # 动态
        if "t.bilibili.com" in url or "/opus" in url:
            matched = re.search(r"/(\d+)", url)
            if not matched:
                logger.warning(f"链接 {url} 无效 - 没有获取到动态 id, 忽略")
                return
            opus_id = int(matched.group(1))
            img_lst, text = await parse_opus(opus_id)
            await bilibili.send(f"{share_prefix}动态")
            segs = [text]
            if img_lst:
                paths = await download_imgs_without_raise(img_lst)
                segs.extend(MessageSegment.image(path) for path in paths)
            await send_segments(bilibili, segs)
            await bilibili.finish()
        # 直播间解析
        elif "/live" in url:
            # https://live.bilibili.com/30528999?hotRank=0
            matched = re.search(r"/(\d+)", url)
            if not matched:
                logger.info(f"链接 {url} 无效 - 没有获取到直播间 id, 忽略")
                return
            room_id = int(matched.group(1))
            title, cover, keyframe = await parse_live(room_id)
            if not title:
                await bilibili.finish(f"{share_prefix}直播 - 未找到直播间信息")
            res = f"{share_prefix}直播 {title}"
            res += MessageSegment.image(cover) if cover else ""
            res += MessageSegment.image(keyframe) if keyframe else ""
            await bilibili.finish(res)
        # 专栏解析
        elif "/read" in url:
            matched = re.search(r"read/cv(\d+)", url)
            if not matched:
                logger.warning(f"链接 {url} 无效 - 没有获取到专栏 id, 忽略")
                return
            read_id = int(matched.group(1))
            texts, urls = await parse_read(read_id)
            await bilibili.send(f"{share_prefix}专栏")
            # 并发下载
            paths = await download_imgs_without_raise(urls)
            # 反转路径列表，pop 时，则为原始顺序，提高性能
            paths.reverse()
            segs = []
            for text in texts:
                if text:
                    segs.append(text)
                else:
                    segs.append(MessageSegment.image(paths.pop()))
            if segs:
                await send_segments(bilibili, segs)
                await bilibili.finish()
        # 收藏夹解析
        elif "/favlist" in url:
            # https://space.bilibili.com/22990202/favlist?fid=2344812202
            matched = re.search(r"favlist\?fid=(\d+)", url)
            if not matched:
                logger.warning(f"链接 {url} 无效 - 没有获取到收藏夹 id, 忽略")
                return
            fav_id = int(matched.group(1))
            # 获取收藏夹内容，并下载封面
            texts, urls = await parse_favlist(fav_id)
            await bilibili.send(f"{share_prefix}收藏夹\n正在为你找出相关链接请稍等...")
            paths: list[Path] = await download_imgs_without_raise(urls)
            segs = []
            # 组合 text 和 image
            for path, text in zip(paths, texts):
                segs.append(MessageSegment.image(path) + text)
            await send_segments(bilibili, segs)
            await bilibili.finish()
        else:
            logger.warning(f"不支持的链接: {url}")
            await bilibili.finish()

    # 视频
    if keyword in ("av", "/av"):
        v = video.Video(aid=int(video_id), credential=CREDENTIAL)
    else:
        v = video.Video(bvid=video_id, credential=CREDENTIAL)
    # 合并转发消息 list
    segs = []
    try:
        video_info = await v.get_info()
    except Exception as e:
        await bilibili.finish(f"{share_prefix}出错 {e}")
    await bilibili.send(f"{share_prefix}视频")
    video_title, video_cover, video_desc, video_duration = (
        video_info["title"],
        video_info["pic"],
        video_info["desc"],
        video_info["duration"],
    )
    # 校准 分 p 的情况
    page_num = (int(page_num) - 1) if page_num else 0
    if (pages := video_info.get("pages")) and len(pages) > 1:
        # 解析URL
        if url and (match := re.search(r"(?:&|\?)p=(\d{1,3})", url)):
            page_num = int(match.group(1)) - 1
        # 取模防止数组越界
        page_num = page_num % len(pages)
        p_video = pages[page_num]
        video_duration = p_video.get("duration", video_duration)
        if p_name := p_video.get("part").strip():
            segs.append(f"分集标题: {p_name}")
        if first_frame := p_video.get("first_frame"):
            segs.append(MessageSegment.image(first_frame))
    else:
        page_num = 0
    online = await v.get_online()
    online_str = f"🏄‍♂️ 总共 {online['total']} 人在观看，{online['count']} 人在网页端观看"
    segs.append(MessageSegment.image(video_cover))
    segs.append(f"{video_title}\n{extra_bili_info(video_info)}\n📝 简介：{video_desc}\n{online_str}")
    # 这里是总结内容，如果写了 cookie 就可以
    if CREDENTIAL:
        ai_conclusion = await v.get_ai_conclusion(await v.get_cid(0))
        ai_summary = ai_conclusion.get("model_result", {"summary": ""}).get("summary", "").strip()
        ai_summary = f"AI总结: {ai_summary}" if ai_summary else "该视频暂不支持AI总结"
        segs.append(ai_summary)
    if video_duration > DURATION_MAXIMUM:
        segs.append(
            f"⚠️ 当前视频时长 {video_duration // 60} 分钟，超过管理员设置的最长时间 {DURATION_MAXIMUM // 60} 分钟!"
        )
    await send_segments(bilibili, segs)
    if video_duration > DURATION_MAXIMUM:
        logger.info(f"video duration > {DURATION_MAXIMUM}, do not download")
        return
    # 下载视频和音频
    try:
        prefix = f"{video_id}-{page_num}"
        video_name = f"{prefix}.mp4"
        video_path = plugin_cache_dir / video_name
        if not video_path.exists():
            download_url_data = await v.get_download_url(page_index=page_num)
            detecter = VideoDownloadURLDataDetecter(download_url_data)
            streams = detecter.detect_best_streams()
            video_stream = streams[0]
            audio_stream = streams[1]
            if video_stream is None or audio_stream is None:
                return await bilibili.finish(f"{share_prefix}未找到视频或音频流")
            video_url, audio_url = video_stream.url, audio_stream.url

            # 下载视频和音频
            v_path, a_path = await asyncio.gather(
                download_file_by_stream(video_url, file_name=f"{prefix}-video.m4s", ext_headers=HEADERS),
                download_file_by_stream(audio_url, file_name=f"{prefix}-audio.m4s", ext_headers=HEADERS),
            )

            await merge_av(v_path=v_path, a_path=a_path, output_path=video_path)
    except Exception:
        await bilibili.send("视频下载失败, 请联系机器人管理员", reply_message=True)
        raise
    try:
        await bilibili.send(await get_video_seg(video_path))
    except ActionFailed as e:
        message: str = e.info.get("message", "")
        # 无缩略图
        if not message.endswith(".png'"):
            raise
        # 重新编码为 h264
        logger.warning("视频上传出现无缩略图错误，将重新编码为 h264 进行上传")
        h264_path = await re_encode_video(video_path)
        await bilibili.send(await get_video_seg(h264_path))


@bili_music.handle()
async def _(bot: Bot, event: MessageEvent, args: Message = CommandArg()):
    text = args.extract_plain_text().strip()
    match = re.match(r"^(BV[1-9a-zA-Z]{10})(?:\s)?(\d{1,3})?$", text)
    if not match:
        await bili_music.finish("命令格式: bm BV1LpD3YsETa [集数](中括号表示可选)")
    await bot.call_api("set_msg_emoji_like", message_id=event.message_id, emoji_id="282")
    bvid, p_num = match.group(1), match.group(2)
    p_num = int(p_num) - 1 if p_num else 0
    v = video.Video(bvid=bvid, credential=CREDENTIAL)
    try:
        video_info: dict = await v.get_info()
        video_title: str = video_info.get("title", "")
        if pages := video_info.get("pages"):
            p_num = p_num % len(pages)
            p_video = pages[p_num]
            # video_duration = p_video.get('duration', video_duration)
            if p_name := p_video.get("part").strip():
                video_title = p_name
        video_title = delete_boring_characters(video_title)
        audio_name = f"{video_title}.mp3"
        audio_path = plugin_cache_dir / audio_name
        if not audio_path.exists():
            download_url_data = await v.get_download_url(page_index=p_num)
            detecter = VideoDownloadURLDataDetecter(download_url_data)
            streams = detecter.detect_best_streams()
            auio_stream = streams[1]
            if auio_stream is None:
                return await bili_music.finish("没有获取到可用音频流")
            audio_url = auio_stream.url
            await download_file_by_stream(audio_url, file_name=audio_name, ext_headers=HEADERS)
    except Exception:
        await bili_music.send("音频下载失败, 请联系机器人管理员", reply_message=True)
        raise
    await bili_music.send(MessageSegment.record(audio_path))
    if NEED_UPLOAD:
        await bili_music.send(get_file_seg(audio_path))


def extra_bili_info(video_info: dict) -> str:
    """
    格式化视频信息
    """
    # 获取视频统计数据
    video_state = video_info["stat"]

    # 定义需要展示的数据及其显示名称
    stats_mapping = [
        ("点赞", "like"),
        ("硬币", "coin"),
        ("收藏", "favorite"),
        ("分享", "share"),
        ("评论", "reply"),
        ("总播放量", "view"),
        ("弹幕数量", "danmaku"),
    ]

    # 构建结果字符串
    result_parts = []
    for display_name, stat_key in stats_mapping:
        value = video_state[stat_key]
        # 数值超过10000时转换为万为单位
        formatted_value = f"{value / 10000:.1f}万" if value > 10000 else str(value)
        result_parts.append(f"{display_name}: {formatted_value}")

    return " | ".join(result_parts)
