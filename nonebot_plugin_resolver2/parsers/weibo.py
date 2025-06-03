import math
import re

import aiohttp

from ..constant import COMMON_HEADER
from ..exception import ParseException
from .data import ParseResult


class WeiBoParser:
    async def parse_share_url(self, share_url: str) -> ParseResult:
        """解析微博分享链接"""
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
        # 无法获取到id则返回失败信息
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
        async with aiohttp.ClientSession() as session:
            async with session.post(req_url, headers=headers, data=post_content) as response:
                response.raise_for_status()
                json_data = await response.json()
        data = json_data["data"]["Component_Play_Playinfo"]

        video_url = data["stream_url"]
        if len(data["urls"]) > 0:
            # stream_url码率最低，urls中第一条码率最高
            _, first_mp4_url = next(iter(data["urls"].items()))
            video_url = f"https:{first_mp4_url}"

        video_info = ParseResult(
            video_url=video_url,
            cover_url="https:" + data["cover_image"],
            title=data["title"],
            author=data["author"],
            # author=Author(
            #     # uid=str(data["user"]["id"]),
            #     name=data["author"],
            #     avatar="https:" + data["avatar"],
            # ),
        )
        return video_info

    async def parse_weibo_id(self, weibo_id: str) -> ParseResult:
        """解析微博 id"""
        headers = {
            "accept": "application/json",
            "cookie": "_T_WM=40835919903; WEIBOCN_FROM=1110006030; MLOGIN=0; XSRF-TOKEN=4399c8",
            "Referer": f"https://m.weibo.cn/detail/{weibo_id}",
            **COMMON_HEADER,
        }

        # 请求数据
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://m.weibo.cn/statuses/show?id={weibo_id}", headers=headers) as resp:
                if resp.status != 200:
                    raise ParseException(f"获取数据失败 {resp.status} {resp.reason}")
                if "application/json" not in resp.headers.get("content-type", ""):
                    raise ParseException("获取数据失败 content-type is not application/json")
                resp = await resp.json()

        weibo_data = resp["data"]
        text, status_title, source, region_name, pics, page_info = (
            weibo_data.get(key)
            for key in [
                "text",
                "status_title",
                "source",
                "region_name",
                "pics",
                "page_info",
            ]
        )
        video_url = ""
        # 图集
        if pics:
            pics = [x["large"]["url"] for x in pics]
        else:
            videos = page_info.get("urls")
            video_url: str = videos.get("mp4_720p_mp4") or videos.get("mp4_hd_mp4") if videos else ""

        return ParseResult(
            author=source,
            cover_url="",
            title=f"{re.sub(r'<[^>]+>', '', text)}\n{status_title}\n{source}\t{region_name if region_name else ''}",
            video_url=video_url,
            pic_urls=pics,
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
