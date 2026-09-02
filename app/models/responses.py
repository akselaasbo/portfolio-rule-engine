from __future__ import annotations

from pydantic import BaseModel

from app.domain.engine import RuleFinding, ValidationResult
from app.domain.exposures import Exposures
from app.domain.optimizer import ChangeSummaryItem, NearestValidResult
from app.models.holding import Holding


class ValidationResponse(BaseModel):
    portfolio_valid: bool
    violations: list[RuleFinding]
    warnings: list[RuleFinding]
    exposures: Exposures
    summary: str
    nearest_valid_portfolio: list[Holding] | None = None
    change_summary: list[ChangeSummaryItem] | None = None

    @classmethod
    def from_result(
        cls,
        result: ValidationResult,
        nearest_valid: NearestValidResult | None = None,
    ) -> ValidationResponse:
        return cls(
            portfolio_valid=result.portfolio_valid,
            violations=result.violations,
            warnings=result.warnings,
            exposures=result.exposures,
            summary=_build_summary(len(result.violations), len(result.warnings)),
            nearest_valid_portfolio=nearest_valid.holdings if nearest_valid else None,
            change_summary=nearest_valid.change_summary if nearest_valid else None,
        )


def _build_summary(violations_count: int, warnings_count: int) -> str:
    if violations_count > 0:
        rule_word = "regel" if violations_count == 1 else "regler"
        return f"Porteføljen bryter {violations_count} {rule_word}."
    if warnings_count > 0:
        warning_word = "advarsel" if warnings_count == 1 else "advarsler"
        return f"Porteføljen oppfyller alle regler, men har {warnings_count} {warning_word}."
    return "Porteføljen oppfyller alle regler."
