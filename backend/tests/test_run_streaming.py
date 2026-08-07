"""
End-to-end tests for the streaming run pipeline.

The LLM is stubbed, so these exercise everything else for real: event
normalization, the run bus and its replay buffer, the SSE endpoint, and run
persistence. Running them costs nothing and needs no API quota.

    python -m pytest tests/ -v
"""

import asyncio
import json
import os
import sys
from typing import List

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.subhost import agent as executor  # noqa: E402
from models.run import RunStatus  # noqa: E402
from services.run_service import RunService  # noqa: E402


class FakeEvent:
    """Stand-in for an Agno RunResponse chunk."""

    def __init__(self, event: str, content=None, metrics=None):
        self.event = event
        self.content = content
        self.metrics = metrics


class FakeRunnable:
    """Minimal Agent/Team lookalike that emits a scripted event stream."""

    def __init__(self, name="Fake Agent", chunks=None, fail_with=None):
        self.name = name
        self.tools = []
        self.chunks = chunks or ["Hello", " ", "world"]
        self.fail_with = fail_with

    async def arun(self, prompt, stream=False, **kwargs):
        if not stream:
            return FakeEvent("RunCompleted", "".join(self.chunks))

        async def gen():
            yield FakeEvent("RunStarted", "Run started")
            yield FakeEvent("ToolCallStarted", None)
            yield FakeEvent("ToolCallCompleted", None)
            for chunk in self.chunks:
                if self.fail_with:
                    raise self.fail_with
                await asyncio.sleep(0)
                yield FakeEvent("RunResponse", chunk)
            yield FakeEvent(
                "RunCompleted",
                None,
                metrics={"input_tokens": [10, 5], "output_tokens": [7], "total_tokens": [22]},
            )

        return gen()


@pytest.fixture
def stub_build(monkeypatch):
    """Replace agent construction with a scripted fake."""

    def _install(runnable):
        async def fake_build(prompt, agent_configs, host_config, execution_mode, session_id):
            if not prompt:
                raise executor.AgentExecutionError("Prompt cannot be empty")
            return runnable, [runnable]

        monkeypatch.setattr(executor, "_build_runnable", fake_build)
        return runnable

    return _install


async def collect(gen) -> List[dict]:
    return [event async for event in gen]


@pytest.mark.asyncio
async def test_stream_emits_tokens_and_completes(stub_build):
    """Token deltas stream individually and assemble into the final output."""
    stub_build(FakeRunnable(chunks=["Unit ", "tests ", "catch ", "regressions."]))

    events = await collect(
        executor.stream_agent_task(prompt="test", agent_configs=[{"agent_id": 1}])
    )

    kinds = [e["type"] for e in events]
    assert kinds[0] == "started"
    assert kinds[-1] == "completed"
    assert kinds.count("token") == 4, f"expected 4 token events, got {kinds}"

    streamed = "".join(e["text"] for e in events if e["type"] == "token")
    assert streamed == "Unit tests catch regressions."
    assert events[-1]["output"] == "Unit tests catch regressions."


@pytest.mark.asyncio
async def test_stream_reports_tool_calls(stub_build):
    """Tool activity is surfaced so the UI can show what an agent is doing."""
    stub_build(FakeRunnable())

    events = await collect(
        executor.stream_agent_task(prompt="test", agent_configs=[{"agent_id": 1}])
    )

    tool_events = [e for e in events if e["type"] == "tool_call"]
    assert [e["status"] for e in tool_events] == ["started", "completed"]


@pytest.mark.asyncio
async def test_stream_extracts_token_usage(stub_build):
    """Per-message metric lists are summed into totals for cost attribution."""
    stub_build(FakeRunnable())

    events = await collect(
        executor.stream_agent_task(prompt="test", agent_configs=[{"agent_id": 1}])
    )

    usage = events[-1]["usage"]
    assert usage["input_tokens"] == 15  # 10 + 5
    assert usage["output_tokens"] == 7
    assert usage["total_tokens"] == 22


@pytest.mark.asyncio
async def test_stream_ends_with_error_event_on_failure(stub_build):
    """A mid-stream failure terminates with an error event, never silence."""
    stub_build(FakeRunnable(fail_with=RuntimeError("model exploded")))

    events = await collect(
        executor.stream_agent_task(prompt="test", agent_configs=[{"agent_id": 1}])
    )

    assert events[-1]["type"] == "error"
    assert "model exploded" in events[-1]["message"]


