"""Onboarding bir marta tugatilsa, boshqa ochilmaydi (muddati yo'q)."""

from datetime import UTC, datetime, timedelta

from app.db.models import User
from app.webapp import api


def test_onboarding_stays_done_forever() -> None:
    now = datetime.now(UTC)

    assert not api._onboarding_valid(User(onboarding_done_at=None))
    assert api._onboarding_valid(User(onboarding_done_at=now - timedelta(days=2)))
    # Ilgari 3 kundan keyin qayta ochilardi.
    assert api._onboarding_valid(User(onboarding_done_at=now - timedelta(days=3, minutes=1)))
    assert api._onboarding_valid(User(onboarding_done_at=now - timedelta(days=400)))
