from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.analysis import router as analysis_router
from app.api.routes import router
from app.core.database import settings

app = FastAPI(title="Carbon-Aware Portfolio Research", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["GET"], allow_headers=["*"])
app.include_router(router)

app.include_router(analysis_router)
