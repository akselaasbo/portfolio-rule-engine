from pydantic import BaseModel


class Holding(BaseModel):
    """Én posisjon i en portefølje, slik den kommer inn fra klienten."""

    ticker: str
    weight_pct: float
