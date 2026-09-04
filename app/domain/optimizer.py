from typing import Literal

import numpy as np
from pydantic import BaseModel
from scipy.optimize import minimize

from app.data.repository import InstrumentRepository, RuleRepository
from app.domain.engine import RuleEngine, RuleFinding
from app.domain.rules import parse_scope
from app.models.holding import Holding
from app.models.instrument import Instrument
from app.models.rule import Rule


# Vekter under dette regnes som avrundingsstøy fra SLSQP og rundes bort.
# Terskelen for en reell posisjon er min_position_weight (2.0), som er noe annet.
MIN_MEANINGFUL_WEIGHT_PCT = 0.5

# Samme sentinelverdi som exposures.py bruker for ukjent klassifisering.
UNKNOWN_CLASSIFICATION_VALUE = "Unknown"


def _has_unknown_classification(instrument: Instrument) -> bool:
    return UNKNOWN_CLASSIFICATION_VALUE in (
        instrument.asset_class,
        instrument.sector,
        instrument.geography,
    )


class ChangeSummaryItem(BaseModel):
    ticker: str
    original_weight_pct: float
    new_weight_pct: float
    diff_pct: float
    category: Literal["adjusted", "added", "removed"]
    explanation: str


class NearestValidResult(BaseModel):
    holdings: list[Holding] | None
    change_summary: list[ChangeSummaryItem] | None
    explanation: str | None


def find_nearest_valid_portfolio(
    holdings: list[Holding],
    instrument_repo: InstrumentRepository,
    rule_repo: RuleRepository,
    tolerance: float,
    min_position_weight: float = 2.0,
) -> NearestValidResult:
    engine = RuleEngine(rule_repo, tolerance)
    original_result = engine.evaluate(holdings, instrument_repo)
    if original_result.portfolio_valid:
        return NearestValidResult(holdings=holdings, change_summary=[], explanation=None)

    universe = instrument_repo.all()
    original_weights = {holding.ticker: holding.weight_pct for holding in holdings}
    x0 = np.array([original_weights.get(inst.ticker, 0.0) for inst in universe], dtype=float)

    error_rules = [rule for rule in rule_repo.all() if rule.severity == "error"]
    bounds = _build_bounds(universe, error_rules, originally_held_tickers=set(original_weights))
    constraints = _build_constraints(universe, error_rules)

    x = _solve(x0, bounds, constraints)
    if x is None:
        return NearestValidResult(
            holdings=None,
            change_summary=None,
            explanation="Optimeringen konvergerte ikke mot en gyldig løsning.",
        )

    min_holdings_rule = _find_min_holdings_rule(error_rules)
    if min_holdings_rule is not None:
        min_count = int(round(min_holdings_rule.threshold))
        enforced = _enforce_min_holdings(x, min_count, bounds, constraints, x0, min_position_weight)
        if enforced is None:
            return NearestValidResult(
                holdings=None,
                change_summary=None,
                explanation="Klarte ikke å oppfylle minimum antall posisjoner uten å bryte andre regler.",
            )
        x = enforced

    x = _enforce_meaningful_positions(
        x, universe, bounds, constraints, x0, min_position_weight, engine, instrument_repo
    )

    new_holdings = _finalize_holdings(x, universe, bounds)

    revalidation = engine.evaluate(new_holdings, instrument_repo)
    if not revalidation.portfolio_valid:
        return NearestValidResult(
            holdings=None,
            change_summary=None,
            explanation="Fant ingen portefølje som er gyldig innenfor toleransen etter etterbehandling.",
        )

    rules_by_code = {rule.rule_code: rule for rule in rule_repo.all()}
    change_summary = _build_change_summary(
        holdings, new_holdings, original_result.violations, rules_by_code, instrument_repo
    )

    return NearestValidResult(holdings=new_holdings, change_summary=change_summary, explanation=None)


