import re
from typing import TypeVar

from nonebot import logger, get_driver, on_command
from nonebot.rule import Rule
from nonebot.params import CommandArg
from nonebot.typing import T_State
from nonebot.matcher import Matcher
from nonebot.adapters import Message
from nonebot.plugin.on import get_matcher_source
from nonebot_plugin_alconna.uniseg import UniMsg

from .rule import SUPER_PRIVATE, Searched, SearchResult, on_keyword_regex
from ..utils import LimitedSizeDict
from ..config import pconfig
from ..helper import UniHelper, UniMessage
from ..parsers import BaseParser, ParseResult, BilibiliParser
from ..renders import get_renderer
from ..download import DOWNLOADER
from ..parsers.data import AudioContent, VideoContent


def _get_enabled_parser_classes() -> list[type[BaseParser]]:
    disabled_platforms = set(pconfig.disabled_platforms)
    all_subclass = BaseParser.get_all_subclass()
    return [_cls for _cls in all_subclass if _cls.platform.name not in disabled_platforms]


# 关键词 -> Parser 映射
KEYWORD_PARSER_MAP: dict[str, BaseParser] = {}
T = TypeVar("T", bound=BaseParser)


def get_parser(keyword: str) -> BaseParser:
    return KEYWORD_PARSER_MAP[keyword]


def get_parser_by_type(parser_type: type[T]) -> T:
    for parser in KEYWORD_PARSER_MAP.values():
        if isinstance(parser, parser_type):
            return parser
    raise ValueError(f"未找到类型为 {parser_type} 的 parser 实例")


@get_driver().on_startup
def register_parser_matcher():
    enabled_classes = _get_enabled_parser_classes()

    enabled_platforms = []
    for _cls in enabled_classes:
        parser = _cls()
        enabled_platforms.append(parser.platform.display_name)
        for keyword, _ in _cls._key_patterns:
            KEYWORD_PARSER_MAP[keyword] = parser
    logger.info(f"启用平台: {', '.join(sorted(enabled_platforms))}")

    patterns = [p for _cls in enabled_classes for p in _cls._key_patterns]
    matcher = on_keyword_regex(*patterns)
    matcher.append_handler(parser_handler)


# 缓存结果
_RESULT_CACHE = LimitedSizeDict[str, ParseResult](max_size=50)
# 消息ID与解析结果的关联缓存，用于多用户场景
_MSG_ID_RESULT_MAP = LimitedSizeDict[str, ParseResult](max_size=100)


def clear_result_cache():
    _RESULT_CACHE.clear()
    _MSG_ID_RESULT_MAP.clear()


@UniHelper.with_reaction
async def parser_handler(
    sr: SearchResult = Searched(),
):
    """统一的解析处理器"""
    # 1. 获取缓存结果
    cache_key = sr.searched.group(0)
    result = _RESULT_CACHE.get(cache_key)

    if result is None:
        # 2. 获取对应平台 parser
        parser = get_parser(sr.keyword)
        result = await parser.parse(sr.keyword, sr.searched)
        logger.debug(f"解析结果: {result}")
    else:
        logger.debug(f"命中缓存: {cache_key}, 结果: {result}")

    # 3. 渲染内容消息并发送，保存消息ID
    renderer = get_renderer(result.platform.name)
    try:
        async for message in renderer.render_messages(result):
            msg_sent = await message.send()
            # 保存消息ID与解析结果的关联
            if msg_sent:
                # 添加详细调试日志，查看msg_sent的类型和属性
                logger.debug(f"消息发送返回对象: type={type(msg_sent)}, repr={repr(msg_sent)}")
                logger.debug(f"msg_sent属性: {dir(msg_sent)}")
                try:
                    # 尝试获取消息ID
                    msg_id = None
                    # 检查是否为Event类型
                    if hasattr(msg_sent, "get_event_name"):
                        from nonebot_plugin_alconna.uniseg import get_message_id
                        try:
                            msg_id = get_message_id(msg_sent)  # type: ignore
                            logger.debug(f"通过get_message_id获取到消息ID: {msg_id}")
                        except TypeError as e:
                            # 如果不是Event类型，跳过
                            logger.debug(f"get_message_id类型错误: {e}")
                    # 尝试直接从对象获取id或message_id属性
                    if hasattr(msg_sent, "id"):
                        msg_id = str(msg_sent.id)  # type: ignore
                        logger.debug(f"通过id属性获取到消息ID: {msg_id}")
                    elif hasattr(msg_sent, "message_id"):
                        msg_id = str(msg_sent.message_id)  # type: ignore
                        logger.debug(f"通过message_id属性获取到消息ID: {msg_id}")
                    elif hasattr(msg_sent, "message_ids"):
                        # 处理可能返回多个消息ID的情况
                        msg_ids = getattr(msg_sent, "message_ids")
                        if msg_ids:
                            msg_id = str(msg_ids[0])  # type: ignore
                            logger.debug(f"通过message_ids属性获取到消息ID: {msg_id}")
                    elif hasattr(msg_sent, "msg_ids"):
                        # 处理Receipt对象的msg_ids属性
                        receipt_msg_ids = getattr(msg_sent, "msg_ids")
                        logger.debug(f"Receipt.msg_ids: {receipt_msg_ids}")
                        if receipt_msg_ids:
                            # 处理msg_ids是列表的情况
                            if isinstance(receipt_msg_ids, list):
                                for msg_id_info in receipt_msg_ids:
                                    if isinstance(msg_id_info, dict) and "message_id" in msg_id_info:
                                        msg_id = str(msg_id_info["message_id"])
                                        logger.debug(f"通过Receipt.msg_ids[0]['message_id']获取到消息ID: {msg_id}")
                                        break
                            # 处理msg_ids是单个消息ID的情况
                            else:
                                msg_id = str(receipt_msg_ids)  # type: ignore
                                logger.debug(f"通过Receipt.msg_ids获取到消息ID: {msg_id}")
                    
                    if msg_id:
                        _MSG_ID_RESULT_MAP[msg_id] = result
                        logger.debug(f"保存消息ID与解析结果的关联: msg_id={msg_id}, url={cache_key}")
                        logger.debug(f"当前_MSG_ID_RESULT_MAP大小: {len(_MSG_ID_RESULT_MAP)}")
                    else:
                        logger.debug("未获取到消息ID")
                except (NotImplementedError, TypeError, AttributeError) as e:
                    # 某些适配器可能不支持获取消息ID，忽略此错误
                    logger.debug(f"获取消息ID失败: {e}")
    except Exception as e:
        # 渲染失败时，尝试直接发送解析结果
        logger.error(f"渲染失败: {e}")
        from ..helper import UniMessage

        await UniMessage(f"解析成功，但渲染失败: {e!s}").send()

    # 4. 缓存解析结果
    _RESULT_CACHE[cache_key] = result


