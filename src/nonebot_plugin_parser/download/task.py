from typing import Any, TypeVar, ParamSpec
from asyncio import Task, create_task
from pathlib import Path
from functools import wraps
from collections.abc import Callable, Coroutine


class PathTask:
    def __init__(self, path_task: Path | Task[Path]):
        self._path_task = path_task
        self._resolved_path: Path | None = None

    async def get(self) -> Path:
        if self._resolved_path is not None:
            return self._resolved_path

        if isinstance(self._path_task, Path):
            self._resolved_path = self._path_task
            return self._resolved_path

        self._resolved_path = await self._path_task
        return self._resolved_path

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
        if isinstance(self._path_task, Path):
            return self._path_task.as_uri()
        elif self._resolved_path is not None:
            return self._resolved_path.as_uri()
        return None

    def __repr__(self) -> str:
        if isinstance(self._path_task, Path):
            return f"(path={self._path_task.name})"
        else:
            return f"(task={self._path_task.get_name()}, done={self._path_task.done()})"


class OptionalPathTask:
    """封装可选的 PathTask, 提供便捷的 API 避免频繁判空"""

    def __init__(self, path_task: PathTask | None = None):
        self._path_task = path_task

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
        if self._path_task is None:
            return "(None)"
        return f"({self._path_task})"


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
