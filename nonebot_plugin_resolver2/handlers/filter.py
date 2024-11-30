
from functools import wraps
from nonebot.permission import SUPERUSER

from nonebot.rule import to_me
from nonebot import logger, on_command
from nonebot.permission import SUPERUSER
from nonebot.adapters.onebot.v11 import GROUP_ADMIN, GROUP_OWNER, Bot, Event, Message

from .utils import get_id_both

from ..core.common import load_or_initialize_list, load_sub_user, save_sub_user


# 内存中关闭解析的名单，第一次先进行初始化
resolve_shutdown_list_in_memory: list = load_or_initialize_list()

enable_resolve = on_command('开启解析', rule=to_me(), permission=GROUP_ADMIN | GROUP_OWNER | SUPERUSER)
disable_resolve = on_command('关闭解析', rule=to_me(), permission=GROUP_ADMIN | GROUP_OWNER | SUPERUSER)
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
        send_id = get_id_both(event)

        if send_id not in resolve_shutdown_list_in_memory:
            return await func(*args, **kwargs)
        else:
            logger.info(f"发送者/群 {send_id} 已关闭解析，不再执行")
            return None

    return wrapper


@enable_resolve.handle()
async def enable(bot: Bot, event: Event):
    """
    开启解析
    :param bot:
    :param event:
    :return:
    """
    send_id = get_id_both(event)
    if send_id in resolve_shutdown_list_in_memory:
        resolve_shutdown_list_in_memory.remove(send_id)
        save_sub_user(resolve_shutdown_list_in_memory)
        logger.info(resolve_shutdown_list_in_memory)
        await enable_resolve.finish('解析已开启')
    else:
        await enable_resolve.finish('解析已开启，无需重复开启')


@disable_resolve.handle()
async def disable(bot: Bot, event: Event):
    """
    关闭解析
    :param bot:
    :param event:
    :return:
    """
    send_id = get_id_both(event)
    if send_id not in resolve_shutdown_list_in_memory:
        resolve_shutdown_list_in_memory.append(send_id)
        save_sub_user(resolve_shutdown_list_in_memory)
        logger.info(resolve_shutdown_list_in_memory)
        await disable_resolve.finish('解析已关闭')
    else:
        await disable_resolve.finish('解析已关闭，无需重复关闭')


@check_resolve.handle()
async def check_disable(bot: Bot, event: Event):
    """
    查看关闭解析
    :param bot:
    :param event:
    :return:
    """
    memory_disable_list = [str(item) + "--" + (await bot.get_group_info(group_id=item))['group_name'] for item in
                           resolve_shutdown_list_in_memory]
    memory_disable_list = "1. 在【内存】中的名单有：\n" + '\n'.join(memory_disable_list)
    persistence_disable_list = [str(item) + "--" + (await bot.get_group_info(group_id=item))['group_name'] for item in
                                list(load_sub_user())]
    persistence_disable_list = "2. 在【持久层】中的名单有：\n" + '\n'.join(persistence_disable_list)

    await check_resolve.send("已经发送到私信了~")
    await bot.send_private_msg(user_id=event.user_id, message=Message(
        "[nonebot-plugin-resolver2 关闭名单如下：]" + "\n\n" + memory_disable_list + '\n\n' + persistence_disable_list + "\n\n" + "🌟 温馨提示：如果想关闭解析需要艾特我然后输入: 关闭解析"))