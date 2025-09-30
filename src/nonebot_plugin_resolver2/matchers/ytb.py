import re

from nonebot import logger
from nonebot_plugin_alconna.uniseg import UniMessage
from nonebot_plugin_waiter import prompt

from ..config import NEED_UPLOAD, NICKNAME, ytb_cookies_file
from ..download.ytdlp import get_video_info, ytdlp_download_audio, ytdlp_download_video
from ..exception import handle_exception
from ..utils import keep_zh_en_num
from .helper import UniHelper
from .preprocess import KeyPatternMatched, on_keyword_regex

# https://youtu.be/EKkzbbLYPuI?si=K_S9zIp5g7DhigVz
# https://www.youtube.com/watch?v=1LnPnmKALL8&list=RD8AxpdwegNKc&index=2
ytb = on_keyword_regex(
    ("youtube.com", r"https?://(?:www\.)?youtube\.com/[A-Za-z\d\._\?%&\+\-=/#]+"),
    ("youtu.be", r"https?://(?:www\.)?youtu\.be/[A-Za-z\d\._\?%&\+\-=/#]+"),
)


@ytb.handle()
@handle_exception()
async def _(searched: re.Match[str] = KeyPatternMatched()):
    url = searched.group(0)
    try:
        info_dict = await get_video_info(url, ytb_cookies_file)
        title = info_dict.get("title", "未知")
    except Exception:
        logger.exception(f"油管标题获取失败 | {url}")
        await ytb.finish(f"{NICKNAME}解析 | 油管 - 标题获取出错")
    await ytb.send(f"{NICKNAME}解析 | 油管 - {title}")

    user_input = await prompt("您需要下载音频(0)，还是视频(1)", timeout=15)
    user_input = user_input.extract_plain_text().strip() if user_input is not None else "1"

    if user_input == "1":
        video_path = await ytdlp_download_video(url, ytb_cookies_file)
        await UniMessage([UniHelper.video_seg(video_path)]).send()

    else:
        audio_path = await ytdlp_download_audio(url, ytb_cookies_file)
        await UniMessage([UniHelper.record_seg(audio_path)]).send()
        if NEED_UPLOAD:
            file_name = f"{keep_zh_en_num(title)}.flac"
            await UniMessage([UniHelper.file_seg(audio_path, display_name=file_name)]).send()
