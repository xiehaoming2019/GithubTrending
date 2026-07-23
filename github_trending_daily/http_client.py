from __future__ import annotations

import json
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class HttpError(RuntimeError):
    pass


def request(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    json_body: dict[str, Any] | None = None,
    timeout: int = 30,
    retries: int = 2,
) -> bytes:
    request_headers = {
        "User-Agent": "github-trending-daily/0.1",
        "Accept-Language": "en-US,en;q=0.9",
        **(headers or {}),
    }
    body = None
    if json_body is not None:
        body = json.dumps(json_body, ensure_ascii=False).encode("utf-8")
        request_headers.setdefault("Content-Type", "application/json")

    for attempt in range(retries + 1):
        try:
            req = Request(url, data=body, headers=request_headers, method=method)
            with urlopen(req, timeout=timeout) as response:
                return response.read()
        except HTTPError as exc:
            retryable = exc.code in {429, 500, 502, 503, 504}
            if retryable and attempt < retries:
                retry_after = exc.headers.get("Retry-After")
                delay = int(retry_after) if retry_after and retry_after.isdigit() else 2**attempt
                time.sleep(min(delay, 10))
                continue
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise HttpError(f"HTTP {exc.code} for {url}: {detail}") from exc
        except (URLError, TimeoutError) as exc:
            if attempt < retries:
                time.sleep(2**attempt)
                continue
            raise HttpError(f"Request failed for {url}: {exc}") from exc

    raise HttpError(f"Request failed for {url}")


def get_text(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: int = 30,
) -> str:
    return request(url, headers=headers, timeout=timeout).decode("utf-8", errors="replace")


def get_json(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: int = 30,
) -> dict[str, Any]:
    return json.loads(get_text(url, headers=headers, timeout=timeout))


def post_json(
    url: str,
    payload: dict[str, Any],
    *,
    headers: dict[str, str] | None = None,
    timeout: int = 90,
) -> dict[str, Any]:
    response = request(
        url,
        method="POST",
        headers=headers,
        json_body=payload,
        timeout=timeout,
    )
    return json.loads(response.decode("utf-8", errors="replace"))

