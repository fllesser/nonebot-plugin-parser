import re
import time
from typing import ClassVar

from httpx import AsyncClient, Cookies
import msgspec

from .base import BaseParser, ParseException, Platform, PlatformEnum


class WeiBoParser(BaseParser):
    # 平台信息
    platform: ClassVar[Platform] = Platform(name=PlatformEnum.weibo, display_name="微博")

    # URL 正则表达式模式（keyword, pattern）
    patterns: ClassVar[list[tuple[str, str]]] = [
        ("weibo.com", r"https?://(?:www|m|video)?\.?weibo\.com/[A-Za-z\d._?%&+\-=/#@:]+"),
        ("m.weibo.cn", r"https?://m\.weibo\.cn/[A-Za-z\d._?%&+\-=/#@]+"),
        ("mapp.api.weibo", r"https?://mapp\.api\.weibo\.cn/[A-Za-z\d._?%&+\-=/#@]+"),
    ]

    def __init__(self):
        super().__init__()
        extra_headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",  # noqa: E501
            "referer": "https://weibo.com/",
        }
        self.headers.update(extra_headers)

    async def parse(self, keyword: str, searched: re.Match[str]):
        # 从匹配对象中获取原始URL
        url = searched.group(0)
        if "mapp.api.weibo" in url:
            # ​​​https://mapp.api.weibo.cn/fx/8102df2b26100b2e608e6498a0d3cfe2.html
            url = await self.get_redirect_url(url)
        # https://video.weibo.com/show?fid=1034:5145615399845897
        if matched := re.search(r"https://video\.weibo\.com/show\?fid=(\d+:\d+)", url):
            return await self.parse_fid(matched.group(1))
        # https://m.weibo.cn/detail/4976424138313924
        elif matched := re.search(r"m\.weibo\.cn(?:/detail|/status)?/([A-Za-z\d]+)", url):
            weibo_id = matched.group(1)
        # https://weibo.com/tv/show/1034:5007449447661594?mid=5007452630158934
        elif matched := re.search(r"mid=([A-Za-z\d]+)", url):
            weibo_id = self._mid2id(matched.group(1))
        # https://weibo.com/1707895270/5006106478773472
        elif matched := re.search(r"(?<=weibo.com/)[A-Za-z\d]+/([A-Za-z\d]+)", url):
            weibo_id = matched.group(1)
        else:
            raise ParseException("无法获取到微博的 id")

        return await self.parse_weibo_id(weibo_id)

    async def parse_fid(self, fid: str):
        """
        解析带 fid 的微博视频
        """

        req_url = f"https://h5.video.weibo.com/api/component?page=/show/{fid}"
        headers = {
            "Referer": f"https://h5.video.weibo.com/show/{fid}",
            "Content-Type": "application/x-www-form-urlencoded",
            **self.headers,
        }
        post_content = 'data={"Component_Play_Playinfo":{"oid":"' + fid + '"}}'

        async with AsyncClient(headers=headers, timeout=self.timeout) as client:
            response = await client.post(req_url, content=post_content)
            response.raise_for_status()
            json_data = response.json()

        data = json_data.get("data", {}).get("Component_Play_Playinfo", {})
        if not data:
            raise ParseException("Component_Play_Playinfo 数据为空")
        # 提取作者
        user = data.get("reward", {}).get("user", {})
        author_name, avatar, description = (
            user.get("name", "未知"),
            user.get("profile_image_url"),
            user.get("description"),
        )
        author = self.create_author(author_name, avatar, description)

        # 提取标题和文本
        title, text = data.get("title", ""), data.get("text", "")
        if text:
            text = re.sub(r"<[^>]*>", "", text)
            text = text.replace("\n\n", "").strip()

        # 获取封面
        cover_url = data.get("cover_image")
        if cover_url:
            cover_url = "https:" + cover_url

        # 获取视频下载链接
        contents = []
        video_url_dict = data.get("urls")
        if video_url_dict and isinstance(video_url_dict, dict):
            # stream_url码率最低，urls中第一条码率最高
            first_mp4_url: str = next(iter(video_url_dict.values()))
            video_url = "https:" + first_mp4_url
        else:
            video_url = data.get("stream_url")

        if video_url:
            contents.append(self.create_video_content(video_url, cover_url))

        # 时间戳
        timestamp = data.get("real_date")

        return self.result(
            title=title,
            text=text,
            author=author,
            contents=contents,
            timestamp=timestamp,
        )

    async def parse_weibo_id(self, weibo_id: str):
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
            **self.headers,
        }

        # 加时间戳参数，减少被缓存/规则命中的概率
        ts = int(time.time() * 1000)
        url = f"https://m.weibo.cn/statuses/show?id={weibo_id}&_={ts}"

        # 关键：不带 cookie、不跟随重定向（避免二跳携 cookie）
        async with AsyncClient(
            headers=headers,
            timeout=self.timeout,
            follow_redirects=False,
            cookies=Cookies(),
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

        return self.build_weibo_data(weibo_data)

    def build_weibo_data(self, data: "WeiboData"):
        contents = []

        # 添加视频内容
        if video_url := data.video_url:
            cover_url = data.cover_url
            contents.append(self.create_video_content(video_url, cover_url))

        # 添加图片内容
        if image_urls := data.image_urls:
            contents.extend(self.create_image_contents(image_urls))

        # 构建作者
        author = self.create_author(data.display_name, data.user.profile_image_url)
        repost = None
        if data.retweeted_status:
            repost = self.build_weibo_data(data.retweeted_status)

        return self.result(
            title=data.title,
            text=data.text_content,
            author=author,
            contents=contents,
            timestamp=data.timestamp,
            url=data.url,
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
        from math import ceil

        mid = str(mid)[::-1]  # 反转输入字符串
        size = ceil(len(mid) / 7)  # 计算每个块的大小
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


class PagePic(Struct):
    url: str


class PageInfo(Struct):
    title: str | None = None
    urls: Urls | None = None
    page_pic: PagePic | None = None


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
    created_at: str
    """发布时间 格式: `Thu Oct 02 14:39:33 +0800 2025`"""

    status_title: str | None = None
    pics: list[Pic] | None = None
    page_info: PageInfo | None = None
    retweeted_status: "WeiboData | None" = None  # 转发微博

    @property
    def title(self) -> str | None:
        return self.page_info.title if self.page_info else None

    @property
    def display_name(self) -> str:
        return self.user.screen_name

    @property
    def text_content(self) -> str:
        # 将 <br /> 转换为 \n
        text = self.text.replace("<br />", "\n")
        # 去除 html 标签
        text = re.sub(r"<[^>]*>", "", text)
        return text

    @property
    def cover_url(self) -> str | None:
        if self.page_info is None:
            return None
        if self.page_info.page_pic:
            return self.page_info.page_pic.url
        return None

    @property
    def video_url(self) -> str | None:
        if self.page_info and self.page_info.urls:
            return self.page_info.urls.get_video_url()
        return None

    @property
    def image_urls(self) -> list[str]:
        if self.pics:
            return [x.large.url for x in self.pics]
        return []

    @property
    def url(self) -> str:
        return f"https://weibo.com/{self.user.id}/{self.bid}"

    @property
    def timestamp(self) -> int:
        return int(time.mktime(time.strptime(self.created_at, "%a %b %d %H:%M:%S %z %Y")))


class WeiboResponse(Struct):
    ok: int
    data: WeiboData
