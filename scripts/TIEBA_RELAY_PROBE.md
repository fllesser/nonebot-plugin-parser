# 百度贴吧 PC 帖页 Relay 摸底（`p/10787181972`）

探测时间：2026-06-14  
工具：Browser Relay（Chrome 已登录会话）+ `curl_cffi` 裸请求对比

## 链接形态

| 类型 | 示例 |
|------|------|
| 帖页 | `https://tieba.baidu.com/p/{thread_id}` |
| 带参 | `?fr=frs` |
| 楼主帖 | `?tab=只看楼主`（URL 编码） |

本帖：`10787181972`  
标题（`document.title` / `.pb-title`）：**X网友抓拍到了鳄鱼捕食的瞬间**

## 页面架构（新版 PC SPA）

- **不是**旧版 `l_post` / `d_post_content` / `data-field` 直出 HTML。
- 首屏 Document 仅 ~11KB（`curl_cffi` 无 Cookie 时几乎空壳），**正文由前端 bundle 渲染**。
- 关键静态资源：
  - `pc-main-core/static/js/pb.f2861951.js`
  - `pc-main-core/static/css/pb.18c49760.css`
  - 公共：`frs~home~home-main~pb~search~token.*.js`

Relay 下完整 DOM 可见；裸 HTTP 需带浏览器 Cookie / 或走 Relay / 或找 XHR 接口。

## DOM 元素来源（Relay `eval` 实测）

### 标题

| 选择器 | 说明 |
|--------|------|
| `.pb-title` | 主标题文案 |
| `.pb-title-wrap.pc-pb-title` | 标题容器 |

### 楼主 / 作者

- 头像：`img.avatar-img` → `himg.bdimg.com/sys/portrait/item/tb.*`
- 昵称 + 等级：楼主块内文本，如 `O钢弹在白露之滨` + `红色有角`
- 主页：`a[href*="/home/main?id=tb."]`，`id` 为贴吧用户 token（如 `tb.1.b01a014e._0rp1F3ZD_zgRMnxkcYS6Q`）
- **注意**：侧栏「我常逛的吧」也会产出 `/home/main` 链接，解析时要限定在**主内容区**（`.center-content` / `.image-text` / 标题附近），避免误取当前登录用户。

### 楼主正文与互动数

标题下方楼主区可见：

- 正文示例：`🐊没事吧？`
- 数字条（推测：分享 / 回复 / 浏览等）：`20`、`212`、`6059`、`252`（需对照页面图标确认字段含义）
- 回复区：`.pc-pb-comments`、`.pc-pb-reply-list`

### 图片

- 帖内图：`https://tiebapic.baidu.com/forum/pic/item/{hash}.jpg?tbpicau=...`
- 吧头像：`tiebapic.baidu.com/forum/w=120;h=120/sign=...`
- 侧栏话题图可能带 `topic-img`，解析时应优先 **楼主正文区域内** 的 `tiebapic.../pic/item/`

本帖 Relay 抓到 **4 张** `pic/item` 图（鳄鱼抓拍多图）。

### 吧信息

- `og:url`（若存在）：`https://tieba.baidu.com/{username}/p/{id}/` 可反推吧主路径；本帖楼主为个人帖，侧栏可能显示所在吧（需从面包屑或吧入口取）。

## 网络请求（Relay `network` 摘要）

| 类型 | URL 模式 | 用途猜测 |
|------|----------|----------|
| Document | `/p/{id}` | 壳 + 引导加载 pb  bundle |
| XHR | `tieba.baidu.com/mo/q/getConfigData?...` | 配置/amis |
| 静态 | `tb3.bdstatic.com/tb/pc/pc-main-core/static/js/pb.*.js` | 帖页逻辑 |
| 图片 | `tiebapic.baidu.com` | 帖图/吧图 |
| 头像 | `himg.bdimg.com/sys/portrait/item/` | 用户头像 |

**未在刷新后 capture 到明显的「单帖 JSON」XHR**（`network` 列表偏静态与埋点）。后续实现可：

1. **Relay + 选择器** 抽 DOM（开发/调试）
2. **带 Cookie 的 curl_cffi** 拉完整 HTML 再解析（与 Relay 结构应对齐）
3. **逆向 `pb.*.js` 或抓包** 找 `thread_id` 对应 API（适合无头批量）

## 与项目内 NGA 解析对比

| | NGA | 贴吧（本帖） |
|---|-----|----------------|
| HTML | 服务端直出 `postcontent0` | SPA，裸请求几乎无正文 |
| 作者 | `postauthor0` + JS `userInfo` | `.avatar-img` + `/home/main?id=tb.` |
| 标题 | `#postsubject0` | `.pb-title` |
| 图片 | 附件 URL 规则 | `tiebapic.baidu.com/forum/pic/item/` |

## 建议解析器字段映射（初稿）

```text
ParseResult
├── title        ← .pb-title
├── text         ← 楼主首楼正文（主内容区首段，不含全楼回复）
├── author       ← 楼主昵称 + portrait URL
├── url          ← canonical /p/{id}/
├── timestamp    ← 楼主时间（如 06-12，需补全年份或从接口）
├── contents[]   ← tiebapic pic/item 多图
└── extra
    ├── forum_name / forum_kw（若能从页面取）
    ├── reply_count ← 「全部回复 (212)」
    └── view_count 等（待图标对齐）
```

## 本地探测脚本

- `scripts/_tieba_relay_probe.js` / `_tieba_relay_probe4.js` — Relay DOM
- `scripts/_probe_tieba_http.py` — 无 Cookie HTTP 对比
- 输出样例：`scripts/_tieba_probe4_out.json`

## 下一步（实现前）

1. 用 **同一 Cookie** 验证 `curl_cffi` 能否拿到与 Relay 一致的 HTML 长度与 `.pb-title`。
2. 锁定**楼主正文**容器 class（避免把评论列表当 `text`）。
3. 在 `PlatformEnum` / `parsers/tieba.py` 注册 `tieba.baidu.com` + `/p/(?P<tid>\d+)`。
4. 卡片渲染：参考 NGA/论坛型，多图网格 + 标题 + 作者行。
