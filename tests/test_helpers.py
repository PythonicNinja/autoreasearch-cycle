from __future__ import annotations

import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from autoresearch_cycle.experiment_io import append_json_list, utc_now_iso, write_json
from autoresearch_cycle.lighthouse import LighthouseConfig, LighthouseRunner
from autoresearch_cycle.readiness import wait_for_url


def test_utc_now_iso_uses_utc_z_suffix() -> None:
    assert utc_now_iso().endswith("Z")


def test_write_json_and_append_json_list(tmp_path: Path) -> None:
    path = tmp_path / "runs.json"

    write_json(path, [{"iteration": 1}])
    items = append_json_list(path, {"iteration": 2})

    assert items == [{"iteration": 1}, {"iteration": 2}]


def test_wait_for_url_returns_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    class Response:
        status = 200

        def __enter__(self) -> Response:
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

    monkeypatch.setattr(urllib.request, "urlopen", lambda request, timeout: Response())

    wait_for_url("http://localhost:4321", total_timeout_seconds=1, request_timeout_seconds=1)


def test_wait_for_url_raises_with_last_error(monkeypatch: pytest.MonkeyPatch) -> None:
    ticks = iter([0.0, 0.5, 2.0])

    monkeypatch.setattr(time, "monotonic", lambda: next(ticks))
    monkeypatch.setattr(time, "sleep", lambda _: None)

    def fail(request, timeout):
        raise urllib.error.URLError("boom")

    monkeypatch.setattr(urllib.request, "urlopen", fail)

    with pytest.raises(RuntimeError, match="boom"):
        wait_for_url("http://localhost:4321", total_timeout_seconds=1, request_timeout_seconds=1)


def test_lighthouse_runner_warms_up_and_runs_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    commands: list[list[str]] = []

    def fake_run(
        command,
        *,
        stdin,
        capture_output,
        text,
        cwd,
        timeout,
        check,
    ):
        del stdin, capture_output, text, timeout, check
        commands.append(command)
        assert cwd == tmp_path
        if command[-1] == "--version":
            return subprocess.CompletedProcess(command, 0, stdout="12.0.0", stderr="")
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=(
                '{"categories":{"accessibility":{"score":0.9},"performance":{"score":0.8}}}'
            ),
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    runner = LighthouseRunner(
        LighthouseConfig(
            cwd=tmp_path,
            url="http://localhost:4321",
            categories="accessibility,performance",
            chrome_flags="--headless=new",
            setup_timeout_seconds=10,
            timeout_seconds=10,
        )
    )

    report = runner.run_report()

    assert runner.prepared is True
    assert commands[0] == ["npx", "--yes", "lighthouse", "--version"]
    assert commands[1][:4] == ["npx", "--yes", "lighthouse", "http://localhost:4321"]
    assert report["categories"]["performance"]["score"] == 0.8
