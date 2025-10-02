import math
import re
import time
from typing import ClassVar

import httpx
import msgspec

from ..constants import COMMON_HEADER, COMMON_TIMEOUT
from ..download import DOWNLOADER
from ..exception import ParseException
from ..parsers.utils import get_redirect_url
from .base import BaseParser
from .data import Author, Content, ImageContent, ParseResult, Platform, VideoContent


class WeiBoParser(BaseParser):
    # 平台信息
    platform: ClassVar[Platform] = Platform(name="weibo", display_name="微博")

    # URL 正则表达式模式（keyword, pattern）
    patterns: ClassVar[list[tuple[str, str]]] = [
        ("weibo.com", r"https?://(?:www|m|video)?\.?weibo\.com/[A-Za-z\d._?%&+\-=/#@:]+"),
        ("m.weibo.cn", r"https?://m\.weibo\.cn/[A-Za-z\d._?%&+\-=/#@]+"),
        ("mapp.api.weibo", r"https?://mapp\.api\.weibo\.cn/[A-Za-z\d._?%&+\-=/#@]+"),
    ]

    def __init__(self):
        self.ext_headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",  # noqa: E501
            "referer": "https://weibo.com/",
        }

    async def parse(self, matched: re.Match[str]) -> ParseResult:
        """解析 URL 获取内容信息并下载资源

        Args:
            matched: 正则表达式匹配对象，由平台对应的模式匹配得到

        Returns:
            ParseResult: 解析结果（已下载资源，包含 Path）

        Raises:
            ParseException: 解析失败时抛出
        """
        # 从匹配对象中获取原始URL
        url = matched.group(0)
        return await self.parse_share_url(url)

    async def parse_share_url(self, share_url: str) -> ParseResult:
        """解析微博分享链接（内部方法）"""
        if "mapp.api.weibo" in share_url:
            # ​​​https://mapp.api.weibo.cn/fx/8102df2b26100b2e608e6498a0d3cfe2.html
            share_url = await get_redirect_url(share_url)
        # https://video.weibo.com/show?fid=1034:5145615399845897
        if matched := re.search(r"https://video\.weibo\.com/show\?fid=(\d+:\d+)", share_url):
            return await self.parse_fid(matched.group(1))
        # https://m.weibo.cn/detail/4976424138313924
        elif matched := re.search(r"m\.weibo\.cn(?:/detail|/status)?/([A-Za-z\d]+)", share_url):
            weibo_id = matched.group(1)
        # https://weibo.com/tv/show/1034:5007449447661594?mid=5007452630158934
        elif matched := re.search(r"mid=([A-Za-z\d]+)", share_url):
            weibo_id = self._mid2id(matched.group(1))
        # https://weibo.com/1707895270/5006106478773472
        elif matched := re.search(r"(?<=weibo.com/)[A-Za-z\d]+/([A-Za-z\d]+)", share_url):
            weibo_id = matched.group(1)
        else:
            raise ParseException("无法获取到微博的 id")

        return await self.parse_weibo_id(weibo_id)

    async def parse_fid(self, fid: str) -> ParseResult:
        """
        解析带 fid 的微博视频
        """
        req_url = f"https://h5.video.weibo.com/api/component?page=/show/{fid}"
        headers = {
            "Referer": f"https://h5.video.weibo.com/show/{fid}",
            "Content-Type": "application/x-www-form-urlencoded",
            **COMMON_HEADER,
        }
        post_content = 'data={"Component_Play_Playinfo":{"oid":"' + fid + '"}}'
        async with httpx.AsyncClient(headers=headers, timeout=COMMON_TIMEOUT) as client:
            response = await client.post(req_url, content=post_content)
            response.raise_for_status()
            json_data = response.json()
        data = json_data["data"]["Component_Play_Playinfo"]

        video_url = data["stream_url"]
        if len(data["urls"]) > 0:
            # stream_url码率最低，urls中第一条码率最高
            _, first_mp4_url = next(iter(data["urls"].items()))
            video_url = f"https:{first_mp4_url}"

        # 下载封面和视频
        cover_url = "https:" + data["cover_image"]
        cover_path = await DOWNLOADER.download_img(cover_url, ext_headers=self.ext_headers)
        video_path = await DOWNLOADER.download_video(video_url, ext_headers=self.ext_headers)

        extra = {}
        if cover_path:
            extra["cover_path"] = cover_path

        return ParseResult(
            title=data["title"],
            platform=self.platform,
            content="",
            author=Author(name=data["author"]) if data.get("author") else None,
            contents=[VideoContent(video_path)],
            extra=extra,
        )

    async def parse_weibo_id(self, weibo_id: str) -> ParseResult:
        """解析微博 id (无 Cookie + 伪装 XHR + 不跟随重定向)"""
        headers = {
            "accept": "application/json, text/plain, */*",
            "referer": f"https://m.weibo.cn/detail/{weibo_id}",
            "origin": "https://m.weibo.cn",
            "x-requested-with": "XMLHttpRequest",
            "mweibo-pwa": "1",
            "sec-fetch-site": "same-origin",
            "sec-fetch-mode": "cors",
            "sec-fetch-dest": "empty",
            **COMMON_HEADER,
        }

        # 加时间戳参数，减少被缓存/规则命中的概率
        ts = int(time.time() * 1000)
        url = f"https://m.weibo.cn/statuses/show?id={weibo_id}&_={ts}"

        # 关键：不带 cookie、不跟随重定向（避免二跳携 cookie）
        async with httpx.AsyncClient(
            headers=headers,
            timeout=COMMON_TIMEOUT,
            follow_redirects=False,
            cookies=httpx.Cookies(),
            trust_env=False,
        ) as client:
            response = await client.get(url)
            if response.status_code != 200:
                if response.status_code in (403, 418):
                    raise ParseException(f"被风控拦截（{response.status_code}），可尝试更换 UA/Referer 或稍后重试")
                raise ParseException(f"获取数据失败 {response.status_code} {response.reason_phrase}")

            ctype = response.headers.get("content-type", "")
            if "application/json" not in ctype:
                raise ParseException(f"获取数据失败 content-type is not application/json (got: {ctype})")

        # 用 bytes 更稳，避免编码歧义
        weibo_data = msgspec.json.decode(response.content, type=WeiboResponse).data

        return await self._parse_weibodata(weibo_data)

    async def _parse_weibodata(self, data: "WeiboData") -> ParseResult:
        """解析 WeiboData 对象，返回 ParseResult"""
        repost = None
        if data.retweeted_status:
            repost = await self._parse_weibodata(data.retweeted_status)

        # 下载内容
        contents: list[Content] = []
        if video_url := data.video_url:
            video_path = await DOWNLOADER.download_video(video_url, ext_headers=self.ext_headers)
            contents.append(VideoContent(video_path))

        if pic_urls := data.pic_urls:
            pic_paths = await DOWNLOADER.download_imgs_without_raise(pic_urls, ext_headers=self.ext_headers)
            contents.extend(ImageContent(path) for path in pic_paths)

        return ParseResult(
            platform=self.platform,
            content=data.text_content,
            author=Author(name=data.display_name, avatar=data.user.profile_image_url),
            contents=contents,
            url=f"https://weibo.com/{data.user.id}/{data.bid}",
            repost=repost,
        )

    def _base62_encode(self, number: int) -> str:
        """将数字转换为 base62 编码"""
        alphabet = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
        if number == 0:
            return "0"

        result = ""
        while number > 0:
            result = alphabet[number % 62] + result
            number //= 62

        return result

    def _mid2id(self, mid: str) -> str:
        """将微博 mid 转换为 id"""
        mid = str(mid)[::-1]  # 反转输入字符串
        size = math.ceil(len(mid) / 7)  # 计算每个块的大小
        result = []

        for i in range(size):
            # 对每个块进行处理并反转
            s = mid[i * 7 : (i + 1) * 7][::-1]
            # 将字符串转为整数后进行 base62 编码
            s = self._base62_encode(int(s))
            # 如果不是最后一个块并且长度不足4位，进行左侧补零操作
            if i < size - 1 and len(s) < 4:
                s = "0" * (4 - len(s)) + s
            result.append(s)

        result.reverse()  # 反转结果数组
        return "".join(result)  # 将结果数组连接成字符串


