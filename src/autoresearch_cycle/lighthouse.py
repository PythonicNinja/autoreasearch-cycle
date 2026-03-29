from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class LighthouseConfig:
    cwd: Path
    url: str
    categories: str
    chrome_flags: str
    setup_timeout_seconds: int = 600
    timeout_seconds: int = 180


class LighthouseRunner:
    def __init__(self, config: LighthouseConfig) -> None:
        self.config = config
        self.prepared = False

    def ensure_ready(self) -> None:
        if self.prepared:
            return

        local_binary = self.config.cwd / "node_modules/.bin/lighthouse"
        if local_binary.exists():
            self.prepared = True
            return

        warmup_command = ["npx", "--yes", "lighthouse", "--version"]
        try:
            result = subprocess.run(
                warmup_command,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                cwd=self.config.cwd,
                timeout=self.config.setup_timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                f"Lighthouse setup timed out after {self.config.setup_timeout_seconds} seconds. "
                f'Run manually: cd "{self.config.cwd}" && npx --yes lighthouse --version'
            ) from exc

        if result.returncode != 0:
            raise RuntimeError(
                result.stderr
                or result.stdout
                or "Lighthouse setup failed. "
                f'Run manually: cd "{self.config.cwd}" && npx --yes lighthouse --version'
            )

        self.prepared = True

    def command(self) -> list[str]:
        local_binary = self.config.cwd / "node_modules/.bin/lighthouse"
        executable = str(local_binary) if local_binary.exists() else "npx"
        command = [executable]
        if executable == "npx":
            command.extend(["--yes", "lighthouse"])
        command.extend(
            [
                self.config.url,
                "--output=json",
                "--quiet",
                f"--only-categories={self.config.categories}",
                f"--chrome-flags={self.config.chrome_flags}",
            ]
        )
        return command

    def run_report(self) -> dict[str, Any]:
        self.ensure_ready()
        command = self.command()
        try:
            result = subprocess.run(
                command,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                cwd=self.config.cwd,
                timeout=self.config.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                f"Lighthouse timed out after {self.config.timeout_seconds} seconds "
                f"for {self.config.url}. Command: {' '.join(command)}"
            ) from exc

        if result.returncode != 0:
            raise RuntimeError(
                result.stderr
                or result.stdout
                or "Lighthouse failed. If this is the first run, try: "
                f'cd "{self.config.cwd}" && npx --yes lighthouse --version'
            )

        return json.loads(result.stdout)
