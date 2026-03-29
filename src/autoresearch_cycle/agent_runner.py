from __future__ import annotations

import json
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from jsonschema import ValidationError
from jsonschema.validators import Draft202012Validator

AgentName = Literal["claude", "codex"]


@dataclass(frozen=True)
class StructuredAgentConfig:
    agent: AgentName
    cwd: Path
    timeout_seconds: int
    codex_bypass_approvals_and_sandbox: bool = True


def run_structured_output(
    prompt: str,
    schema: dict[str, Any],
    config: StructuredAgentConfig,
) -> dict[str, Any]:
    raw_output = _run_agent(prompt, schema, config)
    return parse_structured_output(raw_output, schema, config.agent)


def parse_structured_output(
    raw_output: str,
    schema: dict[str, Any],
    agent: AgentName,
) -> dict[str, Any]:
    payload = raw_output.strip()
    if not payload:
        raise RuntimeError(f"{agent} returned empty output")

    candidates = _collect_json_candidates(payload)
    validator = Draft202012Validator(schema)
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
            validator.validate(parsed)
        except ValidationError:
            continue

        return parsed

    raise RuntimeError(
        f"{agent} returned invalid output; expected JSON matching schema: {payload[:500]}"
    )


def _run_agent(
    prompt: str,
    schema: dict[str, Any],
    config: StructuredAgentConfig,
) -> str:
    if config.agent == "claude":
        return _run_claude(prompt, config)
    if config.agent == "codex":
        return _run_codex(prompt, schema, config)
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
    schema: dict[str, Any],
    config: StructuredAgentConfig,
) -> str:
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", suffix=".txt", delete=False
    ) as output_file:
        output_path = Path(output_file.name)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", suffix=".json", delete=False
    ) as schema_file:
        schema_path = Path(schema_file.name)
        schema_path.write_text(json.dumps(schema), encoding="utf-8")

    try:
        command = [
            "codex",
            "exec",
            "--output-last-message",
            str(output_path),
            "--output-schema",
            str(schema_path),
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
        schema_path.unlink(missing_ok=True)


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
