from __future__ import annotations

import time
import urllib.error
import urllib.request


def wait_for_url(
    url: str,
    total_timeout_seconds: int,
    request_timeout_seconds: int,
    user_agent: str = "autoresearch-cycle-check",
) -> None:
    deadline = time.monotonic() + total_timeout_seconds
    last_error: Exception | None = None

    while time.monotonic() < deadline:
        try:
            request = urllib.request.Request(
                url,
                method="HEAD",
                headers={"User-Agent": user_agent},
            )
            with urllib.request.urlopen(request, timeout=request_timeout_seconds) as response:
                if 200 <= response.status < 500:
                    return
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = exc
            time.sleep(1)

    detail = f" ({last_error})" if last_error else ""
    raise RuntimeError(f"URL is not reachable at {url}{detail}")
