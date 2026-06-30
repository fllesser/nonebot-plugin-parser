import json
from pathlib import Path
from dataclasses import asdict, dataclass

from nonebot import logger, on_command
from nonebot.rule import to_me
from nonebot.matcher import Matcher
from nonebot.permission import SUPERUSER
from nonebot_plugin_uninfo import ADMIN, Session, UniSession

from ..config import pconfig


@dataclass
class GroupConfig:
    """群组配置"""

    enabled: bool = True


_GROUP_CONFIG_PATH: Path = pconfig.data_dir / "group_config.json"
_DISABLED_GROUPS_PATH: Path = pconfig.data_dir / "disabled_groups.json"


def load_or_initialize_group_config() -> dict[str, GroupConfig]:
    """加载或初始化群组配置

    检测并迁移旧版的禁用群组配置（disabled_groups.json），
    迁移后删除旧版配置文件。
    """
    # 检测旧版禁用群组配置并迁移
    if _DISABLED_GROUPS_PATH.exists():
        old_disabled: list[str] = json.loads(_DISABLED_GROUPS_PATH.read_text())
        logger.info(f"检测到旧版禁用群组配置，共 {len(old_disabled)} 个群组，正在迁移...")
        result: dict[str, GroupConfig] = {}
        for group_key in old_disabled:
            result[group_key] = GroupConfig(enabled=False)
        # 保存为新版配置
        _save_group_config_to_file(result)
        # 删除旧版配置文件
        _DISABLED_GROUPS_PATH.unlink()
        logger.info("旧版禁用群组配置迁移完成，已删除旧文件")
        return result

    if not _GROUP_CONFIG_PATH.exists():
        _GROUP_CONFIG_PATH.write_text(json.dumps({}))
        return {}

    raw: dict = json.loads(_GROUP_CONFIG_PATH.read_text())
    return {k: GroupConfig(**v) if isinstance(v, dict) else GroupConfig(enabled=v) for k, v in raw.items()}


def _save_group_config_to_file(group_config: dict[str, GroupConfig]):
    """将群组配置写入文件"""
    _GROUP_CONFIG_PATH.write_text(
        json.dumps(
            {k: asdict(v) for k, v in group_config.items()},
            indent=4,
            ensure_ascii=False,
        )
    )


def save_group_config(group_config: dict[str, GroupConfig]):
    """保存群组配置"""
    _save_group_config_to_file(group_config)


# 群组配置，第一次先进行初始化
_GROUP_CONFIG: dict[str, GroupConfig] = load_or_initialize_group_config()


def get_group_key(session: Session) -> str:
    """获取群组的唯一标识符

    由平台名称和会话场景 ID 组成，例如 `QQClient_123456789`。
    """
    return f"{session.scope}_{session.scene_path}"


def is_enabled(session: Session = UniSession()) -> bool:
    """判断当前会话是否启用解析"""
    if session.scene.is_private:
        return True

    group_key = get_group_key(session)
    if group_key in _GROUP_CONFIG:
        return _GROUP_CONFIG[group_key].enabled
    return pconfig.parser_enable_by_default


@on_command("开启解析", rule=to_me(), permission=SUPERUSER | ADMIN(), block=True).handle()
async def _enable_parser(matcher: Matcher, session: Session = UniSession()):
    """开启解析"""
    group_key = get_group_key(session)
    if group_key in _GROUP_CONFIG and _GROUP_CONFIG[group_key].enabled:
        await matcher.finish("解析已开启，无需重复开启")
    _GROUP_CONFIG[group_key] = GroupConfig(enabled=True)
    save_group_config(_GROUP_CONFIG)
    await matcher.finish("解析已开启")


@on_command("关闭解析", rule=to_me(), permission=SUPERUSER | ADMIN(), block=True).handle()
async def _disable_parser(matcher: Matcher, session: Session = UniSession()):
    """关闭解析"""
    group_key = get_group_key(session)
    if group_key in _GROUP_CONFIG and not _GROUP_CONFIG[group_key].enabled:
        await matcher.finish("解析已关闭，无需重复关闭")
    _GROUP_CONFIG[group_key] = GroupConfig(enabled=False)
    save_group_config(_GROUP_CONFIG)
    await matcher.finish("解析已关闭")
