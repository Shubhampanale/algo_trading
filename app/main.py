from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.bootstrap import lifespan
from app.api.middleware.response_wrapper import ResponseWrapperMiddleware

app = FastAPI(
    title="Trading Engine",
    lifespan=lifespan,
    version="1.0.0",
    openapi_version="3.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Standardize all JSON responses into a common envelope.
app.add_middleware(ResponseWrapperMiddleware)
app.include_router(api_router)


@app.get("/")
async def root():
    return {"message": "Trading Engine Running"}
