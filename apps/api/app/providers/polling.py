"""Shared polling utility for async video generation providers.

All video APIs follow the same pattern:
  1. POST to create a generation job → get a job ID
  2. GET status in a loop until completed/failed/timed out

This module provides `poll_until_complete` to DRY that loop.
"""

import asyncio
import logging
from collections.abc import Callable

import httpx

logger = logging.getLogger(__name__)

# Defaults (can be overridden per-call)
DEFAULT_MAX_POLL_SEC = 180.0
DEFAULT_INTERVAL_INITIAL = 2.0
DEFAULT_INTERVAL_CAP = 10.0
DEFAULT_BACKOFF_FACTOR = 2.0


class PollTimeout(Exception):
    pass


class PollFailed(Exception):
    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


async def poll_until_complete(
    client: httpx.AsyncClient,
    poll_url: str,
    headers: dict,
    *,
    is_complete: Callable[[dict], bool],
    is_failed: Callable[[dict], bool],
    extract_error: Callable[[dict], str] = lambda d: "Generation failed.",
    max_poll_sec: float = DEFAULT_MAX_POLL_SEC,
    interval_initial: float = DEFAULT_INTERVAL_INITIAL,
    interval_cap: float = DEFAULT_INTERVAL_CAP,
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
    method: str = "GET",
) -> dict:
    """Poll a URL until the response indicates completion or failure.

    Args:
        client: An open httpx.AsyncClient.
        poll_url: The URL to poll.
        headers: Headers to send with each request.
        is_complete: Callable that returns True when the job is done.
        is_failed: Callable that returns True when the job has failed.
        extract_error: Callable to pull an error message from a failed response.
        max_poll_sec: Maximum total seconds to poll before raising PollTimeout.
        interval_initial: Starting interval between polls (seconds).
        interval_cap: Maximum interval between polls (seconds).
        backoff_factor: Multiplier applied to interval after each poll.
        method: HTTP method for polling (GET or POST).

    Returns:
        The final JSON response body on success.

    Raises:
        PollTimeout: If max_poll_sec is exceeded.
        PollFailed: If the provider reports failure.
    """
    elapsed = 0.0
    interval = interval_initial

    while elapsed < max_poll_sec:
        await asyncio.sleep(interval)
        elapsed += interval

        if method == "GET":
            resp = await client.get(poll_url, headers=headers)
        else:
            resp = await client.post(poll_url, headers=headers)

        if resp.status_code != 200:
            raise PollFailed(f"Poll request failed ({resp.status_code}): {resp.text[:200]}")

        data = resp.json()

        if is_complete(data):
            return data
        if is_failed(data):
            raise PollFailed(extract_error(data))

        interval = min(interval * backoff_factor, interval_cap)

    raise PollTimeout(f"Polling timed out after {max_poll_sec}s")
