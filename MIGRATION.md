# 迁移指南

## 从旧版本迁移到统一 Resolver

本指南帮助你从使用独立 matchers 的旧版本迁移到使用统一 resolver 的新版本。

## 破坏性变更

### 已删除的 Matchers

以下 matchers 已被删除并合并到统一的 `resolver` 中：

- `matchers.acfun`
- `matchers.bilibili`
- `matchers.douyin`
- `matchers.kuaishou`
- `matchers.tiktok`
- `matchers.twitter`
- `matchers.weibo`
- `matchers.xiaohongshu`
- `matchers.ytb`

### 如果你的代码直接导入了这些 matchers

**之前（不再可用）：**

```python
from nonebot_plugin_resolver2.matchers import douyin, bilibili, xiaohongshu

# 这些导入现在会报错
```

**现在（推荐）：**

```python
from nonebot_plugin_resolver2.matchers import resolver

# 统一使用 resolver
# resolver 会自动识别和处理所有支持的平台
```

## 自动迁移

好消息是，**大多数用户不需要修改任何代码**！

如果你只是安装并使用了这个插件，而没有在自己的代码中导入特定的 matchers，那么：

1. ✅ **无需任何修改** - 插件会自动使用新的统一 resolver
2. ✅ **功能保持一致** - 所有平台的解析功能都保持不变
3. ✅ **体验保持一致** - 用户发送链接的方式和收到的响应格式都不变

## 需要手动迁移的情况

### 场景 1：直接导入并使用了特定 matcher

如果你的代码中有类似这样的导入：

```python
# ❌ 旧代码 - 不再可用
from nonebot_plugin_resolver2.matchers import douyin

@douyin.handle()
async def custom_handler():
    # 自定义处理逻辑
    pass
```

**解决方案：**

```python
# ✅ 新代码 - 使用统一的 resolver
from nonebot_plugin_resolver2.matchers import resolver

@resolver.handle()
async def custom_handler():
    # 自定义处理逻辑
    # 可以通过检查 URL 来判断平台类型
    pass
```

### 场景 2：通过 resolvers 字典访问特定 matcher

```python
# ❌ 旧代码 - 不再可用
from nonebot_plugin_resolver2.matchers import resolvers

douyin_matcher = resolvers["douyin"]
```

**解决方案：**

```python
# ✅ 新代码 - 直接使用统一的 resolver
from nonebot_plugin_resolver2.matchers import resolver

my_resolver = resolver
```

> 注：`resolvers` 字典已被移除，请直接导入 `resolver`。

## 平台支持

统一 resolver 目前支持以下平台：

- ✅ 抖音 (Douyin)
- ✅ 小红书 (Xiaohongshu)
- ✅ 快手 (Kuaishou)
- ✅ 微博 (Weibo)
- ⏳ Twitter/X (开发中)
- ⏳ 哔哩哔哩 (Bilibili) - 开发中
- ⏳ AcFun - 开发中
- ⏳ TikTok - 开发中
- ⏳ YouTube - 开发中

> 注：标记为"开发中"的平台目前使用临时方案，功能正常但实现方式将来会优化。

## 优势

使用统一 resolver 的优势：

1. **更简洁的代码**：只需要导入一个 resolver 而不是多个
2. **更容易维护**：所有平台的渲染逻辑统一，bug 修复更简单
3. **更容易扩展**：添加新平台支持更简单
4. **更一致的体验**：所有平台的输出格式统一

## 常见问题

### Q: 我的插件升级后无法正常工作怎么办？

A: 如果你遇到问题：

1. 检查是否有直接导入特定 matcher 的代码
2. 查看错误日志，定位问题所在
3. 参考本指南进行迁移
4. 如果问题依然存在，请提交 issue

### Q: 新版本是否支持所有旧版本支持的平台？

A: 是的，所有平台的支持都保留了。部分平台（如 Bilibili）的实现方式正在优化中，但功能完全可用。

### Q: 性能是否有影响？

A: 统一 resolver 的性能与旧版本基本相同，在某些场景下甚至更好（减少了代码重复和不必要的判断）。

### Q: 可以同时使用旧版本和新版本吗？

A: 不可以。旧的 matchers 已经被删除。但是你可以：

1. 锁定旧版本号（不推荐）
2. 按照本指南迁移到新版本（推荐）

## 需要帮助？

如果你在迁移过程中遇到问题：

1. 查看 [REFACTOR.md](./REFACTOR.md) 了解详细的重构说明
2. 查看项目的 [issue 页面](https://github.com/he0119/nonebot-plugin-resolver2/issues)
3. 提交新的 issue 描述你的问题

## 版本说明

- **旧版本**：使用独立的 matchers（acfun.py, bilibili.py 等）
- **新版本**：使用统一的 resolver（resolver.py）
- **迁移时间**：2025 年 9 月 30 日

---

感谢你使用 nonebot-plugin-resolver2！
