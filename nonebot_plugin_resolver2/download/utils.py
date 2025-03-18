import asyncio
import hashlib
from pathlib import Path
import re
from urllib.parse import urlparse

from nonebot.log import logger


def delete_boring_characters(sentence: str) -> str:
    """
    去除标题的特殊字符
    """
    return re.sub(
        r'[’!"∀〃\$%&\'\(\)\*\+,\./:;<=>\?@，。?★/、…【】《》？“”‘’！\[\\\]\^_`\{\|\}~～]+',
        "",
        sentence,
    )


def keep_zh_en_num(text: str) -> str:
    """
    保留字符串中的中英文和数字
    """
    # 先把空格替换为下划线
    text = text.replace(" ", "_")
    return re.sub(r"[^\u4e00-\u9fa5a-zA-Z0-9\-_]", "", text)


async def safe_unlink(path: Path):
    """
    安全删除文件
    """
    try:
        await asyncio.to_thread(path.unlink, missing_ok=True)
    except Exception as e:
        logger.error(f"删除 {path} 失败: {e}")


async def exec_ffmpeg_cmd(cmd: list[str]) -> None:
    """
    执行 ffmpeg 命令
    """
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        _, stderr = await process.communicate()
        return_code = process.returncode
    except FileNotFoundError:
        raise RuntimeError("ffmpeg 未安装或无法找到可执行文件")

    if return_code != 0:
        error_msg = stderr.decode().strip()
        raise RuntimeError(f"ffmpeg 执行失败: {error_msg}")


def generate_file_name(url: str, default_suffix: str = "") -> str:
    """
    根据 url 生成文件名
    """
    # 根据 url 获取文件后缀
    path = Path(urlparse(url).path)
    suffix = path.suffix if path.suffix else default_suffix
    # 获取 url 的 md5 值
    url_hash = hashlib.md5(url.encode()).hexdigest()[:16]
    file_name = f"{url_hash}{suffix}"
    return file_name
