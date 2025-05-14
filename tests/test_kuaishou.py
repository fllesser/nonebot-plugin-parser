import asyncio

from nonebot import logger
import pytest
from utils import skip_on_failure, make_onebot_msg


@pytest.mark.asyncio
@skip_on_failure
async def test_kuaishou_video():
    """
    测试快手视频解析
    - https://www.kuaishou.com/short-video/3xhjgcmir24m4nm
    - https://v.kuaishou.com/1ff8QP
    - https://v.m.chenzhongtech.com/fw/photo/3xburnkmj3auazc
    """
    from nonebot_plugin_resolver2.parsers import KuaishouParser

    kuaishou_parser = KuaishouParser()

    test_urls = [
        "https://www.kuaishou.com/short-video/3xhjgcmir24m4nm",
        # "https://v.kuaishou.com/1ff8QP" （该短链接失效）
        # "https://v.m.chenzhongtech.com/fw/photo/3xburnkmj3auazc"
    ]

    async def test_parse_url(url: str) -> None:
        logger.info(f"{url} | 开始解析快手视频")
        video_info = await kuaishou_parser.parse_url(url)
        
        logger.debug(f"{url} | title: {video_info.title}")
        assert video_info.title, "视频标题为空"
        
        logger.debug(f"{url} | cover_url: {video_info.cover_url}")
        assert video_info.cover_url, "视频封面URL为空"
        
        logger.debug(f"{url} | video_url: {video_info.video_url}")
        assert video_info.video_url, "视频URL为空"
        
        if video_info.author:
            logger.debug(f"{url} | author: {video_info.author}")
        
        logger.success(f"{url} | 快手视频解析成功")

    await asyncio.gather(*[test_parse_url(url) for url in test_urls])


@pytest.mark.asyncio
@skip_on_failure
async def test_kuaishou_extract_id():
    """测试从不同格式的快手链接中提取视频ID"""
    from nonebot_plugin_resolver2.parsers import KuaishouParser
    
    kuaishou_parser = KuaishouParser()
    
    url = "https://www.kuaishou.com/short-video/3xhjgcmir24m4nm"
    logger.info(f"{url} | 开始测试视频ID提取")
    
    video_id = await kuaishou_parser._extract_video_id(url)
    logger.debug(f"{url} | 提取到的video_id: {video_id}")
    assert video_id == "3xhjgcmir24m4nm", "标准链接视频ID提取错误"
    logger.success(f"{url} | 视频ID提取成功")
    
    # 测试解析短链接重定向后提取ID（仅在短链接有效时测试）
    # short_url = "https://v.kuaishou.com/1ff8QP"
    # logger.info(f"{short_url} | 开始测试短链接重定向和视频ID提取")
    # 
    # resolved_url = await kuaishou_parser._resolve_short_url(short_url)
    # logger.debug(f"{short_url} | 重定向后的URL: {resolved_url}")
    # assert "kuaishou.com" in resolved_url, "短链接重定向失败"
    # 
    # video_id = await kuaishou_parser._extract_video_id(resolved_url)
    # logger.debug(f"{short_url} | 提取到的video_id: {video_id}")
    # assert video_id, "短链接重定向后视频ID提取错误"
    # logger.success(f"{short_url} | 短链接重定向和视频ID提取成功")


@pytest.mark.asyncio
@skip_on_failure
async def test_kuaishou_matcher_patterns():
    """测试快手匹配器的正则表达式"""
    from nonebot_plugin_resolver2.matchers.kuaishou import PATTERNS

    # 测试消息内容
    test_content = "看看这个视频 https://www.kuaishou.com/short-video/3xhjgcmir24m4nm 挺有意思"
    
    # 测试正则表达式是否能匹配到快手链接
    for pattern_name, pattern in PATTERNS.items():
        match = pattern.search(test_content)
        if match:
            logger.debug(f"正则 {pattern_name} 匹配到URL: {match.group(0)}")
            assert match.group(0) == "https://www.kuaishou.com/short-video/3xhjgcmir24m4nm"
            break
    else:
        assert False, "所有正则表达式都未能匹配到快手链接"
    
    logger.success("快手匹配器正则表达式测试成功") 