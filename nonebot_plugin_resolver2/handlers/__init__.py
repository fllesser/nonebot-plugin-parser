# 使用列表批量导入 matcher
modules = ["bilibili", "douyin", "kugou", "twitter", "ncm", "ytb", "acfun", "tiktok", "weibo", "xhs"]
for module in modules:
    exec(f"from .{module} import {module}")

# import other matcher
from .filter import enable_resolve, disable_resolve, check_resolve

# 定义 resolvers 和 controllers
resolvers = {module: eval(module) for module in modules}
controllers = [enable_resolve, disable_resolve, check_resolve]
