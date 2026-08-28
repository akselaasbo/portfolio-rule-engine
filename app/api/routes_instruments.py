from fastapi import APIRouter, Depends, Request

from app.data.repository import InstrumentRepository
from app.models.instrument import Instrument

router = APIRouter(tags=["instruments"])


def get_repository(request: Request) -> InstrumentRepository:
    return request.app.state.instrument_repository


@router.get("/instruments", response_model=list[Instrument])
def list_instruments(
    repository: InstrumentRepository = Depends(get_repository),
) -> list[Instrument]:
    return repository.all()
