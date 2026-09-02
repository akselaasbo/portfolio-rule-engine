import csv
from collections import defaultdict

from app.config import settings
from app.models.holding import Holding


def load_sample_portfolios() -> dict[str, list[Holding]]:
    portfolios: dict[str, list[Holding]] = defaultdict(list)
    path = settings.data_path / "sample_portfolios.csv"
    with open(path, newline="", encoding="utf-8") as csv_file:
        for row in csv.DictReader(csv_file):
            portfolios[row["portfolio_id"]].append(
                Holding(ticker=row["ticker"], weight_pct=float(row["weight_pct"]))
            )
    return portfolios


def load_expected_outcomes() -> dict[str, str]:
    path = settings.data_path / "expected_outcomes.csv"
    with open(path, newline="", encoding="utf-8") as csv_file:
        return {row["portfolio_id"]: row["expected_result"] for row in csv.DictReader(csv_file)}
