import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import pytest

from app.config import settings
from app.webapp.auth import InitDataError, validate_init_data


def _sign_init_data(fields: dict, bot_token: str) -> str:
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    return urlencode({**fields, "hash": computed_hash})


def _valid_fields(auth_date: int | None = None) -> dict:
    return {
        "auth_date": str(auth_date if auth_date is not None else int(time.time())),
        "query_id": "AAabc123",
        "user": json.dumps({"id": 12345, "username": "tester", "first_name": "Test"}),
    }


def test_validates_correctly_signed_init_data():
    init_data = _sign_init_data(_valid_fields(), settings.bot_token)

    result = validate_init_data(init_data)

    assert result["user"]["id"] == 12345
    assert result["user"]["username"] == "tester"


def test_rejects_tampered_data():
    init_data = _sign_init_data(_valid_fields(), settings.bot_token)
    tampered = init_data.replace("tester", "attacker")

    with pytest.raises(InitDataError):
        validate_init_data(tampered)


def test_rejects_wrong_bot_token_signature():
    init_data = _sign_init_data(_valid_fields(), "wrong-token")

    with pytest.raises(InitDataError):
        validate_init_data(init_data)


def test_rejects_expired_auth_date():
    old_auth_date = int(time.time()) - 100_000
    init_data = _sign_init_data(_valid_fields(auth_date=old_auth_date), settings.bot_token)

    with pytest.raises(InitDataError):
        validate_init_data(init_data)


def test_rejects_empty_string():
    with pytest.raises(InitDataError):
        validate_init_data("")


def test_rejects_missing_user_field():
    fields = {"auth_date": str(int(time.time())), "query_id": "AAabc123"}
    init_data = _sign_init_data(fields, settings.bot_token)

    with pytest.raises(InitDataError):
        validate_init_data(init_data)
