from .bilibili import bilibili
from .douyin import douyin
from .kugou import kugou
from .twitter import twitter
from .ncm import ncm
from .ytb import ytb
from .ac import acfun
from .tiktok import tiktok
from .weibo import weibo
from .kugou import kugou
from .xhs import xhs
from .filter import enable_resolve, disable_resolve, check_resolve

resolvers = {"bilibili": bilibili, "douyin": douyin, "tiktok": tiktok, "acfun": acfun,
              "twitter": twitter, "xhs": xhs, "ytb": ytb, "ncm": ncm, "weibo": weibo, "kugou": kugou}
controllers = [enable_resolve, disable_resolve, check_resolve]
