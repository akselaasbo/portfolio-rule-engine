import csv
from pathlib import Path

from pydantic import ValidationError

from app.models.instrument import Instrument
from app.models.rule import Rule


def load_instruments(path: Path) -> list[Instrument]:
    """Leser instrumenter fra CSV. Kaster videre ved manglende fil eller ugyldige rader."""
    with open(path, newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        return [Instrument(**row) for row in reader]


def load_rules(path: Path) -> list[Rule]:
    """Leser regler fra CSV. Ugyldige rader (f.eks. ukjent operator) feiler med rule_code i meldingen."""
    rules: list[Rule] = []
    with open(path, newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            try:
                rules.append(Rule(**row))
            except ValidationError as exc:
                rule_code = row.get("rule_code", "?")
                raise ValueError(f"Ugyldig regel '{rule_code}' i {path}: {exc}") from exc
    return rules
