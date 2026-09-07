"""Process-local daily request counters for metered Claude models.

Haiku is pay-per-use. SIE caps Anthropic at 25 RPD so a local-LLM outage cannot
burn the monthly budget. BRA enforces the same default for claude-haiku-*.
Sonnet/Opus are listed in the UI catalog but have no BRA daily cap.
UTC day, matching SIE anthropic daily_reset_timezone.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_HAIKU_RPD = 25
_HAIKU_PREFIX = "claude-haiku"

_lock = asyncio.Lock()
_day_utc = ""
_counts: dict[str, int] = {}
_path: Path | None = None


def _today_utc() -> str:
    return datetime.now(UTC).date().isoformat()


def configure_budget_file(path: Path | None) -> None:
    """Tests: point the JSON ledger at a temp file and drop in-memory counts."""
    global _path, _day_utc, _counts
    _path = path
    _day_utc = ""
    _counts = {}
    if path is not None and path.is_file():
        _load_unlocked()


def _settings_path() -> Path | None:
    try:
        from app.core.config import get_settings

        raw = getattr(get_settings(), "haiku_rpd_path", "") or ""
    except Exception:
        raw = ""
    if not isinstance(raw, str):
        raw = ""
    text = raw.strip()
    if not text:
        return Path("llm_daily_rpd.json")
    return Path(text)


def _load_unlocked() -> None:
    global _day_utc, _counts
    path = _path or _settings_path()
    if path is None or not path.is_file():
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        logger.warning("llm daily budget file unreadable: %s", e)
        return
    if not isinstance(data, dict):
        return
    day = str(data.get("day") or "")
    counts = data.get("counts") or {}
    if day != _today_utc():
        _day_utc = _today_utc()
        _counts = {}
        return
    _day_utc = day
    _counts = {
        str(k): int(v) for k, v in counts.items() if isinstance(v, (int, float)) and int(v) >= 0
    }


def _save_unlocked() -> None:
    path = _path if _path is not None else _settings_path()
    if path is None:
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload: dict[str, Any] = {"day": _day_utc or _today_utc(), "counts": _counts}
        path.write_text(json.dumps(payload), encoding="utf-8")
    except OSError as e:
        logger.warning("llm daily budget file not written: %s", e)


def _roll_day_unlocked() -> None:
    global _day_utc, _counts
    today = _today_utc()
    if _day_utc != today:
        if not _day_utc:
            _load_unlocked()
        if _day_utc != today:
            _day_utc = today
            _counts = {}


def rpd_limit_for_model(model: str, settings: object | None = None) -> int | None:
    """Daily cap for this Claude id, or None if BRA does not meter it."""
    if not str(model).startswith(_HAIKU_PREFIX):
        return None
    limit = DEFAULT_HAIKU_RPD
    if settings is not None:
        raw = getattr(settings, "haiku_rpd", DEFAULT_HAIKU_RPD)
        if isinstance(raw, int):
            limit = raw
        elif isinstance(raw, str) and raw.strip().isdigit():
            limit = int(raw.strip())
    else:
        try:
            from app.core.config import get_settings

            raw = get_settings().haiku_rpd
            if isinstance(raw, int):
                limit = raw
        except Exception:
            pass
    return max(0, limit)


def used_today(model: str) -> int:
    _roll_day_unlocked()
    return int(_counts.get(model, 0))


async def try_reserve(model: str, limit: int) -> bool:
    """Return True if this call may proceed. limit 0 means never."""
    async with _lock:
        _roll_day_unlocked()
        used = int(_counts.get(model, 0))
        if used >= limit:
            return False
        _counts[model] = used + 1
        _save_unlocked()
        return True


async def release(model: str) -> None:
    """Undo a reserve when the upstream call failed before a billed completion."""
    async with _lock:
        _roll_day_unlocked()
        used = int(_counts.get(model, 0))
        if used > 0:
            _counts[model] = used - 1
            _save_unlocked()