def _build_bounds(
    universe: list[Instrument], error_rules: list[Rule], originally_held_tickers: set[str]
) -> list[tuple[float, float]]:
    upper = 100.0
    for rule in error_rules:
        dimension, _ = parse_scope(rule.scope)
        if dimension != "holding":
            continue
        if "unknown" in rule.metric_definition.lower():
            continue  # kardinalitetsbasert, ikke en vektgrense - ingen error-regel av denne typen i dag
        if rule.operator == "<=":
            upper = min(upper, rule.threshold)
        # en '>=' på holding-scope ville tvunget alle universets instrumenter over grensen,
        # noe som ikke gir mening som boks-constraint - forekommer ikke i dagens rules.csv

    bounds = []
    for inst in universe:
        inst_upper = upper
        if _has_unknown_classification(inst) and inst.ticker not in originally_held_tickers:
            # Å legge til et ukjent-klassifisert instrument ville "løst" ett regelbrudd (f.eks.
            # geografigrensen) ved å innføre et nytt (UNKNOWN_CLASSIFICATION-warning). Instrumenter
            # brukeren allerede eier beholder normal øvre grense og kan justeres/fjernes fritt.
            inst_upper = 0.0
        bounds.append((0.0, inst_upper))
    return bounds


def _build_constraints(universe: list[Instrument], error_rules: list[Rule]) -> list[dict]:
    constraints: list[dict] = []
    for rule in error_rules:
        dimension, value = parse_scope(rule.scope)

        if dimension == "holding":
            continue  # håndtert som bounds i _build_bounds

        if dimension == "portfolio":
            if "count" in rule.metric_definition.lower():
                continue  # MIN_NUMBER_OF_HOLDINGS er kardinalitet, se _enforce_min_holdings
            indices = list(range(len(universe)))
            constraints.append(_make_group_constraint(indices, rule.operator, rule.threshold))
            continue

        if dimension == "asset_class":
            indices = [i for i, inst in enumerate(universe) if inst.asset_class == value]
            constraints.append(_make_group_constraint(indices, rule.operator, rule.threshold))
            continue

        if dimension in ("sector", "geography"):
            groups = sorted({getattr(inst, dimension) for inst in universe})
            for group in groups:
                indices = [i for i, inst in enumerate(universe) if getattr(inst, dimension) == group]
                constraints.append(_make_group_constraint(indices, rule.operator, rule.threshold))
            continue

        raise ValueError(f"Ukjent scope-mønster '{rule.scope}' i regel {rule.rule_code}")

    return constraints


def _make_group_constraint(indices: list[int], operator: str, threshold: float) -> dict:
    idx = np.array(indices, dtype=int)

    if operator == "==":
        return {"type": "eq", "fun": lambda x: float(np.sum(x[idx])) - threshold}
    if operator == "<=":
        return {"type": "ineq", "fun": lambda x: threshold - float(np.sum(x[idx]))}
    if operator == ">=":
        return {"type": "ineq", "fun": lambda x: float(np.sum(x[idx])) - threshold}
    raise ValueError(f"Ukjent operator: {operator}")


def _find_min_holdings_rule(error_rules: list[Rule]) -> Rule | None:
    for rule in error_rules:
        dimension, _ = parse_scope(rule.scope)
        if dimension == "portfolio" and "count" in rule.metric_definition.lower():
            return rule
    return None


def _solve(x0: np.ndarray, bounds: list[tuple[float, float]], constraints: list[dict]) -> np.ndarray | None:
    def objective(x: np.ndarray) -> float:
        return float(np.sum((x - x0) ** 2))

    def gradient(x: np.ndarray) -> np.ndarray:
        return 2.0 * (x - x0)

    try:
        result = minimize(
            objective,
            x0,
            jac=gradient,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
            options={"maxiter": 200, "ftol": 1e-9},
        )
    except Exception:
        return None

    if not result.success:
        return None

    return result.x


