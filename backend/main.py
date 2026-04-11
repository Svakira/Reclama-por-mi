# backend/main.py
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.api.auth_routes import router as auth_router
from backend.api.cases_routes import router as cases_router
from backend.api.drafts_routes import router as drafts_router
from backend.api.pipeline_routes import router as pipeline_router
from backend.api.lawyer_routes import router as lawyer_router
from backend.api.notify_routes import router as notify_router
from backend.db.firestore_client import seed_demo_case

app = FastAPI(title="JusticIA API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(cases_router, prefix="/api", tags=["cases"])
app.include_router(drafts_router, prefix="/api", tags=["drafts"])
app.include_router(pipeline_router, prefix="/api/pipeline", tags=["pipeline"])
app.include_router(lawyer_router, prefix="/api/lawyer", tags=["lawyer"])
app.include_router(notify_router, prefix="/api/notify", tags=["notify"])


@app.on_event("startup")
async def startup():
    seed_demo_case()


@app.get("/health")
async def health():
    return {"status": "ok"}


# Serve React frontend (built to frontend/dist) — Replit production mode
_frontend_dist = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.isdir(_frontend_dist):
    app.mount("/", StaticFiles(directory=_frontend_dist, html=True), name="frontend")
