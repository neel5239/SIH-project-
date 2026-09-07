from uuid import uuid4
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from .settings import settings
from .api.auth import router as auth_router
from .api.health import router as health_router
from .api.sessions import router as sessions_router
from .api.turn import router as turn_router
from .api.jobs import router as jobs_router
from .api.triage import router as triage_router
from .api.doctor import router as doctor_router
from .api.provenance import router as provenance_router
from .api.patient import router as patient_router
from .api.metrics import router as metrics_router
from .api.admin import router as admin_router
from .api.fhir import router as fhir_router


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="PURVA Platform Core & Clinical Services",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid4()))
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(Exception)
async def generic_error(request: Request, exc: Exception):
    request_id = request.headers.get("X-Request-ID", str(uuid4()))

    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Internal server error",
                "request_id": request_id,
                "retryable": True,
            }
        },
        headers={"X-Request-ID": request_id},
    )


prefix = "/api/v1"

app.include_router(auth_router, prefix=prefix)
app.include_router(health_router, prefix=prefix)
app.include_router(sessions_router, prefix=prefix)
app.include_router(turn_router, prefix=prefix)
app.include_router(jobs_router, prefix=prefix)
app.include_router(triage_router, prefix=prefix)
app.include_router(doctor_router, prefix=prefix)
app.include_router(provenance_router, prefix=prefix)
app.include_router(patient_router, prefix=prefix)
app.include_router(metrics_router, prefix=prefix)
app.include_router(admin_router, prefix=prefix)
app.include_router(fhir_router, prefix=prefix)


@app.get("/")
def root():
    return {
        "service": "PURVA M6",
        "status": "running",
        "version": settings.app_version,
    }
