# 平台禁用功能说明

## 概述

新的统一 resolver 架构支持根据配置动态禁用特定平台的解析功能。

## 实现机制

### 1. 平台映射

在 `matchers/\_\_in## 注意事项

1. **平台名称必须匹配**：配置中使用的平台名称必须与 `MatcherNames` 中定义的名称一致
2. **大小写敏感**：平台名称是大小写敏感的，请使用小写
3. **需要重启生效**：禁用配置在模块导入时读取，修改配置后必须重启机器人才能生效
4. **完全不触发**：被禁用的平台不会参与正则匹配，就像这个平台从未被支持过一样
5. **性能优化**：禁用平台可以减少正则表达式匹配的开销，提高消息处理性能 y` 中定义了关键词到平台名称的映射：

```python
KEYWORD_TO_PLATFORM = {
    "v.douyin": "douyin",
    "douyin": "douyin",
    "xiaohongshu.com": "xiaohongshu",
    "xhslink.com": "xiaohongshu",
    "v.kuaishou.com": "kuaishou",
    "kuaishou": "kuaishou",
    "chenzhongtech": "kuaishou",
    "x.com": "twitter",
    "weibo.com": "weibo",
    "m.weibo.cn": "weibo",
}
```

### 2. 导入时过滤

在模块导入时，根据配置过滤掉被禁用平台的正则表达式：

```python
def _get_enabled_patterns() -> list[tuple[str, str]]:
    """根据配置获取启用的平台正则表达式列表"""
    disabled_platforms = set(rconfig.r_disable_resolvers)

    # 如果未配置小红书 cookie，也禁用小红书
    if not rconfig.r_xhs_ck:
        disabled_platforms.add("xiaohongshu")

    # 过滤掉被禁用的平台
    enabled_patterns = [
        (keyword, pattern)
        for keyword, pattern in ALL_PLATFORM_PATTERNS
        if KEYWORD_TO_PLATFORM.get(keyword) not in disabled_platforms
    ]

    return enabled_patterns

# 创建只包含启用平台的 matcher
resolver = on_keyword_regex(*_get_enabled_patterns())
```

### 3. 性能优化

**关键优势**：被禁用的平台根本不会参与正则表达式匹配，避免了运行时的性能开销。

- ❌ **旧方案**：所有平台都参与匹配 → 匹配成功后检查是否禁用 → 如果禁用则退出
- ✅ **新方案**：只有启用的平台参与匹配 → 直接处理，无需额外检查

这意味着如果禁用了 5 个平台，每次处理消息时就少了 5 次正则表达式匹配的开销。

## 配置方式

### 1. 通过配置文件禁用

在 `.env` 或配置文件中设置：

```ini
# 禁用单个平台
R_DISABLE_RESOLVERS=["douyin"]

# 禁用多个平台
R_DISABLE_RESOLVERS=["douyin", "weibo", "kuaishou"]
```

### 2. 自动禁用（缺少必要配置）

某些平台需要特定的配置才能正常工作，如果缺少这些配置，系统会自动禁用：

- **小红书**：如果未配置 `R_XHS_CK`（小红书 cookie），会自动禁用小红书解析

## 支持的平台名称

根据 `config.py` 中的 `MatcherNames` 类型定义：

- `bilibili` - B 站
- `acfun` - AcFun
- `douyin` - 抖音
- `ytb` - YouTube
- `kuaishou` - 快手
- `twitter` - Twitter/X
- `tiktok` - TikTok
- `weibo` - 微博
- `xiaohongshu` - 小红书

## 启动日志

当平台被禁用时，会在启动时输出警告日志：

```text
[WARNING] 未配置小红书 cookie, 小红书解析已关闭
[WARNING] 已禁用平台解析: douyin, weibo
```

## 注意事项

1. **平台名称必须匹配**：配置中使用的平台名称必须与 `MatcherNames` 中定义的名称一致
2. **大小写敏感**：平台名称是大小写敏感的，请使用小写
3. **即时生效**：禁用配置在机器人启动时加载，修改配置后需要重启机器人
4. **不会报错**：如果 URL 匹配到被禁用的平台，matcher 会静默退出，不会发送任何消息

## 示例

### 示例 1：禁用抖音和微博

```ini
R_DISABLE_RESOLVERS=["douyin", "weibo"]
```

效果：

- 抖音链接（v.douyin.com、douyin.com）不会被解析
- 微博链接（weibo.com、m.weibo.cn）不会被解析
- 其他平台正常工作

### 示例 2：只启用小红书（禁用其他所有平台）

```ini
R_DISABLE_RESOLVERS=["bilibili", "acfun", "douyin", "ytb", "kuaishou", "twitter", "tiktok", "weibo"]
R_XHS_CK="你的小红书cookie"
```

效果：

只有小红书解析功能可用

## 未来扩展

当添加新平台支持时，需要：

1. 在 `PLATFORM_PATTERNS` 中添加正则表达式
2. 在 `KEYWORD_TO_PLATFORM` 中添加映射关系
3. 在 `MatcherNames` 类型中添加平台名称
4. 在处理器中添加对应的解析逻辑
