from __future__ import annotations

from typing import Iterator

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.data.repository import InstrumentRepository, RuleRepository
from app.main import app
from app.models.instrument import Instrument


@pytest.fixture(scope="session")
def instrument_repository() -> InstrumentRepository:
    """Ekte instrumenter lest fra data/instruments.csv."""
    return InstrumentRepository.from_csv(settings.data_path / "instruments.csv")


@pytest.fixture(scope="session")
def rule_repository() -> RuleRepository:
    """Ekte regler lest fra data/rules.csv."""
    return RuleRepository.from_csv(settings.data_path / "rules.csv")


@pytest.fixture
def small_instrument_repository() -> InstrumentRepository:
    """Håndlaget, lite repository til enhetstester av eksponeringsberegning. Ingen filer involvert."""
    instruments = [
        Instrument(
            ticker="AAA",
            name="Alpha Equity",
            asset_class="Equity",
            sector="Tech",
            geography="US",
            instrument_type="ETF",
            expense_ratio_pct=0.1,
        ),
        Instrument(
            ticker="BBB",
            name="Beta Bond",
            asset_class="Fixed Income",
            sector="Government",
            geography="US",
            instrument_type="ETF",
            expense_ratio_pct=0.05,
        ),
        Instrument(
            ticker="CCC",
            name="Global Equity Fund",
            asset_class="Equity",
            sector="Diversified",
            geography="Global ex-US",
            instrument_type="ETF",
            expense_ratio_pct=0.15,
        ),
        Instrument(
            ticker="DDD",
            name="Real Estate Fund",
            asset_class="Real Estate",
            sector="REIT",
            geography="US",
            instrument_type="ETF",
            expense_ratio_pct=0.12,
        ),
        Instrument(
            ticker="MYST",
            name="Mystery Asset",
            asset_class="Unknown",
            sector="Unknown",
            geography="Unknown",
            instrument_type="Other",
            expense_ratio_pct=0.0,
        ),
    ]
    return InstrumentRepository(instruments)


@pytest.fixture(scope="session")
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client
