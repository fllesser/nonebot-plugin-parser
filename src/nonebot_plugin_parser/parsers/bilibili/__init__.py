import json
import asyncio
from re import Match
from typing import ClassVar
from collections.abc import AsyncGenerator

from msgspec import convert
from nonebot import logger
from bilibili_api import HEADERS, Credential, select_client, request_settings
from bilibili_api.opus import Opus
from bilibili_api.video import Video
from bilibili_api.login_v2 import QrCodeLogin, QrCodeLoginEvents

from ..base import (
    DOWNLOADER,
    BaseParser,
    PlatformEnum,
    ParseException,
    DownloadException,
    DurationLimitException,
    handle,
    pconfig,
)
from ..data import Platform, ImageContent, MediaContent
from ..cookie import ck2dict

# 选择客户端
select_client("curl_cffi")
# 模拟浏览器，第二参数数值参考 curl_cffi 文档
# https://curl-cffi.readthedocs.io/en/latest/impersonate.html
request_settings.set("impersonate", "chrome131")


class BilibiliParser(BaseParser):
    # 平台信息
    platform: ClassVar[Platform] = Platform(name=PlatformEnum.BILIBILI, display_name="哔哩哔哩")

    def __init__(self):
        self.headers = HEADERS.copy()
        self._credential: Credential | None = None
        self._cookies_file = pconfig.config_dir / "bilibili_cookies.json"

    # --- 辅助方法：格式化数字 ---
    def _format_stat(self, num: int | None) -> str:
        """将数字格式化为 1.2万 的形式"""
        if num is None:
            return "0"
        if num >= 10000:
            return f"{num / 10000:.1f}万"
        return str(num)

    @handle("b23.tv", r"b23\.tv/[A-Za-z\d\._?%&+\-=/#]+")
    @handle("bili2233", r"bili2233\.cn/[A-Za-z\d\._?%&+\-=/#]+")
    async def _parse_short_link(self, searched: Match[str]):
        """解析短链"""
        url = f"https://{searched.group(0)}"
        return await self.parse_with_redirect(url)

    @handle("BV", r"^(?P<bvid>BV[0-9a-zA-Z]{10})(?:\s)?(?P<page_num>\d{1,3})?$")
    @handle("/BV", r"bilibili\.com(?:/video)?/(?P<bvid>BV[0-9a-zA-Z]{10})(?:\?p=(?P<page_num>\d{1,3}))?")
    async def _parse_bv(self, searched: Match[str]):
        """解析视频信息"""
        bvid = str(searched.group("bvid"))
        page_num = int(searched.group("page_num") or 1)

        return await self.parse_video(bvid=bvid, page_num=page_num)

    @handle("av", r"^av(?P<avid>\d{6,})(?:\s)?(?P<page_num>\d{1,3})?$")
    @handle("/av", r"bilibili\.com(?:/video)?/av(?P<avid>\d{6,})(?:\?p=(?P<page_num>\d{1,3}))?")
    async def _parse_av(self, searched: Match[str]):
        """解析视频信息"""
        avid = int(searched.group("avid"))
        page_num = int(searched.group("page_num") or 1)

        return await self.parse_video(avid=avid, page_num=page_num)

    @handle("/dynamic/", r"bilibili\.com/dynamic/(?P<dynamic_id>\d+)")
    @handle("t.bili", r"t\.bilibili\.com/(?P<dynamic_id>\d+)")
    async def _parse_dynamic(self, searched: Match[str]):
        """解析动态信息"""
        dynamic_id = int(searched.group("dynamic_id"))
        return await self.parse_dynamic(dynamic_id)

    @handle("live.bili", r"live\.bilibili\.com/(?P<room_id>\d+)")
    async def _parse_live(self, searched: Match[str]):
        """解析直播信息"""
        room_id = int(searched.group("room_id"))
        return await self.parse_live(room_id)

    @handle("/favlist", r"favlist\?fid=(?P<fav_id>\d+)")
    async def _parse_favlist(self, searched: Match[str]):
        """解析收藏夹信息"""
        fav_id = int(searched.group("fav_id"))
        return await self.parse_favlist(fav_id)

    @handle("/read/", r"bilibili\.com/read/cv(?P<read_id>\d+)")
    async def _parse_read(self, searched: Match[str]):
        """解析专栏信息"""
        # 注意：这里改回了调用 parse_read 而不是 parse_read_with_opus
        # 以保留你自定义的 stats 提取逻辑
        read_id = int(searched.group("read_id"))
        return await self.parse_read(read_id)

    @handle("/opus/", r"bilibili\.com/opus/(?P<opus_id>\d+)")
    async def _parse_opus(self, searched: Match[str]):
        """解析图文动态信息"""
        opus_id = int(searched.group("opus_id"))
        return await self.parse_opus(opus_id)

    async def parse_video(
        self,
        *,
        bvid: str | None = None,
        avid: int | None = None,
        page_num: int = 1,
    ):
        """解析视频信息"""
        from .video import VideoInfo, AIConclusion

        video = await self._get_video(bvid=bvid, avid=avid)
        info_data = await video.get_info()
        video_info = convert(info_data, VideoInfo)

        # 1. 提取统计数据
        stats = {}
        try:
            if video_info.stat:
                stats = {
                    "play": self._format_stat(video_info.stat.view),
                    "danmaku": self._format_stat(video_info.stat.danmaku),
                    "like": self._format_stat(video_info.stat.like),
                    "coin": self._format_stat(video_info.stat.coin),
                    "favorite": self._format_stat(video_info.stat.favorite),
                    "share": self._format_stat(video_info.stat.share),
                    "reply": self._format_stat(video_info.stat.reply),
                }
                logger.debug(f"[BiliParser] 视频统计数据: {stats}")
        except Exception as e:
            logger.warning(f"[BiliParser] 统计数据提取异常: {e}")

        # 获取简介
        text = f"简介: {video_info.desc}" if video_info.desc else None

        # 使用位置参数调用 create_author
        author = self.create_author(video_info.owner.name, video_info.owner.face)

        # 分P信息
        page_info = video_info.extract_info_with_page(page_num)

        # AI 总结
        ai_summary = None
        if self._credential:
            try:
                cid = await video.get_cid(page_info.index)
                try:
                    ai_res = await video.get_ai_conclusion(cid)
                    ai_conclusion = convert(ai_res, AIConclusion)
                    ai_summary = ai_conclusion.summary
                except Exception:
                    ai_summary = None
            except Exception as e:
                logger.warning(f"[BiliParser] AI总结获取失败: {e}")
        else:
            ai_summary = "哔哩哔哩 cookie 未配置或失效, 无法使用 AI 总结"

        url = f"https://bilibili.com/{video_info.bvid}"
        url += f"?p={page_info.index + 1}" if page_info.index > 0 else ""

        # 视频下载 task
        async def download_video():
            output_path = pconfig.cache_dir / f"{video_info.bvid}-{page_num}.mp4"
            if output_path.exists():
                return output_path
            v_url, a_url = await self.extract_download_urls(video=video, page_index=page_info.index)
            if page_info.duration > pconfig.duration_maximum:
                raise DurationLimitException
            if a_url is not None:
                return await DOWNLOADER.download_av_and_merge(
                    v_url, a_url, output_path=output_path, ext_headers=self.headers
                )
            else:
                return await DOWNLOADER.streamd(v_url, file_name=output_path.name, ext_headers=self.headers)

        video_task = asyncio.create_task(download_video())
        video_content = self.create_video_content(
            video_task,
            page_info.cover,
            page_info.duration,
        )

        # 构造 extra_data
        extra_data = {
            "info": ai_summary,
            "stats": stats,
            "type": "video",
            "type_tag": "视频",
            "type_icon": "fa-circle-play",
            "author_id": str(video_info.owner.mid),
            "content_id": video_info.bvid,
        }

        # 创建结果
        res = self.result(
            url=url,
            title=page_info.title,
            timestamp=page_info.timestamp,
            text=text,
            author=author,
            contents=[video_content],
        )

        # 注入 extra
        res.extra = extra_data
        logger.debug(f"Video extra data: {extra_data}")
        return res

    async def parse_dynamic(self, dynamic_id: int):
        """解析动态信息"""
        from bilibili_api.dynamic import Dynamic

        from .dynamic import DynamicData

        dynamic = Dynamic(dynamic_id, await self.credential)
        dynamic_data = convert(await dynamic.get_info(), DynamicData)
        logger.debug(f"dynamic_data: {dynamic_data}")
        dynamic_info = dynamic_data.item
        logger.debug(f"dynamic_info: {dynamic_info}")

        author = self.create_author(dynamic_info.name, dynamic_info.avatar)

        # 提取当前动态的统计数据
        stats = {}
        try:
            if dynamic_info.modules.module_stat:
                m_stat = dynamic_info.modules.module_stat
                stats = {
                    "like": self._format_stat(m_stat.get("like", {}).get("count", 0)),
                    "reply": self._format_stat(m_stat.get("comment", {}).get("count", 0)),
                    "share": self._format_stat(m_stat.get("forward", {}).get("count", 0)),
                }
        except Exception:
            pass

        # 下载当前动态的图片
        contents: list[MediaContent] = []
        for image_url in dynamic_info.image_urls:
            img_task = DOWNLOADER.download_img(image_url, ext_headers=self.headers)
            contents.append(ImageContent(img_task))

        # --- 基础 extra 数据 ---
        extra_data = {
            "stats": stats,
            "type": "dynamic",
            "type_tag": "动态",
            "type_icon": "fa-quote-left",
            "author_id": str(dynamic_info.modules.module_author.mid),
            "content_id": str(dynamic_id),
        }

        # --- 新增：处理转发内容 (叠加到 extra) ---
        if dynamic_info.type == "DYNAMIC_TYPE_FORWARD" and dynamic_info.orig:
            orig_item = dynamic_info.orig

            if orig_item.visible:
                # 尝试获取源内容的类型标签
                orig_type_tag = "动态"
                major_info = orig_item.modules.major_info
                if major_info:
                    major_type = major_info.get("type")
                    if major_type == "MAJOR_TYPE_ARCHIVE":
                        orig_type_tag = "视频"
                    elif major_type == "MAJOR_TYPE_OPUS":
                        orig_type_tag = "专栏"

                # 获取封面图：优先取视频/专栏封面，没有则取第一张配图
                orig_cover = orig_item.cover_url
                if not orig_cover and orig_item.image_urls:
                    orig_cover = orig_item.image_urls[0]

                # 构造 origin 字典
                extra_data["origin"] = {
                    "exists": True,  # 标记源动态存在
                    "author": orig_item.name,  # 源作者名
                    "title": orig_item.title,  # 源标题 (如视频标题)
                    "text": orig_item.text,  # 源文本 (如视频简介或动态正文)
                    "cover": orig_cover,  # 源封面/配图 URL (字符串)
                    "type_tag": orig_type_tag,  # 类型标签
                    "mid": str(orig_item.modules.module_author.mid),  # 源作者ID
                }
            else:
                # 源动态已失效
                extra_data["origin"] = {
                    "exists": False,
                    "text": "源动态已被删除或不可见",
                    "author": "未知",
                    "title": "资源失效",
                }

        res = self.result(
            title=dynamic_info.title or "B站动态",
            text=dynamic_info.text,
            timestamp=dynamic_info.timestamp,
            author=author,
            contents=contents,
        )

        # 将构造好的 extra_data (包含 origin) 注入结果
        res.extra = extra_data
        return res

    async def parse_opus(self, opus_id: int):
        """解析图文动态信息 (Opus)"""
        opus = Opus(opus_id, await self.credential)
        return await self._parse_opus_obj(opus)

    async def parse_read(self, read_id: int):
        """解析专栏信息 (Article API)"""
        from bilibili_api.article import Article

        from .article import TextNode, ImageNode, ArticleInfo

        ar = Article(read_id)
        # 获取内容，这里需要注意 bilibili-api 的版本，部分版本是 fetch_content
        await ar.fetch_content()
        data = ar.json()
        article_info = convert(data, ArticleInfo)

        stats = {}
        try:
            if article_info.stats:
                stats = {
                    "play": self._format_stat(article_info.stats.view),
                    "like": self._format_stat(article_info.stats.like),
                    "reply": self._format_stat(article_info.stats.reply),
                    "favorite": self._format_stat(article_info.stats.favorite),
                    "share": self._format_stat(article_info.stats.share),
                    "coin": self._format_stat(article_info.stats.coin),
                }
        except Exception:
            pass

        contents: list[MediaContent] = []
        current_text = ""
        for child in article_info.gen_text_img():
            if isinstance(child, ImageNode):
                contents.append(self.create_graphics_content(child.url, current_text.strip(), child.alt))
                current_text = ""
            elif isinstance(child, TextNode):
                current_text += child.text

        author = self.create_author(*article_info.author_info)

        extra_data = {
            "stats": stats,
            "type": "article",
            "type_tag": "专栏",
            "type_icon": "fa-newspaper",
            "author_id": str(article_info.meta.author.mid),
            "content_id": f"CV{read_id}",
        }

        res = self.result(
            title=article_info.title,
            timestamp=article_info.timestamp,
            text=current_text.strip(),
            author=author,
            contents=contents,
        )
        res.extra = extra_data
        return res

    async def parse_read_with_opus(self, read_id: int):
        """解析专栏信息, 使用 Opus 接口 (保留备用)"""
        from bilibili_api.article import Article

        article = Article(read_id)
        return await self._parse_opus_obj(await article.turn_to_opus())

    async def _parse_opus_obj(self, bili_opus: Opus):
        """解析图文动态/Opus对象"""
        from .opus import OpusItem, TextNode, ImageNode

        opus_info = await bili_opus.get_info()
        if not isinstance(opus_info, dict):
            raise ParseException("获取图文动态信息失败")

        opus_data = convert(opus_info, OpusItem)
        logger.debug(f"opus_data: {opus_data}")

        # 使用位置参数解包
        author = self.create_author(*opus_data.name_avatar)

        contents: list[MediaContent] = []
        current_text = ""

        for node in opus_data.gen_text_img():
            if isinstance(node, ImageNode):
                contents.append(self.create_graphics_content(node.url, current_text.strip(), node.alt))
                current_text = ""
            elif isinstance(node, TextNode):
                current_text += node.text

        return self.result(
            title=opus_data.title,
            author=author,
            timestamp=opus_data.timestamp,
            contents=contents,
            text=current_text.strip(),
        )

    async def parse_live(self, room_id: int):
        """解析直播信息"""
        from bilibili_api.live import LiveRoom

        from .live import RoomData

        room = LiveRoom(room_display_id=room_id, credential=await self.credential)
        info_dict = await room.get_room_info()

        room_data = convert(info_dict, RoomData)
        contents: list[MediaContent] = []
        if cover := room_data.cover:
            cover_task = DOWNLOADER.download_img(cover, ext_headers=self.headers)
            contents.append(ImageContent(cover_task))

        if keyframe := room_data.keyframe:
            keyframe_task = DOWNLOADER.download_img(keyframe, ext_headers=self.headers)
            contents.append(ImageContent(keyframe_task))

        author = self.create_author(room_data.name, room_data.avatar)

        url = f"https://www.bilibili.com/blackboard/live/live-activity-player.html?enterTheRoom=0&cid={room_id}"

        extra_data = {
            "type": "live",
            "type_tag": f"直播·{room_data.room_info.parent_area_name}",
            "type_icon": "fa-tower-broadcast",
            "content_id": f"ROOM{room_id}",
            "tags": str(room_data.room_info.tags),
            "live_info": {
                "level": str(room_data.anchor_info.live_info.level),
                "level_color": str(room_data.anchor_info.live_info.level_color),
                "score": str(room_data.anchor_info.live_info.score),
            },
        }

        res = self.result(
            url=url,
            title=room_data.title,
            text=room_data.detail,
            contents=contents,
            author=author,
        )
        res.extra = extra_data
        return res

    async def parse_favlist(self, fav_id: int):
        """解析收藏夹信息"""
        from bilibili_api.favorite_list import get_video_favorite_list_content

        from .favlist import FavData

        # 只会取一页，20 个
        fav_dict = await get_video_favorite_list_content(fav_id)

        if fav_dict["medias"] is None:
            raise ParseException("收藏夹内容为空, 或被风控")

        favdata = convert(fav_dict, FavData)

        author = self.create_author(favdata.info.upper.name, favdata.info.upper.face)

        return self.result(
            title=favdata.title,
            timestamp=favdata.timestamp,
            author=author,
            contents=[self.create_graphics_content(fav.cover, fav.desc) for fav in favdata.medias],
        )

    async def _get_video(self, *, bvid: str | None = None, avid: int | None = None) -> Video:
        """获取 Video 对象 (通用 helper)"""
        if avid:
            return Video(aid=avid, credential=await self.credential)
        elif bvid:
            return Video(bvid=bvid, credential=await self.credential)
        else:
            raise ParseException("avid 和 bvid 至少指定一项")

    async def extract_download_urls(
        self,
        video: Video | None = None,
        *,
        bvid: str | None = None,
        avid: int | None = None,
        page_index: int = 0,
    ) -> tuple[str, str | None]:
        """解析视频下载链接 (保持最新逻辑)"""

        from bilibili_api.video import (
            AudioStreamDownloadURL,
            VideoStreamDownloadURL,
            VideoDownloadURLDataDetecter,
        )

        if video is None:
            video = await self._get_video(bvid=bvid, avid=avid)

        # 获取下载数据
        download_url_data = await video.get_download_url(page_index=page_index)
        detecter = VideoDownloadURLDataDetecter(download_url_data)
        streams = detecter.detect_best_streams(
            video_max_quality=pconfig.bili_video_quality,
            codecs=pconfig.bili_video_codes,
            no_dolby_video=True,
            no_hdr=True,
        )
        video_stream = streams[0]
        if not isinstance(video_stream, VideoStreamDownloadURL):
            raise DownloadException("未找到可下载的视频流")
        logger.debug(f"视频流质量: {video_stream.video_quality.name}, 编码: {video_stream.video_codecs}")

        audio_stream = streams[1]
        if not isinstance(audio_stream, AudioStreamDownloadURL):
            return video_stream.url, None
        logger.debug(f"音频流质量: {audio_stream.audio_quality.name}")
        return video_stream.url, audio_stream.url

    def _save_credential(self):
        """存储哔哩哔哩登录凭证"""
        if self._credential is None:
            return

        self._cookies_file.write_text(json.dumps(self._credential.get_cookies()))

    def _load_credential(self):
        """从文件加载哔哩哔哩登录凭证"""
        if not self._cookies_file.exists():
            return

        self._credential = Credential.from_cookies(json.loads(self._cookies_file.read_text()))

    async def login_with_qrcode(self) -> bytes:
        """通过二维码登录获取哔哩哔哩登录凭证"""
        self._qr_login = QrCodeLogin()
        await self._qr_login.generate_qrcode()

        qr_pic = self._qr_login.get_qrcode_picture()
        return qr_pic.content

    async def check_qr_state(self) -> AsyncGenerator[str]:
        """检查二维码登录状态"""
        scan_tip_pending = True

        for _ in range(30):
            state = await self._qr_login.check_state()
            match state:
                case QrCodeLoginEvents.DONE:
                    yield "登录成功"
                    self._credential = self._qr_login.get_credential()
                    self._save_credential()
                    break
                case QrCodeLoginEvents.CONF:
                    if scan_tip_pending:
                        yield "二维码已扫描, 请确认登录"
                        scan_tip_pending = False
                case QrCodeLoginEvents.TIMEOUT:
                    yield "二维码过期, 请重新生成"
                    break
            await asyncio.sleep(2)
        else:
            yield "二维码登录超时, 请重新生成"

    async def _init_credential(self):
        """初始化哔哩哔哩登录凭证"""
        if pconfig.bili_ck is None:
            self._load_credential()
            return

        credential = Credential.from_cookies(ck2dict(pconfig.bili_ck))
        if await credential.check_valid():
            logger.info(f"`parser_bili_ck` 有效, 保存到 {self._cookies_file}")
            self._credential = credential
            self._save_credential()
        else:
            logger.info(f"`parser_bili_ck` 已过期, 尝试从 {self._cookies_file} 加载")
            self._load_credential()

    @property
    async def credential(self) -> Credential | None:
        """哔哩哔哩登录凭证"""

        if self._credential is None:
            await self._init_credential()
            return self._credential

        if not await self._credential.check_valid():
            logger.warning("哔哩哔哩凭证已过期, 请重新配置")
            return None

        if await self._credential.check_refresh():
            logger.info("哔哩哔哩凭证需要刷新")
            if self._credential.has_ac_time_value() and self._credential.has_bili_jct():
                await self._credential.refresh()
                logger.info(f"哔哩哔哩凭证刷新成功, 保存到 {self._cookies_file}")
                self._save_credential()
            else:
                logger.warning("哔哩哔哩凭证刷新需要包含 `SESSDATA`, `ac_time_value` 项")

        return self._credential
