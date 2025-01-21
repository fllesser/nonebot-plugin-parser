from nonebot.matcher import Matcher
from .bilibili import bilibili
from .acfun import acfun
from .douyin import douyin
from .ytb import ytb
from .kugou import kugou
from .ncm import ncm
from .twitter import twitter
from .tiktok import tiktok
from .weibo import weibo
from .xiaohongshu import xiaohongshu

resolvers: dict[str, Matcher] = {
    "bilibili": bilibili,
    "acfun": acfun,
    "douyin": douyin,
    "ytb": ytb,
    "kugou": kugou,
    "ncm": ncm,
    "twitter": twitter,
    "tiktok": tiktok,
    "weibo": weibo,
    "xiaohongshu": xiaohongshu,
}
