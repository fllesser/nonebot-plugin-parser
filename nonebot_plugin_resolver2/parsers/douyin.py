import json
import re

import aiohttp
from nonebot.log import logger

from .base import BaseParser, ParseException, VideoAuthor, VideoInfo


class DouYin(BaseParser):
    """
    抖音 / 抖音火山版
    """

    async def parse_share_url(self, share_url: str) -> VideoInfo:
        if match := re.match(r"(video|note)/([0-9]+)", share_url):
            # https://www.douyin.com/video/xxxxxx
            _type, video_id = match.group(1), match.group(2)
            iesdouyin_url = self._iesdouyin_by_video_id(_type, video_id)
        else:
            # https://v.douyin.com/xxxxxx
            iesdouyin_url = await self.get_redirect_url(share_url)
            # https://www.iesdouyin.com/share/video/7468908569061100857/?region=CN&mid=0&u_
            match = re.search(r"(slides|video|note)/(\d+)", iesdouyin_url)
            if not match:
                raise ValueError(
                    f"failed to parse video id from iesdouyin url: {iesdouyin_url}, share_url: {share_url}"
                )
            _type, video_id = match.group(1), match.group(2)
            if _type == "slides":
                return await self.parse_slides(video_id)
        for url in [
            iesdouyin_url,
            self._m_douyin_by_video_id(_type, video_id),
            share_url,
        ]:
            try:
                return await self.parse_video(url)
            except Exception as e:
                logger.warning(f"failed to parse video url from {url[:60]}, error: {e}")
                continue
        raise ParseException("failed to parse video url from share_url")

    async def parse_video(self, url: str) -> VideoInfo:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.default_headers, ssl=False) as response:
                response.raise_for_status()
                text = await response.text()
                data = self.format_response(text)
        # 获取图集图片地址
        images = []
        # 如果data含有 images，并且 images 是一个列表
        if "images" in data and isinstance(data["images"], list):
            # 获取每个图片的url_list中的第一个元素，非空时添加到images列表中
            for img in data["images"]:
                if (
                    "url_list" in img
                    and isinstance(img["url_list"], list)
                    and len(img["url_list"]) > 0
                    and len(img["url_list"][0]) > 0
                ):
                    images.append(img["url_list"][0])

        # 获取视频播放地址
        video_url = data["video"]["play_addr"]["url_list"][0].replace("playwm", "play")
        # 如果图集地址不为空时，因为没有视频，上面抖音返回的视频地址无法访问，置空处理
        if len(images) > 0:
            video_url = ""

        # 获取重定向后的mp4视频地址
        # 图集时，视频地址为空，不处理
        video_mp4_url = ""
        if len(video_url) > 0:
            video_mp4_url = await self.get_redirect_url(video_url)

        video_info = VideoInfo(
            video_url=video_mp4_url,
            cover_url=data["video"]["cover"]["url_list"][0],
            title=data["desc"],
            images=images,
            author=VideoAuthor(
                uid=data["author"]["sec_uid"],
                name=data["author"]["nickname"],
                avatar=data["author"]["avatar_thumb"]["url_list"][0],
            ),
        )
        return video_info

    def _iesdouyin_by_video_id(self, _type: str, video_id: str) -> str:
        return f"https://www.iesdouyin.com/share/{_type}/{video_id}"

    def _m_douyin_by_video_id(self, _type: str, video_id: str) -> str:
        return f"https://m.douyin.com/share/{_type}/{video_id}"

    def format_response(self, text: str) -> dict:
        pattern = re.compile(
            pattern=r"window\._ROUTER_DATA\s*=\s*(.*?)</script>",
            flags=re.DOTALL,
        )
        find_res = pattern.search(text)

        if not find_res or not find_res.group(1):
            raise ValueError("parse video json info from html fail")

        json_data = json.loads(find_res.group(1).strip())

        # 获取链接返回json数据进行视频和图集判断,如果指定类型不存在，抛出异常
        # 返回的json数据中，视频字典类型为 video_(id)/page
        VIDEO_ID_PAGE_KEY = "video_(id)/page"
        # 返回的json数据中，视频字典类型为 note_(id)/page
        NOTE_ID_PAGE_KEY = "note_(id)/page"
        if VIDEO_ID_PAGE_KEY in json_data["loaderData"]:
            original_video_info = json_data["loaderData"][VIDEO_ID_PAGE_KEY]["videoInfoRes"]
        elif NOTE_ID_PAGE_KEY in json_data["loaderData"]:
            original_video_info = json_data["loaderData"][NOTE_ID_PAGE_KEY]["videoInfoRes"]
        else:
            raise Exception("failed to parse Videos or Photo Gallery info from json")

        # 如果没有视频信息，获取并抛出异常
        if len(original_video_info["item_list"]) == 0:
            err_detail_msg = "failed to parse video info from HTML"
            if len(filter_list := original_video_info["filter_list"]) > 0:
                err_detail_msg = filter_list[0]["detail_msg"]
            raise Exception(err_detail_msg)

        return original_video_info["item_list"][0]

    async def parse_slides(self, video_id: str) -> VideoInfo:
        url = "https://www.iesdouyin.com/web/api/v2/aweme/slidesinfo/"
        params = {
            "aweme_ids": f"[{video_id}]",
            "request_source": "200",
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 10; VOG-AL00 Build/HUAWEIVOG-AL00) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.88 Mobile Safari/537.36",  # noqa: E501
            "Accept": "application/json, text/plain, */*",
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers, ssl=False) as resp:
                resp.raise_for_status()
                resp = await resp.json()
        detail = resp.get("aweme_details")
        if not detail:
            raise ValueError("链接作品不存在")
        data = detail[0]
        title = data.get("share_info").get("share_desc_info")
        images = []
        dynamic_images = []
        for image in data.get("images"):
            if video := image.get("video"):
                dynamic_images.append(video["play_addr"]["url_list"][0])
            else:
                images.append(image["url_list"][0])

        return VideoInfo(
            title=title,
            video_url="",
            cover_url="",
            images=images,
            dynamic_images=dynamic_images,
        )

    async def parse_video_id(self, video_id: str) -> VideoInfo:
        raise NotImplementedError
