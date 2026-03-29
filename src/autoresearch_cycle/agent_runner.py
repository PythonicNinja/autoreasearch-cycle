from __future__ import annotations

import json
import subprocess
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, TypeVar

AgentName = Literal["claude", "codex"]
T = TypeVar("T")


@dataclass(frozen=True)
class StructuredAgentConfig:
    agent: AgentName
    cwd: Path
    timeout_seconds: int
    codex_bypass_approvals_and_sandbox: bool = True


def validate_required_fields(
    payload: dict[str, Any],
    *,
    string_fields: tuple[str, ...] = (),
    string_list_fields: tuple[str, ...] = (),
) -> dict[str, Any]:
    validated: dict[str, Any] = {}

    for field in string_fields:
        value = payload.get(field)
        if not isinstance(value, str) or not value:
            raise ValueError(f"missing {field}")
        validated[field] = value

    for field in string_list_fields:
        value = payload.get(field)
        if not isinstance(value, list) or not value:
            raise ValueError(f"missing {field}")
        if not all(isinstance(item, str) and item for item in value):
            raise ValueError(f"invalid {field}")
        validated[field] = value

    return validated


def run_structured_output(
    prompt: str,
    validator: Callable[[dict[str, Any]], T],
    config: StructuredAgentConfig,
) -> T:
    raw_output = _run_agent(prompt, config)
    return parse_structured_output(raw_output, validator, config.agent)


def parse_structured_output(
    raw_output: str,
    validator: Callable[[dict[str, Any]], T],
    agent: AgentName,
) -> T:
    payload = raw_output.strip()
    if not payload:
        raise RuntimeError(f"{agent} returned empty output")

    candidates = _collect_json_candidates(payload)
    seen: set[str] = set()
    index = 0

    while index < len(candidates):
        candidate = candidates[index]
        index += 1

        if candidate in seen:
            continue
        seen.add(candidate)

        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue

        if not isinstance(parsed, dict):
            continue

        nested_result = parsed.get("result")
        if parsed.get("is_error") is True and isinstance(nested_result, str):
            raise RuntimeError(f"{agent} error: {nested_result}")
        if isinstance(nested_result, str) and nested_result.strip():
            candidates.extend(_collect_json_candidates(nested_result.strip()))

        try:
            return validator(parsed)
        except (TypeError, ValueError, KeyError):
            continue

    raise RuntimeError(
        f"{agent} returned invalid output for the expected shape: {payload[:500]}"
    )


def _run_agent(
    prompt: str,
    config: StructuredAgentConfig,
) -> str:
    if config.agent == "claude":
        return _run_claude(prompt, config)
    if config.agent == "codex":
        return _run_codex(prompt, config)
    raise ValueError(f"Unsupported agent={config.agent!r}. Use 'claude' or 'codex'.")


def _run_claude(prompt: str, config: StructuredAgentConfig) -> str:
    try:
        result = subprocess.run(
            [
                "claude",
                "--dangerously-skip-permissions",
                "-p",
                prompt,
            ],
            cwd=config.cwd,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=config.timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"Claude timed out after {config.timeout_seconds} seconds") from exc

    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout or "Claude command failed")
    if result.stdout.strip():
        return result.stdout
    if result.stderr.strip():
        return result.stderr
    raise RuntimeError("Claude returned no stdout or stderr output")


def _run_codex(
    prompt: str,
    config: StructuredAgentConfig,
) -> str:
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", suffix=".txt", delete=False
    ) as output_file:
        output_path = Path(output_file.name)

    try:
        command = [
            "codex",
            "exec",
            "--output-last-message",
            str(output_path),
        ]
        if config.codex_bypass_approvals_and_sandbox:
            command.append("--dangerously-bypass-approvals-and-sandbox")
        else:
            command.append("--full-auto")
        command.append(prompt)

        try:
            result = subprocess.run(
                command,
                cwd=config.cwd,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=config.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"Codex timed out after {config.timeout_seconds} seconds") from exc

        if result.returncode != 0:
            raise RuntimeError(result.stderr or result.stdout or "Codex command failed")
        return output_path.read_text(encoding="utf-8")
    finally:
        output_path.unlink(missing_ok=True)


def _collect_json_candidates(payload: str) -> list[str]:
    candidates = [payload]

    if payload.startswith("```") and payload.endswith("```"):
        lines = payload.splitlines()
        if len(lines) >= 3:
            candidates.append("\n".join(lines[1:-1]).strip())

    decoder = json.JSONDecoder()
    for index, char in enumerate(payload):
        if char != "{":
            continue
        try:
            parsed, end = decoder.raw_decode(payload[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            candidates.append(payload[index : index + end].strip())

    return candidates
