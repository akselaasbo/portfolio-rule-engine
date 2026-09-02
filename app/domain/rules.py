from app.domain.exposures import Exposures

KNOWN_SCOPE_DIMENSIONS = {"portfolio", "holding", "asset_class", "sector", "geography"}


def parse_scope(scope: str) -> tuple[str, str | None]:
    """Splitter 'asset_class:Equity' -> ('asset_class', 'Equity'), 'portfolio' -> ('portfolio', None)."""
    dimension, sep, value = scope.partition(":")
    return dimension, (value if sep else None)


def evaluate_portfolio(metric_definition: str, exposures: Exposures) -> tuple[float, str, str]:
    if "count" in metric_definition.lower():
        return float(exposures.number_of_holdings), "portfolio", "count"
    return exposures.total_weight, "portfolio", "percent"


def evaluate_holding(metric_definition: str, exposures: Exposures) -> tuple[float, str, str]:
    if "unknown" in metric_definition.lower():
        return float(exposures.unknown_classification_count), "holding", "count"
    return exposures.max_holding_weight, "holding", "percent"


def evaluate_asset_class(value: str, exposures: Exposures) -> tuple[float, str, str]:
    return exposures.by_asset_class.get(value, 0.0), value, "percent"


def evaluate_sector(exposures: Exposures) -> tuple[float, str, str]:
    value, group = _max_group(exposures.by_sector)
    return value, group, "percent"


def evaluate_geography(exposures: Exposures) -> tuple[float, str, str]:
    value, group = _max_group(exposures.by_geography)
    return value, group, "percent"


def _max_group(groups: dict[str, float]) -> tuple[float, str]:
    if not groups:
        return 0.0, "-"
    group, value = max(groups.items(), key=lambda item: item[1])
    return value, group


def satisfies(value: float, operator: str, threshold: float, tolerance: float) -> bool:
    if operator == "<=":
        return value <= threshold + tolerance
    if operator == ">=":
        return value >= threshold - tolerance
    if operator == "==":
        return abs(value - threshold) <= tolerance
    raise ValueError(f"Ukjent operator: {operator}")
