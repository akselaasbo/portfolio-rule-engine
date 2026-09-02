from pydantic import BaseModel, ConfigDict

from app.models.holding import Holding


class ValidatePortfolioRequest(BaseModel):
    holdings: list[Holding]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "holdings": [
                    {"ticker": "VTI", "weight_pct": 25},
                    {"ticker": "VXUS", "weight_pct": 20},
                    {"ticker": "BND", "weight_pct": 20},
                    {"ticker": "VNQ", "weight_pct": 10},
                    {"ticker": "GLD", "weight_pct": 5},
                    {"ticker": "XLF", "weight_pct": 10},
                    {"ticker": "XLK", "weight_pct": 10},
                ]
            }
        }
    )
