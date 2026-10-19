
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.customers import router as customers_router
from app.api.fish_types import router as fish_types_router
from app.api.health import router as health_router
from app.api.suppliers import router as suppliers_router
from app.api.trip_customer_requirements import (
    router as trip_customer_requirements_router,
)
from app.api.trip_customers import router as trip_customers_router
from app.api.trips import router as trips_router
from app.core.config import settings

# FRONTEND_DIR = Path(__file__).resolve().parent / "frontend"

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_origin_regex=settings.cors_origin_regex,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
)

# if FRONTEND_DIR.is_dir():
#     app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

#     @app.get("/", include_in_schema=False)
#     def root():
#         return FileResponse(FRONTEND_DIR / "index.html")

@app.get("/")
def root():
    return "root"
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

