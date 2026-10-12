"""Asyncio-based task scheduler for background execution of ETL pipelines."""

import asyncio
from datetime import datetime, timezone
import logging
from typing import Any, Callable, Dict, List, Optional

from pybi.etl.executor import ETLExecutor, ETLResult

logger = logging.getLogger(__name__)


class ScheduledTask:
    """Represents a scheduled ETL execution job."""

    def __init__(
        self,
        task_id: str,
        dag: Dict[str, Any],
        interval_seconds: int,
        base_dir: Optional[str] = None,
        on_complete: Optional[Callable[[str, ETLResult], None]] = None,
    ) -> None:
        """Initialize ScheduledTask.

        Args:
            task_id: Unique task identifier.
            dag: Dict representing ETL DAG pipeline.
            interval_seconds: Execution interval in seconds.
            base_dir: Base data directory for file paths.
            on_complete: Callback invoked after each execution with (task_id, result).
        """
        self.task_id = task_id
        self.dag = dag
        self.interval_seconds = interval_seconds
        self.base_dir = base_dir
        self.on_complete = on_complete

        self.is_running = False
        self.run_count = 0
        self.last_run: Optional[str] = None
        self.last_result: Optional[ETLResult] = None
        self._async_task: Optional[asyncio.Task] = None

    async def _loop(self) -> None:
        """Main periodic execution loop."""
        while self.is_running:
            try:
                executor = ETLExecutor(base_dir=self.base_dir)
                # Execute DAG in default thread pool to avoid blocking asyncio loop
                result = await asyncio.to_thread(executor.execute, self.dag)
                self.run_count += 1
                self.last_run = datetime.now(timezone.utc).isoformat()
                self.last_result = result

                if self.on_complete:
                    try:
                        self.on_complete(self.task_id, result)
                    except Exception as err:
                        logger.error(f"Scheduled task callback error on '{self.task_id}': {err}")

            except Exception as err:
                logger.error(f"Scheduled task error executing '{self.task_id}': {err}")

            try:
                await asyncio.sleep(self.interval_seconds)
            except asyncio.CancelledError:
                break

    def start(self) -> None:
        """Start the background execution task."""
        if self.is_running:
            return
        self.is_running = True
        self._async_task = asyncio.create_task(self._loop())

    def stop(self) -> None:
        """Stop the background execution task."""
        self.is_running = False
        if self._async_task and not self._async_task.done():
            self._async_task.cancel()


class ETLScheduler:
    """ETLScheduler manages periodic background tasks for ETL pipeline DAGs."""

    def __init__(self) -> None:
        self.tasks: Dict[str, ScheduledTask] = {}

    def schedule_pipeline(
        self,
        task_id: str,
        dag: Dict[str, Any],
        interval_seconds: int,
        base_dir: Optional[str] = None,
        on_complete: Optional[Callable[[str, ETLResult], None]] = None,
    ) -> ScheduledTask:
        """Schedule a new periodic pipeline task or update an existing schedule.

        Args:
            task_id: Unique identifier for task schedule.
            dag: ETL DAG configuration.
            interval_seconds: Repeat interval in seconds.
            base_dir: Optional base directory for dataset files.
            on_complete: Optional completion callback.

        Returns:
            ScheduledTask: Scheduled task object.
        """
        if task_id in self.tasks:
            self.cancel_pipeline(task_id)

        task = ScheduledTask(
            task_id=task_id,
            dag=dag,
            interval_seconds=interval_seconds,
            base_dir=base_dir,
            on_complete=on_complete,
        )
        self.tasks[task_id] = task
        task.start()
        return task

    def cancel_pipeline(self, task_id: str) -> bool:
        """Cancel and remove a scheduled task.

        Args:
            task_id: Unique task identifier.

        Returns:
            bool: True if task was found and canceled.
        """
        task = self.tasks.pop(task_id, None)
        if task:
            task.stop()
            return True
        return False

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get current status summary for a scheduled task.

        Args:
            task_id: Task identifier.

        Returns:
            Optional[Dict[str, Any]]: Task status metadata or None if not found.
        """
        task = self.tasks.get(task_id)
        if not task:
            return None
        return {
            "task_id": task.task_id,
            "is_running": task.is_running,
            "interval_seconds": task.interval_seconds,
            "run_count": task.run_count,
            "last_run": task.last_run,
            "last_status": task.last_result.status if task.last_result else None,
            "last_error": task.last_result.error if task.last_result else None,
        }

    def stop_all(self) -> None:
        """Stop all scheduled tasks."""
        for task_id in list(self.tasks.keys()):
            self.cancel_pipeline(task_id)


# Global singleton scheduler instance
default_scheduler = ETLScheduler()
