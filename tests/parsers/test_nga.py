"""测试NGA解析器"""

import pytest
from nonebot import logger


@pytest.mark.asyncio
async def test_nga_parse():
    """测试NGA帖子解析"""
    from nonebot_plugin_parser.parsers.nga import NGAParser

    url = "https://nga.178.com/read.php?tid=45263995"
    parser = NGAParser()

    # 测试URL匹配
    keyword, searched = parser.search_url(url)

    assert searched, "URL应该能被NGA解析器匹配"

    # 测试解析
    result = await parser.parse(keyword, searched)

    # 验证结果
    assert result.title, "应该能提取标题"
    assert result.url == url, "URL应该保持一致"
    assert result.author is not None, "应该能提取作者信息"
    assert result.timestamp is not None, "应该能提取发布时间"
    logger.debug(f"标题: {result.title}")
    logger.debug(f"作者: {result.author.name if result.author else 'N/A'}")
    logger.debug(f"时间: {result.timestamp}")
    logger.debug(f"内容: {result.contents}")
    assert result.graphics, "应该能提取图片内容"
    await result.ensure_downloads_complete()
    logger.success("NGA帖子解析成功")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
