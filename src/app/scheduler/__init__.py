"""Background task scheduler for the Magma API.

Provides a lightweight cron-like daemon thread (TaskScheduler) and a
library of predefined maintenance and alerting tasks (tasks module).

Quick start
-----------
::

    from app.scheduler import build_default_scheduler

    scheduler = build_default_scheduler(
        price_aggregator=my_price_svc,
        webhook_dispatcher=my_dispatcher,
    )
    scheduler.start()
"""

from .scheduler import TaskScheduler
from .tasks import build_default_scheduler

__all__ = ["TaskScheduler", "build_default_scheduler"]
