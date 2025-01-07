import os
import pytest
import nonebot
from pytest_asyncio import is_async_test
# 导入适配器
from nonebot.adapters.onebot.v11 import Adapter as OnebotAdapter
from nonebug import NONEBOT_INIT_KWARGS

os.environ["ENVIRONMENT"] = "test"

def pytest_configure(config: pytest.Config):
    config.stash[NONEBOT_INIT_KWARGS] = {"secret": os.getenv("INPUT_SECRET")}

def pytest_collection_modifyitems(items: list[pytest.Item]):
    pytest_asyncio_tests = (item for item in items if is_async_test(item))
    session_scope_marker = pytest.mark.asyncio(loop_scope="session")
    for async_test in pytest_asyncio_tests:
        async_test.add_marker(session_scope_marker, append=False)

@pytest.fixture(scope="session", autouse=True)
async def after_nonebot_init(after_nonebot_init: None):
    # 加载适配器
    driver = nonebot.get_driver()
    driver.register_adapter(OnebotAdapter)

    # 加载插件
    nonebot.load_from_toml("pyproject.toml")
    