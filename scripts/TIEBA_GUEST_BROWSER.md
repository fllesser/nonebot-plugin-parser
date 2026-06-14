# 贴吧「未登录 / 隐身」为何能浏览（Relay 实测）

探测帖：`https://tieba.baidu.com/p/10780369243`  
工具：Browser Relay 接管 Chrome 标签（可为隐身窗口，只要扩展已附着该标签）

## 结论（一句话）

**未登录也能看**，靠的是 **访客 Cookie + 带签名的 XHR**，由 **`pb.f2861951.js` 在浏览器里拼请求**；正文/视频 URL 会写进 **渲染后的 DOM/HTML**，不是首屏 11KB 壳子里的静态字段。  
**Python 裸 GET 帖页** 拿不到这套流程，所以和隐身浏览器不是一回事。

## 访客身份（`/c/s/pc/sync`）

```json
"user": { "is_login": 0 },
"anti": { "tbs": "5f93bd7649de07091781401682" }
```

- **`is_login: 0`**：明确未登录。
- **`tbs`**：后续接口常用的防刷 token（需在请求里带上，具体字段以 bundle 为准）。

## `document.cookie`（非登录）

| 项 | 值 |
|----|-----|
| 长度 | ~239 |
| **BDUSS** | **无** |
| 典型键 | `TIEBA_NEW_PC=1`、`TIEBA_SID=...`、`BAIDUID=...`、`USER_JUMP=-1` |

说明：隐身/访客仍有 **贴吧会话 Cookie**，但没有百度账号登录态。

## 页面如何有内容

1. **Document** 仍可能是小壳子；**执行** `pb.*.js` 等 bundle。
2. 浏览器发起（`performance` / network 可见）：
   - `POST https://tieba.baidu.com/c/f/pb/page_pc` → 本环境返回 **`error_code: 110001`**（接口仍被调用）
   - `GET .../c/s/pc/sync?...&sign=...` → **成功**，`error_code: 0`
   - `GET .../c/f/pc/pbSidebarRight?tid=...&sign=...` → **成功**，含吧信息 JSON
3. 前端把数据 **灌进 Vue/DOM** 后：
   - `htmlLen` ≈ **77 万**
   - `.pb-title`、`<video src="http://tb-video.bdstatic.com/...mp4">` 均在 DOM 中
   - HTML 内 **`post_list` 字符串出现 0 次**（不是旧版内嵌 JSON 帖列表）

## 和 Python 解析器的差距

| 步骤 | 隐身 Chrome | curl_cffi 无 Cookie |
|------|-------------|---------------------|
| GET `/p/{id}` | 小文档 + 跑 JS | ~11KB，无 `pb-title` |
| `sync` + `sign` | 自动带 Cookie/tbs | 未实现 sign → 失败 |
| `page_pc` | 会请求（可能失败但仍能靠其它接口+DOM） | `110001` |
| 结果 | 可看视频 | 解析失败 |

## 对「不登录也能解析」的启示

若要服务端接近隐身效果，不能只 GET HTML，需要至少：

1. 模拟访客：**首页 → 收 `TIEBA_SID` / `BAIDUID` 等 Cookie**
2. 调 **`/c/s/pc/sync`** 拿 **`tbs`** 与 `is_login`
3. 按前端规则计算 **`sign`**，请求 **`pbSidebarRight`** 等（`page_pc` 可能仍 110001，需再挖备用数据源）
4. 或：**用无头 Chrome / Relay 导出渲染后 HTML**（当前 `tieba_delivery_from_html.py` 路线）

## Relay 复现命令

```powershell
browser-relay tabs
# 在隐身窗口打开贴吧帖并附着扩展后：
Get-Content scripts\_tieba_incognito_probe.js -Raw | browser-relay eval --stdin --tab <TAB_ID>
Get-Content scripts\_tieba_incognito_fetch.js -Raw | browser-relay eval --stdin --tab <TAB_ID>
```

## 脚本

- `scripts/_tieba_incognito_probe.js` — Cookie / 脚本 / DOM 规模
- `scripts/_tieba_incognito_fetch.js` — 同页 `fetch(page_pc)` 与 resource 列表
- `scripts/_tieba_html_embed.js` — HTML 内嵌关键字统计
- `scripts/_probe_tieba_guest_cookies.py` — Python 访客 Cookie 链（仍可能只有 11KB）

## 2026-06-14 更新：服务端未登录主路径

**未登录解析优先** `GET https://tieba.baidu.com/mo/q/m?kz={tid}`（先 `GET /` 拿访客 Cookie）。

| 步骤 | 说明 |
|------|------|
| 实现 | `src/nonebot_plugin_parser/parsers/tieba.py` → `_fetch_best_html` / `_result_from_mo_html` |
| 帖元数据 | 内嵌 `threadInfo` / `'thread'` JSON，按 `tid` 取 `title`、`reply_num`、`share_num`、`author` |
| 图集 | `tiebapic.baidu.com/forum/pic/item/`（`src=` 优先，按 pic id 去重） |
| 视频 | 优先 `tieba-smallvideo-transcode-cae`；裸 `tieba-movideo` 易 HTTP 401 |
| 落盘 | `scripts/tieba_delivery.py <url>` → `tieba_{tid}_out/` |

验收（本机已跑通）：

- `tieba_10787181972_out`：图集 + `card.png` + `meta.json`
- `tieba_10780369243_out`：`media_00_video.mp4` + 封面 + `card.png`
