from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.auth import router as auth_router
from app.routers.health import router as health_router
from app.routers.incidents import router as incidents_router
from app.routers.users import router as users_router
from app.routers.vehicles import router as vehicles_router

app = FastAPI(title="Emergencias API")

app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=False,
	allow_methods=["*"],
	allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(vehicles_router)
app.include_router(incidents_router)
