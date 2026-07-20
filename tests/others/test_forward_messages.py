def test_construct_forward_messages_flattens_existing_references():
    from nonebot_plugin_alconna.uniseg import Text, Image, Video, Reference, CustomNode, UniMessage

    from nonebot_plugin_parser.helper import UniHelper

    existing = Reference(
        nodes=[
            CustomNode(uid="1", name="parser", content=UniMessage(Image(url="https://example.com/1.jpg"))),
            CustomNode(uid="1", name="parser", content=UniMessage(Image(url="https://example.com/2.jpg"))),
        ]
    )
    messages = [
        UniMessage(Text("preview")),
        UniMessage(existing),
        UniMessage(Video(url="https://example.com/1.mp4")),
        UniMessage(Video(url="https://example.com/2.mp4")),
    ]

    forward = UniHelper.construct_forward_messages(messages, user_id="1")

    assert len(forward.children) == 5
    node_types = []
    for node in forward.children:
        assert isinstance(node, CustomNode)
        assert isinstance(node.content, UniMessage)
        node_types.append(node.content[0].type)
    assert node_types == ["text", "image", "image", "video", "video"]


async def test_send_rendered_messages_sends_once(monkeypatch):
    from nonebot_plugin_alconna.uniseg import Text, Image, Video, Reference, CustomNode, UniMessage

    from nonebot_plugin_parser.config import pconfig
    from nonebot_plugin_parser.matchers import send_rendered_messages

    class Renderer:
        async def render_messages(self):
            yield UniMessage(Text("preview"))
            yield UniMessage(
                Reference(
                    nodes=[
                        CustomNode(uid="1", name="parser", content=UniMessage(Image(url="https://example.com/1.jpg"))),
                        CustomNode(uid="1", name="parser", content=UniMessage(Image(url="https://example.com/2.jpg"))),
                    ]
                )
            )
            yield UniMessage(Video(url="https://example.com/1.mp4"))
            yield UniMessage(Video(url="https://example.com/2.mp4"))

    sent: list[UniMessage] = []

    async def send(message, *args, **kwargs):
        sent.append(message)

    monkeypatch.setattr(pconfig, "parser_forward_all_messages", True)
    bot_context = type("BotContext", (), {"get": lambda self: type("Bot", (), {"self_id": "1"})()})()
    monkeypatch.setattr("nonebot_plugin_parser.helper.current_bot", bot_context)
    monkeypatch.setattr(UniMessage, "send", send)

    await send_rendered_messages(Renderer())

    assert len(sent) == 1
    assert len(sent[0]) == 1
    assert isinstance(sent[0][0], Reference)
    assert len(sent[0][0].children) == 5


async def test_send_rendered_messages_preserves_original_behavior_when_disabled(monkeypatch):
    from nonebot_plugin_alconna.uniseg import Text, UniMessage

    from nonebot_plugin_parser.config import pconfig
    from nonebot_plugin_parser.matchers import send_rendered_messages

    class Renderer:
        async def render_messages(self):
            yield UniMessage(Text("first"))
            yield UniMessage(Text("second"))

    sent: list[UniMessage] = []

    async def send(message, *args, **kwargs):
        sent.append(message)

    monkeypatch.setattr(pconfig, "parser_forward_all_messages", False)
    monkeypatch.setattr(UniMessage, "send", send)

    await send_rendered_messages(Renderer())

    assert [message.extract_plain_text() for message in sent] == ["first", "second"]


async def test_send_rendered_messages_sends_partial_results_before_reraising(monkeypatch):
    import pytest
    from nonebot_plugin_alconna.uniseg import Text, Reference, UniMessage

    from nonebot_plugin_parser.config import pconfig
    from nonebot_plugin_parser.matchers import send_rendered_messages

    class RenderError(Exception):
        pass

    class Renderer:
        async def render_messages(self):
            yield UniMessage(Text("preview"))
            raise RenderError

    sent: list[UniMessage] = []

    async def send(message, *args, **kwargs):
        sent.append(message)

    monkeypatch.setattr(pconfig, "parser_forward_all_messages", True)
    bot_context = type("BotContext", (), {"get": lambda self: type("Bot", (), {"self_id": "1"})()})()
    monkeypatch.setattr("nonebot_plugin_parser.helper.current_bot", bot_context)
    monkeypatch.setattr(UniMessage, "send", send)

    with pytest.raises(RenderError):
        await send_rendered_messages(Renderer())

    assert len(sent) == 1
    assert isinstance(sent[0][0], Reference)
    assert len(sent[0][0].children) == 1


def test_construct_forward_messages_does_not_limit_nodes():
    from nonebot_plugin_alconna.uniseg import Text, UniMessage

    from nonebot_plugin_parser.helper import UniHelper

    messages = [UniMessage(Text(str(index))) for index in range(128)]

    forward = UniHelper.construct_forward_messages(messages, user_id="1")

    assert len(forward.children) == len(messages)