@on_command("bm", priority=3, block=True).handle()
@UniHelper.with_reaction
async def _(message: Message = CommandArg()):
    text = message.extract_plain_text()
    matched = re.search(r"(BV[A-Za-z0-9]{10})(\s\d{1,3})?", text)
    if not matched:
        await UniMessage("请发送正确的 BV 号").finish()

    bvid, page_num = matched.group(1), matched.group(2)
    page_idx = int(page_num) if page_num else 0

    parser = get_parser_by_type(BilibiliParser)

    _, audio_url = await parser.extract_download_urls(bvid=bvid, page_index=page_idx)
    if not audio_url:
        await UniMessage("未找到可下载的音频").finish()

    audio_path = await DOWNLOADER.download_audio(
        audio_url, audio_name=f"{bvid}-{page_idx}.mp3", ext_headers=parser.headers
    )
    await UniMessage(UniHelper.record_seg(audio_path)).send()

    if pconfig.need_upload:
        await UniMessage(UniHelper.file_seg(audio_path)).send()


from ..download import YTDLP_DOWNLOADER

if YTDLP_DOWNLOADER is not None:
    from ..parsers import YouTubeParser

    @on_command("ym", priority=3, block=True).handle()
    @UniHelper.with_reaction
    async def _(message: Message = CommandArg()):
        text = message.extract_plain_text()
        parser = get_parser_by_type(YouTubeParser)
        _, matched = parser.search_url(text)
        if not matched:
            await UniMessage("请发送正确的油管链接").finish()

        url = matched.group(0)

        audio_path = await YTDLP_DOWNLOADER.download_audio(url)
        await UniMessage(UniHelper.record_seg(audio_path)).send()

        if pconfig.need_upload:
            await UniMessage(UniHelper.file_seg(audio_path)).send()


@on_command("blogin", block=True, permission=SUPER_PRIVATE).handle()
async def _():
    parser = get_parser_by_type(BilibiliParser)
    qrcode = await parser.login_with_qrcode()
    await UniMessage(UniHelper.img_seg(raw=qrcode)).send()
    async for msg in parser.check_qr_state():
        await UniMessage(msg).send()


# 监听特定表情，触发延迟发送的媒体内容
class EmojiTriggerRule:
    """表情触发规则类"""

    async def __call__(self, message: UniMsg, state: T_State) -> bool:
        """检查消息是否是触发表情"""
        text = message.extract_plain_text().strip()
        return text == pconfig.delay_send_emoji


def emoji_trigger_rule() -> Rule:
    """创建表情触发规则"""
    return Rule(EmojiTriggerRule())


