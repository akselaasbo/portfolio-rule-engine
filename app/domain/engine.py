from __future__ import annotations

from pydantic import BaseModel

from app.data.repository import InstrumentRepository, RuleRepository
from app.domain.exposures import Exposures, calculate_exposures
from app.domain.rules import (
    KNOWN_SCOPE_DIMENSIONS,
    evaluate_asset_class,
    evaluate_geography,
    evaluate_holding,
    evaluate_portfolio,
    evaluate_sector,
    parse_scope,
    satisfies,
)
from app.models.holding import Holding
from app.models.rule import Rule


class RuleFinding(BaseModel):
    """Ett brutt eller advarende regelutfall, klart til å vises i API-responsen."""

    rule_code: str
    severity: str
    description: str
    actual_value: float
    operator: str
    threshold: float
    scope_detail: str
    excess: float


class ValidationResult(BaseModel):
    portfolio_valid: bool
    violations: list[RuleFinding]
    warnings: list[RuleFinding]
    exposures: Exposures


class RuleEngine:
    """Evaluerer en portefølje mot regelsettet fra rules.csv."""

    def __init__(self, rule_repository: RuleRepository, tolerance: float) -> None:
        self._rule_repository = rule_repository
        self._tolerance = tolerance
        self._validate_rules()

    @property
    def rule_repository(self) -> RuleRepository:
        return self._rule_repository

    def _validate_rules(self) -> None:
        for rule in self._rule_repository.all():
            dimension, _ = parse_scope(rule.scope)
            if dimension not in KNOWN_SCOPE_DIMENSIONS:
                raise ValueError(f"Ukjent scope-mønster '{rule.scope}' i regel {rule.rule_code}")

    def evaluate(self, holdings: list[Holding], instrument_repo: InstrumentRepository) -> ValidationResult:
        exposures = calculate_exposures(holdings, instrument_repo)

        violations: list[RuleFinding] = []
        warnings: list[RuleFinding] = []

        for rule in self._rule_repository.all():
            value, scope_detail = self._evaluate_rule(rule, exposures)
            if satisfies(value, rule.operator, rule.threshold, self._tolerance):
                continue

            finding = RuleFinding(
                rule_code=rule.rule_code,
                severity=rule.severity,
                description=rule.description_no,
                actual_value=value,
                operator=rule.operator,
                threshold=rule.threshold,
                scope_detail=scope_detail,
                excess=_compute_excess(value, rule.operator, rule.threshold),
            )
            if rule.severity == "error":
                violations.append(finding)
            else:
                warnings.append(finding)

        return ValidationResult(
            portfolio_valid=len(violations) == 0,
            violations=violations,
            warnings=warnings,
            exposures=exposures,
        )

    def _evaluate_rule(self, rule: Rule, exposures: Exposures) -> tuple[float, str]:
        dimension, value = parse_scope(rule.scope)
        if dimension == "portfolio":
            return evaluate_portfolio(rule.metric_definition, exposures)
        if dimension == "holding":
            return evaluate_holding(rule.metric_definition, exposures)
        if dimension == "asset_class":
            return evaluate_asset_class(value, exposures)
        if dimension == "sector":
            return evaluate_sector(exposures)
        return evaluate_geography(exposures)


def _compute_excess(value: float, operator: str, threshold: float) -> float:
    if operator == "<=":
        return max(0.0, value - threshold)
    if operator == ">=":
        return max(0.0, threshold - value)
    if operator == "==":
        return abs(value - threshold)
    raise ValueError(f"Ukjent operator: {operator}")
