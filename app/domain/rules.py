from app.domain.exposures import Exposures

KNOWN_SCOPE_DIMENSIONS = {"portfolio", "holding", "asset_class", "sector", "geography"}


def parse_scope(scope: str) -> tuple[str, str | None]:
    """Splitter 'asset_class:Equity' -> ('asset_class', 'Equity'), 'portfolio' -> ('portfolio', None)."""
    dimension, sep, value = scope.partition(":")
    return dimension, (value if sep else None)


def evaluate_portfolio(metric_definition: str, exposures: Exposures) -> tuple[float, str]:
    if "count" in metric_definition.lower():
        return float(exposures.number_of_holdings), "portfolio"
    return exposures.total_weight, "portfolio"


def evaluate_holding(metric_definition: str, exposures: Exposures) -> tuple[float, str]:
    if "unknown" in metric_definition.lower():
        return float(exposures.unknown_classification_count), "holding"
    return exposures.max_holding_weight, "holding"


def evaluate_asset_class(value: str, exposures: Exposures) -> tuple[float, str]:
    return exposures.by_asset_class.get(value, 0.0), value


def evaluate_sector(exposures: Exposures) -> tuple[float, str]:
    return _max_group(exposures.by_sector)


def evaluate_geography(exposures: Exposures) -> tuple[float, str]:
    return _max_group(exposures.by_geography)


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
