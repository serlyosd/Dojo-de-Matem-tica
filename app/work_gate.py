from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar


T = TypeVar("T")


class WorkBusyError(RuntimeError):
    pass


class WorkTimeoutError(RuntimeError):
    pass


class WorkCancelledError(RuntimeError):
    pass


class WorkGate:
    """Permite somente uma operação pesada e possibilita cancelá-la."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._current: asyncio.Task[object] | None = None

    @property
    def busy(self) -> bool:
        return self._lock.locked()

    async def run(self, operation: Callable[[], Awaitable[T]], timeout_seconds: float) -> T:
        if self._lock.locked():
            raise WorkBusyError("Outra leitura já está em andamento.")
        await self._lock.acquire()
        self._current = asyncio.current_task()
        try:
            return await asyncio.wait_for(operation(), timeout=timeout_seconds)
        except TimeoutError as exc:
            raise WorkTimeoutError("A tarefa ultrapassou o tempo seguro e foi encerrada.") from exc
        except asyncio.CancelledError as exc:
            raise WorkCancelledError("A tarefa foi cancelada.") from exc
        finally:
            self._current = None
            self._lock.release()

    def cancel(self) -> bool:
        if self._current is None or self._current.done():
            return False
        self._current.cancel()
        return True

