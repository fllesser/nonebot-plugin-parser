import json
from pathlib import Path

from nonebot import on_command
from nonebot.rule import to_me
from nonebot.matcher import Matcher
from nonebot.permission import SUPERUSER
from nonebot_plugin_uninfo import ADMIN, Session, UniSession

from ..config import pconfig

_DISABLED_GROUPS_PATH: Path = pconfig.data_dir / "disabled_groups.json"


def load_or_initialize_set() -> set[str]:
    """加载或初始化关闭解析的名单"""
    # 判断是否存在
    if not _DISABLED_GROUPS_PATH.exists():
        _DISABLED_GROUPS_PATH.write_text(json.dumps([]))
    return set(json.loads(_DISABLED_GROUPS_PATH.read_text()))


def save_disabled_groups():
    """保存关闭解析的名单"""
    _DISABLED_GROUPS_PATH.write_text(json.dumps(list(_DISABLED_GROUPS_SET)))


# 内存中关闭解析的名单，第一次先进行初始化
_DISABLED_GROUPS_SET: set[str] = load_or_initialize_set()


def get_group_key(session: Session) -> str:
    """获取群组的唯一标识符

    由平台名称和会话场景 ID 组成，例如 `QQClient_123456789`。
    """
    return f"{session.scope}_{session.scene_path}"


# Rule
def is_enabled(session: Session = UniSession()) -> bool:
    """判断当前会话是否在关闭解析的名单中"""
    if session.scene.is_private:
        return True

    group_key = get_group_key(session)
    if group_key in _DISABLED_GROUPS_SET:
        return False
    return True


@on_command("开启解析", rule=to_me(), permission=SUPERUSER | ADMIN(), block=True).handle()
async def _(matcher: Matcher, session: Session = UniSession()):
    """开启解析"""
    group_key = get_group_key(session)
    if group_key in _DISABLED_GROUPS_SET:
        _DISABLED_GROUPS_SET.remove(group_key)
        save_disabled_groups()
        await matcher.finish("解析已开启")
    else:
        await matcher.finish("解析已开启，无需重复开启")


@on_command("关闭解析", rule=to_me(), permission=SUPERUSER | ADMIN(), block=True).handle()
async def _(matcher: Matcher, session: Session = UniSession()):
    """关闭解析"""
    group_key = get_group_key(session)
    if group_key not in _DISABLED_GROUPS_SET:
        _DISABLED_GROUPS_SET.add(group_key)
        save_disabled_groups()
        await matcher.finish("解析已关闭")
    else:
        await matcher.finish("解析已关闭，无需重复关闭")
