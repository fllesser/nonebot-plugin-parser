# Instagram 适配说明

## 已支持链接

- Reel: `https://www.instagram.com/reel/<id>/`
- Reels: `https://www.instagram.com/reels/<id>/`
- 帖子: `https://www.instagram.com/p/<id>/`
- IGTV: `https://www.instagram.com/tv/<id>/`

## 实现方式

- 解析与下载：**yt-dlp**（与 TikTok / YouTube 同路径）
- 发送：**卡片 + 视频消息**（Reel）；多图帖子为 **图集**

## 本机已验证（Reel）

`https://www.instagram.com/reel/DBOC0Z4hOR1/`

- 作者：`@kiran.mazumder`
- 时长：约 25s
- 封面 + mp4 CDN 可由 yt-dlp 直接提取（未登录亦可，视地区/风控而定）

## 环境变量（可选）

```env
PARSER_INSTAGRAM_CK=sessionid=...; csrftoken=...; ds_user_id=...
```

登录 Cookie 写入 `instagram_cookies.txt`（Netscape），用于私密帖、风控失败时的回退。

## Browser Relay（接管浏览器）

Relay 服务已可在本机启动；要**读取你当前 Chrome 标签页**需：

1. Chrome 打开 `https://www.instagram.com/reel/DBOC0Z4hOR1/`
2. 安装并启用 **Browser Relay** 扩展（`browser-relay path` 可查看扩展目录）
3. 执行 `browser-relay tabs` 应能看到该标签

之后可用：

```bash
browser-relay snapshot --tab <id> --max-length 20000
browser-relay network --tab <id> --show-secrets --json
```

从 **network** 里提取 `sessionid` / `csrftoken` 填入 `PARSER_INSTAGRAM_CK`。

当前会话：`connected: false, tabCount: 0` — 扩展未连上，因此尚未抓取页面 DOM；解析逻辑已按 yt-dlp 字段对齐。
