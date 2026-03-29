from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def append_json_list(path: Path, item: dict[str, Any]) -> list[dict[str, Any]]:
    items = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    if not isinstance(items, list):
        raise ValueError(f"Expected JSON list at {path}")
    items.append(item)
    write_json(path, items)
    return items
