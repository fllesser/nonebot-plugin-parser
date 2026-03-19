from typing import Any
from asyncio import Task, create_task
from pathlib import Path
from collections.abc import Callable, Coroutine


class PathTask:
    __slots__ = ("_path", "_task")

    def __init__(
        self,
        task: Task[Path] | Coroutine[Any, Any, Path],
    ):
        if isinstance(task, Task):
            self._task: Task[Path] = task
        else:
            self._task = create_task(task, name=task.__name__)
        self._path: Path | None = None

    async def get(self) -> Path:
        if self._path is not None:
            return self._path

        self._path = await self._task
        return self._path

    async def safe_get(
        self,
        on_error: Callable[[Exception], None] | None = None,
    ) -> Path | None:
        try:
            return await self.get()
        except Exception as e:
            if on_error is not None:
                on_error(e)
            return None

    @property
    async def uri(self) -> str | None:
        path = await self.safe_get()
        if path is not None:
            return path.as_uri()
        return None

    def __repr__(self) -> str:
        if self._path is not None:
            return f"PathTask(path={self._path.name})"
        else:
            return f"PathTask(task={self._task.get_name()}, done={self._task.done()})"
