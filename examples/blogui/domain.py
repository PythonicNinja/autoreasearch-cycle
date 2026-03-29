from __future__ import annotations

import subprocess

from config import (
    BLOG_BUILD_DIR,
    BLOG_COMPONENTS_GIT_PATH,
    BLOG_DIR,
    BLOG_EDIT_PATHS,
    BLOG_GLOBAL_CSS_GIT_PATH,
    BLOG_GLOBAL_CSS_PATH,
    BLOG_REPO_DIR,
    CODEX_BYPASS_APPROVALS_AND_SANDBOX,
    LIGHTHOUSE_CATEGORIES,
    LIGHTHOUSE_CHROME_FLAGS,
    LIGHTHOUSE_SETUP_TIMEOUT_SECONDS,
    LIGHTHOUSE_TIMEOUT_SECONDS,
    LIGHTHOUSE_URL,
    OPTIMIZER_AGENT,
    OPTIMIZER_TIMEOUT_SECONDS,
)

from autoresearch_cycle.agent_runner import StructuredAgentConfig, run_structured_output
from autoresearch_cycle.lighthouse import LighthouseConfig, LighthouseRunner

OUTPUT_EXAMPLE = '{"change": "what you changed", "reason": "why", "files": ["list"]}'

OPTIMIZER_CONFIG = StructuredAgentConfig(
    agent=OPTIMIZER_AGENT,
    cwd=BLOG_REPO_DIR,
    timeout_seconds=OPTIMIZER_TIMEOUT_SECONDS,
    codex_bypass_approvals_and_sandbox=CODEX_BYPASS_APPROVALS_AND_SANDBOX,
)
LIGHTHOUSE_CONFIG = LighthouseConfig(
    cwd=BLOG_DIR,
    url=LIGHTHOUSE_URL,
    categories=LIGHTHOUSE_CATEGORIES,
    chrome_flags=LIGHTHOUSE_CHROME_FLAGS,
    setup_timeout_seconds=LIGHTHOUSE_SETUP_TIMEOUT_SECONDS,
    timeout_seconds=LIGHTHOUSE_TIMEOUT_SECONDS,
)


class BlogUIDomain:
    def __init__(self) -> None:
        self._lighthouse = LighthouseRunner(LIGHTHOUSE_CONFIG)

    def read_policy(self) -> dict[str, object]:
        if not BLOG_GLOBAL_CSS_PATH.exists():
            raise FileNotFoundError(f"Expected stylesheet at {BLOG_GLOBAL_CSS_PATH}")

        css = BLOG_GLOBAL_CSS_PATH.read_text(encoding="utf-8")
        return {"css_hash": hash(css), "css_preview": css[:500]}

    def optimize(self, policy: dict[str, object], iteration: int) -> dict[str, object]:
        del policy
        prompt = f"""
UI autoresearch iteration {iteration}.
Read {BLOG_GLOBAL_CSS_GIT_PATH} and files in {BLOG_COMPONENTS_GIT_PATH}.
Make ONE focused improvement to readability or aesthetics.
Then run: cd {BLOG_BUILD_DIR} && npm run build
If build fails: git checkout {" ".join(BLOG_EDIT_PATHS)} and stop.
If build succeeds, return exactly one JSON object and nothing else:
{OUTPUT_EXAMPLE}
"""
        print(f"Running {OPTIMIZER_AGENT} optimizer...", flush=True)
        return run_structured_output(prompt, _validate_run_output, OPTIMIZER_CONFIG)

    def evaluate(self, run_output: dict[str, object]) -> float:
        del run_output
        if not self._lighthouse.prepared:
            print("Preparing Lighthouse CLI...", flush=True)
        print(f"Running Lighthouse against {LIGHTHOUSE_URL}...", flush=True)
        scores = self._lighthouse.run_report()
        a11y = scores["categories"]["accessibility"]["score"]
        perf = scores["categories"]["performance"]["score"]
        return (a11y + perf) / 2

    def rollback(self) -> None:
        subprocess.run(["git", "checkout", *BLOG_EDIT_PATHS], cwd=BLOG_REPO_DIR, check=False)

    def commit(self, change_desc: str, iteration: int) -> None:
        subprocess.run(["git", "add", *BLOG_EDIT_PATHS], cwd=BLOG_REPO_DIR, check=False)
        subprocess.run(
            ["git", "commit", "-m", f"ui(autoresearch iter-{iteration}): {change_desc}"],
            cwd=BLOG_REPO_DIR,
            check=False,
        )


def _validate_run_output(payload: dict[str, object]) -> dict[str, object]:
    change = payload.get("change")
    reason = payload.get("reason")
    files = payload.get("files")

    if not isinstance(change, str) or not change:
        raise ValueError("missing change")
    if not isinstance(reason, str) or not reason:
        raise ValueError("missing reason")
    if not isinstance(files, list) or not files:
        raise ValueError("missing files")
    if not all(isinstance(item, str) and item for item in files):
        raise ValueError("invalid files")

    return {
        "change": change,
        "reason": reason,
        "files": files,
    }
