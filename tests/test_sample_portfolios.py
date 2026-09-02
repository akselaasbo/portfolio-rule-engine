import csv
from collections import defaultdict

import pytest

from app.config import settings
from app.data.repository import InstrumentRepository, RuleRepository
from app.domain.engine import RuleEngine
from app.models.holding import Holding

# rules.csv er kilden til sannhet for validering (jf. oppgaveteksten). expected_outcomes.csv
# stemmer ikke fullt ut med rules.csv: disse porteføljene er merket "valid" i fasiten, men
# bryter faktisk terskler fra rules.csv når de evalueres. Vi dokumenterer avviket eksplisitt
# her i stedet for å skjule det eller endre fasiten, slik at testen feiler hvis noe endrer seg.
KJENTE_AVVIK: dict[str, set[str]] = {
    "P1_VALID_BALANCED": {"MAX_SINGLE_GEOGRAPHY_EXPOSURE"},  # 77 % US mot 60 %
    "P6_NEAR_LIMITS": {"MAX_SINGLE_GEOGRAPHY_EXPOSURE"},  # 70 % US mot 60 %
    "P7_DEFENSIVE": {  # 85 % US mot 60 %, 45 % US Aggregate Bond mot 40 %
        "MAX_SINGLE_GEOGRAPHY_EXPOSURE",
        "MAX_SINGLE_SECTOR_EXPOSURE",
    },
}


def _load_portfolios() -> dict[str, list[Holding]]:
    portfolios: dict[str, list[Holding]] = defaultdict(list)
    path = settings.data_path / "sample_portfolios.csv"
    with open(path, newline="", encoding="utf-8") as csv_file:
        for row in csv.DictReader(csv_file):
            portfolios[row["portfolio_id"]].append(
                Holding(ticker=row["ticker"], weight_pct=float(row["weight_pct"]))
            )
    return portfolios


def _load_expected_outcomes() -> dict[str, str]:
    path = settings.data_path / "expected_outcomes.csv"
    with open(path, newline="", encoding="utf-8") as csv_file:
        return {row["portfolio_id"]: row["expected_result"] for row in csv.DictReader(csv_file)}


PORTFOLIOS = _load_portfolios()
EXPECTED_OUTCOMES = _load_expected_outcomes()


@pytest.mark.parametrize("portfolio_id", sorted(PORTFOLIOS))
def test_sample_portfolio_matches_expected_outcome(
    portfolio_id: str,
    instrument_repository: InstrumentRepository,
    rule_repository: RuleRepository,
) -> None:
    engine = RuleEngine(rule_repository, tolerance=settings.weight_tolerance)
    result = engine.evaluate(PORTFOLIOS[portfolio_id], instrument_repository)

    expected = EXPECTED_OUTCOMES[portfolio_id]
    violated_rule_codes = {violation.rule_code for violation in result.violations}

    if portfolio_id in KJENTE_AVVIK:
        assert expected == "valid", (
            f"{portfolio_id} er ikke lenger merket 'valid' i fasiten – KJENTE_AVVIK bør oppdateres."
        )
        assert violated_rule_codes == KJENTE_AVVIK[portfolio_id]
        return

    if expected == "valid":
        assert result.portfolio_valid is True
    elif expected == "invalid":
        assert result.portfolio_valid is False
    elif expected == "warning_or_invalid":
        has_unknown_warning = any(
            warning.rule_code == "UNKNOWN_CLASSIFICATION" for warning in result.warnings
        )
        assert not result.portfolio_valid or has_unknown_warning
    else:
        pytest.fail(f"Ukjent expected_result i expected_outcomes.csv: {expected}")
