<div align="center">
    <a href="https://v2.nonebot.dev/store">
    <img src="./.docs/NoneBotPlugin.svg" width="300" alt="logo"></a>
</div>

<div align="center">

## ✨ 链接分享自动解析 ✨

<a href="./LICENSE">
    <img src="https://img.shields.io/github/license/fllesser/nonebot-plugin-resolver2.svg" alt="license">
</a>
<a href="https://pypi.python.org/pypi/nonebot-plugin-resolver2">
    <img src="https://img.shields.io/pypi/v/nonebot-plugin-resolver2.svg" alt="pypi">
</a>
<img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="python">
<a href="https://github.com/astral-sh/ruff">
    <img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v2.json" alt="ruff">
</a>
</div>

> [!IMPORTANT]
> **收藏项目**，你将从 GitHub 上无延迟地接收所有发布通知～⭐️

<img width="100%" src="https://starify.komoridevs.icu/api/starify?owner=fllesser&repo=nonebot-plugin-resolver2" alt="starify" />

## 📖 介绍

[nonebot-plugin-resolver](https://github.com/zhiyu1998/nonebot-plugin-resolver) 重制版

| 平台    | 触发的消息形态                        | 视频 | 图集 | 音频 |
| ------- | ------------------------------------- | ---- | ---- | ---- |
| B站     | BV号/链接(包含短链,BV,av)/卡片/小程序 | ✅​   | ✅​   | ✅​   |
| 抖音    | 链接(分享链接，兼容电脑端链接)        | ✅​   | ✅​   | ❌️    |
| 网易云  | 链接/卡片                             | ❌️    | ❌️    | ✅​   |
| 微博    | 链接(博文，视频，show)                | ✅​   | ✅​   | ❌️    |
| 小红书  | 链接(含短链)/卡片                     | ✅​   | ✅​   | ❌️    |
| 酷狗    | 链接/卡片                             | ❌️    | ❌️    | ✅​   |
| acfun   | 链接                                  | ✅​   | ❌️    | ❌️    |
| youtube | 链接(含短链)                          | ✅​   | ❌️    | ✅​   |
| tiktok  | 链接                                  | ✅​   | ❌️    | ❌️    |
| twitter | 链接                                  | ✅​   | ✅​   | ❌️    |

支持的链接，可参考 [测试链接](https://github.com/fllesser/nonebot-plugin-resolver2/blob/master/test_url.md)

## 💿 安装
> [!Warning]
> **如果你已经在使用 nonebot-plugin-resolver，请在安装此插件前卸载**
    
<details open>
<summary>使用 nb-cli 安装/更新</summary>
在 nonebot2 项目的根目录下打开命令行, 输入以下指令即可安装

    nb plugin install nonebot-plugin-resolver2 --upgrade
使用 pypi 源更新

    nb plugin install nonebot-plugin-resolver2 --upgrade -i https://pypi.org/simple
安装仓库 dev 分支

    uv pip install git+https://github.com/fllesser/nonebot-plugin-resolver2.git@dev
</details>

<details>
<summary>使用包管理器安装</summary>
在 nonebot2 项目的插件目录下, 打开命令行, 根据你使用的包管理器, 输入相应的安装命令
<details open>
<summary>uv</summary>
使用 uv 安装

    uv add nonebot-plugin-resolver2
安装仓库 dev 分支

    uv add git+https://github.com/fllesser/nonebot-plugin-resolver2.git@master
</details>


<details>
<summary>pip</summary>

    pip install --upgrade nonebot-plugin-resolver2
</details>
<details>
<summary>pdm</summary>

    pdm add nonebot-plugin-resolver2
</details>
<details>
<summary>poetry</summary>

    poetry add nonebot-plugin-resolver2
</details>

打开 nonebot2 项目根目录下的 `pyproject.toml` 文件, 在 `[tool.nonebot]` 部分追加写入

    plugins = ["nonebot_plugin_resolver2"]

</details>

<details open>
<summary>安装必要组件</summary>
大部分解析都依赖于 ffmpeg

ubuntu/debian

    sudo apt-get install ffmpeg

其他 linux 参考(原项目推荐): https://gitee.com/baihu433/ffmpeg

Windows 参考(原项目推荐): https://www.jianshu.com/p/5015a477de3c
</details>

## ⚙️ 配置

在 nonebot2 项目的`.env`文件中添加下表中的必填配置

|          配置项          | 必填  |         默认值          |                                                                                                     说明                                                                                                      |
| :----------------------: | :---: | :---------------------: | :-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------: |
|         NICKNAME         |  否   |          [""]           |                                                                                  nonebot2 内置配置，可作为解析结果消息的前缀                                                                                  |
|       API_TIMEOUT        |  否   |          30.0           |                                                                          nonebot2 内置配置，若服务器上传带宽太低，建议调高，防止超时                                                                          |
|         r_xhs_ck         |  否   |           ""            |                                                                                       小红书 cookie，想要解析小红书必填                                                                                       |
|        r_bili_ck         |  否   |           ""            |                  B站 cookie, 可不填，若填写，必须含有 SESSDATA 项，可附加 B 站 AI 总结功能,如果需要长期使用此凭据则不应该在**浏览器登录账户**导致 Cookies 被刷新，建议注册个小号获取 cookie                   |
|         r_ytb_ck         |  否   |           ""            |                                                                             Youtube cookie, Youtube 视频因人机检测下载失败，需填                                                                              |
|       r_is_oversea       |  否   |          False          |                                                                                海外服务器部署，或者使用了透明代理，设置为 True                                                                                |
|         r_proxy          |  否   | 'http://127.0.0.1:7890' |                                                                                    # 代理，仅在 r_is_oversea=False 时生效                                                                                     |
|      r_need_upload       |  否   |          False          |                                                                                         音频解析，是否需要上传群文件                                                                                          |
|      r_need_forward      |  否   |          True           |                                                                                      超过 4 条的解析消息是否需要合并转发                                                                                      |
| r_video_duration_maximum |  否   |           480           |                                                                                         视频最大解析长度，单位：_秒_                                                                                          |
|   r_disable_resolvers    |  否   |           []            | 全局禁止的解析，示例 r_disable_resolvers=["bilibili", "douyin"] 表示禁止了哔哩哔哩和抖, 请根据自己需求填写["bilibili", "douyin", "kugou", "twitter", "ncm", "ytb", "acfun", "tiktok", "weibo", "xiaohongshu"] |


## 🎉 使用
### 指令表
|     指令     |         权限          | 需要@ | 范围  |          说明          |
| :----------: | :-------------------: | :---: | :---: | :--------------------: |
|   开启解析   | SUPERUSER/OWNER/ADMIN |  是   | 群聊  |        开启解析        |
|   关闭解析   | SUPERUSER/OWNER/ADMIN |  是   | 群聊  |        关闭解析        |
| 开启所有解析 |       SUPERUSER       |  否   | 私聊  |    开启所有群的解析    |
| 关闭所有解析 |       SUPERUSER       |  否   | 私聊  |    关闭所有群的解析    |
| 查看关闭解析 |       SUPERUSER       |  否   |   -   | 获取已经关闭解析的群聊 |
|   bm BV...   |         USER          |  否   |   -   |     下载 b站 音乐      |


## 致谢
[nonebot-plugin-resolver](https://github.com/zhiyu1998/nonebot-plugin-resolver)
[parse-video-py](https://github.com/wujunwei928/parse-video-py)