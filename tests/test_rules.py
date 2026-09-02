import pytest

from app.domain.rules import parse_scope, satisfies


@pytest.mark.parametrize(
    "scope, expected",
    [
        ("portfolio", ("portfolio", None)),
        ("holding", ("holding", None)),
        ("sector", ("sector", None)),
        ("geography", ("geography", None)),
        ("asset_class:Equity", ("asset_class", "Equity")),
        ("asset_class:Fixed Income", ("asset_class", "Fixed Income")),
    ],
)
def test_parse_scope(scope: str, expected: tuple[str, str | None]) -> None:
    assert parse_scope(scope) == expected


def test_less_than_or_equal_is_inclusive_at_boundary() -> None:
    assert satisfies(35, "<=", 35, tolerance=0.01) is True


def test_less_than_or_equal_within_tolerance() -> None:
    assert satisfies(35.005, "<=", 35, tolerance=0.01) is True


def test_less_than_or_equal_outside_tolerance() -> None:
    assert satisfies(35.02, "<=", 35, tolerance=0.01) is False


def test_greater_than_or_equal_is_inclusive_at_boundary() -> None:
    assert satisfies(10, ">=", 10, tolerance=0.01) is True


def test_equals_within_tolerance_allows_near_miss() -> None:
    assert satisfies(99.999, "==", 100, tolerance=0.01) is True


def test_equals_outside_tolerance_fails() -> None:
    assert satisfies(99.98, "==", 100, tolerance=0.01) is False


def test_unknown_operator_raises_value_error() -> None:
    with pytest.raises(ValueError):
        satisfies(50, "!=", 50, tolerance=0.01)
