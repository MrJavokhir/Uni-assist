import asyncio
import contextlib
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqladmin import Admin
from starlette.responses import RedirectResponse, Response

from app.admin.auth import AdminAuth
from app.admin.csv_views import CatalogImportView
from app.admin.kit_views import AdmissionKitView
from app.admin.mentor_views import MentorComplaintsView, MentorQuestionsView
from app.admin.stats import StatsView
from app.admin.suggestions import SuggestionView
from app.admin.views import (
    AdmissionServiceAdmin,
    BalanceTransactionAdmin,
    BotAdminAdmin,
    CountryAdmin,
    FieldAdmin,
    PaymentAdmin,
    PaymentSettingsAdmin,
    ProgramAdmin,
    RequiredChannelAdmin,
    SavedProgramAdmin,
    ScholarshipAdmin,
    ScholarshipDeadlineAdmin,
    ServiceRequestAdmin,
    SubscriptionExemptionAdmin,
    UniversityAdmin,
    UserAdmin,
)
from app.admin.wizards import ScholarshipWizard, UniversityWizard
from app.config import settings
from app.db.session import engine
from app.webapp.api import router as webapp_api_router
from app.webapp.mentor_api import router as mentor_api_router

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent / "templates"
ADMIN_STATIC_DIR = Path(__file__).parent / "static"
WEBAPP_STATIC_DIR = Path(__file__).parent.parent / "webapp" / "static"


class NoCacheStaticFiles(StaticFiles):
    """Telegram Mini App'lar statik fayllarni agressiv keshlaydi va yangilanish
    foydalanuvchiga yetib bormaydi. `no-cache` bilan brauzer har safar serverdan
    so'raydi (o'zgarmagan bo'lsa 304 qaytadi, ya'ni trafik deyarli oshmaydi)."""

    def file_response(self, *args, **kwargs) -> Response:
        response = super().file_response(*args, **kwargs)
        response.headers["Cache-Control"] = "no-cache, must-revalidate"
        return response


async def _supervise_bot() -> None:
    """Botni ishga tushiradi va u kutilmaganda to'xtasa, butun jarayonni yopadi.

    Ilgari bot alohida jarayon edi va entrypoint'dagi `wait -n` u yiqilganda
    konteynerni to'xtatardi — Railway uni qayta ishga tushirardi. Bitta
    jarayonda yiqilgan vazifa jimgina o'lib, veb-server esa ishlashda davom
    etardi (bot javob bermaydi, lekin servis "sog'lom" ko'rinadi). Shu
    xatti-harakatni saqlash uchun bu yerda ham jarayon yopiladi.
    """
    from app.bot.main import run_bot

    try:
        await run_bot(handle_signals=False)
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception("Bot to'xtadi — konteyner qayta ishga tushiriladi")
    else:
        logger.error("Bot kutilmaganda tugadi — konteyner qayta ishga tushiriladi")
    # ATAYLAB `os._exit(1)`, SIGTERM emas. Linux'da uvicorn SIGTERM'ni
    # ushlab, chiroyli yopiladi va 0 kodi bilan chiqadi — Railway'ning
    # `ON_FAILURE` siyosati esa 0 kodda konteynerni QAYTA ISHGA TUSHIRMAYDI.
    # Natijada servis o'chib, bot javob bermay qolardi. Noldan farqli kod
    # bilan darhol chiqish Railway'ni uni qayta ko'tarishga majbur qiladi.
    logging.shutdown()
    os._exit(1)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    task = None
    if settings.run_bot_in_process:
        task = asyncio.create_task(_supervise_bot(), name="telegram-bot")
    try:
        yield
    finally:
        if task is not None:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task


app = FastAPI(title="Uni Assist", lifespan=lifespan)

app.include_router(webapp_api_router, prefix="/api/webapp", tags=["webapp"])
app.include_router(mentor_api_router, prefix="/api/webapp", tags=["webapp"])
app.mount("/webapp", NoCacheStaticFiles(directory=str(WEBAPP_STATIC_DIR), html=True), name="webapp")
app.mount("/admin-assets", NoCacheStaticFiles(directory=str(ADMIN_STATIC_DIR)), name="admin-assets")


