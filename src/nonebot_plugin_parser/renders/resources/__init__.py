import random
from pathlib import Path

RESOURCES_DIR = Path(__file__).parent
"""默认资源目录"""
DEFAULT_FONT_PATH = RESOURCES_DIR / "HYSongYunLangHeiW.ttf"
"""默认字体文件路径"""
DEFAULT_AVATAR_PATH = RESOURCES_DIR / "avatar.png"
"""默认头像文件路径"""
DEFAULT_VIDEO_BUTTON_PATH = RESOURCES_DIR / "play.png"
"""默认视频播放按钮文件路径"""
FAILED_PIC_DIR = RESOURCES_DIR / "failed_pic"
"""下载失败显示的图片文件路径"""


def random_failed_pic() -> Path:
    return FAILED_PIC_DIR / f"{random.randint(1, 9)}.jpg"
