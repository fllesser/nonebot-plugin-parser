import asyncio
import json
import re
from typing import ClassVar
from typing_extensions import override

from bilibili_api import HEADERS, Credential, request_settings, select_client
from bilibili_api.opus import Opus
from bilibili_api.video import Video
import msgspec
from nonebot import logger

from ...config import pconfig
from ...download import DOWNLOADER
from ...exception import DownloadException, DurationLimitException, ParseException
from ..base import BaseParser
from ..cookie import ck2dict
from ..data import (
    ImageContent,
    MediaContent,
    Platform,
)


class BilibiliParser(BaseParser):
    # 平台信息
    platform: ClassVar[Platform] = Platform(name="bilibili", display_name="哔哩哔哩")

    # URL 正则表达式模式（keyword, pattern）
    patterns: ClassVar[list[tuple[str, str]]] = [
        ("bilibili", r"https?://(?:space|www|live|m|t)?\.?bilibili\.com/[A-Za-z\d\._?%&+\-=/#]+()()"),
        ("bili2233", r"https?://bili2233\.cn/[A-Za-z\d\._?%&+\-=/#]+()()"),
        ("b23", r"https?://b23\.tv/[A-Za-z\d\._?%&+\-=/#]+()()"),
        ("BV", r"(BV[1-9a-zA-Z]{10})(?:\s)?(\d{1,3})?"),
        ("av", r"av(\d{6,})(?:\s)?(\d{1,3})?"),
    ]

    def __init__(self):
        self.headers = HEADERS.copy()
        self._credential: Credential | None = None
        self._cookies_file = pconfig.config_dir / "bilibili_cookies.json"
        # 选择客户端
        select_client("curl_cffi")
        # 模仿浏览器
        request_settings.set("impersonate", "chrome131")
        # 第二参数数值参考 curl_cffi 文档
        # https://curl-cffi.readthedocs.io/en/latest/impersonate.html

    @override
    async def parse(self, matched: re.Match[str]):
        """解析 URL 获取内容信息并下载资源

        Args:
            matched: 正则表达式匹配对象，由平台对应的模式匹配得到

        Returns:
            ParseResult: 解析结果（已下载资源，包含 Path）

        Raises:
            ParseException: 解析失败时抛出
        """
        # 从匹配对象中获取原始URL, 视频ID, 页码
        url, video_id, page_num = str(matched.group(0)), str(matched.group(1)), matched.group(2)

        # 处理短链
        if "b23.tv" in url or "bili2233.cn" in url:
            url = await self.get_redirect_url(url, self.headers)

        if not video_id:
            if _matched := re.search(r"(BV[\dA-Za-z]{10})[^?]*?(?:\?[^#]*?p=(\d{1,3}))?", url):
                video_id = _matched.group(1)
                page_num = _matched.group(2)
            elif _matched := re.search(r"av(\d{6,})[^?]*?(?:\?[^#]*?p=(\d{1,3}))?", url):
                video_id = _matched.group(1)
                page_num = _matched.group(2)
            else:
                return await self.parse_others(url)

        avid, bvid = None, None
        page_num = int(page_num) if page_num and page_num.isdigit() else 1

        # 链接中是否包含BV，av号
        if video_id.isdigit():
            avid = int(video_id)
        else:
            bvid = video_id

        # 解析视频信息
        return await self.parse_video(bvid=bvid, avid=avid, page_num=page_num)

    async def parse_video(
        self,
        *,
        bvid: str | None = None,
        avid: int | None = None,
        page_num: int = 1,
    ):
        """解析视频信息

        Args:
            bvid (str | None): bvid
            avid (int | None): avid
            page_num (int): 页码
        """

        from .video import AIConclusion, VideoInfo

        video = await self._parse_video(bvid=bvid, avid=avid)

        # 转换为 msgspec struct
        video_info = msgspec.convert(await video.get_info(), VideoInfo)

        # 获取简介
        text = f"简介: {video_info.desc}" if video_info.desc else None

        # up
        author = self.create_author(video_info.owner.name, video_info.owner.face)

        # 处理分 p
        page_idx, title, duration, timestamp, cover_url = video_info.extract_info_with_page(page_num)

        # 获取 AI 总结
        if self._credential:
            cid = await video.get_cid(page_idx)
            ai_conclusion = await video.get_ai_conclusion(cid)
            ai_conclusion = msgspec.convert(ai_conclusion, AIConclusion)
            ai_summary = ai_conclusion.summary
        else:
            ai_summary: str = "哔哩哔哩 cookie 未配置或失效, 无法使用 AI 总结"

        url = f"https://bilibili.com/{video_info.bvid}" + (f"?p={page_idx + 1}" if page_idx > 0 else "")

        # 视频下载 task
        async def download_video():
            output_path = pconfig.cache_dir / f"{video_info.bvid}-{page_num}.mp4"
            if output_path.exists():
                return output_path
            v_url, a_url = await self.get_download_urls(video=video, page_index=page_idx)
            if duration > pconfig.duration_maximum:
                raise DurationLimitException
            if a_url is not None:
                return await DOWNLOADER.download_av_and_merge(
                    v_url, a_url, output_path=output_path, ext_headers=self.headers
                )
            else:
                return await DOWNLOADER.streamd(v_url, file_name=output_path.name, ext_headers=self.headers)

        video_task = asyncio.create_task(download_video())
        video_content = self.create_video_content(video_task, cover_url, duration)

        return self.result(
            url=url,
            title=title,
            timestamp=timestamp,
            text=text,
            author=author,
            contents=[video_content],
            extra={"info": ai_summary},
        )

    async def parse_others(self, url: str):
        """解析其他类型链接"""
        # 判断链接类型并解析
        # 1. 动态
        if "t.bilibili.com" in url:
            return await self.parse_dynamic(url)

        # 2.图文动态
        if "/opus" in url:
            matched = re.search(r"/(\d+)", url)
            if not matched:
                raise ParseException("无效的动态链接")
            opus_id = int(matched.group(1))
            return await self.parse_opus(opus_id)

        # 3. 专栏
        if "/read" in url:
            matched = re.search(r"/cv(\d+)", url)
            if matched is None:
                raise ParseException("无效的专栏链接")
            read_id = int(matched.group(1))
            return await self.parse_read(read_id)

        # 4. 直播
        if "/live" in url:
            matched = re.search(r"/(\d+)", url)
            if matched is None:
                raise ParseException("无效的直播链接")
            room_id = int(matched.group(1))
            return await self.parse_live(room_id)

        # 5. 收藏夹
        if "/favlist" in url:
            matched = re.search(r"fid=(\d+)", url)
            if matched is None:
                raise ParseException("无效的收藏夹链接")
            fav_id = int(matched.group(1))
            return await self.parse_favlist(fav_id)

        raise ParseException("不支持的 Bilibili 链接")

    async def _init_credential(self) -> Credential | None:
        """初始化 bilibili api"""

        if not pconfig.bili_ck:
            logger.warning("未配置 r_bili_ck, 无法使用哔哩哔哩 AI 总结, 可能无法解析 720p 以上画质视频")
            return None

        credential = Credential.from_cookies(ck2dict(pconfig.bili_ck))
        if not await credential.check_valid() and self._cookies_file.exists():
            logger.info(f"r_bili_ck 已过期, 尝试从 {self._cookies_file} 加载")
            credential = Credential.from_cookies(json.loads(self._cookies_file.read_text()))
        else:
            logger.info(f"r_bili_ck 有效, 保存到 {self._cookies_file}")
            self._cookies_file.write_text(json.dumps(credential.get_cookies()))

        return credential

    @property
    async def credential(self) -> Credential | None:
        """获取哔哩哔哩登录凭证"""

        if self._credential is None:
            self._credential = await self._init_credential()
            if self._credential is None:
                return None

        if not await self._credential.check_valid():
            logger.warning("哔哩哔哩 cookies 已过期, 请重新配置 r_bili_ck")
            return self._credential

        if await self._credential.check_refresh():
            logger.info("哔哩哔哩 cookies 需要刷新")
            if self._credential.has_ac_time_value() and self._credential.has_bili_jct():
                await self._credential.refresh()
                logger.info(f"哔哩哔哩 cookies 刷新成功, 保存到 {self._cookies_file}")
                self._cookies_file.write_text(json.dumps(self._credential.get_cookies()))
            else:
                logger.warning("哔哩哔哩 cookies 刷新需要包含 SESSDATA, ac_time_value, bili_jct")

        return self._credential

    async def parse_dynamic(self, url: str):
        """解析动态信息

        Args:
            url (str): 动态链接
        """
        from bilibili_api.dynamic import Dynamic

        from .dynamic import DynamicItem

        matched = re.search(r"/(\d+)", url)
        if matched is None:
            raise ParseException("无效的动态链接")
        dynamic_id = int(matched.group(1))
        dynamic = Dynamic(dynamic_id, await self.credential)

        # 转换为结构体
        dynamic_data = msgspec.convert(await dynamic.get_info(), DynamicItem)
        dynamic_info = dynamic_data.item
        # 使用结构体属性提取信息
        author = self.create_author(dynamic_info.name, dynamic_info.avatar)

        # 下载图片
        contents: list[MediaContent] = []
        for image_url in dynamic_info.image_urls:
            img_task = DOWNLOADER.download_img(image_url, ext_headers=self.headers)
            contents.append(ImageContent(img_task))

        return self.result(
            url=url,
            title=dynamic_info.title,
            text=dynamic_info.text,
            timestamp=dynamic_info.timestamp,
            author=author,
            contents=contents,
        )

    async def parse_opus(self, opus_id: int):
        """解析图文动态信息

        Args:
            opus_id (int): 图文动态 id
        """
        opus = Opus(opus_id, await self.credential)
        return await self._parse_opus(opus)

    async def parse_read(self, read_id: int):
        """解析专栏信息

        Args:
            read_id (int): 专栏 id
        """
        from bilibili_api.article import Article

        article = Article(read_id)
        return await self._parse_opus(await article.turn_to_opus())

    async def _parse_opus(self, bili_opus: Opus):
        """解析图文动态信息

        Args:
            opus_id (int): 图文动态 id

        Returns:
            ParseResult: 解析结果
        """

        from .opus import OpusImageNode, OpusItem, OpusTextNode

        opus_info = await bili_opus.get_info()
        if not isinstance(opus_info, dict):
            raise ParseException("获取图文动态信息失败")
        # 转换为结构体
        opus_data = msgspec.convert(opus_info, OpusItem)

        author = self.create_author(*opus_data.name_avatar)

        # 按顺序处理图文内容（参考 parse_read 的逻辑）
        contents: list[MediaContent] = []
        temp_text = None

        for node in opus_data.gen_text_img():
            match node:
                case OpusImageNode():
                    contents.append(self.create_graphics_content(node.url, temp_text))
                    temp_text = None
                case OpusTextNode():
                    if temp_text is None:
                        temp_text = ""
                    temp_text += node.text

        # 处理最后的文本内容
        text_content = temp_text

        return self.result(
            title=opus_data.title,
            author=author,
            timestamp=opus_data.timestamp,
            contents=contents,
            text=text_content,
        )

    async def parse_live(self, room_id: int):
        """解析直播信息

        Args:
            room_id (int): 直播 id

        Returns:
            ParseResult: 解析结果
        """
        from bilibili_api.live import LiveRoom

        from .live import RoomData

        room = LiveRoom(room_display_id=room_id, credential=await self.credential)
        info_dict = await room.get_room_info()

        room_data = msgspec.convert(info_dict, RoomData)
        contents: list[MediaContent] = []
        # 下载封面
        if cover := room_data.cover:
            cover_task = DOWNLOADER.download_img(cover, ext_headers=self.headers)
            contents.append(ImageContent(cover_task))

        # 下载关键帧
        if keyframe := room_data.keyframe:
            keyframe_task = DOWNLOADER.download_img(keyframe, ext_headers=self.headers)
            contents.append(ImageContent(keyframe_task))

        author = self.create_author(room_data.name, room_data.avatar)

        return self.result(title=room_data.title, text=room_data.detail, contents=contents, author=author)

    async def parse_read_old(self, read_id: int):
        """专栏解析

        Args:
            read_id (int): 专栏 id

        Returns:
            texts: list[str], urls: list[str]
        """
        from bilibili_api.article import Article

        from .article import ArticleInfo, ImageNode, TextNode

        ar = Article(read_id)
        # 加载内容
        await ar.fetch_content()
        data = ar.json()
        article_info = msgspec.convert(data, ArticleInfo)
        logger.debug(f"article_info: {article_info}")
        contents: list[MediaContent] = []
        temp_text = None
        for child in article_info.gen_text_img():
            match child:
                case ImageNode():
                    contents.append(self.create_graphics_content(child.url, temp_text, child.alt))
                    temp_text = None
                case TextNode():
                    if temp_text is None:
                        temp_text = ""
                    temp_text += child.text

        return self.result(
            title=article_info.meta.title,
            timestamp=article_info.meta.publish_time,
            text=temp_text,
            author=self.create_author(article_info.meta.author.name, article_info.meta.author.face),
            contents=contents,
        )

    async def parse_favlist(self, fav_id: int):
        """解析收藏夹信息

        Args:
            fav_id (int): 收藏夹 id

        Returns:
            list[GraphicsContent]: 图文内容列表
        """
        from bilibili_api.favorite_list import get_video_favorite_list_content

        from .favlist import FavData

        # 只会取一页，20 个
        fav_dict = await get_video_favorite_list_content(fav_id)

        if fav_dict["medias"] is None:
            raise ParseException("收藏夹内容为空, 或被风控")

        favdata = msgspec.convert(fav_dict, FavData)

        return self.result(
            title=favdata.title,
            timestamp=favdata.timestamp,
            author=self.create_author(favdata.info.upper.name, favdata.info.upper.face),
            contents=[self.create_graphics_content(fav.cover, fav.desc) for fav in favdata.medias],
        )

    async def _parse_video(self, *, bvid: str | None = None, avid: int | None = None) -> Video:
        """解析视频信息

        Args:
            bvid (str | None): bvid
            avid (int | None): avid
        """
        if avid:
            return Video(aid=avid, credential=await self.credential)
        elif bvid:
            return Video(bvid=bvid, credential=await self.credential)
        else:
            raise ParseException("avid 和 bvid 至少指定一项")

    async def get_download_urls(
        self,
        *,
        video: Video | None = None,
        bvid: str | None = None,
        avid: int | None = None,
        page_index: int = 0,
    ) -> tuple[str, str | None]:
        """解析视频下载链接

        Args:
            bvid (str | None): bvid
            avid (int | None): avid
            page_index (int): 页索引 = 页码 - 1
        """

        from bilibili_api.video import (
            AudioStreamDownloadURL,
            VideoDownloadURLDataDetecter,
            VideoQuality,
            VideoStreamDownloadURL,
        )

        if video is None:
            video = await self._parse_video(bvid=bvid, avid=avid)
        # 获取下载数据
        download_url_data = await video.get_download_url(page_index=page_index)
        detecter = VideoDownloadURLDataDetecter(download_url_data)
        streams = detecter.detect_best_streams(
            video_max_quality=VideoQuality._1080P,
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
