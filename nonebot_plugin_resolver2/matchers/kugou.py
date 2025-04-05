import re

from nonebot import logger, on_message
from nonebot.adapters.onebot.v11 import MessageSegment

from ..config import NEED_UPLOAD, NICKNAME
from ..download import download_audio, download_img
from ..download.utils import keep_zh_en_num
from ..parsers.kugou import KuGou
from .filter import is_not_in_disabled_groups
from .helper import get_file_seg, get_img_seg
from .preprocess import ExtractText, r_keywords

kugou = on_message(rule=is_not_in_disabled_groups & r_keywords("kugou.com"))
kugou_parser = KuGou()


@kugou.handle()
async def _(text: str = ExtractText()):
    share_prefix = f"{NICKNAME}解析 | 酷狗音乐 - "
    # https://t1.kugou.com/song.html?id=1hfw6baEmV3
    pattern = r"https?://.*kugou\.com.*id=[a-zA-Z0-9]+"
    # pattern = r"https?://.*?kugou\.com.*?(?=\s|$|\n)"
    if match := re.search(pattern, text):
        url = match.group(0)
    else:
        logger.info(f"{share_prefix}无效链接，忽略 - {text}")
        return
    try:
        video_info = await kugou_parser.parse_share_url(url)
    except Exception as e:
        logger.error(f"链接 {url} 资源直链获取失败- {e}", exc_info=True)
        await kugou.finish("资源直链获取失败, 请联系机器人管理员", reply_message=True)

    title_author_name = f"{video_info.title} - {video_info.author.name}"

    await kugou.send(f"{share_prefix}{title_author_name}" + get_img_seg(await download_img(video_info.cover_url)))

    audio_path = await download_audio(url=video_info.music_url)
    # 发送语音
    await kugou.send(MessageSegment.record(audio_path))
    # 发送群文件
    if NEED_UPLOAD:
        filename = f"{keep_zh_en_num(title_author_name)}.flac"
        await kugou.finish(get_file_seg(audio_path, filename))
