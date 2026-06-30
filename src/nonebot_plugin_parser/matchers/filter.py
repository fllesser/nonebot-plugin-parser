import json
from pathlib import Path

from nonebot import on_command
from nonebot.rule import to_me
from nonebot.matcher import Matcher
from nonebot.permission import SUPERUSER
from nonebot_plugin_uninfo import ADMIN, Session, UniSession

from ..config import pconfig

_DISABLED_GROUPS_PATH: Path = pconfig.data_dir / "disabled_groups.json"
_GROUP_SET_PATH: Path = pconfig.data_dir / "group_set.json"


def _load_or_initialize_set() -> set[str]:
    """加载群配置"""
    # 判断是否存在
    if not _GROUP_SET_PATH.exists():
        if _DISABLED_GROUPS_PATH.exists():
            # 迁移旧的关闭解析名单
            _DISABLED_GROUPS_PATH.rename(_GROUP_SET_PATH)
        else:
            _GROUP_SET_PATH.write_text(json.dumps({}))

    return set(json.loads(_GROUP_SET_PATH.read_text()))


_GROUP_SET: set[str] = _load_or_initialize_set()


def _save_group_set():
    _GROUP_SET_PATH.write_text(json.dumps(list(_GROUP_SET)))


def _add_group(group_key: str):
    _GROUP_SET.add(group_key)
    _save_group_set()


def _remove_group(group_key: str):
    _GROUP_SET.discard(group_key)
    _save_group_set()


def _get_group_key(session: Session) -> str:
    """获取群组的唯一标识符 由平台名称和会话场景 ID 组成，例如 `QQClient_123456789`"""
    return f"{session.scope}_{session.scene_path}"


def is_enabled(session: Session = UniSession()) -> bool:
    """判断当前会话是否在关闭解析的名单中"""
    if session.scene.is_private:
        return True

    group_key = _get_group_key(session)
    if pconfig.group_blacklist_enabled:
        return group_key not in _GROUP_SET
    else:
        return group_key in _GROUP_SET


@on_command("开启解析", rule=to_me(), permission=SUPERUSER | ADMIN(), block=True).handle()
async def _(matcher: Matcher, session: Session = UniSession()):
    """开启解析"""
    group_key = _get_group_key(session)
    if pconfig.group_blacklist_enabled:
        _remove_group(group_key)
    else:
        _add_group(group_key)
    await matcher.finish("解析已开启")


@on_command("关闭解析", rule=to_me(), permission=SUPERUSER | ADMIN(), block=True).handle()
async def _(matcher: Matcher, session: Session = UniSession()):
    """关闭解析"""
    group_key = _get_group_key(session)
    if pconfig.group_blacklist_enabled:
        _add_group(group_key)
    else:
        _remove_group(group_key)
    await matcher.finish("解析已关闭")
