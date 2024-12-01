
from functools import wraps

from nonebot.rule import to_me
from nonebot import logger, on_command
from nonebot.permission import SUPERUSER
from nonebot.adapters.onebot.v11 import GROUP_ADMIN, GROUP_OWNER, Bot, Event, Message
from nonebot.adapters.onebot.v11.event import PrivateMessageEvent, MessageEvent, GroupMessageEvent

from ..core.common import load_or_initialize_list, save


# 内存中关闭解析的名单，第一次先进行初始化
disable_group_list: list = load_or_initialize_list()

enable_resolve = on_command('开启解析', rule=to_me(), permission=GROUP_ADMIN | GROUP_OWNER | SUPERUSER)
disable_resolve = on_command('关闭解析', rule=to_me(), permission=GROUP_ADMIN | GROUP_OWNER | SUPERUSER)
enable_all_resolve = on_command('开启所有解析', permission=SUPERUSER)
disable_all_resolve = on_command('关闭所有解析', permission=SUPERUSER)
check_resolve = on_command('查看关闭解析', permission=SUPERUSER)

def resolve_filter(func):
    """
    解析控制装饰器
    :param func:
    :return:
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        # 假设 `event` 是通过被装饰函数的参数传入的
        event = kwargs.get('event') or args[1]  # 根据位置参数或者关键字参数获取 event
        if not isinstance(event, GroupMessageEvent): return # 只过滤群聊
        if event.group_id not in disable_group_list:
            return await func(*args, **kwargs)
        else:
            logger.info(f"群 [{event.group_id}] 已关闭解析，不再执行")
            return None

    return wrapper

@enable_all_resolve.handle()
async def _(bot: Bot, event: PrivateMessageEvent):
    """
    开启所有解析
    
    """
    disable_group_list.clear()
    save(disable_group_list)
    await enable_all_resolve.finish('所有解析已开启')
    

@disable_all_resolve.handle() 
async def _(bot: Bot, event: PrivateMessageEvent):
    """
    关闭所有解析
    
    """
    gid_list: list[int] = [g["group_id"] for g in await bot.get_group_list(no_cache=True)]
    disable_group_list.extend(gid_list)
    disable_group_list = list(set(disable_group_list))  # 去重
    save(disable_group_list)
    await disable_all_resolve.finish('所有解析已关闭')


@enable_resolve.handle()
async def _(bot: Bot, event: GroupMessageEvent):
    """
    开启解析
    :param bot:
    :param event:
    :return:
    """
    gid = event.group_id
    if gid in disable_group_list:
        disable_group_list.remove(gid)
        save(disable_group_list)
        await enable_resolve.finish('解析已开启')
    else:
        await enable_resolve.finish('解析已开启，无需重复开启')


@disable_resolve.handle()
async def _(bot: Bot, event: GroupMessageEvent):
    """
    关闭解析
    :param bot:
    :param event:
    :return:
    """
    gid = event.group_id
    if gid not in disable_group_list:
        disable_group_list.append(gid)
        save(disable_group_list)
        await disable_resolve.finish('解析已关闭')
    else:
        await disable_resolve.finish('解析已关闭，无需重复关闭')


@check_resolve.handle()
async def _(bot: Bot, event: MessageEvent):
    """
    查看关闭解析
    :param bot:
    :param event:
    :return:
    """
    disable_groups = [str(item) + "--" + (await bot.get_group_info(group_id=item))['group_name'] for item in disable_group_list]
    disable_groups = '\n'.join(disable_groups)
    if isinstance(event, GroupMessageEvent):
        await check_resolve.send("已经发送到私信了~")
    message = f"""
        解析关闭的群聊如下：
            {disable_groups}
        🌟 温馨提示：如果想开关解析需要在群聊@我然后输入[开启/关闭解析], 另外还可以私信我发送[开启/关闭全部解析]
    """
    await bot.send_private_msg(user_id=event.user_id, message=message)


