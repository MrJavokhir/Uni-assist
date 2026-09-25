from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqladmin import Admin
from starlette.responses import Response

from app.admin.auth import AdminAuth
from app.admin.csv_views import CatalogImportView
from app.admin.stats import StatsView
from app.admin.views import (
    AdmissionServiceAdmin,
    CountryAdmin,
    FieldAdmin,
    ProgramAdmin,
    ReportAdmin,
    RequiredChannelAdmin,
    ScholarshipAdmin,
    ScholarshipDeadlineAdmin,
    ServiceRequestAdmin,
    UniversityAdmin,
    UserAdmin,
)
from app.admin.wizards import ScholarshipWizard, UniversityWizard
from app.config import settings
from app.db.session import engine
from app.webapp.api import router as webapp_api_router

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


app = FastAPI(title="Uni Assist")

app.include_router(webapp_api_router, prefix="/api/webapp", tags=["webapp"])
app.mount("/webapp", NoCacheStaticFiles(directory=str(WEBAPP_STATIC_DIR), html=True), name="webapp")
app.mount("/admin-assets", NoCacheStaticFiles(directory=str(ADMIN_STATIC_DIR)), name="admin-assets")

admin = Admin(
    app,
    engine,
    title="Uni Assist Admin",
    authentication_backend=AdminAuth(secret_key=settings.admin_secret_key),
    templates_dir=str(TEMPLATES_DIR),
)

# Yon menyu tartibi shu qo'shilish tartibidan kelib chiqadi va u ataylab
# tekis (bo'limlarsiz): sehrgar -> katalog -> grantlar -> qolgani.
admin.add_base_view(StatsView)
# "Universitet qo'shish" — universitetni dasturlari, talablari, xarajatlari va
# muddatlari bilan kiritish/tahrirlashning yagona joyi.
admin.add_base_view(UniversityWizard)

for view in (CountryAdmin, UniversityAdmin, ProgramAdmin, FieldAdmin):
    admin.add_view(view)
# Katalogni ommaviy kiritish va zaxiralash (katalog kodda emas — faqat adminka).
admin.add_base_view(CatalogImportView)

admin.add_base_view(ScholarshipWizard)
for view in (
    ScholarshipAdmin,
    ScholarshipDeadlineAdmin,
    UserAdmin,
    AdmissionServiceAdmin,
    ServiceRequestAdmin,
    ReportAdmin,
    RequiredChannelAdmin,
):
    admin.add_view(view)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
