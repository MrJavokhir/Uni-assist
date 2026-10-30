"""Talablar matnidan minimal GPA'ni ajratish — haqiqiy katalog matnlari asosida."""

import pytest

from app.db.models.program import GpaScale
from app.services.gpa_requirement import extract_gpa_requirement


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Bachelor degree in a related field, min CGPA 2.750/4.00 (2.000-2.749 subject to faculty assessment)", 2.75),
        ("Bachelor degree with CGPA at least 3.00; CGPA 2.50-2.99 considered with work experience", 3.0),
        ("Bachelor's degree (MQF Level 6) in computing with CGPA 2.50 (lower CGPA subject to assessment)", 2.5),
        ("Bachelor's degree with CGPA 2.50 (CGPA 2.00 accepted with three years' experience)", 2.5),
        ("Bachelor's degree in Engineering with CGPA 2.50, or CGPA 2.00-2.49 with 5 years' work experience", 2.5),
        ("UK 2.1 honours degree, or typically a GPA of 3.0 to 3.3 out of 4.0, in any discipline", 3.0),
        ("Applications go through SOPHAS; transcripts; a GPA of 3.0 or higher is expected", 3.0),
    ],
)
def test_four_point_scale(text, expected):
    result = extract_gpa_requirement(text)
    assert result is not None
    assert result.scale == GpaScale.SCALE_4
    assert result.value == expected


def test_hundred_point_scale():
    result = extract_gpa_requirement("Three-year bachelor's degree in ICT engineering; minimum GPA 80/100")
    assert result is not None
    assert (result.value, result.scale) == (80.0, GpaScale.SCALE_100)


@pytest.mark.parametrize(
    "text",
    [
        # Bitirish talabi — kirish emas
        "A cumulative GPA of 3.00 or higher and a pass in the foreign-language examination are required to graduate",
        "Mode: by coursework, 3 semesters, min 40 credits, final CGPA 3.00/4.00",
        "30 credit hours with grade B- or better and cumulative GPA 3.00",
        # Imtiyoz sharti — minimal emas
        "GMAT or GRE required, but waived if the undergraduate cumulative GPA is 3.30 or above",
        # Minimal yo'q
        "GRE optional; no minimum GPA, GRE or English test score is set",
        # Boshqa shkala (nemis: kichigi yaxshi)
        "Bachelor with a GPA no worse than 2.49 on the German scale",
        # O'qish davomidagi talab
        "Research master's: minimum eight courses plus a thesis; two years, GPA of 2.0 or higher required",
    ],
)
def test_not_an_entry_requirement(text):
    assert extract_gpa_requirement(text) is None
