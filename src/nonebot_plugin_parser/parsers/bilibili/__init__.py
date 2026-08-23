"""Bilibili 解析器 — 基于 curl_cffi 直连 API"""

import asyncio
from re import Match
from typing import ClassVar

from msgspec import convert
from nonebot import logger

from .api import BILI_HEADERS, BiliAPIClient
from ..base import (
    BaseParser,
    PlatformEnum,
    ParseException,
    IgnoreException,
    DownloadException,
    handle,
    pconfig,
)
from ..data import Platform, ImageContent, MediaContent
from .dynamic import DynamicInfo


class BilibiliParser(BaseParser):
    platform: ClassVar[Platform] = Platform(name=PlatformEnum.BILIBILI, display_name="哔哩哔哩")

    def __init__(self):
        self.headers = BILI_HEADERS.copy()
        self._api_client = BiliAPIClient()

    @handle("b23.tv", r"b23\.tv/[0-9a-zA-Z._?%&+-=/#]+")
    @handle("bili2233", r"bili2233\.cn/[0-9a-zA-Z._?%&+-=/#]+")
    async def _parse_short_link(self, searched: Match[str]):
        """解析短链"""
        url = f"https://{searched.group(0)}"
        return await self.parse_with_redirect(url)

    @handle("BV", r"^(?P<bvid>BV[0-9a-zA-Z]{10})(?:\s)?(?P<page_num>\d{1,3})?$")
    @handle("/BV", r"bilibili\.com(?:/video)?/(?P<bvid>BV[0-9A-Za-z]{10})(?:.*?[?&]p=(?P<page_num>\d{1,3}))?")
    async def _parse_bv(self, searched: Match[str]):
        """解析视频信息"""
        bvid = str(searched.group("bvid"))
        page_num = int(searched.group("page_num") or 1)
        return await self.parse_video(bvid=bvid, page_num=page_num)

    @handle("av", r"^av(?P<avid>\d{6,})(?:\s)?(?P<page_num>\d{1,3})?$")
    @handle("/av", r"bilibili\.com(?:/video)?/av(?P<avid>\d{6,})(?:.*?[?&]p=(?P<page_num>\d{1,3}))?")
    async def _parse_av(self, searched: Match[str]):
        """解析视频信息"""
        avid = int(searched.group("avid"))
        page_num = int(searched.group("page_num") or 1)
        return await self.parse_video(avid=avid, page_num=page_num)

    @handle("/dynamic/", r"bilibili\.com/dynamic/(?P<dynamic_id>\d+)")
    @handle("/opus/", r"bilibili\.com/opus/(?P<dynamic_id>\d+)")
    @handle("t.bili", r"t\.bilibili\.com/(?P<dynamic_id>\d+)")
    async def _parse_dynamic(self, searched: Match[str]):
        """解析动态信息"""
        dynamic_id = int(searched.group("dynamic_id"))
        return await self.parse_dynamic_or_opus(dynamic_id)

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
        read_id = int(searched.group("read_id"))
        opus_id = await self._api_client.turn_article_to_opus(read_id)
        return await self._parse_opus_by_id(opus_id)

    async def parse_video(
        self,
        *,
        bvid: str | None = None,
        avid: int | None = None,
        page_num: int = 1,
    ):
        """解析视频信息"""
        from .video import VideoInfo, AIConclusion

        # 获取视频信息
        video_data = await self._api_client.get_video_info(bvid=bvid, aid=avid)
        video_info = convert(video_data, VideoInfo)

        # UP主
        author = self.create_author(video_info.owner.name, video_info.owner.face)

        # 处理分 P
        page_info = video_info.extract_info_with_page(page_num)

        # 获取 AI 总结
        if self._api_client.has_credential():
            try:
                cid = await self._api_client.get_cid(video_info.bvid, page_info.index)
                ai_data = await self._api_client.get_ai_conclusion(video_info.bvid, cid)
                ai_conclusion = convert(ai_data, AIConclusion) if ai_data else AIConclusion()
                ai_summary = ai_conclusion.summary
            except ParseException:
                ai_summary = "AI总结获取失败"
        else:
            ai_summary = "哔哩哔哩 cookie 未配置或失效, 无法使用 AI 总结"

        url = f"https://bilibili.com/{video_info.bvid}"
        url += f"?p={page_info.index + 1}" if page_info.index > 0 else ""

        # 视频下载 task
        async def download_video():
            output_path = pconfig.cache_dir / f"{video_info.bvid}-{page_num}.mp4"
            if output_path.exists():
                return output_path
            v_url, a_url = await self.extract_download_urls(bvid=video_info.bvid, page_index=page_info.index)
            if page_info.duration > pconfig.duration_maximum:
                logger.warning(f"视频时长 {page_info.duration} 秒, 超过 {pconfig.duration_maximum} 秒, 取消下载")
                raise IgnoreException
            if a_url is not None:
                path = await self.downloader.download_av_and_merge(
                    v_url,
                    a_url,
                    output_path=output_path,
                    ext_headers=self.headers,
                )
            else:
                path = await self.downloader._download_file(
                    v_url,
                    file_name=output_path.name,
                    ext_headers=self.headers,
                )
            return path

        video_content = self.create_video(
            asyncio.create_task(download_video()),
            page_info.cover,
            page_info.duration,
        )

        return self.result(
            url=url,
            title=page_info.title,
            timestamp=page_info.timestamp,
            text=video_info.desc,
            author=author,
            contents=[video_content],
            extra={"info": ai_summary},
        )

    async def parse_dynamic_or_opus(self, dynamic_id: int):
        """解析动态或图文"""
        try:
            # 先尝试作为图文动态 (opus) 解析
            opus_data = await self._api_client.get_opus_detail(dynamic_id)
            if opus_data and opus_data.get("item"):
                return await self._parse_opus_data(opus_data)
        except ParseException:
            pass

        # 作为普通动态解析
        dynamic_data = await self._api_client.get_dynamic_detail(dynamic_id)
        dynamic_info = convert(dynamic_data["item"], DynamicInfo)
        return await self._parse_dynamic_info(dynamic_info)

    async def _parse_dynamic_info(self, dynamic_info: DynamicInfo):
        if dynamic_info.is_video():
            if (major := dynamic_info.modules.major) and (archive := major.archive):
                result = await self.parse_video(bvid=archive.bvid)
                result.text = dynamic_info.text
                result.extra["content_type"] = "动态"
                return result

        # 下载图片
        author = self.create_author(dynamic_info.name, dynamic_info.avatar)
        contents: list[MediaContent] = []
        contents.extend(self.create_images(dynamic_info.image_urls))

        repost = None
        if dynamic_info.type == "DYNAMIC_TYPE_FORWARD" and dynamic_info.orig is not None:
            repost = await self._parse_dynamic_info(dynamic_info.orig)

        return self.result(
            title=dynamic_info.title,
            text=dynamic_info.text,
            timestamp=dynamic_info.timestamp,
            author=author,
            contents=contents,
            repost=repost,
            extra={"content_type": "动态"},
        )

    async def _parse_opus_by_id(self, opus_id: int):
        """根据 opus_id 解析图文动态"""
        client = self._api_client
        opus_data = await client.get_opus_detail(opus_id)
        return await self._parse_opus_data(opus_data)

    async def _parse_opus_data(self, opus_data: dict):
        """解析图文动态数据 (Opus)"""
        from .opus import OpusItem

        opus_item = convert(opus_data["item"], OpusItem)
        logger.debug(f"opus_data: {opus_item}")

        author = self.create_author(*opus_item.name_avatar)

        result = self.result(
            author=author,
            title=opus_item.title,
            timestamp=opus_item.timestamp,
        )

        for node in opus_item.extract_nodes():
            if isinstance(node, str):
                result.graphics.append(node)
            else:
                result.graphics.append(self.create_image(node.url, alt=node.alt))

        return result

    async def parse_live(self, room_id: int):
        """解析直播"""
        from .live import RoomData

        client = self._api_client
        info_dict = await client.get_live_room_info(room_id)

        room_data = convert(info_dict, RoomData)
        contents: list[MediaContent] = []
        # 下载封面
        if cover := room_data.cover:
            cover_task = self.downloader.download_img(cover, ext_headers=self.headers)
            contents.append(self.create_image(cover_task))

        # 下载关键帧
        if keyframe := room_data.keyframe:
            keyframe_task = self.downloader.download_img(keyframe, ext_headers=self.headers)
            contents.append(self.create_image(keyframe_task))

        author = self.create_author(room_data.name, room_data.avatar)

        url = f"https://www.bilibili.com/blackboard/live/live-activity-player.html?enterTheRoom=0&cid={room_id}"
        return self.result(
            url=url,
            title=room_data.title,
            text=room_data.detail,
            contents=contents,
            author=author,
        )

    async def parse_favlist(self, fav_id: int):
        """解析收藏夹"""
        from .favlist import FavData

        client = self._api_client
        resource_list = await client.get_fav_resource_list(fav_id)

        if resource_list.get("medias") is None:
            raise ParseException("收藏夹内容为空, 或被风控")

        favdata = convert(resource_list, FavData)

        author = self.create_author(favdata.info.upper.name, favdata.info.upper.face)

        graphics: list[str | ImageContent] = []
        for fav in favdata.medias:
            graphics.append(self.create_image(fav.cover, alt=fav.desc))
            graphics.append(fav.desc)

        return self.result(
            title=favdata.title,
            timestamp=favdata.timestamp,
            author=author,
            graphics=graphics,
        )

    async def extract_download_urls(
        self,
        *,
        bvid: str | None = None,
        avid: int | None = None,
        page_index: int = 0,
    ) -> tuple[str, str | None]:
        """解析视频下载链接 — 直接使用 curl_cffi 获取 playurl 并选择最佳流"""
        from ...constants import BiliVideoCodec, BiliVideoQuality

        if bvid is None and avid is not None:
            video_data = await self._api_client.get_video_info(aid=avid)
            bvid = video_data.get("bvid", "")

        if bvid is None:
            raise DownloadException("无法获取 bvid")

        # 获取 cid
        cid = await self._api_client.get_cid(bvid, page_index)

        # 获取播放 URL 数据
        play_data = await self._api_client.get_play_url(bvid, cid, platform="")

        # 选择最佳视频/音频流 (移植自 bilibili-api-python 的 VideoDownloadURLDataDetecter)
        video_url: str | None = None
        audio_url: str | None = None

        # 处理 FLV/MP4 流
        if play_data.durl:
            video_url = play_data.durl[0].url
            return video_url, None

        # 处理 DASH 流
        if not play_data.dash:
            raise DownloadException("未找到可播放的视频流")

        dash = play_data.dash

        # 视频质量映射
        quality_map = {
            16: BiliVideoQuality._360P,
            32: BiliVideoQuality._480P,
            64: BiliVideoQuality._720P,
            80: BiliVideoQuality._1080P,
            112: BiliVideoQuality._1080P_PLUS,
            116: BiliVideoQuality._1080P_60,
            120: BiliVideoQuality._4K,
        }

        # 音频质量映射
        audio_quality_map = {
            30216: "64K",
            30232: "128K",
            30280: "192K",
            30250: "Dolby",
            30251: "Hi-Res",
        }

        # 编码优先级
        codec_priority = {
            BiliVideoCodec.AVC: 0,
            BiliVideoCodec.HEV: 1,
            BiliVideoCodec.AV1: 2,
        }
        codec_keywords = {
            BiliVideoCodec.AVC: ["avc"],
            BiliVideoCodec.HEV: ["hev"],
            BiliVideoCodec.AV1: ["av1"],
        }

        max_quality = pconfig.bili_video_quality
        allowed_codecs = pconfig.bili_video_codes

        # 选视频: 最高质量 + 最高优先级编码，并过滤 mcdn
        best_video_stream = None
        best_video_matached_codec = None
        best_video_score = (-1, -1, 0)  # (quality_score, codec_score, not_mcdn)

        for stream in dash.video:
            q = quality_map.get(stream.id)
            if q is None or q.value > max_quality.value:
                continue

            # 检测编码
            matched_codec = None
            for codec in allowed_codecs:
                keywords = codec_keywords.get(codec, [])
                if any(kw in stream.codecs.lower() for kw in keywords):
                    matched_codec = codec
                    break
            if matched_codec is None:
                continue

            quality_score = q.value
            codec_score = codec_priority.get(matched_codec, 99)
            not_mcdn = 0 if "mcdn" in stream.base_url else 1  # 优先非 mcdn
            score = (quality_score, -codec_score, not_mcdn)  # 高画质优先，编码优先级高优先，非 mcdn 优先

            if score > best_video_score:
                best_video_score = score
                best_video_stream = stream
                best_video_matached_codec = matched_codec

        if best_video_stream is None:
            raise DownloadException("未找到匹配的视频流")

        # 若选中的 stream 是 mcdn，尝试用 backup_url 替换
        video_url = best_video_stream.base_url
        if "mcdn" in video_url and best_video_stream.backup_url:
            for bu in best_video_stream.backup_url:
                if "mcdn" not in bu:
                    video_url = bu
                    logger.debug("mcdn 链接替换为备用链接")
                    break

        q_name = quality_map[best_video_stream.id].name.lstrip("_")
        matched_codec_name = best_video_matached_codec.name  # type: ignore[union-attr]
        logger.debug(f"视频流 {q_name} | {matched_codec_name} | {video_url[:64]}...")

        # 选音频: 最高质量，并过滤 mcdn
        if dash.audio:
            best_audio_stream = max(
                (s for s in dash.audio if "mcdn" not in s.base_url),
                key=lambda s: s.id,
                default=None,
            )
            if best_audio_stream is None:
                # 全是 mcdn，选最高质量
                best_audio_stream = max(dash.audio, key=lambda s: s.id)

            if best_audio_stream:
                audio_url = best_audio_stream.base_url
                if "mcdn" in audio_url and best_audio_stream.backup_url:
                    for bu in best_audio_stream.backup_url:
                        if "mcdn" not in bu:
                            audio_url = bu
                            break
                aq_name = audio_quality_map.get(best_audio_stream.id, f"id={best_audio_stream.id}")
                logger.debug(f"音频流 {aq_name} | {audio_url[:64]}...")

        if video_url:
            return video_url, audio_url
        raise DownloadException("未找到可下载的视频流")
