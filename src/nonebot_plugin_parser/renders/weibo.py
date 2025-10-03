from typing_extensions import override

from nonebot_plugin_htmlkit import template_to_pic

from .base import BaseRenderer, ParseResult, UniHelper, UniMessage


class Renderer(BaseRenderer):
    @override
    async def render_messages(self, result: ParseResult):
        # 生成图片消息
        image_raw = await template_to_pic(
            self.templates_dir.as_posix(),
            "weibo.html.jinja",
            templates={"result": result},
        )
        # 组合文本消息
        texts = [result.header]
        if result.repost and result.repost.url:
            texts.append(f"源微博详情: {result.repost.url}")
        if result.url:
            texts.append(f"微博详情: {result.url}" if result.url else "")

        yield UniMessage("\n".join(texts) + UniHelper.img_seg(raw=image_raw))

        # 将其他内容通过转发消息发送
        separate_segs, forwardable_segs = await result.convert_segs()
        # 处理可以合并转发的消息段
        if forwardable_segs:
            # 根据 NEED_FORWARD 和消息段数量决定是否使用转发消息
            if self.need_forward or len(forwardable_segs) > 2:
                # 使用转发消息
                forward_msg = UniHelper.construct_forward_message(forwardable_segs)
                yield UniMessage([forward_msg])
            else:
                forwardable_segs[:-1] = [seg + "\n" for seg in forwardable_segs[:-1]]
                # 单条消息
                yield UniMessage(*forwardable_segs)
        # 处理必须单独发送的消息段
        if separate_segs:
            for seg in separate_segs:
                yield UniMessage(seg)
