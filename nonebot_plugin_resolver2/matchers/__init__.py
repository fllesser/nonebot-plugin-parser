# 使用列表批量导入 matcher
modules = ["bilibili", "douyin", "kugou", "twitter", "ncm", "ytb", "acfun", "tiktok", "weibo", "xiaohongshu"]
for module in modules:
    exec(f"from .{module} import {module}")
    
resolvers = {module: eval(module) for module in modules}
