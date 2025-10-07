import asyncio
import json
import re
from typing import Any, ClassVar
from typing_extensions import override

from bilibili_api import HEADERS, Credential, request_settings, select_client
from bilibili_api.video import Video
import msgspec
from nonebot import logger

from ...config import pconfig
from ...download import DOWNLOADER
from ...exception import DownloadException, DurationLimitException, ParseException
from ..base import BaseParser
from ..cookie import ck2dict
from ..data import (
    Author,
    GraphicsContent,
    ImageContent,
    MediaContent,
    Platform,
    VideoContent,
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

        avid, bvid = None, None
        # 链接中是否包含BV，av号
        if video_id:
            if video_id.isdigit():
                avid = int(video_id)
            else:
                bvid = video_id
        else:
            if _matched := re.search(r"(BV[\dA-Za-z]{10})[^?]*?(?:\?[^#]*?p=(\d{1,3}))?", url):
                bvid = _matched.group(1)
                page_num = _matched.group(2)
            elif _matched := re.search(r"av(\d{6,})[^?]*?(?:\?[^#]*?p=(\d{1,3}))?", url):
                avid = int(_matched.group(1))
                page_num = _matched.group(2)
            else:
                return await self.parse_others(url)

        page_num = int(page_num) if page_num and page_num.isdigit() else 1

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

        # 额外信息
        extra = {"info": f"简介：{video_info.desc}\n\n{ai_summary}"}

        # 下载封面
        cover_path = DOWNLOADER.download_img(cover_url, ext_headers=self.headers) if cover_url else None

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

        return self.result(
            title=title,
            url=url,
            extra=extra,
            timestamp=timestamp,
            author=Author(name=video_info.owner.name, avatar=DOWNLOADER.download_img(video_info.owner.face)),
            contents=[VideoContent(video_task, cover_path, duration)],
        )

    async def parse_others(self, url: str):
        """解析其他类型链接"""
        # 判断链接类型并解析
        # 1. 动态/图文 (opus)
        if "t.bilibili.com" in url or "/opus" in url:
            matched = re.search(r"/(\d+)", url)
            if not matched:
                raise ParseException("无效的动态链接")
            opus_id = int(matched.group(1))
            img_urls, text = await self.parse_opus(opus_id)

            # 下载图片
            contents: list[MediaContent] = []
            if img_urls:
                img_tasks = [DOWNLOADER.download_img(url, ext_headers=self.headers) for url in img_urls]
                contents.extend(ImageContent(task) for task in img_tasks)

            return self.result(title=f"动态 - {opus_id}", text=text, contents=contents)

        # 2. 直播
        if "/live" in url:
            match_result = re.search(r"/(\d+)", url)
            if not match_result:
                raise ParseException("无效的直播链接")
            room_id = int(match_result.group(1))
            title, cover, keyframe = await self.parse_live(room_id)

            contents = []
            # 下载封面
            if cover:
                cover_task = DOWNLOADER.download_img(cover, ext_headers=self.headers)
                contents.append(ImageContent(cover_task))

            # 下载关键帧
            if keyframe:
                keyframe_task = DOWNLOADER.download_img(keyframe, ext_headers=self.headers)
                contents.append(ImageContent(keyframe_task))

            return self.result(title="直播 - " + title, contents=contents)

        # 3. 专栏
        if "/read" in url:
            match_result = re.search(r"/cv(\d+)", url)
            if not match_result:
                raise ParseException("无效的专栏链接")
            read_id = int(match_result.group(1))
            texts, img_urls = await self.parse_read(read_id)
            combined_text = "\n".join(texts)

            # 下载图片
            contents = []
            if img_urls:
                img_tasks = [DOWNLOADER.download_img(url, ext_headers=self.headers) for url in img_urls]
                contents.extend(ImageContent(task) for task in img_tasks)

            return self.result(title=f"专栏 - {read_id}", text=combined_text, contents=contents)

        # 4. 收藏夹
        if "/favlist" in url:
            match_result = re.search(r"fid=(\d+)", url)
            if not match_result:
                raise ParseException("无效的收藏夹链接")
            fav_id = int(match_result.group(1))
            titles, cover_urls = await self.parse_favlist(fav_id)

            # 并发下载封面
            cover_tasks = [DOWNLOADER.download_img(url, ext_headers=self.headers) for url in cover_urls]
            contents = [GraphicsContent(task, title) for task, title in zip(cover_tasks, titles)]
            return self.result(
                title=f"收藏夹 - {fav_id}",
                contents=contents,
            )

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

    async def parse_opus(self, opus_id: int) -> tuple[list[str], str]:
        """解析动态信息

        Args:
            opus_id (int): 动态 id

        Returns:
            tuple[list[str], str]: 图片 url 列表和动态信息
        """
        from bilibili_api.opus import Opus

        opus = Opus(opus_id, await self.credential)
        opus_info = await opus.get_info()
        if not isinstance(opus_info, dict):
            raise ParseException("获取动态信息失败")

        # 获取图片信息
        urls = await opus.get_images_raw_info()
        urls = [url["url"] for url in urls]

        dynamic = opus.turn_to_dynamic()
        dynamic_info: dict[str, Any] = await dynamic.get_info()
        orig_text = (
            dynamic_info.get("item", {})
            .get("modules", {})
            .get("module_dynamic", {})
            .get("major", {})
            .get("opus", {})
            .get("summary", {})
            .get("rich_text_nodes", [{}])[0]
            .get("orig_text", "")
        )
        return urls, orig_text

    async def parse_live(self, room_id: int) -> tuple[str, str, str]:
        """解析直播信息

        Args:
            room_id (int): 直播 id

        Returns:
            tuple[str, str, str]: 标题、封面、关键帧
        """
        from bilibili_api.live import LiveRoom

        room = LiveRoom(room_display_id=room_id, credential=await self.credential)
        room_info: dict[str, Any] = (await room.get_room_info())["room_info"]
        title, cover, keyframe = (
            room_info["title"],
            room_info["cover"],
            room_info["keyframe"],
        )
        return (title, cover, keyframe)

    async def parse_read(self, read_id: int) -> tuple[list[str], list[str]]:
        """专栏解析

        Args:
            read_id (int): 专栏 id

        Returns:
            texts: list[str], urls: list[str]
        """
        from bilibili_api.article import Article

        ar = Article(read_id)

        # 加载内容
        await ar.fetch_content()
        data = ar.json()

        def accumulate_text(node: dict):
            text = ""
            if "children" in node:
                for child in node["children"]:
                    text += accumulate_text(child) + " "
            if _text := node.get("text"):
                text += _text if isinstance(_text, str) else str(_text) + node["url"]
            return text

        urls: list[str] = []
        texts: list[str] = []
        for node in data.get("children", []):
            node_type = node.get("type")
            if node_type == "ImageNode":
                if img_url := node.get("url", "").strip():
                    urls.append(img_url)
                    # 补空串占位符
                    texts.append("")
            elif node_type == "ParagraphNode":
                if text := accumulate_text(node).strip():
                    texts.append(text)
            elif node_type == "TextNode":
                if text := node.get("text", "").strip():
                    texts.append(text)
        return texts, urls

    async def parse_favlist(self, fav_id: int) -> tuple[list[str], list[str]]:
        """解析收藏夹信息

        Args:
            fav_id (int): 收藏夹 id

        Returns:
            tuple[list[str], list[str]]: 标题、封面、简介、链接
        """
        from bilibili_api.favorite_list import get_video_favorite_list_content

        fav_list: dict[str, Any] = await get_video_favorite_list_content(fav_id)
        if fav_list["medias"] is None:
            raise ParseException("收藏夹内容为空, 或被风控")
        # 取前 50 个
        medias_50: list[dict[str, Any]] = fav_list["medias"][:50]
        texts: list[str] = []
        urls: list[str] = []
        for fav in medias_50:
            title, cover, intro, link = (
                fav["title"],
                fav["cover"],
                fav["intro"],
                fav["link"],
            )
            link: str = link.replace("bilibili://video/", "https://bilibili.com/video/av")
            urls.append(cover)
            texts.append(f"🧉 标题：{title}\n📝 简介：{intro}\n🔗 链接: {link}")
        return texts, urls

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
