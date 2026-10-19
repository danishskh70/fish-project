from urllib.parse import urlparse

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.auth import router as auth_router
from app.api.customers import router as customers_router
from app.api.deps import require_owner
from app.api.fish_types import router as fish_types_router
from app.api.health import router as health_router
from app.api.suppliers import router as suppliers_router
from app.api.trip_customer_requirements import (
    router as trip_customer_requirements_router,
)
from app.api.trip_customers import router as trip_customers_router
from app.api.trips import router as trips_router
from app.core.config import settings

docs_off = settings.app_env == "production"

app = FastAPI(
    docs_url=None if docs_off else "/docs",
    redoc_url=None if docs_off else "/redoc",
    openapi_url=None if docs_off else "/openapi.json",
)

UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


@app.middleware("http")
async def reject_foreign_origin(request: Request, call_next):
    # Browsers always send Origin on cross-site writes. Block unknown ones.
    # No Origin header (curl, server to server) passes. Reads pass.
    origin = request.headers.get("origin")
    if origin and request.method in UNSAFE_METHODS:
        same_site = urlparse(origin).netloc == request.headers.get("host", "")
        if origin not in settings.allowed_origins and not same_site:
            return JSONResponse(
                status_code=403,
                content={"detail": "Origin not allowed."},
            )
    return await call_next(request)


# Added after the middleware above, so CORS runs first.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["content-type", "authorization"],
    allow_credentials=True,
)


@app.get("/")
def root():
    return "root"


guard = [Depends(require_owner)]

app.include_router(health_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(fish_types_router, prefix="/api", dependencies=guard)
app.include_router(customers_router, prefix="/api", dependencies=guard)
app.include_router(suppliers_router, prefix="/api", dependencies=guard)
app.include_router(trips_router, prefix="/api", dependencies=guard)
app.include_router(trip_customers_router, prefix="/api", dependencies=guard)
app.include_router(
    trip_customer_requirements_router,
    prefix="/api",
    dependencies=guard,
)