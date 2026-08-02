from functools import partial

from rich.progress import (
    Progress,
    BarColumn,
    TextColumn,
    DownloadColumn,
)

progress_bar: Progress = Progress(
    TextColumn("[bold blue]{task.description}", justify="right"),
    BarColumn(bar_width=None),
    "[progress.percentage]{task.percentage:>3.1f}%",
    "•",
    DownloadColumn(),
)


def add_progress_task(
    desc: str,
    total: int | None = None,
):
    task_id = progress_bar.add_task(description=desc, total=total)
    progress_bar.start_task(task_id)
    return partial(progress_bar.update, task_id)
