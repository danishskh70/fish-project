from fastapi import FastAPI
from app.api.health import router as health_router
from app.api.fish_types import router as fish_types_router
from app.api.customers import router as customers_router


app=FastAPI()

app.include_router(health_router,prefix="/api")
app.include_router(fish_types_router, prefix="/api")
app.include_router(customers_router, prefix="/api")


@app.get("/")
def root():
    return {"message": "Root endpoint"} 