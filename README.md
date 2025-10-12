<div align="center">
<a href="https://v2.nonebot.dev/store">
    <img src="https://raw.githubusercontent.com/fllesser/nonebot-plugin-template/refs/heads/resource/.docs/NoneBotPlugin.svg" width="310" alt="logo">
</a>

## ✨ [Nonebot2](https://github.com/nonebot/nonebot2) 链接分享自动解析插件 ✨
[![LICENSE](https://img.shields.io/github/license/fllesser/nonebot-plugin-parser.svg)](./LICENSE)
[![pypi](https://img.shields.io/pypi/v/nonebot-plugin-parser.svg)](https://pypi.python.org/pypi/nonebot-plugin-parser)
[![python](https://img.shields.io/badge/python-3.10|3.11|3.12|3.13-blue.svg)](https://python.org)
[![uv](https://img.shields.io/badge/package%20manager-uv-black?style=flat-square&logo=uv)](https://github.com/astral-sh/uv)
[![ruff](https://img.shields.io/badge/code%20style-ruff-black?style=flat-square&logo=ruff)](https://github.com/astral-sh/ruff)
<br/>
[![pre-commit](https://results.pre-commit.ci/badge/github/fllesser/nonebot-plugin-parser/master.svg)](https://results.pre-commit.ci/latest/github/fllesser/nonebot-plugin-parser/master)
[![codecov](https://codecov.io/gh/fllesser/nonebot-plugin-parser/graph/badge.svg?token=VCS8IHSO7U)](https://codecov.io/gh/fllesser/nonebot-plugin-parser)
[![qqgroup](https://img.shields.io/badge/QQ%E7%BE%A4-820082006-orange?style=flat-square)](https://qm.qq.com/q/y4T4CjHimc)
</div>

> [!IMPORTANT]
> **收藏项目**，你将从 GitHub 上无延迟地接收所有发布通知～⭐️

<img width="100%" src="https://starify.komoridevs.icu/api/starify?owner=fllesser&repo=nonebot-plugin-parser" alt="starify" />

## 📖 介绍

[nonebot-plugin-resolver](https://github.com/zhiyu1998/nonebot-plugin-resolver) 重制版

| 平台    | 触发的消息形态                        | 视频 | 图集 | 音频 |
| ------- | ------------------------------------- | ---- | ---- | ---- |
| B站     | BV号/链接(包含短链,BV,av)/卡片/小程序 | ✅​   | ✅​   | ✅​   |
| 抖音    | 链接(分享链接，兼容电脑端链接)        | ✅​   | ✅​   | ❌️    |
| 微博    | 链接(博文，视频，show)                | ✅​   | ✅​   | ❌️    |
| 小红书  | 链接(含短链)/卡片                     | ✅​   | ✅​   | ❌️    |
| 快手    | 链接(包含标准链接和短链)              | ✅​   | ✅​   | ❌️    |
| acfun   | 链接                                  | ✅​   | ❌️    | ❌️    |
| youtube | 链接(含短链)                          | ✅​   | ❌️    | ✅​   |
| tiktok  | 链接                                  | ✅​   | ❌️    | ❌️    |
| twitter | 链接                                  | ✅​   | ✅​   | ❌️    |

支持的链接，可参考 [测试链接](https://github.com/fllesser/nonebot-plugin-parser/blob/master/test_url.md)

## 💿 安装
> [!Warning]
> **如果你已经在使用 nonebot-plugin-resolver，请在安装此插件前卸载**
    
<details open>
<summary>使用 nb-cli 安装/更新</summary>
在 nonebot2 项目的根目录下打开命令行, 输入以下指令即可安装

    nb plugin install nonebot-plugin-parser --upgrade
使用 pypi 源更新

    nb plugin install nonebot-plugin-parser --upgrade -i https://pypi.org/simple
安装仓库 dev 分支

    uv pip install git+https://github.com/fllesser/nonebot-plugin-parser.git@dev
</details>

<details>
<summary>使用包管理器安装</summary>
在 nonebot2 项目的插件目录下, 打开命令行, 根据你使用的包管理器, 输入相应的安装命令
<details open>
<summary>uv</summary>
使用 uv 安装

    uv add nonebot-plugin-parser
安装仓库 dev 分支

    uv add git+https://github.com/fllesser/nonebot-plugin-parser.git@master
</details>


<details>
<summary>pip</summary>

    pip install --upgrade nonebot-plugin-parser
</details>
<details>
<summary>pdm</summary>

    pdm add nonebot-plugin-parser
</details>
<details>
<summary>poetry</summary>

    poetry add nonebot-plugin-parser
</details>

打开 nonebot2 项目根目录下的 `pyproject.toml` 文件, 在 `[tool.nonebot]` 部分追加写入

    plugins = ["nonebot_plugin_parser"]

</details>

<details>
<summary>使用 nbr 安装(使用 uv 管理依赖可用)</summary>

[nbr](https://github.com/fllesser/nbr) 是一个基于 uv 的 nb-cli，可以方便地管理 nonebot2

    nbr plugin install nonebot-plugin-parser
使用 **pypi** 源安装

    nbr plugin install nonebot-plugin-parser -i "https://pypi.org/simple"
使用**清华源**安装

    nbr plugin install nonebot-plugin-parser -i "https://pypi.tuna.tsinghua.edu.cn/simple"

</details>

<details open>
<summary>安装必要组件</summary>
部分解析依赖于 ffmpeg

ubuntu/debian

    sudo apt-get install ffmpeg

其他 linux 参考(原项目推荐): https://gitee.com/baihu433/ffmpeg

Windows 参考(原项目推荐): https://www.jianshu.com/p/5015a477de3c
</details>

## ⚙️ 配置

在 nonebot2 项目的`.env`文件中添加下表中的必填配置

|            配置项            | 必填  |          默认值          |                                                                                                                                      说明                                                                                                                                       |
| :--------------------------: | :---: | :----------------------: | :-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------: |
|           NICKNAME           |  否   |           [""]           |                                                                                                                   nonebot2 内置配置，可作为解析结果消息的前缀                                                                                                                   |
|         API_TIMEOUT          |  否   |           30.0           |                                                                                                           nonebot2 内置配置，若服务器上传带宽太低，建议调高，防止超时                                                                                                           |
|        parser_bili_ck        |  否   |            ""            | B 站 cookie, 必须含有 SESSDATA 项，可附加 B 站 AI 总结功能, 如果需要长期使用此凭据则不应该在**浏览器登录账户**导致 cookie 被刷新，建议注册个小号获取, 也可以配置 ac_time_value 项，用于凭据的自动刷新，[获取方式](https://github.com/fllesser/nonebot-plugin-parser/issues/177) |
|   parser_bili_video_codes    |  否   | '["avc", "av01", "hev"]' |                                                  允许的 B 站视频编码，越靠前的编码优先级越高，可选 "avc"(H.264，体积较大), "hev"(HEVC), "av01"(AV1), 后两项在不同设备可能有兼容性问题，如需完全避免，可只填一项，如 '["avc"]'                                                   |
|        parser_ytb_ck         |  否   |            ""            |                                                                                                              Youtube cookie, Youtube 视频因人机检测下载失败，需填                                                                                                               |
|         parser_proxy         |  否   |           None           |                                                                                 仅作用于 youtube, tiktok 解析，推特解析会自动读取环境变量中的 http_proxy / https_proxy(代理软件通常会自动设置)                                                                                  |
|      parser_need_upload      |  否   |          False           |                                                                                                                          音频解析，是否需要上传群文件                                                                                                                           |
|      parser_use_base64       |  否   |          False           |                                            视频，图片，音频是否使用 base64 发送，注意：编解码和传输 base64 会占用更多的内存,性能和带宽, 甚至可能会使 websocket 连接崩溃，因此该配置项仅推荐 nonebot 和 协议端不在同一机器的用户配置                                             |
|   parser_duration_maximum    |  否   |           480            |                                                                                                                          视频最大解析时长，单位：_秒_                                                                                                                           |
|       parser_max_size        |  否   |            90            |                                                                                                              音视频下载最大文件大小，单位 MB，超过该配置将阻断下载                                                                                                              |
|  parser_disabled_platforms   |  否   |            []            |                               全局禁止的解析，示例 parser_disabled_platforms=["bilibili", "douyin"] 表示禁止了哔哩哔哩和抖, 请根据自己需求填写["bilibili", "douyin", "kuaishou", "twitter", "youtube", "acfun", "tiktok", "weibo", "xiaohongshu"]                               |
|      parser_render_type      |  否   |         "common"         |                                                                                        渲染器类型，可选 "default"(无图片渲染), "common"(PIL 通用图片渲染), "htmlkit"(htmlkit, 暂不可用)                                                                                         |
|      parser_append_url       |  否   |          False           |                                                                                                                           是否在解析结果中附加原始URL                                                                                                                           |
|      parser_custom_font      |  否   |           None           |                                                                            自定义渲染字体，配置字体文件名，并将字体文件放置于 localstore 生成的插件 data 目录下（如 ./data/nonebot_plugin_parser/）                                                                             |
| parser_need_forward_contents |  否   |           True           |                                                                                                                是否需要转发媒体内容(超过 4 项时始终使用合并转发)                                                                                                                |
## 🎉 使用
### 指令表
|   指令   |         权限          | 需要@ | 范围  |   说明   |
| :------: | :-------------------: | :---: | :---: | :------: |
| 开启解析 | SUPERUSER/OWNER/ADMIN |  是   | 群聊  | 开启解析 |
| 关闭解析 | SUPERUSER/OWNER/ADMIN |  是   | 群聊  | 关闭解析 |


## 🔧 高级配置
### 推荐的字体
- [LXGW ZhenKai / 霞鹜臻楷](https://github.com/lxgw/LxgwZhenKai) 效果图使用字体
- [LXGW Neo XiHei / 霞鹜新晰黑](https://github.com/lxgw/LxgwNeoXiHei)
- [LXGW Neo ZhiSong / 霞鹜新致宋 / 霞鶩新緻宋](https://github.com/lxgw/LxgwNeoZhiSong)

## 🎨 效果图

<div align="center">

<img src="https://raw.githubusercontent.com/fllesser/nonebot-plugin-parser/refs/heads/resources/resources/renderdamine/video.png" width="160" />
<img src="https://raw.githubusercontent.com/fllesser/nonebot-plugin-parser/refs/heads/resources/resources/renderdamine/9_pic.png" width="160" />
<img src="https://raw.githubusercontent.com/fllesser/nonebot-plugin-parser/refs/heads/resources/resources/renderdamine/4_pic.png" width="160" />
<img src="https://raw.githubusercontent.com/fllesser/nonebot-plugin-parser/refs/heads/resources/resources/renderdamine/repost_video.png" width="160" />
<img src="https://raw.githubusercontent.com/fllesser/nonebot-plugin-parser/refs/heads/resources/resources/renderdamine/repost_2_pic.png" width="160" />

</div>

## 致谢
[nonebot-plugin-resolver](https://github.com/zhiyu1998/nonebot-plugin-resolver)
[parse-video-py](https://github.com/wujunwei928/parse-video-py)