def _enforce_min_holdings(
    x: np.ndarray,
    min_count: int,
    bounds: list[tuple[float, float]],
    constraints: list[dict],
    x0: np.ndarray,
    min_position_weight: float,
) -> np.ndarray | None:
    # Bruker min_position_weight (domenegrensen for en "reell" posisjon) her, ikke
    # MIN_MEANINGFUL_WEIGHT_PCT (ren avrundingsstøy) - MIN_NUMBER_OF_HOLDINGS skal telle
    # meningsfulle posisjoner, ellers kan _enforce_meaningful_positions siden fjerne nok
    # posisjoner til at antallet igjen havner under minimumskravet.
    current_count = int(np.sum(x >= min_position_weight))
    if current_count >= min_count:
        return x

    needed = min_count - current_count
    candidates = sorted(
        (i for i in range(len(x)) if x[i] < min_position_weight and bounds[i][1] > 0),
        key=lambda i: x[i],
        reverse=True,
    )
    if len(candidates) < needed:
        return None

    forced_bounds = list(bounds)
    for i in candidates[:needed]:
        lower, upper = forced_bounds[i]
        forced_bounds[i] = (max(lower, min_position_weight), upper)

    return _solve(x0, forced_bounds, constraints)


def _enforce_meaningful_positions(
    x: np.ndarray,
    universe: list[Instrument],
    bounds: list[tuple[float, float]],
    constraints: list[dict],
    x0: np.ndarray,
    min_position_weight: float,
    engine: RuleEngine,
    instrument_repo: InstrumentRepository,
) -> np.ndarray:
    """Fjerner posisjoner uten reell betydning (over avrundingsstøy, men under
    min_position_weight). Den kvadratiske målfunksjonen foretrekker i seg selv å spre en
    nødvendig vektendring tynt ut over mange posisjoner fremfor å konsentrere den - det er
    derfor slike posisjoner oppstår. Løsningen er etterbehandling med fallback: ekskluder de
    små posisjonene helt og løs på nytt, slik at vekten samler seg på de gjenværende (typisk
    posisjoner brukeren allerede eier, siden de sjelden er blant de som ble ekskludert).
    Gir ikke det andre forsøket en gyldig løsning, beholdes det opprinnelige resultatet."""
    small_indices = [i for i in range(len(x)) if MIN_MEANINGFUL_WEIGHT_PCT <= x[i] < min_position_weight]
    if not small_indices:
        return x

    trimmed_bounds = list(bounds)
    for i in small_indices:
        trimmed_bounds[i] = (0.0, 0.0)

    retried = _solve(x0, trimmed_bounds, constraints)
    if retried is None:
        return x

    retried_holdings = _finalize_holdings(retried, universe, trimmed_bounds)
    revalidation = engine.evaluate(retried_holdings, instrument_repo)
    if not revalidation.portfolio_valid:
        return x

    return retried


def _finalize_holdings(
    x: np.ndarray, universe: list[Instrument], bounds: list[tuple[float, float]]
) -> list[Holding]:
    rounded = np.round(x, 2)
    rounded[rounded < MIN_MEANINGFUL_WEIGHT_PCT] = 0.0

    # TOTAL_WEIGHT_EQUALS_100 er allerede en constraint i selve optimeringen, så x summerer
    # til ~100 før avrunding. Avviket her kommer kun fra uavhengig 2-desimalers avrunding av
    # hver posisjon - derfor korrigeres det additivt på én posisjon, ikke ved multiplikativ
    # skalering av alle (som kan skyve en posisjon som allerede ligger på sin grense, over den).
    if float(rounded.sum()) > 0:
        diff = round(100.0 - float(rounded.sum()), 2)
        if diff != 0:
            _apply_rounding_diff(rounded, diff, bounds)

    return [
        Holding(ticker=universe[i].ticker, weight_pct=float(rounded[i]))
        for i in range(len(universe))
        if rounded[i] > 0
    ]


def _apply_rounding_diff(rounded: np.ndarray, diff: float, bounds: list[tuple[float, float]]) -> None:
    """Legger siste avrundingsdiff (typisk +/-0.01-0.02) på den største posisjonen som faktisk
    har takhøyde, slik at summen blir eksakt 100 uten å skyve en posisjon over sin egen grense
    (f.eks. MAX_SINGLE_HOLDING) - noe som ellers kan skje når en posisjon allerede ligger på taket."""
    order = np.argsort(-rounded)
    for i in order:
        candidate = round(float(rounded[i]) + diff, 2)
        _, upper = bounds[i]
        if MIN_MEANINGFUL_WEIGHT_PCT <= candidate <= upper:
            rounded[i] = candidate
            return
    # Ingen enkeltposisjon hadde takhøyde (skjer sjelden med diff i denne størrelsesordenen).
    # Revalideringen lenger opp fanger opp om dette faktisk bryter en regel.
    idx = int(np.argmax(rounded))
    rounded[idx] = round(float(rounded[idx]) + diff, 2)


