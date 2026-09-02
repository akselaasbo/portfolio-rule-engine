from pydantic import BaseModel

from app.data.repository import InstrumentRepository
from app.models.holding import Holding

_UNKNOWN = "Unknown"


class Exposures(BaseModel):
    """Aggregert eksponering for en portefølje. Beregnes én gang per validering."""

    by_asset_class: dict[str, float]
    by_sector: dict[str, float]
    by_geography: dict[str, float]
    total_weight: float
    number_of_holdings: int
    max_holding_weight: float
    unknown_classification_count: int


def calculate_exposures(holdings: list[Holding], instrument_repo: InstrumentRepository) -> Exposures:
    by_asset_class: dict[str, float] = {}
    by_sector: dict[str, float] = {}
    by_geography: dict[str, float] = {}
    total_weight = 0.0
    max_holding_weight = 0.0
    unknown_classification_count = 0

    for holding in holdings:
        instrument = instrument_repo.get(holding.ticker)
        if instrument is None:
            raise ValueError(f"Ukjent ticker: {holding.ticker}")

        weight = holding.weight_pct
        total_weight += weight
        max_holding_weight = max(max_holding_weight, weight)

        by_asset_class[instrument.asset_class] = by_asset_class.get(instrument.asset_class, 0.0) + weight
        by_sector[instrument.sector] = by_sector.get(instrument.sector, 0.0) + weight
        by_geography[instrument.geography] = by_geography.get(instrument.geography, 0.0) + weight

        if _UNKNOWN in (instrument.asset_class, instrument.sector, instrument.geography):
            unknown_classification_count += 1

    return Exposures(
        by_asset_class=by_asset_class,
        by_sector=by_sector,
        by_geography=by_geography,
        total_weight=total_weight,
        number_of_holdings=len(holdings),
        max_holding_weight=max_holding_weight,
        unknown_classification_count=unknown_classification_count,
    )
