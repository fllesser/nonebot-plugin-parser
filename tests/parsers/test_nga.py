"""测试NGA解析器"""

import pytest


@pytest.mark.asyncio
async def test_nga_parse():
    """测试NGA帖子解析"""
    from nonebot_plugin_parser.parsers.nga import NGAParser

    url = "https://nga.178.com/read.php?tid=45263995"
    parser = NGAParser()

    # 测试URL匹配
    matched = None
    for _, pattern in parser.patterns:
        import re

        match = re.search(pattern, url)
        if match:
            matched = match
            break

    assert matched is not None, "URL应该能被NGA解析器匹配"

    # 测试解析
    result = await parser.parse(matched)

    # 验证结果
    assert result.title, "应该能提取标题"
    assert result.url == url, "URL应该保持一致"
    assert result.author is not None, "应该能提取作者信息"
    assert result.timestamp is not None, "应该能提取发布时间"
    print(f"标题: {result.title}")
    print(f"作者: {result.author.name if result.author else 'N/A'}")
    print(f"时间: {result.timestamp}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
