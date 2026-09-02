from pydantic import BaseModel, Field


class Holding(BaseModel):
    """Én posisjon i en portefølje, slik den kommer inn fra klienten."""

    ticker: str = Field(min_length=1)
    weight_pct: float = Field(ge=0, le=100)
