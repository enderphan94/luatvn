"""HTTP helpers — retry logic cho transient errors."""
from __future__ import annotations

import time
from typing import Optional

import requests

# Status codes coi là transient (server-side, có thể retry)
TRANSIENT_STATUS = {500, 502, 503, 504, 408, 429}


def get_with_retry(
    session: requests.Session,
    url: str,
    params: Optional[dict] = None,
    timeout: int = 20,
    retries: int = 2,
    backoff: float = 1.5,
    **kwargs,
) -> requests.Response:
    """GET với retry cho transient errors (5xx, timeout, connection error).

    Backoff exponential: backoff^attempt giây. Không retry cho 4xx (client error).
    Raise last exception nếu hết retry.
    """
    last_exc: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            r = session.get(url, params=params, timeout=timeout, **kwargs)
            if r.status_code in TRANSIENT_STATUS:
                last_exc = requests.HTTPError(
                    f"Transient HTTP {r.status_code} for {url}"
                )
                if attempt < retries:
                    time.sleep(backoff ** attempt)
                    continue
                r.raise_for_status()
            return r
        except (requests.Timeout, requests.ConnectionError) as e:
            last_exc = e
            if attempt < retries:
                time.sleep(backoff ** attempt)
                continue
            raise
    if last_exc:
        raise last_exc
    raise RuntimeError("get_with_retry exited without response")
