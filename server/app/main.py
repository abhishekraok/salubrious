from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, engine
from .routers import allocation, insights, policy, portfolio, prices, recommendation, settings, spending


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Salubrious", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(policy.router)
app.include_router(settings.router)
app.include_router(portfolio.router)
app.include_router(allocation.router)
app.include_router(recommendation.router)
app.include_router(prices.router)
app.include_router(spending.router)
app.include_router(insights.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
