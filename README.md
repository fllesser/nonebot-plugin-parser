<div align="center">
    <a href="https://v2.nonebot.dev/store">
    <img src="./.docs/NoneBotPlugin.svg" width="300" alt="logo"></a>
</div>

<div align="center">

# nonebot-plugin-resolver2

_✨ NoneBot2 链接分享解析器插件重制版 ✨_


<a href="./LICENSE">
    <img src="https://img.shields.io/github/license/fllesser/nonebot-plugin-resolver2.svg" alt="license">
</a>
<a href="https://pypi.python.org/pypi/nonebot-plugin-resolver2">
    <img src="https://img.shields.io/pypi/v/nonebot-plugin-resolver2.svg" alt="pypi">
</a>
<img src="https://img.shields.io/badge/python-3.9+-blue.svg" alt="python">

</div>

**:warning: 如果你已经在使用 nonebot-plugin-resolver 请在安装此插件前卸载 **

<details>
<summary>触发发布工作流</summary>
从本地推送任意 tag 即可触发。

创建 tag:

    git tag <tag_name>

推送本地所有 tag:

    git push origin --tags

</details>

## 📖 介绍

[nonebot-plugin-resolver](https://github.com/zhiyu1998/nonebot-plugin-resolver) 重制版，优化了一些交互逻辑，效果见实际体验

支持的解析(BV号/链接/小程序/卡片)

支持平台(b站，抖音，网易云，微博，小红书，youtube，tiktok，twitter...) 

## 💿 安装

<details open>
<summary>使用 nb-cli 安装</summary>
在 nonebot2 项目的根目录下打开命令行, 输入以下指令即可安装

    nb plugin install nonebot-plugin-resolver2

</details>

<details>
<summary>使用包管理器安装</summary>
在 nonebot2 项目的插件目录下, 打开命令行, 根据你使用的包管理器, 输入相应的安装命令

<details>
<summary>pip</summary>

    pip install nonebot-plugin-resolver2
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

## ⚙️ 配置

在 nonebot2 项目的`.env`文件中添加下表中的必填配置

| 配置项 | 必填 | 默认值 | 说明 |
|:-----:|:----:|:----:|:----:|
| NICKNAME | 否 | "" | nonebot2内置配置，可作为解析结果消息的前缀 |
| r_xhs_ck | 否 | "" | 小红书 cookie，想要解析小红书必填|
| r_douyin_ck | 否 | "" | 抖音 cookie，想要解析抖音必填 |
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


## 致谢
大部分解析代码来自 [nonebot-plugin-resolver](https://github.com/zhiyu1998/nonebot-plugin-resolver)