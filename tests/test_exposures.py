from app.data.repository import InstrumentRepository
from app.domain.exposures import calculate_exposures
from app.models.holding import Holding


def _holdings() -> list[Holding]:
    return [
        Holding(ticker="AAA", weight_pct=30),
        Holding(ticker="BBB", weight_pct=20),
        Holding(ticker="CCC", weight_pct=15),
        Holding(ticker="DDD", weight_pct=10),
        Holding(ticker="MYST", weight_pct=25),
    ]


def test_aggregates_by_asset_class(small_instrument_repository: InstrumentRepository) -> None:
    exposures = calculate_exposures(_holdings(), small_instrument_repository)
    assert exposures.by_asset_class == {
        "Equity": 45.0,
        "Fixed Income": 20.0,
        "Real Estate": 10.0,
        "Unknown": 25.0,
    }


def test_aggregates_by_sector(small_instrument_repository: InstrumentRepository) -> None:
    exposures = calculate_exposures(_holdings(), small_instrument_repository)
    assert exposures.by_sector == {
        "Tech": 30.0,
        "Government": 20.0,
        "Diversified": 15.0,
        "REIT": 10.0,
        "Unknown": 25.0,
    }


def test_aggregates_by_geography(small_instrument_repository: InstrumentRepository) -> None:
    exposures = calculate_exposures(_holdings(), small_instrument_repository)
    assert exposures.by_geography == {
        "US": 60.0,
        "Global ex-US": 15.0,
        "Unknown": 25.0,
    }


def test_total_weight(small_instrument_repository: InstrumentRepository) -> None:
    exposures = calculate_exposures(_holdings(), small_instrument_repository)
    assert exposures.total_weight == 100.0


def test_number_of_holdings(small_instrument_repository: InstrumentRepository) -> None:
    exposures = calculate_exposures(_holdings(), small_instrument_repository)
    assert exposures.number_of_holdings == 5


def test_max_holding_weight(small_instrument_repository: InstrumentRepository) -> None:
    exposures = calculate_exposures(_holdings(), small_instrument_repository)
    assert exposures.max_holding_weight == 30.0


def test_unknown_classification_count(small_instrument_repository: InstrumentRepository) -> None:
    exposures = calculate_exposures(_holdings(), small_instrument_repository)
    assert exposures.unknown_classification_count == 1
