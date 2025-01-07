<div align="center">
    <a href="https://v2.nonebot.dev/store">
    <img src="./.docs/NoneBotPlugin.svg" width="300" alt="logo"></a>
</div>

<div align="center">

# nonebot-plugin-resolver2

_✨ NoneBot2 链接分享自动解析插件 ✨_


<a href="./LICENSE">
    <img src="https://img.shields.io/github/license/fllesser/nonebot-plugin-resolver2.svg" alt="license">
</a>
<a href="https://pypi.python.org/pypi/nonebot-plugin-resolver2">
    <img src="https://img.shields.io/pypi/v/nonebot-plugin-resolver2.svg" alt="pypi">
</a>
<img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="python">

</div>

## 📖 介绍

[nonebot-plugin-resolver](https://github.com/zhiyu1998/nonebot-plugin-resolver) 重制版

- 重构了整体结构，优化了一些交互体验，尽可能避免刷屏（还没改到自己满意）
- 重构解析逻辑，通过预处理，提取文本消息、小程序、卡片中的链接，减少重复的字符串序列化, 正则匹配，逻辑判断，匹配消息换用 `on_keyword` 和 `on_message` ，防止 `on_regex` 导致 Bot 卡死
- 重构并统一下载逻辑，添加下载进度条，使用 nb 官方的 `localstore` 存储数据，避免重复下载同一资源，定时清理（原插件全是用的绝对路径，给孩子改哭了）

- 抖音解析换用别的方法，不再需要 cookie，支持解析图集中的视频
- 微博解析额外支持了带 fid 的视频链接，图集下载原图
- 添加了 B站，Youtube 音频下载功能

| 平台     | 触发的消息形态 | 视频 | 图集 | 音频 |
| -------- | -------------- | ---- | ---- | ---- |
| B站      | BV号/链接(包含短链,BV,av)/卡片/小程序| ✔️ | ✔️ | ✔️ |
| 抖音     | 链接(分享链接，兼容电脑端链接) | ✔️ | ✔️ | ❌️ |
| 网易云   | 链接/卡片 | ❌️ | ❌️ | ✔️ |
| 微博     | 链接(博文，视频，show)| ✔️ | ✔️ | ❌️ |
| 小红书   | 链接(含短链)/卡片 | ✔️ | ✔️ | ❌️ |
| 酷狗     | 链接/卡片 | ❌️ | ❌️ | ✔️ |
| acfun    | 链接 | ✔️ | ❌️ | ❌️ |
| youtube  | 链接(含短链) | ✔️ | ❌️ | ✔️ |
| tiktok   | 链接 | ✔️ | ❌️ | ❌️ |
| twitter  | 链接 | ✔️ | ✔️ | ❌️ |

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
</details>

<details>
<summary>使用包管理器安装</summary>
在 nonebot2 项目的插件目录下, 打开命令行, 根据你使用的包管理器, 输入相应的安装命令

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
<details>
<summary>conda</summary>

    conda install nonebot-plugin-resolver2
</details>

打开 nonebot2 项目根目录下的 `pyproject.toml` 文件, 在 `[tool.nonebot]` 部分追加写入

    plugins = ["nonebot_plugin_resolver2"]

</details>

<details open>
<summary>安装必要组件</summary>
<summary>部分解析都依赖于 ffmpeg</summary>

    # ubuntu/debian
    sudo apt-get install ffmpeg
    ffmpeg -version
    # 其他 linux 参考(原项目推荐): https://gitee.com/baihu433/ffmpeg
    # Windows 参考(原项目推荐): https://www.jianshu.com/p/5015a477de3c
</details>

## ⚙️ 配置

在 nonebot2 项目的`.env`文件中添加下表中的必填配置

| 配置项 | 必填 | 默认值 | 说明 |
|:-----:|:----:|:----:|:----:|
| NICKNAME | 否 | [""] | nonebot2内置配置，可作为解析结果消息的前缀 |
| r_xhs_ck | 否 | "" | 小红书 cookie，想要解析小红书必填|
| r_bili_ck | 否 | "" | B站 cookie, 可不填，若填写，必须含有 SESSDATA 项，可附加 B 站 AI 总结功能 |
| r_ytb_ck | 否 | "" | Youtube cookie, Youtube 视频因人机检测下载失败，需填 |
| r_is_oversea | 否 | False | 海外服务器部署，或者使用了透明代理，设置为 True |
| r_proxy | 否 | 'http://127.0.0.1:7890' | # 代理，仅在 r_is_oversea=False 时生效 |
| r_video_duration_maximum | 否 | 480 | 视频最大解析长度，单位：_秒_ |
| r_disable_resolvers | 否 | [] | 全局禁止的解析，示例 r_disable_resolvers=["bilibili", "douyin"] 表示禁止了哔哩哔哩和抖, 请根据自己需求填写["bilibili", "douyin", "kugou", "twitter", "ncm", "ytb", "acfun", "tiktok", "weibo", "xiaohongshu"] |

## 🎉 使用
### 指令表
| 指令 | 权限 | 需要@ | 范围 | 说明 |
|:-----:|:----:|:----:|:----:|:----:|
| 开启解析 | SUPERUSER/OWNER/ADMIN | 是 | 群聊 | 开启解析 |
| 关闭解析 | SUPERUSER/OWNER/ADMIN | 是 | 群聊 | 关闭解析 |
| 开启所有解析 | SUPERUSER | 否 | 私聊 | 开启所有群的解析 |
| 关闭所有解析 | SUPERUSER | 否 | 私聊 | 关闭所有群的解析 |
| 查看关闭解析 | SUPERUSER | 否 | - | 获取已经关闭解析的群聊 |
| bm BV... | USER | 否 | - | 下载 b站 音乐 |


## 历史更新
v1.6.4
1. 重写B站解析逻辑，预编译正则，并支持解析av号(之前是av号链接)
2. 事件预处理逻辑优化
3. 支持的链接，可参考 [测试链接](https://github.com/fllesser/nonebot-plugin-resolver2/blob/master/test_url.md)

v1.6.x
1. 添加 B站专栏(article) 解析
2. 更新一些依赖
3. 优化 B站 解析正则，修复动态和收藏夹解析的潜藏错误
4. 配置项 r_disable_resolvers 使用字面量限制，防止用户填错
5. 添加 ffmpeg 未正确配置报错
6. 修复小红书图集名称问题
7. 添加事件预处理，用于提取小程序链接
8. 优化 B站，小红书，酷狗，网易云，acfun链接/资源ID 提取逻辑

v1.5.x
1. 适配 B 站新域名 bili2233.cn
2. 支持解析微博带 fid 的视频链接
3. 抖音解析添加重试
4. 优化 acfun 解析的逻辑
5. 支持解析小红书分享卡片
6. 支持解析抖音图集中的视频
7. 缓存，避免重复下载同一资源
8. 添加下载进度条
9. 修复windows环境特殊字符导致的路径问题
10. 优化历史遗留逻辑



## 致谢
[nonebot-plugin-resolver](https://github.com/zhiyu1998/nonebot-plugin-resolver)
[parse-video-py](https://github.com/wujunwei928/parse-video-py)