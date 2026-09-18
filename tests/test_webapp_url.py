from urllib.parse import parse_qs, urlparse

from app.bot.handlers.start import webapp_url


def test_adds_cache_busting_version():
    query = parse_qs(urlparse(webapp_url()).query)

    assert "v" in query
    assert query["v"][0].isdigit()


def test_version_is_stable_within_a_run():
    # Bitta ishga tushish davomida URL o'zgarmasligi kerak, aks holda har
    # /start uchun Telegram fayllarni qaytadan yuklab olardi.
    assert webapp_url() == webapp_url()


def test_keeps_base_path():
    parsed = urlparse(webapp_url())

    assert parsed.scheme in ("http", "https")
    assert parsed.path.endswith("/webapp/")
