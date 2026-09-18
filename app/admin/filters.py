"""Admin panel uchun maxsus filtrlar.

SQLAdmin'ning tayyor `ForeignKeyFilter`'i haqiqiy FK ustunini talab qiladi
(`column.type`, `column == value`), shuning uchun many-to-many bog'lanish
bo'yicha filtrlay olmaydi. Davlat stipendiyalari esa aynan M2M orqali
davlatlarga bog'langan, shu sababli o'z filtrimiz kerak.

Filtrlar SQLAdmin'da duck-typing orqali ishlaydi: `parameter_name`, `title`,
`template`, `has_operator` atributlari va `lookups()` / `get_filtered_query()`
metodlari bo'lsa kifoya.
"""

from collections.abc import Callable
from typing import Any

from sqlalchemy import Select, select
from starlette.requests import Request

ALL_VALUE = "__all"


class RelationshipFilter:
    """Many-to-many (yoki one-to-many) bog'lanish bo'yicha filtrlaydi.

    Args:
        relationship: filtrlanadigan model relationship'i, masalan `Scholarship.countries`.
        related_model: bog'langan model klassi, masalan `Country`.
        label_column: ro'yxatda ko'rsatiladigan ustun, masalan `Country.name_uz`.
        title: yon paneldagi sarlavha.
    """

    has_operator = False
    template = "sqladmin/filters/lookup_filter.html"

    def __init__(
        self,
        relationship: Any,
        related_model: Any,
        label_column: Any,
        title: str,
        parameter_name: str | None = None,
    ) -> None:
        self.relationship = relationship
        self.related_model = related_model
        self.label_column = label_column
        self.title = title
        self.parameter_name = parameter_name or relationship.key

    async def lookups(
        self,
        request: Request,
        model: Any,
        run_query: Callable[[Select], Any],
    ) -> list[tuple[str, str]]:
        rows = await run_query(
            select(self.related_model.id, self.label_column).order_by(self.label_column)
        )
        return [(ALL_VALUE, "Barchasi")] + [(str(key), str(label)) for key, label in rows]

    async def get_filtered_query(self, query: Select, value: Any, model: Any) -> Select:
        if value is None or value == "" or value == ALL_VALUE:
            return query

        try:
            related_id = int(value)
        except (TypeError, ValueError):
            return query

        return query.filter(self.relationship.any(self.related_model.id == related_id))
