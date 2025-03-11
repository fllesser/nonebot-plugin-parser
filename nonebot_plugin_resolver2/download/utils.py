import asyncio
from pathlib import Path
import re

from nonebot.log import logger


def delete_boring_characters(sentence: str) -> str:
    """
    去除标题的特殊字符
    :param sentence:
    :return:
    """
    return re.sub(
        r'[’!"∀〃\$%&\'\(\)\*\+,\./:;<=>\?@，。?★、…【】《》？“”‘’！\[\\\]\^_`\{\|\}~～]+',
        "",
        sentence,
    )


# 安全删除文件
async def safe_unlink(path: Path):
    try:
        await asyncio.to_thread(path.unlink, missing_ok=True)
    except Exception as e:
        logger.error(f"删除 {path} 失败: {e}")


async def exec_ffmpeg_cmd(cmd: list[str]) -> None:
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
