"""GPA konvertori: 5 balli / 100 balli / 4.0 tizimlari orasida taxminiy o'girish.

Har doim taxminiy hisob-kitob ekanligini eslatib turish kerak — yakuniy qarorni
universitet yoki tan olish idorasi (WES, Uni-Assist, ANABIN) qabul qiladi.
Aniq formulalar manbasi: app_spec (loyiha texnik topshirig'i).
"""

from dataclasses import dataclass

from app.db.models.program import GpaScale

# Har bir shkalaning (minimal, maksimal) qiymati — ECTS foizini hisoblash uchun.
_SCALE_BOUNDS: dict[GpaScale, tuple[float, float]] = {
    GpaScale.SCALE_4: (0.0, 4.0),
    GpaScale.SCALE_5: (2.0, 5.0),  # O'zbekistonda 2 — yiqilgan, 3 — minimal o'tish balli
    GpaScale.SCALE_100: (0.0, 100.0),
}

# Bavariya formulasi uchun standart taxminlar (Nmax, o'tish balli Nmin).
# Aniq qiymatlar universitetdan universitetga farq qilishi mumkin — bu shunchaki
# odatiy taxmin, foydalanuvchiga har doim ogohlantirish bilan birga ko'rsatiladi.
_BAVARIAN_MAX: dict[GpaScale, float] = {
    GpaScale.SCALE_4: 4.0,
    GpaScale.SCALE_5: 5.0,
    GpaScale.SCALE_100: 100.0,
}
_BAVARIAN_MIN_PASS: dict[GpaScale, float] = {
    GpaScale.SCALE_4: 2.0,
    GpaScale.SCALE_5: 3.0,
    GpaScale.SCALE_100: 60.0,
}


# AQSH 4.0 GPA -> Buyuk Britaniya diplom darajasi (quyi chegaralar).
# Britaniya universitetlari xorijiy baholarni odatda shunday solishtiradi:
# 3.7 ≈ First, 3.3 ≈ Upper Second (2:1), 3.0 ≈ Lower Second (2:2).
# Har universitetning o'z jadvali bor — natija faqat taxminiy.
_UK_CLASSES: list[tuple[float, str]] = [
    (3.7, "first"),
    (3.3, "upper_second"),
    (3.0, "lower_second"),
    (2.5, "third"),
]


@dataclass(frozen=True)
class GpaConversionResult:
    us4: float
    ects: str
    bavarian: float
    # Kalit: first / upper_second / lower_second / third / below —
    # Mini App uni foydalanuvchi tilida yozadi.
    uk: str


def to_us4(value: float, scale: GpaScale) -> float:
    """Berilgan bahoni taxminiy AQSH 4.0 shkalasiga o'giradi."""
    if scale == GpaScale.SCALE_4:
        return round(max(0.0, min(4.0, value)), 2)

    if scale == GpaScale.SCALE_5:
        lo, hi = _SCALE_BOUNDS[GpaScale.SCALE_5]
        us4 = (value - lo) / (hi - lo) * 4.0
        return round(max(0.0, min(4.0, us4)), 2)

    if scale == GpaScale.SCALE_100:
        # Foizlarni AQSH GPA'siga o'girishning keng tarqalgan bosqichli jadvali.
        if value >= 90:
            us4 = 4.0
        elif value >= 80:
            us4 = 3.0 + (value - 80) / 10
        elif value >= 70:
            us4 = 2.0 + (value - 70) / 10
        elif value >= 60:
            us4 = 1.0 + (value - 60) / 10
        else:
            us4 = 0.0
        return round(max(0.0, min(4.0, us4)), 2)

    raise ValueError(f"Noma'lum GPA shkalasi: {scale}")


def to_ects(value: float, scale: GpaScale) -> str:
    """Berilgan bahoni taxminiy ECTS harf bahosiga (A-F) o'giradi."""
    lo, hi = _SCALE_BOUNDS[scale]
    percent = (value - lo) / (hi - lo) * 100
    percent = max(0.0, min(100.0, percent))

    if percent >= 90:
        return "A"
    if percent >= 80:
        return "B"
    if percent >= 70:
        return "C"
    if percent >= 60:
        return "D"
    if percent >= 50:
        return "E"
    return "F"


def to_bavarian(
    value: float,
    scale: GpaScale,
    *,
    n_max: float | None = None,
    n_min: float | None = None,
) -> float:
    """Bavariya formulasi: N = 1 + 3 * (Nmax - Nd) / (Nmax - Nmin).

    Natija Germaniya shkalasida (1.0 — eng yaxshi, 4.0 — o'tish chegarasi,
    undan yuqori — yiqilgan) taxminiy baho.
    """
    n_max = n_max if n_max is not None else _BAVARIAN_MAX[scale]
    n_min = n_min if n_min is not None else _BAVARIAN_MIN_PASS[scale]
    if n_max == n_min:
        raise ValueError("n_max va n_min bir xil bo'lishi mumkin emas")

    n = 1 + 3 * (n_max - value) / (n_max - n_min)
    return round(max(1.0, min(5.0, n)), 2)


def to_uk(value: float, scale: GpaScale) -> str:
    """Berilgan bahoni taxminiy Buyuk Britaniya diplom darajasiga o'giradi."""
    us4 = to_us4(value, scale)
    for threshold, uk_class in _UK_CLASSES:
        if us4 >= threshold:
            return uk_class
    return "below"


def convert(value: float, scale: GpaScale) -> GpaConversionResult:
    return GpaConversionResult(
        us4=to_us4(value, scale),
        ects=to_ects(value, scale),
        bavarian=to_bavarian(value, scale),
        uk=to_uk(value, scale),
    )
