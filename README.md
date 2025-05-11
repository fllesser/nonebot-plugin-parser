<div align="center">
<a href="https://v2.nonebot.dev/store">
    <img src="https://raw.githubusercontent.com/fllesser/nonebot-plugin-template/refs/heads/resource/.docs/NoneBotPlugin.svg" width="310" alt="logo">
</a>

## ✨ [Nonebot2](https://github.com/nonebot/nonebot2) 链接分享自动解析插件 ✨

<a href="./LICENSE">
    <img src="https://img.shields.io/github/license/fllesser/nonebot-plugin-resolver2.svg" alt="license">
</a>
<a href="https://pypi.python.org/pypi/nonebot-plugin-resolver2">
    <img src="https://img.shields.io/pypi/v/nonebot-plugin-resolver2.svg" alt="pypi">
</a>
<img src="https://img.shields.io/badge/python-3.10|3.11|3.12|3.13-blue.svg" alt="python">
<a href="https://github.com/astral-sh/ruff">
    <img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v2.json" alt="ruff">
</a>
<a href="https://github.com/astral-sh/uv">
    <img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json" alt="uv">
</a>
<a href="https://onebot.dev/">
<img src="https://img.shields.io/badge/OneBot-v11-black?style=social&logo=data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEAAAABABAMAAABYR2ztAAAAIVBMVEUAAAAAAAADAwMHBwceHh4UFBQNDQ0ZGRkoKCgvLy8iIiLWSdWYAAAAAXRSTlMAQObYZgAAAQVJREFUSMftlM0RgjAQhV+0ATYK6i1Xb+iMd0qgBEqgBEuwBOxU2QDKsjvojQPvkJ/ZL5sXkgWrFirK4MibYUdE3OR2nEpuKz1/q8CdNxNQgthZCXYVLjyoDQftaKuniHHWRnPh2GCUetR2/9HsMAXyUT4/3UHwtQT2AggSCGKeSAsFnxBIOuAggdh3AKTL7pDuCyABcMb0aQP7aM4AnAbc/wHwA5D2wDHTTe56gIIOUA/4YYV2e1sg713PXdZJAuncdZMAGkAukU9OAn40O849+0ornPwT93rphWF0mgAbauUrEOthlX8Zu7P5A6kZyKCJy75hhw1Mgr9RAUvX7A3csGqZegEdniCx30c3agAAAABJRU5ErkJggg==" alt="onebot">
</a>
<a href="https://results.pre-commit.ci/latest/github/fllesser/nonebot-plugin-resolver2/master">
<img src="https://results.pre-commit.ci/badge/github/fllesser/nonebot-plugin-resolver2/master.svg" alt="pre-commit" />
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

|          配置项          | 必填  | 默认值 |                                                                                                              说明                                                                                                              |
| :----------------------: | :---: | :----: | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------: |
|         NICKNAME         |  否   |  [""]  |                                                                                          nonebot2 内置配置，可作为解析结果消息的前缀                                                                                           |
|       API_TIMEOUT        |  否   |  30.0  |                                                                                  nonebot2 内置配置，若服务器上传带宽太低，建议调高，防止超时                                                                                   |
|         r_xhs_ck         |  否   |   ""   |                                                                                               小红书 cookie，想要解析小红书必填                                                                                                |
|        r_bili_ck         |  否   |   ""   |                           B站 cookie, 可不填，若填写，必须含有 SESSDATA 项，可附加 B 站 AI 总结功能,如果需要长期使用此凭据则不应该在**浏览器登录账户**导致 Cookies 被刷新，建议注册个小号获取 cookie                           |
|         r_ytb_ck         |  否   |   ""   |                                                                                      Youtube cookie, Youtube 视频因人机检测下载失败，需填                                                                                      |
|         r_proxy          |  否   |  None  |                                                                                                   youtube, tiktok, x 的代理                                                                                                    |
|      r_need_upload       |  否   | False  |                                                                                                  音频解析，是否需要上传群文件                                                                                                  |
|      r_need_forward      |  否   |  True  |                                                                **不超过** 4 条的解析消息是否需要合并转发，配置为 False ，超过4条的解析消息仍然会用合并转发包裹                                                                 |
|       r_use_base64       |  否   | False  | 视频，图片，音频是否使用 base64 发送，注意：编解码和传输 base64 会占用更多的内存,性能和带宽, 甚至可能会使 websocket 连接崩溃，因此该配置项仅推荐 nonebot 和 协议端不在同一机器，或者使用 docker 懒得映射插件缓存目录的用户配置 |
| r_video_duration_maximum |  否   |  480   |                                                                                                B站视频最大解析时长，单位：_秒_                                                                                                 |
|        r_max_size        |  否   |  100   |                                                                                     音视频下载最大文件大小，单位 MB，超过该配置将阻断下载                                                                                      |
|   r_disable_resolvers    |  否   |   []   |         全局禁止的解析，示例 r_disable_resolvers=["bilibili", "douyin"] 表示禁止了哔哩哔哩和抖, 请根据自己需求填写["bilibili", "douyin", "kugou", "twitter", "ncm", "ytb", "acfun", "tiktok", "weibo", "xiaohongshu"]          |


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