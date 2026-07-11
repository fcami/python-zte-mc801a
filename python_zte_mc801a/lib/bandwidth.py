"""Active download-bandwidth measurement.

This firmware exposes no realtime throughput field (the goform traffic-stats
fields read empty), so achievable download bandwidth is measured directly by
fetching a test file from a configured fast mirror, capped by a maximum byte
count and a maximum duration.
"""
import time

import requests

DEFAULT_CHUNK = 65536


def measure_bandwidth(
    url: str,
    max_bytes: int = 50_000_000,
    max_seconds: float = 20.0,
    chunk_size: int = DEFAULT_CHUNK,
    timeout: float = 10.0,
) -> dict:
    """Download from ``url`` (streamed) and return a measurement dict.

    Stops as soon as either ``max_bytes`` have been read or ``max_seconds``
    have elapsed since the first received byte. Timing starts at the first
    byte so connection setup / time-to-first-byte does not depress the result.

    Returns ``{mbps, bytes, seconds, url, capped_by}`` where ``capped_by`` is
    one of ``"bytes"``, ``"seconds"``, ``"complete"`` (server ended first), or
    ``"empty"`` (no body received).
    """
    total = 0
    start = None
    capped_by = "complete"
    with requests.get(url, stream=True, timeout=timeout) as resp:
        resp.raise_for_status()
        for chunk in resp.iter_content(chunk_size=chunk_size):
            if not chunk:
                continue
            if start is None:
                start = time.monotonic()
            total += len(chunk)
            if total >= max_bytes:
                capped_by = "bytes"
                break
            if time.monotonic() - start >= max_seconds:
                capped_by = "seconds"
                break

    if start is None:
        return {"mbps": 0.0, "bytes": 0, "seconds": 0.0, "url": url, "capped_by": "empty"}

    seconds = max(time.monotonic() - start, 1e-9)
    mbps = (total * 8) / seconds / 1_000_000
    return {
        "mbps": round(mbps, 2),
        "bytes": total,
        "seconds": round(seconds, 3),
        "url": url,
        "capped_by": capped_by,
    }
