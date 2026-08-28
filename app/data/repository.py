from __future__ import annotations

from pathlib import Path

from app.data.loader import load_instruments
from app.models.instrument import Instrument


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
