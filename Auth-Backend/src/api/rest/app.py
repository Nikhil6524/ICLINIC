from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.rest.routes.health import router as health_router
from src.api.rest.routes.auth import router as auth_router
from src.api.rest.routes.users import router as users_router

app = FastAPI(
    title="AuthBackend"
)

# CORS — allow frontend origins with credentials (cookies)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # Docker/production
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    health_router,
    tags=["Health"]
)

app.include_router(auth_router)
app.include_router(users_router)