class UniAssistAdmin(Admin):
    """Saqlangandan keyin qayerga qaytish.

    Sqladmin sukut bo'yicha o'zining ro'yxat sahifasiga qaytaradi. Admission
    Kit bo'limida bunday ro'yxat sahifasi menyuda yo'q va u alohida bo'lim
    taassurotini berardi: "Tahrirlash" bosilgan odam saqlab bo'lgach
    boshqa sahifada qolib ketardi. Shuning uchun bu ikki model uchun
    qaytish manzili Admission Kit sahifasiga burib yuboriladi.

    Formadagi "Bekor qilish" havolasi shablonda — u admin.js'da
    almashtiriladi (sqladmin shablonlari forklanmasligi uchun).
    """

    KIT_IDENTITIES = ("admission-service", "service-request")

    @staticmethod
    def get_save_redirect_url(request, form, model_view, obj):
        identity = request.path_params.get("identity")
        if identity in UniAssistAdmin.KIT_IDENTITIES and form.get("save") == "Save":
            return request.url_for("admin:view-admission-kit")
        return Admin.get_save_redirect_url(
            request=request, form=form, model_view=model_view, obj=obj
        )


admin = UniAssistAdmin(
    app,
    engine,
    title="Uni Assist Admin",
    authentication_backend=AdminAuth(secret_key=settings.admin_secret_key),
    templates_dir=str(TEMPLATES_DIR),
)

# Yon menyu tartibi shu qo'shilish tartibidan kelib chiqadi va u ataylab
# tekis (bo'limlarsiz): katalog -> grantlar -> qolgani. Sehrgarlar menyuda
# ko'rinmaydi — ularga tegishli ro'yxat orqali kelinadi.
admin.add_base_view(StatsView)
# Universitetni dasturlari, talablari, xarajatlari va muddatlari bilan
# kiritish/tahrirlashning yagona joyi. "Universitetlar" ro'yxatidan ochiladi.
admin.add_base_view(UniversityWizard)

for view in (CountryAdmin, UniversityAdmin, ProgramAdmin, FieldAdmin):
    admin.add_view(view)
# Katalogni ommaviy kiritish va zaxiralash (katalog kodda emas — faqat adminka).
admin.add_base_view(CatalogImportView)

# Grant sehrgari va muddatlar yon menyuda ko'rinmaydi — ikkalasi ham
# "Grantlar" ro'yxati orqali ochiladi (uchta alohida bo'lim chalkash edi).
# Foydalanuvchilar taklif qilgan deadline sanalari — katalogga faqat
# admin tasdiqlagandan keyin tushadi.
admin.add_base_view(SuggestionView)
admin.add_base_view(ScholarshipWizard)
for view in (
    ScholarshipAdmin,
    ScholarshipDeadlineAdmin,
    UserAdmin,
):
    admin.add_view(view)

# Admission Kit — BITTA bo'lim. Xizmatlar, ularning PDF fayllari va sotib
# olishlar bitta sahifada: ular doim birga ishlatiladi, uchta alohida qator
# esa menyuni cho'zib yuborardi.
#
# Ikkala ModelView menyuda ko'rinmaydi (`is_visible`), lekin qo'shiladi —
# ularning formalari o'sha sahifadagi havolalardan ochiladi.
admin.add_base_view(AdmissionKitView)
for view in (
    AdmissionServiceAdmin,
    ServiceRequestAdmin,
    PaymentSettingsAdmin,
    PaymentAdmin,
    BalanceTransactionAdmin,
    BotAdminAdmin,
    RequiredChannelAdmin,
    SubscriptionExemptionAdmin,
    # Menyuda ko'rinmaydi — boshqaruv panelidagi "Saqlangan" kartasi
    # orqali ochiladi (app/admin/views.py).
    SavedProgramAdmin,
):
    admin.add_view(view)

# Mentordan so'rash — faqat savollar va shikoyatlar. Mentorlarni boshqarish
# bo'limi ATAYLAB yo'q: mentorlik = guruh a'zoligi (Telegram'da qo'lda).
admin.add_base_view(MentorQuestionsView)
admin.add_base_view(MentorComplaintsView)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    """Domen bosh sahifasi Mini App'ga yo'naltiriladi.

    BotFather'da Mini App manzili sifatida "https://uniassist.uz/" (oxirida
    /webapp/ siz) qo'yilsa, Telegram 404 JSON'ni ko'rsatardi. Telegram
    `#tgWebAppData=...` ni hash'da beradi — brauzer uni yo'naltirishda saqlaydi.
    """
    return RedirectResponse("/webapp/", status_code=307)
