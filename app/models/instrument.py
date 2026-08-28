from pydantic import BaseModel


class Instrument(BaseModel):
    """Ett instrument fra instruments.csv. Brukes både som API-respons og domeneobjekt."""

    ticker: str
    name: str
    asset_class: str
    sector: str
    geography: str
    instrument_type: str
    expense_ratio_pct: float
