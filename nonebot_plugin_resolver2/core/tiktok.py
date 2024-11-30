import random
import execjs
import urllib.parse
import os

header = {
    'User-Agent': "Mozilla/5.0 (Linux; Android 8.0; Pixel 2 Build/OPD3.170816.012) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Mobile Safari/537.36 Edg/87.0.664.66"
}


def generate_x_bogus_url(url, headers):
    """
            生成抖音A-Bogus签名
            :param url: 视频链接
            :return: 包含X-Bogus签名的URL
            """
    # 调用JavaScript函数
    query = urllib.parse.urlparse(url).query
    abogus_file_path = f'{os.path.dirname(os.path.abspath(__file__))}/a-bogus.js'
    with open(abogus_file_path, 'r', encoding='utf-8') as abogus_file:
        abogus_file_path_transcoding = abogus_file.read()
    abogus = execjs.compile(abogus_file_path_transcoding).call('generate_a_bogus', query, headers['User-Agent'])
    # logger.info('生成的A-Bogus签名为: {}'.format(abogus))
    return url + "&a_bogus=" + abogus


def generate_random_str(self, randomlength=16):
    """
    根据传入长度产生随机字符串
    param :randomlength
    return:random_str
    """
    random_str = ''
    base_str = 'ABCDEFGHIGKLMNOPQRSTUVWXYZabcdefghigklmnopqrstuvwxyz0123456789='
    length = len(base_str) - 1
    for _ in range(randomlength):
        random_str += base_str[random.randint(0, length)]
    return random_str
