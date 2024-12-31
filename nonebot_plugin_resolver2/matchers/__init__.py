# 使用列表批量导入 matcher
modules = ["bilibili", "douyin", "kugou", "twitter", "ncm", "ytb", "acfun", "tiktok", "weibo", "xiaohongshu"]
for module in modules:
    exec(f"from .{module} import {module}")
    
resolvers = {module: eval(module) for module in modules}

from .filter import *
commands = [enable_resolve, disable_resolve, check_resolve, enable_all_resolve, disable_all_resolve]