from msgspec import Struct


class LargeInPic(Struct):
    url: str


class Pic(Struct):
    url: str
    large: LargeInPic


class Urls(Struct):
    mp4_720p_mp4: str | None = None
    mp4_hd_mp4: str | None = None
    mp4_ld_mp4: str | None = None

    def get_video_url(self) -> str | None:
        return self.mp4_720p_mp4 or self.mp4_hd_mp4 or self.mp4_ld_mp4 or None


class PageInfo(Struct):
    urls: Urls | None = None


class User(Struct):
    id: int
    screen_name: str
    """用户昵称"""
    profile_image_url: str
    """头像"""


class WeiboData(Struct):
    user: User
    text: str
    # source: str  # 如 微博网页版
    # region_name: str | None = None

    bid: str

    status_title: str | None = None
    pics: list[Pic] | None = None
    page_info: PageInfo | None = None
    retweeted_status: "WeiboData | None" = None  # 转发微博

    @property
    def display_name(self) -> str:
        return self.user.screen_name

    @property
    def text_content(self) -> str:
        # 去除 html 标签
        return re.sub(r"<[^>]*>", "", self.text)

    @property
    def video_url(self) -> str | None:
        if self.page_info and self.page_info.urls:
            return self.page_info.urls.get_video_url()
        if self.retweeted_status and self.retweeted_status.page_info and self.retweeted_status.page_info.urls:
            return self.retweeted_status.page_info.urls.get_video_url()
        return None

    @property
    def pic_urls(self) -> list[str]:
        if self.pics:
            return [x.large.url for x in self.pics]
        if self.retweeted_status and self.retweeted_status.pics:
            return [x.large.url for x in self.retweeted_status.pics]
        return []


class WeiboResponse(Struct):
    ok: int
    data: WeiboData
