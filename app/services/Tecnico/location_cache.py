from datetime import datetime
from pydantic import BaseModel

class TechnicianLocationInMemory(BaseModel):
    tecnico_id: int
    solicitud_id: int | None = None
    latitud: float
    longitud: float
    precision_metros: float | None = None
    actualizada_en: datetime

ACTIVE_TECHNICIAN_LOCATIONS: dict[int, TechnicianLocationInMemory] = {}
