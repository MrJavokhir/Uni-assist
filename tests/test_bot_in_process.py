"""Bot admin panel bilan bitta jarayonda ishlashi (app/admin/main.py, lifespan).

Haqiqiy polling ishga tushirilmaydi: bir token bilan ikkinchi polling
prodakshendagi botdan xabarlarni tortib olardi. `run_bot` o'rniga soxta
korutina qo'yiladi.
"""

import asyncio

import pytest

import app.admin.main as admin_main
import app.bot.main as bot_main

pytestmark = pytest.mark.asyncio


async def test_bot_not_started_when_disabled(monkeypatch):
    """docker-compose va testlarda bot alohida — bu yerda ishga tushmasligi kerak."""
    started = False

    async def fake_run_bot(**_kwargs):
        nonlocal started
        started = True

    monkeypatch.setattr(bot_main, "run_bot", fake_run_bot)
    monkeypatch.setattr(admin_main.settings, "run_bot_in_process", False)

    async with admin_main.lifespan(admin_main.app):
        await asyncio.sleep(0)

    assert started is False


async def test_bot_started_and_cancelled_cleanly(monkeypatch):
    calls: dict = {}
    stopped = asyncio.Event()

    async def fake_run_bot(**kwargs):
        calls.update(kwargs)
        try:
            await asyncio.sleep(3600)
        finally:
            stopped.set()

    killed: list = []
    monkeypatch.setattr(bot_main, "run_bot", fake_run_bot)
    monkeypatch.setattr(admin_main.settings, "run_bot_in_process", True)
    monkeypatch.setattr(admin_main.os, "_exit", lambda code: killed.append(code))

    async with admin_main.lifespan(admin_main.app):
        await asyncio.sleep(0.05)
        # Signallarni uvicorn boshqaradi — bot ularga tegmasligi shart.
        assert calls == {"handle_signals": False}

    assert stopped.is_set(), "server to'xtaganda bot ham to'xtashi kerak"
    # Oddiy to'xtatish — "yiqildi" deb jarayon yopilmasligi kerak.
    assert killed == []


async def test_crashed_bot_terminates_process(monkeypatch):
    """Bot yiqilsa jarayon 1 kodi bilan yopiladi — Railway uni qayta ko'taradi.

    Busiz yiqilgan vazifa jimgina o'lib, veb-server "sog'lom" ko'rinardi,
    bot esa javob bermay qolardi.
    """

    async def fake_run_bot(**_kwargs):
        raise RuntimeError("Telegram'ga ulanib bo'lmadi")

    killed: list = []
    monkeypatch.setattr(bot_main, "run_bot", fake_run_bot)
    monkeypatch.setattr(admin_main.settings, "run_bot_in_process", True)
    monkeypatch.setattr(admin_main.os, "_exit", lambda code: killed.append(code))

    async with admin_main.lifespan(admin_main.app):
        await asyncio.sleep(0.05)

    # Noldan farqli kod: Railway'ning ON_FAILURE siyosati faqat shunda
    # konteynerni qayta ishga tushiradi.
    assert killed == [1]
