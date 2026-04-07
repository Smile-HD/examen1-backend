# Rutas de API para incidentes reportados por clientes moviles.

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.controllers.incident_controller import report_incident_controller
from app.database import get_db
from app.dependencies.auth import AuthenticatedUser, require_mobile_cliente
from app.models.incident_schemas import IncidentReportRequest, IncidentReportResponse

router = APIRouter(prefix="/api/v1/incidentes", tags=["Incidentes"])


@router.post(
    "/reportar",
    response_model=IncidentReportResponse,
    status_code=status.HTTP_201_CREATED,
)
def report_incident_endpoint(
    payload: IncidentReportRequest,
    current_user: AuthenticatedUser = Depends(require_mobile_cliente),
    db: Session = Depends(get_db),
) -> IncidentReportResponse:
    # Endpoint CU4: recibe solicitud de emergencia desde cliente autenticado.
    return report_incident_controller(payload, cliente_id=current_user.user_id, db=db)
