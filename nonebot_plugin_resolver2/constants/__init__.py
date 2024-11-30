import importlib
import os
import pkgutil
# from nonebot import logger

# 获取当前包下的所有模块
package_dir = os.path.dirname(__file__)

# 模块列表，用于存储导入的模块
modules = []

# 遍历并导入包中的所有模块
for module_info in pkgutil.iter_modules([package_dir]):
    module_name = module_info.name
    # logger.info(f"Importing module: {module_name}")
    module = importlib.import_module(f".{module_name}", package=__name__)
    modules.append(module)

# logger.info(f"Imported modules: {[module.__name__ for module in modules]}")

# 动态导出每个模块中定义的常量
__all__ = []

for module in modules:
    # logger.info(f"Checking module: {module.__name__}")
    for name in dir(module):
        if name.isupper():  # 假设常量以大写字母命名
            # logger.info(f"Found constant: {name} in module {module.__name__}")
            globals()[name] = getattr(module, name)
            __all__.append(name)

# logger.info(f"Exported constants: {__all__}")
