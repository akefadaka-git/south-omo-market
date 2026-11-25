import pytest

from app.routers.listings import _is_minor_text_normalization


@pytest.mark.parametrize(
    ("current", "proposed"),
    [
        ("Fresh tomatoes from Koybe", "Fresh tomatoes, from Koybe!"),
        ("MAALE Coffee", "Maale coffee"),
        ("  Fresh   honey  ", "Fresh honey"),
    ],
)
def test_formatting_only_description_corrections_are_minor(current, proposed):
    assert _is_minor_text_normalization(current, proposed)


@pytest.mark.parametrize(
    ("current", "proposed"),
    [
        ("Fresh tomatoes", "Organic tomatoes"),
        ("One kilogram", "Two kilograms"),
        ("Safe for children", "Not safe for children"),
        ("Price 100 ETB", "Price 200 ETB"),
        ("Fresh tomatoes", "Fresh tomatoes available today"),
    ],
)
def test_claim_or_meaning_changes_require_moderation(current, proposed):
    assert not _is_minor_text_normalization(current, proposed)


def test_identical_description_is_not_a_correction():
    assert not _is_minor_text_normalization("Fresh tomatoes", "Fresh tomatoes")
