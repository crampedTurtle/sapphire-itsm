"""
Sapphire Support Core - Decision Plane + System of Record
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1 import intake, cases, ops, portal, webhooks, onboarding

app = FastAPI(
    title="Sapphire Support Core API",
    description="Decision plane and system of record for customer operations",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(intake.router, prefix="/v1/intake", tags=["intake"])
app.include_router(cases.router, prefix="/v1/cases", tags=["cases"])
app.include_router(ops.router, prefix="/v1/ops", tags=["ops"])
app.include_router(portal.router, prefix="/v1/portal", tags=["portal"])
app.include_router(webhooks.router, prefix="/v1/webhooks", tags=["webhooks"])
app.include_router(onboarding.router, prefix="/v1/onboarding", tags=["onboarding"])


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "sapphire-support-core"}


@app.get("/")
async def root():
    return {
        "service": "sapphire-support-core",
        "version": "1.0.0",
        "docs": "/docs"
    }

