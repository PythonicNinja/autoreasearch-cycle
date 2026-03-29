from __future__ import annotations

import json
from datetime import datetime, timezone

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

from autoresearch_cycle.experiment_io import append_json_list, utc_now_iso, write_json
from autoresearch_cycle.readiness import wait_for_url


def build_experiment() -> dict[str, object]:
    return {
        "id": f"exp_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        "name": EXPERIMENT_NAME,
        "domain": DOMAIN_ID,
        "optimizer_agent": OPTIMIZER_AGENT,
        "max_iterations": MAX_ITERATIONS,
        "eval_threshold": EVAL_THRESHOLD,
        "created_at": utc_now_iso(),
    }


def dev_server_command() -> str:
    return f'cd "{BLOG_DIR}" && npm run dev'


def ensure_dev_server_ready() -> None:
    try:
        wait_for_url(
            LIGHTHOUSE_URL,
            total_timeout_seconds=DEV_SERVER_WAIT_SECONDS,
            request_timeout_seconds=DEV_SERVER_REQUEST_TIMEOUT_SECONDS,
            user_agent="autoresearch-blogui-check",
        )
    except RuntimeError as exc:
        raise RuntimeError(
            f"{exc}\nStart it in another terminal:\n  {dev_server_command()}"
        ) from exc


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
            "created_at": utc_now_iso(),
        }
        runs = append_json_list(runs_path, run_record)

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
