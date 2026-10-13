from fastapi import FastAPI
from app.api.health import router as health_router
from app.api.fish_types import router as fish_types_router
from app.api.customers import router as customers_router
from app.api.suppliers import router as suppliers_router
from app.api.trips import router as trips_router
from app.api.trip_customers import router as trip_customers_router

app=FastAPI()

app.include_router(health_router,prefix="/api")
app.include_router(fish_types_router, prefix="/api")
app.include_router(customers_router, prefix="/api")
app.include_router(suppliers_router, prefix="/api")
app.include_router(trips_router,prefix="/api")
app.include_router(trip_customers_router,prefix="/api")


@app.get("/")
def root():
    return {"message": "Root endpoint"} 