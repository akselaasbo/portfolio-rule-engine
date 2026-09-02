from typing import Literal

from pydantic import BaseModel


class Rule(BaseModel):
    """Én rad fra rules.csv, uttolket rått. Modellen tolker ikke scope eller metric_definition."""

    rule_code: str
    severity: Literal["error", "warning"]
    metric_definition: str
    scope: str
    operator: Literal["==", "<=", ">="]
    threshold: float
    description_no: str
