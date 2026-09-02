import pytest

from app.config import settings
from app.data.repository import InstrumentRepository, RuleRepository
from app.domain.engine import RuleEngine
from app.domain.optimizer import find_nearest_valid_portfolio
from app.models.holding import Holding
from tests._sample_data import load_expected_outcomes, load_sample_portfolios

PORTFOLIOS = load_sample_portfolios()
EXPECTED_OUTCOMES = load_expected_outcomes()

INVALID_PORTFOLIO_IDS = [
    portfolio_id for portfolio_id, expected in EXPECTED_OUTCOMES.items() if expected == "invalid"
]


@pytest.mark.parametrize("portfolio_id", INVALID_PORTFOLIO_IDS)
def test_nearest_valid_portfolio_is_actually_valid(
    portfolio_id: str,
    instrument_repository: InstrumentRepository,
    rule_repository: RuleRepository,
) -> None:
    result = find_nearest_valid_portfolio(
        PORTFOLIOS[portfolio_id], instrument_repository, rule_repository, settings.weight_tolerance
    )
    assert result.holdings is not None, result.explanation

    engine = RuleEngine(rule_repository, settings.weight_tolerance)
    revalidation = engine.evaluate(result.holdings, instrument_repository)
    assert revalidation.portfolio_valid is True


def test_already_valid_portfolio_is_unchanged(
    instrument_repository: InstrumentRepository,
    rule_repository: RuleRepository,
) -> None:
    holdings = PORTFOLIOS["P5_UNKNOWN_INSTRUMENT"]
    result = find_nearest_valid_portfolio(
        holdings, instrument_repository, rule_repository, settings.weight_tolerance
    )

    assert result.holdings is not None
    original_weights = {holding.ticker: holding.weight_pct for holding in holdings}
    new_weights = {holding.ticker: holding.weight_pct for holding in result.holdings}
    assert new_weights == original_weights
    assert result.change_summary == []


def test_p2_adds_non_us_instrument(
    instrument_repository: InstrumentRepository,
    rule_repository: RuleRepository,
) -> None:
    holdings = PORTFOLIOS["P2_TOO_MUCH_US_EQUITY"]
    result = find_nearest_valid_portfolio(
        holdings, instrument_repository, rule_repository, settings.weight_tolerance
    )
    assert result.holdings is not None, result.explanation

    original_tickers = {holding.ticker for holding in holdings}
    added = [holding for holding in result.holdings if holding.ticker not in original_tickers]
    non_us_added = [
        holding
        for holding in added
        if instrument_repository.get(holding.ticker).geography != "US"
    ]
    assert len(non_us_added) >= 1


@pytest.mark.parametrize("portfolio_id", INVALID_PORTFOLIO_IDS)
def test_optimizer_never_introduces_unknown_classification(
    portfolio_id: str,
    instrument_repository: InstrumentRepository,
    rule_repository: RuleRepository,
) -> None:
    holdings = PORTFOLIOS[portfolio_id]
    result = find_nearest_valid_portfolio(
        holdings, instrument_repository, rule_repository, settings.weight_tolerance
    )
    assert result.holdings is not None, result.explanation

    original_tickers = {holding.ticker for holding in holdings}
    for holding in result.holdings:
        if holding.ticker in original_tickers:
            continue
        instrument = instrument_repository.get(holding.ticker)
        assert "Unknown" not in (
            instrument.asset_class,
            instrument.sector,
            instrument.geography,
        ), f"{holding.ticker} har ukjent klassifisering og ble likevel lagt til"


def test_already_owned_unknown_instrument_is_kept(
    instrument_repository: InstrumentRepository,
    rule_repository: RuleRepository,
) -> None:
    # P5 er allerede gyldig (MYST gir kun en warning), så vi bruker en variant som tvinger
    # optimeringen til faktisk å justere porteføljen mens MYST fortsatt eies fra før.
    holdings = [Holding(ticker="MYST", weight_pct=100.0)]
    result = find_nearest_valid_portfolio(
        holdings, instrument_repository, rule_repository, settings.weight_tolerance
    )
    assert result.holdings is not None, result.explanation

    myst_weight = next((h.weight_pct for h in result.holdings if h.ticker == "MYST"), 0.0)
    assert myst_weight > 0
