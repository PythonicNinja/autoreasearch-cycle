from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from config import (
    BLOG_DIR,
    DATA_DIR,
    DEV_SERVER_REQUEST_TIMEOUT_SECONDS,
    DEV_SERVER_WAIT_SECONDS,
    DOMAIN_ID,
    EVAL_THRESHOLD,
    EXPERIMENT_NAME,
    LIGHTHOUSE_URL,
    MAX_ITERATIONS,
    OPTIMIZER_AGENT,
)
from domain import BlogUIDomain


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def build_experiment() -> dict[str, object]:
    return {
        "id": f"exp_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        "name": EXPERIMENT_NAME,
        "domain": DOMAIN_ID,
        "optimizer_agent": OPTIMIZER_AGENT,
        "max_iterations": MAX_ITERATIONS,
        "eval_threshold": EVAL_THRESHOLD,
        "created_at": utc_now(),
    }


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def append_run(path: Path, run: dict[str, object]) -> list[dict[str, object]]:
    if path.exists():
        runs = json.loads(path.read_text(encoding="utf-8"))
    else:
        runs = []
    runs.append(run)
    write_json(path, runs)
    return runs


def dev_server_command() -> str:
    return f'cd "{BLOG_DIR}" && npm run dev'


def ensure_dev_server_ready() -> None:
    deadline = time.monotonic() + DEV_SERVER_WAIT_SECONDS
    last_error: Exception | None = None

    while time.monotonic() < deadline:
        try:
            request = urllib.request.Request(
                LIGHTHOUSE_URL,
                method="HEAD",
                headers={"User-Agent": "autoresearch-blogui-check"},
            )
            with urllib.request.urlopen(
                request, timeout=DEV_SERVER_REQUEST_TIMEOUT_SECONDS
            ) as response:
                if 200 <= response.status < 500:
                    return
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = exc
            time.sleep(1)

    detail = f" ({last_error})" if last_error else ""
    raise RuntimeError(
        f"Blog dev server is not reachable at {LIGHTHOUSE_URL}{detail}\n"
        f"Start it in another terminal:\n  {dev_server_command()}"
    )


def main() -> None:
    print("Start the blog dev server in another terminal:")
    print(f"  {dev_server_command()}\n")
    print(f"Optimizer agent: {OPTIMIZER_AGENT}")
    print(f"Checking blog dev server at {LIGHTHOUSE_URL}...", flush=True)
    ensure_dev_server_ready()
    print("Blog dev server is reachable.\n", flush=True)

    domain = BlogUIDomain()
    experiment = build_experiment()
    runs_path = DATA_DIR / f"{experiment['id']}.runs.json"
    experiment_path = DATA_DIR / f"{experiment['id']}.experiment.json"
    write_json(experiment_path, experiment)

    runs: list[dict[str, object]] = []
    for iteration in range(1, MAX_ITERATIONS + 1):
        print(f"\n=== ITERATION {iteration} ===")

        run_output = domain.optimize(domain.read_policy(), iteration)
        print(f"Change: {run_output.get('change')}")

        score = domain.evaluate(run_output)
        print(f"Score: {score:.2f}")

        accepted = score >= EVAL_THRESHOLD
        run_record = {
            "iteration": iteration,
            "output": run_output,
            "score": score,
            "accepted": accepted,
            "created_at": utc_now(),
        }
        runs = append_run(runs_path, run_record)

        if accepted:
            domain.commit(str(run_output["change"]), iteration)
            print("Accepted and committed")
        else:
            domain.rollback()
            print("Rejected, rollback")

    print("\n=== HISTORY ===")
    print(json.dumps(runs, indent=2))


if __name__ == "__main__":
    main()
