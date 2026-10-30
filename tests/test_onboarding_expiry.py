"""Onboarding 3 kun amal qiladi, keyin Mini App uni yana ochadi."""

from datetime import UTC, datetime, timedelta

from app.db.models import User
from app.webapp import api


def test_onboarding_is_valid_for_three_days() -> None:
    now = datetime.now(UTC)

    assert not api._onboarding_valid(User(onboarding_done_at=None))
    assert api._onboarding_valid(User(onboarding_done_at=now - timedelta(days=2, hours=23)))
    assert not api._onboarding_valid(User(onboarding_done_at=now - timedelta(days=3, minutes=1)))
