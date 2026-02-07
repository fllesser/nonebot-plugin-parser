from re import Match
from time import time
from uuid import uuid4
from typing import ClassVar

from bs4 import Tag, BeautifulSoup
from httpx import Cookies, AsyncClient

from . import common, article
from ..base import Platform, BaseParser, PlatformEnum, ParseException, handle
from ..data import MediaContent


class WeiBoParser(BaseParser):
    platform: ClassVar[Platform] = Platform(name=PlatformEnum.WEIBO, display_name="微博")

    def __init__(self):
        super().__init__()
        extra_headers = {
            "accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,"
                "image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9"
            ),
            "referer": "https://weibo.com/",
        }
        self.headers.update(extra_headers)

    # https://weibo.com/tv/show/1034:5007449447661594?mid=5007452630158934
    @handle("weibo.com/tv", r"weibo\.com/tv/show/\d{4}:\d+\?mid=(?P<mid>\d+)")
    async def _parse_weibo_tv(self, searched: Match[str]):
        mid = str(searched.group("mid"))
        weibo_id = self._mid2id(mid)
        return await self.parse_weibo_id(weibo_id)

    # https://video.weibo.com/show?fid=1034:5145615399845897
    @handle("video.weibo", r"video\.weibo\.com/show\?fid=(?P<fid>\d+:\d+)")
    async def _parse_video_weibo(self, searched: Match[str]):
        fid = str(searched.group("fid"))
        return await self.parse_fid(fid)

    # https://m.weibo.cn/status/5234367615996775
    # https://m.weibo.cn/detail/4976424138313924
    # https://m.weibo.cn/status/Q0KtXh6z2
    # https://m.weibo.cn/{uid}\d+/{wid}[0-9a-zA-Z]+/qq
    @handle("m.weibo.cn", r"weibo\.cn/(?:status|detail|\d+)/(?P<wid>[0-9a-zA-Z]+)")
    # https://weibo.com/7207262816/P5kWdcfDe
    @handle("weibo.com", r"weibo\.com/\d+/(?P<wid>[0-9a-zA-Z]+)")
    async def _parse_m_weibo_cn(self, searched: Match[str]):
        wid = str(searched.group("wid"))
        return await self.parse_weibo_id(wid)

    # https://mapp.api.weibo.cn/fx/233911ddcc6bffea835a55e725fb0ebc.html
    @handle("mapp.api.weibo", r"mapp\.api\.weibo\.cn/fx/[0-9A-Za-z]+\.html")
    async def _parse_mapp_api_weibo(self, searched: Match[str]):
        url = f"https://{searched.group(0)}"
        return await self.parse_with_redirect(url)

    # https://weibo.com/ttarticle/p/show?id=2309404962180771742222
    # https://weibo.com/ttarticle/x/m/show#/id=2309404962180771742222
    @handle("weibo.com/ttarticle", r"id=(?P<id>\d+)")
    # https://card.weibo.com/article/m/show/id/2309404962180771742222
    @handle("weibo.com/article", r"/id/(?P<id>\d+)")
    async def _parse_article(self, searched: Match[str]):
        _id = searched.group("id")
        return await self.parse_article(_id)

    async def parse_article(self, _id: str):
        url = "https://card.weibo.com/article/m/aj/detail"
        params = {
            "_rid": str(uuid4()),
            "id": _id,
            "_t": int(time() * 1000),
        }

        async with AsyncClient(
            headers=self.headers,
            timeout=self.timeout,
        ) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()

        detail = article.decoder.decode(response.content)

        if detail.msg != "success":
            raise ParseException("请求失败")

        data = detail.data

        soup = BeautifulSoup(data.content, "html.parser")
        contents: list[MediaContent] = []
        text_buffer: list[str] = []

        for element in soup.find_all(["p", "img"]):
            if not isinstance(element, Tag):
                continue

            if element.name == "p":
                text = element.get_text(strip=True)
                # 去除零宽空格
                text = text.replace("\u200b", "")
                if text:
                    text_buffer.append(text)
            elif element.name == "img":
                src = element.get("src")
                if isinstance(src, str):
                    text = "\n\n".join(text_buffer)
                    contents.append(self.create_graphics_content(src, text=text))
                    text_buffer.clear()

        author = self.create_author(
            data.userinfo.screen_name,
            data.userinfo.profile_image_url,
        )

        end_text = "\n\n".join(text_buffer) if text_buffer else None

        return self.result(
            url=data.url,
            title=data.title,
            author=author,
            timestamp=data.create_at_unix,
            text=end_text,
            contents=contents,
        )

    async def parse_fid(self, fid: str):
        """解析 show (带 fid)"""
        from . import show

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

        data = show.decoder.decode(response.content).data
        play_info = data.Component_Play_Playinfo
        author = self.create_author(
            play_info.name,
            play_info.avatar,
            play_info.description,
        )
        video_content = self.create_video_content(
            play_info.video_url,
            play_info.cover_url,
        )

        return self.result(
            title=play_info.title,
            text=play_info.text,
            author=author,
            contents=[video_content],
            timestamp=play_info.real_date,
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
        ts = int(time() * 1000)
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
                    raise ParseException(f"被风控拦截({response.status_code}), 可尝试更换 UA/Referer 或稍后重试")
                raise ParseException(f"获取数据失败 {response.status_code} {response.reason_phrase}")

            ctype = response.headers.get("content-type", "")
            if "application/json" not in ctype:
                raise ParseException(f"获取数据失败 content-type is not application/json (got: {ctype})")

        weibo_data = common.decoder.decode(response.content).data

        return self._collect_result(weibo_data)

    def _collect_result(self, data: common.WeiboData):
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
            repost = self._collect_result(data.retweeted_status)

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
