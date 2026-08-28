import csv
from pathlib import Path

from app.models.instrument import Instrument


def load_instruments(path: Path) -> list[Instrument]:
    """Leser instrumenter fra CSV. Kaster videre ved manglende fil eller ugyldige rader."""
    with open(path, newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        return [Instrument(**row) for row in reader]
