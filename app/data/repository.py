from __future__ import annotations

from pathlib import Path

from app.data.loader import load_instruments, load_rules
from app.models.instrument import Instrument
from app.models.rule import Rule


class InstrumentRepository:
    """Oppslag på ticker over instrumentene lastet fra CSV."""

    def __init__(self, instruments: list[Instrument]) -> None:
        self._by_ticker = {instrument.ticker: instrument for instrument in instruments}

    @classmethod
    def from_csv(cls, path: Path) -> InstrumentRepository:
        return cls(load_instruments(path))

    def get(self, ticker: str) -> Instrument | None:
        return self._by_ticker.get(ticker)

    def all(self) -> list[Instrument]:
        return list(self._by_ticker.values())

    def exists(self, ticker: str) -> bool:
        return ticker in self._by_ticker


class RuleRepository:
    """Alle regler lastet fra rules.csv, uten tolkning av innholdet."""

    def __init__(self, rules: list[Rule]) -> None:
        self._rules = list(rules)

    @classmethod
    def from_csv(cls, path: Path) -> RuleRepository:
        return cls(load_rules(path))

    def all(self) -> list[Rule]:
        return list(self._rules)

    def by_severity(self, severity: str) -> list[Rule]:
        return [rule for rule in self._rules if rule.severity == severity]