def _direction_relieves_violation(rule: Rule, diff: float) -> bool:
    """Et makstak (<=) kan bare avlastes ved reduksjon, en bunngrense (>=) bare ved økning.
    En instrument-økning kan altså aldri være årsaken til at et makstak overholdes, og omvendt."""
    if rule.operator == "<=":
        return diff < 0
    if rule.operator == ">=":
        return diff > 0
    return True  # "==" (totalvekt) kan kreve justering i begge retninger


def _rule_applies_to_instrument(
    rule: Rule, violation: RuleFinding, instrument: Instrument, original_weight: float, diff: float
) -> bool:
    if not _direction_relieves_violation(rule, diff):
        return False
    dimension, value = parse_scope(rule.scope)
    if dimension == "asset_class":
        return instrument.asset_class == value
    if dimension == "sector":
        return instrument.sector == violation.scope_detail
    if dimension == "geography":
        return instrument.geography == violation.scope_detail
    if dimension == "holding":
        return original_weight > rule.threshold
    if dimension == "portfolio":
        return True
    return False


def _select_driver(candidates: list[tuple[Rule, RuleFinding]]) -> tuple[Rule, RuleFinding] | None:
    if not candidates:
        return None

    def priority(item: tuple[Rule, RuleFinding]) -> tuple[int, float]:
        rule, violation = item
        dimension, _ = parse_scope(rule.scope)
        is_generic = dimension == "portfolio"
        return (1 if is_generic else 0, -violation.excess)

    return min(candidates, key=priority)


def _explain_change(
    instrument: Instrument,
    diff: float,
    original_weight: float,
    violations: list[RuleFinding],
    rules_by_code: dict[str, Rule],
) -> str:
    candidates = [
        (rules_by_code[violation.rule_code], violation)
        for violation in violations
        if violation.rule_code in rules_by_code
        and _rule_applies_to_instrument(
            rules_by_code[violation.rule_code], violation, instrument, original_weight, diff
        )
    ]
    driver = _select_driver(candidates)
    direction = "økt" if diff > 0 else "redusert"

    if driver is None:
        return f"Vekt {direction} for å oppfylle regelverket."

    rule, _ = driver
    return f"Vekt {direction} fordi porteføljen brøt {rule.rule_code} ({rule.description_no})."


def _build_change_summary(
    original_holdings: list[Holding],
    new_holdings: list[Holding],
    original_violations: list[RuleFinding],
    rules_by_code: dict[str, Rule],
    instrument_repo: InstrumentRepository,
) -> list[ChangeSummaryItem]:
    original_weights = {holding.ticker: holding.weight_pct for holding in original_holdings}
    new_weights = {holding.ticker: holding.weight_pct for holding in new_holdings}

    items: list[ChangeSummaryItem] = []
    for ticker in sorted(set(original_weights) | set(new_weights)):
        original_weight = original_weights.get(ticker, 0.0)
        new_weight = new_weights.get(ticker, 0.0)
        diff = round(new_weight - original_weight, 2)
        if diff == 0:
            continue

        if original_weight == 0:
            category: Literal["adjusted", "added", "removed"] = "added"
        elif new_weight == 0:
            category = "removed"
        else:
            category = "adjusted"

        instrument = instrument_repo.get(ticker)
        if instrument is None:
            continue

        explanation = _explain_change(instrument, diff, original_weight, original_violations, rules_by_code)

        items.append(
            ChangeSummaryItem(
                ticker=ticker,
                original_weight_pct=original_weight,
                new_weight_pct=new_weight,
                diff_pct=diff,
                category=category,
                explanation=explanation,
            )
        )
    return items
