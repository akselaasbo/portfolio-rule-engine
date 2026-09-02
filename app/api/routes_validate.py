from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.routes_instruments import get_repository as get_instrument_repository
from app.config import settings
from app.data.repository import InstrumentRepository
from app.domain.engine import RuleEngine
from app.domain.optimizer import find_nearest_valid_portfolio
from app.models.requests import ValidatePortfolioRequest
from app.models.responses import ValidationResponse

router = APIRouter(tags=["validate"])


def get_rule_engine(request: Request) -> RuleEngine:
    return request.app.state.rule_engine


@router.post("/validate", response_model=ValidationResponse)
def validate_portfolio(
    body: ValidatePortfolioRequest,
    rule_engine: RuleEngine = Depends(get_rule_engine),
    instrument_repo: InstrumentRepository = Depends(get_instrument_repository),
) -> ValidationResponse:
    holdings = body.holdings

    if not holdings:
        raise HTTPException(status_code=400, detail="Porteføljen må inneholde minst én posisjon.")

    ticker_counts = Counter(holding.ticker for holding in holdings)
    duplicates = sorted(ticker for ticker, count in ticker_counts.items() if count > 1)
    if duplicates:
        raise HTTPException(
            status_code=400,
            detail=f"Samme ticker er oppgitt flere ganger: {', '.join(duplicates)}",
        )

    unknown_tickers = [holding.ticker for holding in holdings if not instrument_repo.exists(holding.ticker)]
    if unknown_tickers:
        raise HTTPException(
            status_code=400,
            detail=f"Ukjente tickere: {', '.join(unknown_tickers)}",
        )

    try:
        result = rule_engine.evaluate(holdings, instrument_repo)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    nearest_valid = None
    if result.violations:
        nearest_valid = find_nearest_valid_portfolio(
            holdings,
            instrument_repo,
            rule_engine.rule_repository,
            settings.weight_tolerance,
            settings.min_position_weight_pct,
        )

    return ValidationResponse.from_result(result, nearest_valid)