@pytest.mark.asyncio
async def test_setup_failure_yields_error_not_exception(stub_build):
    """Setup problems arrive as a terminal event so consumers see one contract."""
    stub_build(FakeRunnable())

    events = await collect(
        executor.stream_agent_task(prompt="", agent_configs=[{"agent_id": 1}])
    )

    assert len(events) == 1
    assert events[0]["type"] == "error"
    assert "empty" in events[0]["message"].lower()


@pytest.mark.asyncio
async def test_late_subscriber_receives_replayed_events():
    """Subscribing after a run starts still yields everything from the top."""
    from services.run_bus import RunChannel

    channel = RunChannel("replay-test")
    channel.publish({"type": "started"})
    channel.publish({"type": "token", "text": "a"})
    channel.publish({"type": "token", "text": "b"})

    received = []

    async def subscriber():
        async for event in channel.subscribe():
            received.append(event)

    task = asyncio.create_task(subscriber())
    await asyncio.sleep(0)

    channel.publish({"type": "completed", "output": "ab"})
    channel.close()
    await asyncio.wait_for(task, timeout=2)

    assert [e["type"] for e in received] == ["started", "token", "token", "completed"]


@pytest.mark.asyncio
async def test_two_subscribers_both_receive_events():
    """Fan-out: every subscriber sees the same stream."""
    from services.run_bus import RunChannel

    channel = RunChannel("fanout-test")
    a, b = [], []

    async def sub(sink):
        async for event in channel.subscribe():
            sink.append(event)

    tasks = [asyncio.create_task(sub(a)), asyncio.create_task(sub(b))]
    await asyncio.sleep(0)

    channel.publish({"type": "token", "text": "x"})
    channel.close()
    await asyncio.wait_for(asyncio.gather(*tasks), timeout=2)

    assert len(a) == 1 and len(b) == 1


def test_run_record_persists_lifecycle():
    """A run row captures status, output, duration, and usage."""
    record = RunService.create(prompt="persistence check", mode="single", agent_ids=[1])
    run_id = record["run_id"]
    assert record["status"] == RunStatus.PENDING

    RunService.mark_running(run_id)
    assert RunService.get(run_id)["status"] == RunStatus.RUNNING

    RunService.finish(
        run_id,
        RunStatus.COMPLETED,
        output="done",
        usage={"input_tokens": 3, "output_tokens": 4, "total_tokens": 7},
    )

    final = RunService.get(run_id)
    assert final["status"] == RunStatus.COMPLETED
    assert final["output"] == "done"
    assert final["total_tokens"] == 7
    assert final["duration_ms"] is not None and final["duration_ms"] >= 0
    assert final["finished_at"] is not None


@pytest.mark.asyncio
async def test_sse_endpoint_streams_tokens_over_http(stub_build, monkeypatch):
    """
    Drive the real SSE route in-process: POST /api/runs, then read the event
    stream and confirm tokens arrive individually and the run is persisted.
    """
    import httpx

    from app import app
    from services.run_bus import run_bus

    stub_build(FakeRunnable(chunks=["Streaming ", "works ", "end ", "to ", "end."]))

    # Skip the database lookups; this test is about the transport.
    from controllers import agent_execution_controller as aec

    monkeypatch.setattr(
        aec.AgentExecutionController, "_load_agents",
        staticmethod(lambda ids: [{"agent_id": 1, "name": "Fake", "config": {}}]),
    )

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        created = await client.post("/api/runs", json={"prompt": "go", "agentIds": [1]})
        assert created.status_code == 202
        run_id = created.json()["run_id"]

        # Let the background task publish before subscribing, to also exercise
        # the replay buffer.
        await asyncio.sleep(0.2)

        events = []
        async with client.stream("GET", f"/api/runs/{run_id}/events") as response:
            assert response.status_code == 200
            assert "text/event-stream" in response.headers["content-type"]
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    events.append(json.loads(line[6:]))
                    if events[-1]["type"] in ("completed", "error"):
                        break

    kinds = [e["type"] for e in events]
    assert kinds[-1] == "completed", f"stream ended with {kinds[-1]}: {events[-1]}"
    assert kinds.count("token") == 5, f"expected 5 token events over HTTP, got {kinds}"
    assert events[-1]["output"] == "Streaming works end to end."

    # And the run was durably recorded.
    for _ in range(20):
        record = RunService.get(run_id)
        if record["status"] in (RunStatus.COMPLETED, RunStatus.ERROR):
            break
        await asyncio.sleep(0.1)

    assert record["status"] == RunStatus.COMPLETED
    assert record["output"] == "Streaming works end to end."
    assert record["total_tokens"] == 22
    run_bus.discard(run_id)
