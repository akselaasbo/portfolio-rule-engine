from fastapi.testclient import TestClient

VALID_EXAMPLE_PORTFOLIO = {
    "holdings": [
        {"ticker": "VTI", "weight_pct": 25},
        {"ticker": "VXUS", "weight_pct": 20},
        {"ticker": "BND", "weight_pct": 20},
        {"ticker": "VNQ", "weight_pct": 10},
        {"ticker": "GLD", "weight_pct": 5},
        {"ticker": "XLF", "weight_pct": 10},
        {"ticker": "XLK", "weight_pct": 10},
    ]
}


def test_health_returns_200(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200


def test_instruments_returns_all_instruments(client: TestClient) -> None:
    response = client.get("/instruments")
    assert response.status_code == 200
    assert len(response.json()) == 18


def test_validate_example_from_oppgavetekst_returns_200(client: TestClient) -> None:
    response = client.post("/validate", json=VALID_EXAMPLE_PORTFOLIO)
    assert response.status_code == 200


def test_validate_invalid_portfolio_returns_200_with_invalid_flag(client: TestClient) -> None:
    payload = {"holdings": [{"ticker": "VTI", "weight_pct": 100}]}
    response = client.post("/validate", json=payload)
    assert response.status_code == 200
    assert response.json()["portfolio_valid"] is False


def test_violations_carry_correct_unit_per_metric(client: TestClient) -> None:
    # Ett enkelt instrument på 100 % bryter både MIN_NUMBER_OF_HOLDINGS (teller antall
    # posisjoner, ikke prosent) og MAX_SINGLE_GEOGRAPHY_EXPOSURE (prosent) - god dekning for
    # at "unit" per regelbrudd faktisk skiller de to, slik frontend er avhengig av.
    payload = {"holdings": [{"ticker": "VTI", "weight_pct": 100}]}
    response = client.post("/validate", json=payload)
    violations_by_code = {v["rule_code"]: v for v in response.json()["violations"]}

    assert violations_by_code["MIN_NUMBER_OF_HOLDINGS"]["unit"] == "count"
    assert violations_by_code["MAX_SINGLE_GEOGRAPHY_EXPOSURE"]["unit"] == "percent"


def test_validate_unknown_ticker_returns_400(client: TestClient) -> None:
    payload = {"holdings": [{"ticker": "NOPE", "weight_pct": 100}]}
    response = client.post("/validate", json=payload)
    assert response.status_code == 400


def test_validate_empty_holdings_returns_400(client: TestClient) -> None:
    response = client.post("/validate", json={"holdings": []})
    assert response.status_code == 400


def test_validate_duplicate_ticker_returns_400(client: TestClient) -> None:
    payload = {
        "holdings": [
            {"ticker": "VTI", "weight_pct": 50},
            {"ticker": "VTI", "weight_pct": 50},
        ]
    }
    response = client.post("/validate", json=payload)
    assert response.status_code == 400


def test_validate_negative_weight_returns_422(client: TestClient) -> None:
    payload = {"holdings": [{"ticker": "VTI", "weight_pct": -5}]}
    response = client.post("/validate", json=payload)
    assert response.status_code == 422
