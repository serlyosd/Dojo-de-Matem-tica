import asyncio

import pytest

from app.work_gate import WorkBusyError, WorkCancelledError, WorkGate, WorkTimeoutError


def test_only_one_heavy_task_runs_at_once():
    async def scenario():
        gate = WorkGate()
        started = asyncio.Event()
        release = asyncio.Event()

        async def slow():
            started.set()
            await release.wait()
            return "ok"

        first = asyncio.create_task(gate.run(slow, 2))
        await started.wait()
        with pytest.raises(WorkBusyError):
            await gate.run(slow, 2)
        release.set()
        assert await first == "ok"

    asyncio.run(scenario())


def test_timeout_ends_task_and_releases_gate():
    async def scenario():
        gate = WorkGate()
        with pytest.raises(WorkTimeoutError):
            await gate.run(lambda: asyncio.sleep(1), 0.01)
        assert not gate.busy

    asyncio.run(scenario())


def test_current_task_can_be_cancelled():
    async def scenario():
        gate = WorkGate()
        started = asyncio.Event()

        async def slow():
            started.set()
            await asyncio.sleep(10)

        task = asyncio.create_task(gate.run(slow, 20))
        await started.wait()
        assert gate.cancel()
        with pytest.raises(WorkCancelledError):
            await task
        assert not gate.busy

    asyncio.run(scenario())
