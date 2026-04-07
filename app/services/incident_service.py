# Servicio de negocio para CU4: reportar emergencia vehicular.

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.incident_schemas import IncidentReportRequest, IncidentReportResponse
from app.repositories.incident_repository import IncidentRepository
from app.services.ai_incident_processor import process_incident_payload_for_ai


class VehicleNotOwnedError(Exception):
    # Error de dominio cuando el vehiculo no existe o no pertenece al cliente.
    pass


class LocationRequiredError(Exception):
    # Error de dominio cuando no se pudo obtener ubicacion para la solicitud.
    pass


def report_incident(
    data: IncidentReportRequest,
    *,
    cliente_id: int,
    db: Session,
) -> IncidentReportResponse:
    # Ejecuta flujo principal del CU4: validar, registrar e iniciar procesamiento.
    repository = IncidentRepository(db)

    if data.latitud is None or data.longitud is None:
        raise LocationRequiredError("No se pudo obtener la ubicacion del usuario.")

    vehicle = repository.get_vehicle_for_client(data.vehiculo_placa, cliente_id)
    if not vehicle:
        raise VehicleNotOwnedError(
            "El vehiculo no existe o no pertenece al cliente autenticado."
        )

    pending_state = repository.get_or_create_service_state(
        name="pendiente",
        description="Incidente reportado pendiente de evaluacion.",
    )

    # Preprocesamiento IA previo a despacho a talleres (placeholder para integración real).
    ai_result = process_incident_payload_for_ai(
        image_url=data.imagen_url,
        audio_url=data.audio_url,
        user_text=data.texto_usuario,
    )

    try:
        # Registramos el incidente base con la informacion enviada por app movil.
        incident = repository.create_incident(
            cliente_id=cliente_id,
            vehiculo_placa=data.vehiculo_placa,
            estado_servicio_id=pending_state.id,
            tipo_problema=ai_result.tipo_problema,
            descripcion=data.texto_usuario,
            ubicacion=data.ubicacion,
            latitud=data.latitud,
            longitud=data.longitud,
            prioridad=2,
        )

        # Guardamos imagen (si existe) en columna url de evidencia, como pidió el flujo móvil.
        if data.imagen_url:
            repository.create_evidence(
                incidente_id=incident.id,
                tipo="imagen",
                url=data.imagen_url,
                texto_extraido=None,
            )

        # Guardamos texto extraído (audio + texto usuario) en evidencia textual.
        if ai_result.texto_extraido:
            repository.create_evidence(
                incidente_id=incident.id,
                tipo="texto",
                url=None,
                texto_extraido=ai_result.texto_extraido,
            )

        # Trazabilidad del flujo: reporte recibido y procesamiento iniciado.
        repository.create_history(
            incidente_id=incident.id,
            accion="incidente_reportado",
            descripcion="Cliente reporto emergencia desde app movil.",
            actor_usuario_id=cliente_id,
        )
        repository.create_history(
            incidente_id=incident.id,
            accion="ia_preprocesamiento",
            descripcion=(
                "Preprocesamiento IA ejecutado. "
                f"estado={ai_result.estado_procesamiento}, "
                f"tipo_problema={ai_result.tipo_problema}."
            ),
            actor_usuario_id=cliente_id,
        )
        repository.create_history(
            incidente_id=incident.id,
            accion="procesamiento_iniciado",
            descripcion="Se inicia procesamiento inicial de clasificacion del incidente.",
            actor_usuario_id=cliente_id,
        )

        db.commit()
        db.refresh(incident)
    except IntegrityError:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise

    return IncidentReportResponse(
        incidente_id=incident.id,
        estado=repository.get_service_state_name(incident.estado_servicio_id),
        tipo_problema=incident.tipo_problema,
        procesamiento_ia=ai_result.estado_procesamiento,
        vehiculo_placa=incident.vehiculo_placa,
        fecha_hora=incident.fecha_hora,
        mensaje="Incidente registrado y procesamiento iniciado.",
    )
