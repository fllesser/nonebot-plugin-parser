from urllib.parse import parse_qs, urlparse


def parse_url_query(url: str, query_key: str) -> str:
    """从 url 的 query 参数中解析出 query_key 对应的值

    Args:
        url (str): url 地址
        query_key (str): query 参数的 key

    Raises:
        KeyError: url 中不存在 query_key 参数
        ValueError: url 中 query_key 参数值为空

    Returns:
        str: query_key 对应的值
    """
    url_res = urlparse(url)
    url_query = parse_qs(url_res.query, keep_blank_values=True)

    try:
        query_val = url_query[query_key][0]
    except KeyError:
        raise KeyError(f"url 中不存在 {query_key} 参数")

    if len(query_val) == 0:
        raise ValueError(f"url 中 {query_key} 参数值为空")

    return query_val


def escape_special_chars(json_str: str) -> str:
    """转义特殊字符

    Args:
        json_str (str): json 字符串

    Returns:
        str: 转义后的 json 字符串
    """
    return json_str.replace('\\\\"', '\\"').replace('\\"', '"')
