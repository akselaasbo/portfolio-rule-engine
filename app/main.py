from fastapi import FastAPI

app = FastAPI(
    title="Portfolio Rule Engine",
    description="Validerer porteføljer mot regelsettet i rules.csv",
    version="0.1.0",
)


@app.get("/health")
def health() -> dict:
    """Enkel liveness-sjekk. Brukes av Azure App Service."""
    return {"status": "ok", "version": app.version}
