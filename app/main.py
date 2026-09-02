from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes_instruments import router as instruments_router
from app.api.routes_validate import router as validate_router
from app.config import settings
from app.data.repository import InstrumentRepository, RuleRepository
from app.domain.engine import RuleEngine


@asynccontextmanager
async def lifespan(app: FastAPI):
    instruments_path = settings.data_path / "instruments.csv"
    try:
        app.state.instrument_repository = InstrumentRepository.from_csv(instruments_path)
    except Exception as exc:
        raise RuntimeError(
            f"Klarte ikke å laste instrumenter fra {instruments_path}: {exc}"
        ) from exc

    rules_path = settings.data_path / "rules.csv"
    try:
        rule_repository = RuleRepository.from_csv(rules_path)
        app.state.rule_engine = RuleEngine(rule_repository, settings.weight_tolerance)
    except Exception as exc:
        raise RuntimeError(f"Klarte ikke å laste regler fra {rules_path}: {exc}") from exc

    yield


app = FastAPI(
    title="Portfolio Rule Engine",
    description="Validerer porteføljer mot regelsettet i rules.csv",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(instruments_router)
app.include_router(validate_router)


@app.get("/health")
def health() -> dict:
    """Enkel liveness-sjekk. Brukes av Azure App Service."""
    return {"status": "ok", "version": app.version}
