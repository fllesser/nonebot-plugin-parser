# 重构说明

## 概述

本次重构将多个独立的 matchers 合并为一个统一的 resolver，并统一了 parsers 的输出格式。

⚠️ **重要变更**：所有旧的独立 matchers（acfun.py、bilibili.py、douyin.py 等）已被删除，现在只使用统一的 `resolver`。

## 主要变更

### 1. 数据结构统一 (`parsers/data.py`)

- **ParseResult** 数据类现在同时支持 URL 和文件路径：
  - 添加了 `platform` 字段（平台名称，如 "抖音"、"哔哩哔哩"等）
  - `cover_url` 和 `cover_path` 可以同时存在
  - `AudioContent`、`VideoContent`、`ImageContent` 都支持 URL 和 Path 两种形式
  - 添加了 `extra_info` 字段用于存储额外信息（如视频时长、AI 总结等）

### 2. Parser 层改进

所有 parser 现在都包含：

- `platform` 属性，用于标识平台名称
- `parse_and_download()` 方法（部分实现），直接返回包含下载文件路径的 ParseResult

已完成的 parsers：

- ✅ `DouyinParser` - 实现了 `parse_and_download()` 方法
- ✅ `XiaoHongShuParser` - 添加了 `platform` 字段
- ✅ `KuaishouParser` - 添加了 `platform` 字段
- ✅ `WeiBoParser` - 添加了 `platform` 字段

待完成的 parsers（目前在统一 matcher 中临时处理）：

- ⏳ `BilibiliParser`
- ⏳ `TwitterParser`
- ⏳ `AcfunParser`
- ⏳ `TiktokParser`
- ⏳ `YtbParser`

### 3. 统一的 Matcher (`matchers/resolver.py`)

新增了统一的 `resolver` matcher：

**功能特性：**

- 支持多个平台的正则匹配（抖音、小红书、快手、微博、Twitter 等）
- 统一的解析处理流程
- 统一的 `Renderer` 渲染器，处理所有平台的输出

**渲染器特性：**

- 根据 `ParseResult` 的内容类型自动选择渲染方式
- 支持视频、图片、音频三种内容类型
- 自动处理封面、标题、作者等元信息
- 自动处理额外信息（如 AI 总结、视频时长等）

### 4. 清理旧代码 ✅

**已删除的文件：**

- ❌ `matchers/acfun.py`
- ❌ `matchers/bilibili.py`
- ❌ `matchers/douyin.py`
- ❌ `matchers/kuaishou.py`
- ❌ `matchers/tiktok.py`
- ❌ `matchers/twitter.py`
- ❌ `matchers/weibo.py`
- ❌ `matchers/xiaohongshu.py`
- ❌ `matchers/ytb.py`

**保留的文件：**

- ✅ `matchers/resolver.py` - 统一的解析器（处理路由和调用 parser）
- ✅ `matchers/render.py` - 统一的渲染器（处理消息渲染）
- ✅ `matchers/helper.py` - 辅助工具类
- ✅ `matchers/preprocess.py` - 预处理和规则定义
- ✅ `matchers/filter.py` - 消息过滤器

**模块职责：**

```
matchers/
├── __init__.py          # 导出 resolver
├── resolver.py          # 路由：URL 匹配 → 调用 Parser → 调用 Renderer
├── render.py            # 渲染：ParseResult → 消息段 → 发送
├── helper.py            # 工具：消息段构建、转发消息等
├── preprocess.py        # 规则：关键词匹配、URL提取等
└── filter.py            # 过滤：群组黑名单等
```

## 使用示例

### 使用统一的 resolver

```python
from nonebot_plugin_resolver2.matchers import resolver

# resolver 会自动匹配支持的平台并解析
# 用户只需发送包含平台链接的消息即可
```

### 为 parser 添加 parse_and_download 方法

```python
class YourParser:
    def __init__(self):
        self.platform = "平台名称"

    async def parse_and_download(self, url: str) -> ParseResult:
        # 1. 解析 URL 获取元数据
        result = await self.parse_url(url)

        # 2. 下载封面
        if result.cover_url:
            result.cover_path = await DOWNLOADER.download_img(result.cover_url)

        # 3. 下载内容
        if isinstance(result.content, VideoContent) and result.content.video_url:
            result.content.video_path = await DOWNLOADER.download_video(
                result.content.video_url
            )
        # ... 处理其他内容类型

        return result
```

## 架构优势

1. **代码复用**：渲染逻辑统一，减少重复代码
2. **易于维护**：新增平台只需实现对应的 parser，无需编写 matcher
3. **统一体验**：所有平台的输出格式一致
4. **职责清晰**：
   - Parser 负责解析和下载
   - Renderer 负责渲染
   - Matcher 负责路由

## 后续计划

1. ✅ ~~逐步移除旧的独立 matchers~~ - **已完成**
2. 为剩余的 parsers 实现 `parse_and_download()` 方法
   - ⏳ BilibiliParser（包括直播、动态、专栏等特殊情况）
   - ⏳ TwitterParser
   - ⏳ AcfunParser
   - ⏳ TiktokParser
   - ⏳ YtbParser
3. 添加更完善的错误处理和日志记录
4. 添加单元测试验证重构正确性
5. 更新使用文档和示例

## 注意事项

- ⚠️ **破坏性变更**：所有旧的 matchers 已被删除，如果有外部代码直接引用了这些 matchers，需要更新为使用 `resolver`
- 当前实现中，部分平台（如 Bilibili、Twitter、AcFun、TikTok、Ytb）还在使用临时下载方案
- 建议在生产环境中先进行充分测试
- 如需支持新平台，只需：
  1. 在 `parsers/` 下创建对应的 parser
  2. 实现 `parse_and_download()` 方法
  3. 在 `matchers/resolver.py` 的 `PLATFORM_PATTERNS` 中添加正则表达式
  4. 在 resolver 的处理器中添加对应的判断逻辑
