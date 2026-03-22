"""Chunked async streaming for DRS object bytes (backpressure-friendly reads).

Large files are read in fixed-size blocks on a thread pool so the event loop
stays responsive; each read is bounded by a timeout (Ferrum-style robustness).

Crypt4GH / re-encryption is intentionally out of scope here.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from pathlib import Path
from typing import BinaryIO

logger = logging.getLogger(__name__)

# Align with Ferrum DRS plaintext stream defaults (order-of-magnitude).
STREAM_CHUNK_BYTES = 64 * 1024
STREAM_READ_TIMEOUT_SEC = 120.0


async def _read_chunk(file_obj: BinaryIO, max_bytes: int) -> bytes:
    """Read up to max_bytes from a binary file object with timeout."""

    def _read() -> bytes:
        return file_obj.read(max_bytes)

    return await asyncio.wait_for(asyncio.to_thread(_read), timeout=STREAM_READ_TIMEOUT_SEC)


async def iter_object_bytes(
    path: Path,
    *,
    start: int = 0,
    end_inclusive: int | None = None,
) -> AsyncIterator[bytes]:
    """Yield file bytes from ``start`` through ``end_inclusive`` (inclusive).

    If ``end_inclusive`` is None, stream through end of file from ``start``.
    """
    stat = path.stat()
    file_size = stat.st_size
    if file_size == 0:
        return
    last = end_inclusive if end_inclusive is not None else file_size - 1
    if start < 0 or start >= file_size or last < start:
        logger.warning(
            "drs_stream invalid range start=%s end=%s size=%s",
            start,
            last,
            file_size,
        )
        return
    last = min(last, file_size - 1)
    remaining: int = last - start + 1

    def _open_and_seek() -> BinaryIO:
        fh = path.open("rb")
        fh.seek(start)
        return fh

    fh = await asyncio.to_thread(_open_and_seek)
    try:
        while remaining > 0:
            take = min(STREAM_CHUNK_BYTES, remaining)
            chunk = await _read_chunk(fh, take)
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk
    finally:

        def _close() -> None:
            fh.close()

        await asyncio.to_thread(_close)
