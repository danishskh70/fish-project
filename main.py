from fastapi import FastAPI
from app.api.health import router as health_router
from app.api.fish_types import router as fish_types_router
from app.api.customers import router as customers_router
from app.api.suppliers import router as suppliers_router
from app.api.trips import router as trips_router
from app.api.trip_customers import router as trip_customers_router
from app.api.trip_customer_requirements import (
    router as trip_customer_requirements_router,
)
from pathlib import Path
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
FRONTEND_DIR = Path(__file__).resolve().parent / "frontend"

app=FastAPI()
app.mount(
    "/static",
    StaticFiles(directory=FRONTEND_DIR),
    name="static",
)
app.include_router(health_router,prefix="/api")
app.include_router(fish_types_router, prefix="/api")
app.include_router(customers_router, prefix="/api")
app.include_router(suppliers_router, prefix="/api")
app.include_router(trips_router,prefix="/api")
app.include_router(trip_customers_router,prefix="/api")
app.include_router(
    trip_customer_requirements_router,
    prefix="/api",
)


FRONTEND_DIR = Path(__file__).resolve().parent / "frontend"


@app.get("/", include_in_schema=False)
def root():
    return FileResponse(FRONTEND_DIR / "index.html")