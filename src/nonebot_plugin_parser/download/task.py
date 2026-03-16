from typing import Any, TypeVar, ParamSpec
from asyncio import Task, create_task
from pathlib import Path
from functools import wraps
from collections.abc import Callable, Coroutine


class PathTask:
    def __init__(self, task: Task[Path]):
        self._task: Task[Path] = task
        self._path: Path | None = None

    async def get(self) -> Path:
        if self._path is not None:
            return self._path

        self._path = await self._task
        return self._path

    def __await__(self):
        return self.get().__await__()

    async def safe_get(self) -> Path | None:
        """任务失败, 返回 None"""
        try:
            return await self.get()
        except Exception:
            return None

    @property
    def uri(self) -> str | None:
        return self._path.as_uri() if self._path is not None else None

    def __repr__(self) -> str:
        if self._path is not None:
            return f"PathTask(path={self._path.name})"
        else:
            return f"PathTask(task={self._task.get_name()}, done={self._task.done()})"


class OptionalPathTask:
    """封装可选的 PathTask, 提供便捷的 API 避免频繁判空"""

    def __init__(self, path_task: PathTask | None = None):
        self._path_task: PathTask | None = path_task

    async def get(self) -> Path | None:
        if self._path_task is None:
            return None
        return await self._path_task.get()

    def __await__(self):
        return self.get().__await__()

    async def safe_get(self) -> Path | None:
        """任务失败, 返回 None"""
        if self._path_task is None:
            return None
        return await self._path_task.safe_get()

    @property
    def uri(self) -> str | None:
        if self._path_task is None:
            return None
        return self._path_task.uri

    def __repr__(self) -> str:
        return f"{self._path_task}"


P = ParamSpec("P")
T = TypeVar("T")


def auto_task(func: Callable[P, Coroutine[Any, Any, Path]]) -> Callable[P, PathTask]:
    """装饰器：自动将异步函数调用转换为 Task, 完整保留类型提示"""

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> PathTask:
        coro = func(*args, **kwargs)
        name = " | ".join(str(arg) for arg in args if isinstance(arg, str))
        return PathTask(create_task(coro, name=func.__name__ + " | " + name))

    return wrapper
