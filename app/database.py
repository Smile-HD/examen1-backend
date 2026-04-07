# Configuracion de base de datos y dependencia de sesion para FastAPI.

import os
from pathlib import Path
from typing import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Cargamos variables de entorno desde backend/.env para una configuracion unificada.
BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")

# Usamos PostgreSQL si existe DATABASE_URL; si no, caemos a SQLite local para desarrollo rapido.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./dev.db")

engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)

# SessionLocal crea sesiones cortas por request para evitar conexiones colgadas.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    # Dependency de FastAPI para inyectar una sesion de base de datos por request.
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
