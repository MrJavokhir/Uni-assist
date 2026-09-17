from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqladmin import Admin

from app.admin.auth import AdminAuth
from app.admin.stats import StatsView
from app.admin.views import (
    CountryAdmin,
    DeadlineAdmin,
    ProgramAdmin,
    ProgramCostAdmin,
    ProgramRequirementAdmin,
    ReportAdmin,
    SavedProgramAdmin,
    ScholarshipAdmin,
    ScholarshipDeadlineAdmin,
    UniversityAdmin,
    UserAdmin,
    UserLanguageCertificateAdmin,
    UserOtherTestAdmin,
)
from app.config import settings
from app.db.session import engine
from app.webapp.api import router as webapp_api_router

TEMPLATES_DIR = Path(__file__).parent / "templates"
WEBAPP_STATIC_DIR = Path(__file__).parent.parent / "webapp" / "static"

app = FastAPI(title="Uni Assist")

app.include_router(webapp_api_router, prefix="/api/webapp", tags=["webapp"])
app.mount("/webapp", StaticFiles(directory=str(WEBAPP_STATIC_DIR), html=True), name="webapp")

admin = Admin(
    app,
    engine,
    title="Uni Assist Admin",
    authentication_backend=AdminAuth(secret_key=settings.admin_secret_key),
    templates_dir=str(TEMPLATES_DIR),
)

for view in (
    CountryAdmin,
    UniversityAdmin,
    ProgramAdmin,
    ProgramRequirementAdmin,
    ProgramCostAdmin,
    DeadlineAdmin,
    ScholarshipAdmin,
    ScholarshipDeadlineAdmin,
    UserAdmin,
    UserLanguageCertificateAdmin,
    UserOtherTestAdmin,
    SavedProgramAdmin,
    ReportAdmin,
):
    admin.add_view(view)

admin.add_base_view(StatsView)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
