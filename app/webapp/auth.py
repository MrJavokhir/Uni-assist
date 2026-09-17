"""Telegram Mini App initData tekshiruvi.

https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
"""

import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

from app.config import settings

MAX_INIT_DATA_AGE_SECONDS = 24 * 3600


class InitDataError(Exception):
    pass


def validate_init_data(init_data: str, *, max_age_seconds: int = MAX_INIT_DATA_AGE_SECONDS) -> dict:
    """initData satrini tekshiradi va {"user": {...}, "auth_date": int} qaytaradi."""
    if not init_data:
        raise InitDataError("initData bo'sh")

    try:
        parsed = dict(parse_qsl(init_data, strict_parsing=True))
    except ValueError as exc:
        raise InitDataError("initData formatini o'qib bo'lmadi") from exc

    received_hash = parsed.pop("hash", None)
    if not received_hash:
        raise InitDataError("hash yo'q")

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))

    secret_key = hmac.new(b"WebAppData", settings.bot_token.encode(), hashlib.sha256).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(computed_hash, received_hash):
        raise InitDataError("imzo mos emas")

    auth_date = int(parsed.get("auth_date", 0))
    if time.time() - auth_date > max_age_seconds:
        raise InitDataError("initData eskirgan")

    user_raw = parsed.get("user")
    if not user_raw:
        raise InitDataError("foydalanuvchi ma'lumoti yo'q")

    user = json.loads(user_raw)
    if "id" not in user:
        raise InitDataError("foydalanuvchi id'si yo'q")

    return {"user": user, "auth_date": auth_date}
