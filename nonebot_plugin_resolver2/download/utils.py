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