# 创建表情触发的消息处理器
delay_send_matcher = Matcher.new(
    "message",
    emoji_trigger_rule(),
    priority=5,
    block=True,
    source=get_matcher_source(1),
)


@delay_send_matcher.handle()
async def delay_media_trigger_handler():
    from ..helper import UniHelper, UniMessage

    # 获取最新的解析结果
    if not _RESULT_CACHE:
        return

    # 获取最近的解析结果
    latest_url = next(reversed(_RESULT_CACHE.keys()))
    result = _RESULT_CACHE[latest_url]

    # 发送延迟的媒体内容
    for media_type, path in result.media_contents:
        if media_type == VideoContent:
            await UniMessage(UniHelper.video_seg(path)).send()
        elif media_type == AudioContent:
            await UniMessage(UniHelper.record_seg(path)).send()

    # 清空当前结果的媒体内容
    result.media_contents.clear()


# 监听group_msg_emoji_like事件，处理点赞触发
from nonebot import on_notice
from nonebot_plugin_alconna.uniseg import message_reaction

on_notice_ = on_notice(priority=1, block=False)


@on_notice_.handle()
async def handle_group_msg_emoji_like(event):
    from ..helper import UniHelper, UniMessage

    # 检查是否是group_msg_emoji_like事件
    is_group_emoji_like = False
    emoji_id = ""
    liked_message_id = ""

    # 处理不同形式的事件对象（字典或对象）
    if isinstance(event, dict):
        # 字典形式的事件
        if event.get("notice_type") == "group_msg_emoji_like":
            is_group_emoji_like = True
            emoji_id = event["likes"][0]["emoji_id"]
            liked_message_id = event["message_id"]
    else:
        # 对象形式的事件
        if hasattr(event, "notice_type") and event.notice_type == "group_msg_emoji_like":
            is_group_emoji_like = True
            if hasattr(event, "likes") and event.likes:
                if isinstance(event.likes[0], dict):
                    emoji_id = event.likes[0].get("emoji_id", "")
                else:
                    emoji_id = event.likes[0].emoji_id
            if hasattr(event, "message_id"):
                liked_message_id = event.message_id

    # 检查是否是group_msg_emoji_like事件且表情ID有效
    if not is_group_emoji_like or not emoji_id:
        return

    # 检查表情ID是否在配置列表中
    if emoji_id not in pconfig.delay_send_emoji_ids:
        return

    # 发送"听到需求"的表情（使用用户指定的表情ID 282）
    try:
        # 只有当liked_message_id有效时，才发送表情反馈
        if liked_message_id:
            await message_reaction("282", message_id=str(liked_message_id))
    except Exception as e:
        logger.warning(f"Failed to send resolving reaction: {e}")

    try:
        logger.debug(f"收到表情点赞事件: emoji_id={emoji_id}, message_id={liked_message_id}, event={event}")
        logger.debug(f"当前_MSG_ID_RESULT_MAP: {list(_MSG_ID_RESULT_MAP.keys())}")
        
        # 根据消息ID获取对应的解析结果
        result = _MSG_ID_RESULT_MAP.get(str(liked_message_id))
        if not result:
            # 发送"失败"的表情（使用用户指定的表情ID 10060）
            logger.debug(f"未找到消息ID {liked_message_id} 对应的解析结果")
            try:
                if liked_message_id:
                    await message_reaction("10060", message_id=str(liked_message_id))
            except Exception as e:
                logger.warning(f"Failed to send fail reaction: {e}")
            return

        # 发送延迟的媒体内容
        sent = False
        for media_type, path in result.media_contents:
            if media_type == VideoContent:
                await UniMessage(UniHelper.video_seg(path)).send()
                sent = True
            elif media_type == AudioContent:
                await UniMessage(UniHelper.record_seg(path)).send()
                sent = True

        # 清空当前结果的媒体内容
        result.media_contents.clear()

        # 发送对应的表情
        if sent:
            # 发送"完成"的表情（使用用户指定的表情ID 124）
            try:
                if liked_message_id:
                    await message_reaction("124", message_id=str(liked_message_id))
            except Exception as e:
                logger.warning(f"Failed to send done reaction: {e}")
        else:
            # 没有可发送的媒体内容，发送"失败"的表情（使用用户指定的表情ID 10060）
            try:
                if liked_message_id:
                    await message_reaction("10060", message_id=str(liked_message_id))
            except Exception as e:
                logger.warning(f"Failed to send fail reaction: {e}")
    except Exception as e:
        # 发送"失败"的表情（使用用户指定的表情ID 10060）
        try:
            if liked_message_id:
                await message_reaction("10060", message_id=str(liked_message_id))
        except Exception as reaction_e:
            logger.warning(f"Failed to send fail reaction: {reaction_e}")
        logger.error(f"Failed to send media content: {e}")
