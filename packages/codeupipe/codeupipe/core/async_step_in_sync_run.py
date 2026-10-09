"""Raised when the sync ``Pipeline.run()`` meets async work."""

__all__ = ["AsyncStepInSyncRun"]


class AsyncStepInSyncRun(RuntimeError):
    """``run()`` never starts an event loop; use ``run_async()`` for async steps."""
