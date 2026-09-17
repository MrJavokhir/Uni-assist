from pathlib import Path

from fastapi import FastAPI
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

TEMPLATES_DIR = Path(__file__).parent / "templates"

app = FastAPI(title="Uni Assist — Admin panel")

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
