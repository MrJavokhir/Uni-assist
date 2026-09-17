import pytest

from app.db.models.program import GpaScale
from app.services.gpa_converter import to_bavarian, to_ects, to_us4


def test_to_us4_scale_4_passthrough():
    assert to_us4(3.5, GpaScale.SCALE_4) == 3.5
    assert to_us4(5.0, GpaScale.SCALE_4) == 4.0  # yuqori chegaradan oshmaydi


def test_to_us4_scale_5():
    assert to_us4(5.0, GpaScale.SCALE_5) == 4.0
    assert to_us4(2.0, GpaScale.SCALE_5) == 0.0
    assert to_us4(3.5, GpaScale.SCALE_5) == pytest.approx(2.0, abs=0.01)


def test_to_us4_scale_100():
    assert to_us4(95, GpaScale.SCALE_100) == 4.0
    assert to_us4(85, GpaScale.SCALE_100) == pytest.approx(3.5, abs=0.01)
    assert to_us4(55, GpaScale.SCALE_100) == 0.0


def test_to_ects_letter_grades():
    assert to_ects(95, GpaScale.SCALE_100) == "A"
    assert to_ects(85, GpaScale.SCALE_100) == "B"
    assert to_ects(45, GpaScale.SCALE_100) == "F"
    assert to_ects(5.0, GpaScale.SCALE_5) == "A"
    assert to_ects(2.0, GpaScale.SCALE_5) == "F"


def test_to_bavarian_formula_matches_spec():
    # N = 1 + 3 * (Nmax - Nd) / (Nmax - Nmin)
    # 100 balli tizim, Nmax=100, Nmin=60 (standart taxmin)
    assert to_bavarian(100, GpaScale.SCALE_100) == pytest.approx(1.0, abs=0.01)
    assert to_bavarian(60, GpaScale.SCALE_100) == pytest.approx(4.0, abs=0.01)
    assert to_bavarian(80, GpaScale.SCALE_100) == pytest.approx(2.5, abs=0.01)


def test_to_bavarian_custom_bounds():
    # Nd = Nmax bo'lsa har doim 1.0 (eng yaxshi) bo'lishi kerak
    assert to_bavarian(5.0, GpaScale.SCALE_5, n_max=5.0, n_min=3.0) == pytest.approx(1.0, abs=0.01)
    # Nd = Nmin bo'lsa har doim 4.0 (o'tish chegarasi)
    assert to_bavarian(3.0, GpaScale.SCALE_5, n_max=5.0, n_min=3.0) == pytest.approx(4.0, abs=0.01)


def test_to_bavarian_rejects_equal_bounds():
    with pytest.raises(ValueError):
        to_bavarian(50, GpaScale.SCALE_100, n_max=60, n_min=60)
