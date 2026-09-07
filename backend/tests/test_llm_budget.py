"""Haiku daily request cap (UTC), SIE analog of anthropic rpd=25."""

from pathlib import Path

import pytest

from app.core.llm_budget import (
    configure_budget_file,
    release,
    rpd_limit_for_model,
    try_reserve,
    used_today,
)


def test_only_haiku_is_metered():
    settings = type("S", (), {"haiku_rpd": 25})()
    assert rpd_limit_for_model("claude-haiku-4-5", settings) == 25
    assert rpd_limit_for_model("claude-sonnet-5", settings) is None
    assert rpd_limit_for_model("claude-opus-5", settings) is None


@pytest.mark.asyncio
async def test_26th_reserve_fails_closed():
    for _ in range(25):
        assert await try_reserve("claude-haiku-4-5", 25)
    assert await try_reserve("claude-haiku-4-5", 25) is False
    assert used_today("claude-haiku-4-5") == 25


@pytest.mark.asyncio
async def test_limit_zero_never_reserves():
    assert await try_reserve("claude-haiku-4-5", 0) is False
    assert used_today("claude-haiku-4-5") == 0


@pytest.mark.asyncio
async def test_release_undoes_failed_upstream():
    assert await try_reserve("claude-haiku-4-5", 25)
    await release("claude-haiku-4-5")
    assert used_today("claude-haiku-4-5") == 0


@pytest.mark.asyncio
async def test_ledger_survives_reload(tmp_path: Path):
    path = tmp_path / "haiku-rpd.json"
    configure_budget_file(path)
    for _ in range(25):
        assert await try_reserve("claude-haiku-4-5", 25)
    configure_budget_file(path)
    assert used_today("claude-haiku-4-5") == 25
    assert await try_reserve("claude-haiku-4-5", 25) is False
