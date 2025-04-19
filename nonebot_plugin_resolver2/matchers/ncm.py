from nonebot import on_message

from ..config import NEED_UPLOAD, NICKNAME
from ..download import download_audio, download_img
from ..download.utils import keep_zh_en_num
from ..exception import handle_exception
from ..parsers import NCMParser
from .filter import is_not_in_disabled_groups
from .helper import get_file_seg, get_img_seg, get_record_seg
from .preprocess import ExtractText, Keyword, r_keywords

ncm = on_message(rule=is_not_in_disabled_groups & r_keywords("music.163.com", "163cn.tv"))

parser = NCMParser()


@ncm.handle()
@handle_exception(ncm)
async def _(text: str = ExtractText(), keyword: str = Keyword()):
    result = await parser.parse_ncm(text)
    detail = f"{NICKNAME}解析 | 网易云 - {result.title}-{result.author}"
    img_seg = get_img_seg(await download_img(result.cover_url))
    await ncm.send(detail + img_seg)
    # 下载音频文件后会返回一个下载路径
    audio_path = await download_audio(result.audio_url)
    # 发送语音
    await ncm.send(get_record_seg(audio_path))
    # 上传群文件
    if NEED_UPLOAD:
        file_name = keep_zh_en_num(f"{result.title}-{result.author}")
        file_name = f"{file_name}.flac"
        await ncm.send(get_file_seg(audio_path, file_name))
