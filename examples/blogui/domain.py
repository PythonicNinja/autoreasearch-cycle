from __future__ import annotations

import json
import subprocess

from autoresearch_cycle.agent_runner import StructuredAgentConfig, run_structured_output
from config import (
    BLOG_BUILD_DIR,
    BLOG_DIR,
    BLOG_COMPONENTS_GIT_PATH,
    CODEX_BYPASS_APPROVALS_AND_SANDBOX,
    BLOG_EDIT_PATHS,
    BLOG_GLOBAL_CSS_PATH,
    BLOG_GLOBAL_CSS_GIT_PATH,
    BLOG_REPO_DIR,
    LIGHTHOUSE_CATEGORIES,
    LIGHTHOUSE_TIMEOUT_SECONDS,
    LIGHTHOUSE_URL,
    OPTIMIZER_AGENT,
    OPTIMIZER_TIMEOUT_SECONDS,
)

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "change": {"type": "string", "minLength": 1},
        "reason": {"type": "string", "minLength": 1},
        "files": {
            "type": "array",
            "items": {"type": "string", "minLength": 1},
        },
    },
    "required": ["change", "reason", "files"],
    "additionalProperties": False,
}

OPTIMIZER_CONFIG = StructuredAgentConfig(
    agent=OPTIMIZER_AGENT,
    cwd=BLOG_REPO_DIR,
    timeout_seconds=OPTIMIZER_TIMEOUT_SECONDS,
    codex_bypass_approvals_and_sandbox=CODEX_BYPASS_APPROVALS_AND_SANDBOX,
)


class BlogUIDomain:
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
{{"change": "what you changed", "reason": "why", "files": ["list"]}}
"""
        print(f"Running {OPTIMIZER_AGENT} optimizer...", flush=True)
        return run_structured_output(prompt, OUTPUT_SCHEMA, OPTIMIZER_CONFIG)

    def evaluate(self, run_output: dict[str, object]) -> float:
        del run_output
        print(f"Running Lighthouse against {LIGHTHOUSE_URL}...", flush=True)
        try:
            result = subprocess.run(
                [
                    "npx",
                    "lighthouse",
                    LIGHTHOUSE_URL,
                    "--output=json",
                    "--quiet",
                    f"--only-categories={LIGHTHOUSE_CATEGORIES}",
                ],
                capture_output=True,
                text=True,
                cwd=BLOG_DIR,
                timeout=LIGHTHOUSE_TIMEOUT_SECONDS,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                f"Lighthouse timed out after {LIGHTHOUSE_TIMEOUT_SECONDS} seconds "
                f"for {LIGHTHOUSE_URL}"
            ) from exc
        if result.returncode != 0:
            raise RuntimeError(result.stderr or result.stdout or "Lighthouse failed")
        scores = json.loads(result.stdout)
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
