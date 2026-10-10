"""Mentor testlari uchun umumiy narsalar: soxta Telegram bot va sozlamalar.

Soxta bot faqat yozib boradi — kim nima yubordi, qaysi xabar tahrirlandi.
Testlar shu yozuvlarga qarab Telegram tomonida nima bo'lganini tekshiradi.
"""

from dataclasses import dataclass, field
from types import SimpleNamespace

import pytest
from aiogram.exceptions import TelegramBadRequest
from aiogram.methods import SendMessage

from app.db.models import Country, MentorLevel, MentorTopic, User
from app.services import mentor_service

GROUP_ID = -1001234567890


@dataclass
class Sent:
    chat_id: int
    text: str
    thread_id: int | None
    reply_markup: object
    reply_to: int | None
    message_id: int


@dataclass
class FakeBot:
    members: dict[int, str] = field(default_factory=dict)  # tg_id -> status
    usernames: dict[int, str] = field(default_factory=dict)
    deleted_threads: set[int] = field(default_factory=set)
    sent: list[Sent] = field(default_factory=list)
    edits: list[dict] = field(default_factory=list)
    deleted: list[int] = field(default_factory=list)
    reactions: list[int] = field(default_factory=list)
    topics_created: list[str] = field(default_factory=list)
    _next_message: int = 1000
    _next_thread: int = 10

    def __post_init__(self) -> None:
        self.session = SimpleNamespace(close=self._close)

    async def _close(self) -> None:
        pass

    async def create_forum_topic(self, chat_id, name, **kwargs):
        self._next_thread += 1
        self.topics_created.append(name)
        return SimpleNamespace(message_thread_id=self._next_thread, name=name)

    async def send_message(
        self, chat_id, text, message_thread_id=None, reply_markup=None, reply_parameters=None, **kw
    ):
        if message_thread_id is not None and message_thread_id in self.deleted_threads:
            raise TelegramBadRequest(
                method=SendMessage(chat_id=chat_id, text=text),
                message="Bad Request: message thread not found",
            )
        self._next_message += 1
        self.sent.append(
            Sent(
                chat_id=chat_id,
                text=text,
                thread_id=message_thread_id,
                reply_markup=reply_markup,
                reply_to=reply_parameters.message_id if reply_parameters else None,
                message_id=self._next_message,
            )
        )
        return SimpleNamespace(message_id=self._next_message, chat=SimpleNamespace(id=chat_id))

    async def edit_message_text(self, text, chat_id=None, message_id=None, reply_markup=None, **kw):
        self.edits.append(
            {"text": text, "message_id": message_id, "reply_markup": reply_markup}
        )

    async def delete_message(self, chat_id, message_id, **kw):
        self.deleted.append(message_id)

    async def set_message_reaction(self, chat_id, message_id, reaction=None, **kw):
        self.reactions.append(message_id)

    async def get_chat_member(self, chat_id, user_id, **kw):
        return SimpleNamespace(
            status=self.members.get(user_id, "left"),
            user=SimpleNamespace(id=user_id, username=self.usernames.get(user_id)),
        )

    # ---- yordamchilar
    def to_chat(self, chat_id: int) -> list[Sent]:
        return [s for s in self.sent if s.chat_id == chat_id]

    def has_claim_button(self, markup) -> bool:
        if markup is None or not hasattr(markup, "inline_keyboard"):
            return False
        return any(
            (b.callback_data or "").startswith("claim:")
            for row in markup.inline_keyboard
            for b in row
        )


@pytest.fixture
def mentor_settings(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "bot_token", "123:test")
    monkeypatch.setattr(settings, "mentor_group_id", GROUP_ID)
    monkeypatch.setattr(settings, "active_countries", "DE,KR")
    monkeypatch.setattr(settings, "question_monthly_limit", 3)
    monkeypatch.setattr(settings, "followup_limit", 3)
    monkeypatch.setattr(settings, "allowed_link_domains", ".de,.edu,.ac.uk,daad.de,uni-assist.de")
    monkeypatch.setattr(settings, "admin_telegram_id", 999)
    monkeypatch.setattr(settings, "webapp_url", "https://example.com/webapp/")
    return settings


async def add_country(session, code: str = "DE", name: str = "Germaniya") -> Country:
    country = Country(name_uz=name, name_ru=name, name_en=name, iso_code=code)
    session.add(country)
    await session.flush()
    return country


async def add_user(session, telegram_id: int = 500) -> User:
    user = User(telegram_id=telegram_id, username=f"u{telegram_id}")
    session.add(user)
    await session.flush()
    return user


QUESTION_TEXT = "Germaniyada magistraturaga hujjat topshirish uchun qaysi tartibda harakat qilish kerak?"
ANSWER_TEXT = (
    "Avval uni-assist.de orqali hujjatlaringizni tekshirtiring, keyin universitet "
    "portalida ariza to'ldiring. Odatda bu 4-6 hafta oladi."
)


async def make_question(session, user, **kwargs):
    params = {
        "country_code": "DE",
        "level": MentorLevel.MASTER,
        "topic": MentorTopic.ADMISSION,
        "text": QUESTION_TEXT,
    }
    params.update(kwargs)
    return await mentor_service.create_question(session, user, **params)
