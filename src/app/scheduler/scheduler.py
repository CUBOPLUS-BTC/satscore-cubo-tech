"""TaskScheduler — lightweight cron-like background task runner.

Runs as a daemon thread and fires registered tasks at fixed intervals.
Task execution is isolated so one failing task never prevents others
from running.  Full execution history is kept per task (up to a
configurable limit) for diagnostics.
"""

from __future__ import annotations

import threading
import time
import traceback
from collections import deque
from typing import Callable, Dict, List, Optional


# Maximum history entries stored per task.
MAX_HISTORY_PER_TASK = 50
# Minimum interval the scheduler will accept (seconds).
MIN_INTERVAL = 1
# How often the scheduler main loop wakes to check for due tasks.
TICK_INTERVAL = 1  # second


class _TaskEntry:
    """Internal record for a registered task."""

    __slots__ = (
        "name", "func", "interval", "enabled",
        "last_run", "next_run", "run_count", "error_count",
        "history", "_lock",
    )

    def __init__(
        self,
        name: str,
        func: Callable,
        interval: int,
        enabled: bool,
    ) -> None:
        self.name = name
        self.func = func
        self.interval = interval
        self.enabled = enabled
        self.last_run: Optional[float] = None
        self.next_run: float = time.time() + interval
        self.run_count: int = 0
        self.error_count: int = 0
        self.history: deque = deque(maxlen=MAX_HISTORY_PER_TASK)
        self._lock = threading.Lock()

    def to_dict(self) -> dict:
        return {
            "name":        self.name,
            "interval":    self.interval,
            "enabled":     self.enabled,
            "last_run":    int(self.last_run) if self.last_run else None,
            "next_run":    int(self.next_run),
            "run_count":   self.run_count,
            "error_count": self.error_count,
        }


class TaskScheduler:
    """Cron-like in-process task scheduler.

    Usage
    -----
    ::

        scheduler = TaskScheduler()
        scheduler.register("cleanup", my_cleanup_fn, interval=300)
        scheduler.start()
        ...
        scheduler.stop()

    Thread safety
    -------------
    All public methods acquire an internal lock before modifying task
    state so they are safe to call from any thread.
    """

    def __init__(self) -> None:
        self._tasks: Dict[str, _TaskEntry] = {}
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the scheduler background thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._loop,
            name="task-scheduler",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        """Request the scheduler to stop and wait for the thread to exit."""
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=TICK_INTERVAL * 3)

    def is_running(self) -> bool:
        return self._running and self._thread is not None and self._thread.is_alive()

    # ------------------------------------------------------------------
    # Task registration
    # ------------------------------------------------------------------

    def register(
        self,
        name: str,
        func: Callable,
        interval: int,
        enabled: bool = True,
    ) -> None:
        """Register a recurring task.

        Parameters
        ----------
        name:
            Unique task identifier.
        func:
            Zero-argument callable to execute.
        interval:
            Seconds between executions.
        enabled:
            Whether the task should run.  Can be toggled later via
            :meth:`enable` / :meth:`disable`.

        Raises
        ------
        ValueError
            If *name* is already registered or *interval* is too small.
        """
        if interval < MIN_INTERVAL:
            raise ValueError(
                f"Interval must be at least {MIN_INTERVAL} second(s); got {interval}."
            )
        with self._lock:
            if name in self._tasks:
                raise ValueError(f"Task {name!r} is already registered.")
            self._tasks[name] = _TaskEntry(name, func, interval, enabled)

    def unregister(self, name: str) -> None:
        """Remove a task by name.  Raises ``KeyError`` if not found."""
        with self._lock:
            if name not in self._tasks:
                raise KeyError(f"Task {name!r} is not registered.")
            del self._tasks[name]

    def enable(self, name: str) -> None:
        """Enable a disabled task."""
        with self._lock:
            self._tasks[name].enabled = True
            # Reset next_run so it fires at the next interval from now.
            self._tasks[name].next_run = time.time() + self._tasks[name].interval

    def disable(self, name: str) -> None:
        """Disable a task so it is skipped during normal scheduling."""
        with self._lock:
            self._tasks[name].enabled = False

    def update_interval(self, name: str, interval: int) -> None:
        """Change the interval of a registered task."""
        if interval < MIN_INTERVAL:
            raise ValueError(f"Interval must be >= {MIN_INTERVAL}.")
        with self._lock:
            task = self._tasks[name]
            task.interval = interval
            task.next_run = time.time() + interval

    # ------------------------------------------------------------------
    # Immediate execution
    # ------------------------------------------------------------------

    def run_once(self, name: str) -> dict:
        """Execute *name* immediately in the calling thread.

        Returns a history entry dict with ``success``, ``error``,
        ``duration_ms``, and ``ran_at``.
        """
        with self._lock:
            task = self._tasks.get(name)
        if task is None:
            raise KeyError(f"Task {name!r} is not registered.")
        return self._execute(task)

    # ------------------------------------------------------------------
    # Status / history
    # ------------------------------------------------------------------

    def get_status(self) -> dict:
        """Return a snapshot of all registered tasks."""
        with self._lock:
            tasks = {name: task.to_dict() for name, task in self._tasks.items()}
        return {
            "running":    self.is_running(),
            "task_count": len(tasks),
            "tasks":      tasks,
            "timestamp":  int(time.time()),
        }

    def get_task_history(self, name: str, limit: int = 20) -> list:
        """Return the last *limit* execution history entries for *name*."""
        with self._lock:
            task = self._tasks.get(name)
        if task is None:
            raise KeyError(f"Task {name!r} is not registered.")
        with task._lock:
            entries = list(task.history)
        return entries[-limit:]

    # ------------------------------------------------------------------
    # Internal scheduler loop
    # ------------------------------------------------------------------

    def _loop(self) -> None:
        while self._running:
            now = time.time()
            due: List[_TaskEntry] = []

            with self._lock:
                for task in self._tasks.values():
                    if task.enabled and now >= task.next_run:
                        due.append(task)

            for task in due:
                t = threading.Thread(
                    target=self._execute,
                    args=(task,),
                    name=f"sched-{task.name}",
                    daemon=True,
                )
                t.start()

            time.sleep(TICK_INTERVAL)

    # ------------------------------------------------------------------
    # Task execution
    # ------------------------------------------------------------------

    def _execute(self, task: _TaskEntry) -> dict:
        """Run *task.func* and record the result in the history deque."""
        ran_at = time.time()
        start = ran_at
        error_msg: Optional[str] = None
        success = False

        try:
            task.func()
            success = True
        except Exception as exc:
            error_msg = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"

        duration_ms = int((time.time() - start) * 1000)

        entry = {
            "ran_at":      int(ran_at),
            "duration_ms": duration_ms,
            "success":     success,
            "error":       error_msg,
        }

        with task._lock:
            task.run_count += 1
            task.last_run = ran_at
            task.next_run = ran_at + task.interval
            if not success:
                task.error_count += 1
            task.history.append(entry)

        return entry
