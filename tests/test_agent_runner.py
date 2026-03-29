from __future__ import annotations

import pytest

from autoresearch_cycle.agent_runner import parse_structured_output


def validate_output(payload: dict[str, object]) -> dict[str, object]:
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

    return {"change": change, "reason": reason, "files": files}


def test_parse_structured_output_accepts_plain_json() -> None:
    payload = '{"change":"Adjust spacing","reason":"Improve readability","files":["a.css"]}'

    parsed = parse_structured_output(payload, validate_output, "claude")

    assert parsed["change"] == "Adjust spacing"


def test_parse_structured_output_extracts_json_from_text() -> None:
    payload = """
I made one focused tweak.

{"change":"Tune colors","reason":"Better contrast","files":["b.css"]}
"""

    parsed = parse_structured_output(payload, validate_output, "claude")

    assert parsed["files"] == ["b.css"]


def test_parse_structured_output_unwraps_nested_result() -> None:
    payload = (
        '{"type":"result","is_error":false,"result":"{'
        '\\"change\\":\\"Refine hero\\",'
        '\\"reason\\":\\"Clearer hierarchy\\",'
        '\\"files\\":[\\"hero.astro\\"]}"}'
    )

    parsed = parse_structured_output(payload, validate_output, "claude")

    assert parsed["reason"] == "Clearer hierarchy"


def test_parse_structured_output_raises_for_agent_error_wrapper() -> None:
    payload = '{"type":"result","is_error":true,"result":"Not logged in"}'

    with pytest.raises(RuntimeError, match="Not logged in"):
        parse_structured_output(payload, validate_output, "claude")


def test_parse_structured_output_rejects_invalid_shape() -> None:
    payload = '{"change":"Only one field"}'

    with pytest.raises(RuntimeError, match="invalid output"):
        parse_structured_output(payload, validate_output, "codex")
