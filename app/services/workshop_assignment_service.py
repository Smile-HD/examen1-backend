"""Logica de matching/asignacion de talleres para incidentes."""

import math
import re

from app.models.incident import Incidente
from app.models.incident_schemas import WorkshopCandidateItem

PROBLEM_SERVICE_MAP: dict[str, set[str]] = {
    "bateria": {"bateria", "auxilio_electrico", "mecanica_general"},
    "llanta": {"llanta", "vulcanizado", "mecanica_general"},
    "choque": {"carroceria", "grua", "accidentes", "mecanica_general"},
    "motor": {"motor", "mecanica_general", "grua"},
    "llave": {"cerrajeria", "apertura", "mecanica_general"},
    "otros": {"mecanica_general"},
}


def _parse_location_coordinates(raw_location: str | None) -> tuple[float, float] | None:
    # Intenta extraer latitud,longitud desde texto de ubicacion del taller.
    if not raw_location:
        return None

    match = re.search(r"(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)", raw_location)
    if not match:
        return None

    lat = float(match.group(1))
    lon = float(match.group(2))
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None

    return (lat, lon)


def _calculate_distance_km(
    incident_lat: float | None,
    incident_lon: float | None,
    workshop_lat: float | None,
    workshop_lon: float | None,
) -> float | None:
    # Distancia Haversine para ranking geografico.
    if (
        incident_lat is None
        or incident_lon is None
        or workshop_lat is None
        or workshop_lon is None
    ):
        return None

    radius = 6371.0
    lat1 = math.radians(float(incident_lat))
    lon1 = math.radians(float(incident_lon))
    lat2 = math.radians(float(workshop_lat))
    lon2 = math.radians(float(workshop_lon))

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    haversine = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    arc = 2 * math.atan2(math.sqrt(haversine), math.sqrt(1 - haversine))
    return round(radius * arc, 2)


def _resolve_workshop_coordinates(row: dict[str, object]) -> tuple[float, float] | None:
    # Prioriza coordenadas estructuradas; si faltan, intenta parsear el texto legacy.
    lat = row.get("latitud")
    lon = row.get("longitud")
    if lat is not None and lon is not None:
        return float(lat), float(lon)

    return _parse_location_coordinates(str(row.get("ubicacion") or ""))


def _score_workshop_candidate(
    *,
    distance_meters: float | None,
    is_active: bool,
    has_service: bool,
    has_capacity: bool,
) -> float:
    # Score estricto: primero criterios booleanos, luego desempata por distancia.
    criteria_score = (
        (25.0 if is_active else 0.0)
        + (25.0 if has_service else 0.0)
        + (25.0 if has_capacity else 0.0)
        + (25.0 if distance_meters is not None else 0.0)
    )

    if distance_meters is None:
        distance_bonus = 0.0
    else:
        # 0m -> +10, 10km o mas -> +0
        distance_bonus = max(0.0, 10.0 - (float(distance_meters) / 1000.0))

    return round(criteria_score + distance_bonus, 2)


def build_incident_candidates(
    *,
    incident: Incidente,
    workshop_rows: list[dict[str, object]],
) -> list[WorkshopCandidateItem]:
    # Arma ranking estricto y conserva opciones no recomendadas para fallback UI.
    expected_services = PROBLEM_SERVICE_MAP.get(incident.tipo_problema, {"mecanica_general"})

    pre_candidates: list[tuple[WorkshopCandidateItem, bool]] = []
    for row in workshop_rows:
        services = {str(name).strip().lower() for name in row.get("services", [])}
        service_match = bool(services.intersection(expected_services))

        available_technicians = int(row.get("available_technicians", 0))
        available_transports = int(row.get("available_transports", 0))
        capacity_available = available_technicians > 0 and available_transports > 0

        is_active = str(row.get("estado") or "").strip().lower() == "activo"

        workshop_coords = _resolve_workshop_coordinates(row)
        distance_km = _calculate_distance_km(
            incident.latitud,
            incident.longitud,
            workshop_coords[0] if workshop_coords else None,
            workshop_coords[1] if workshop_coords else None,
        )
        distance_meters = round(distance_km * 1000, 2) if distance_km is not None else None

        is_recommended = all(
            [
                is_active,
                service_match,
                capacity_available,
                distance_meters is not None,
            ]
        )

        score = _score_workshop_candidate(
            distance_meters=distance_meters,
            is_active=is_active,
            has_service=service_match,
            has_capacity=capacity_available,
        )

        reason_parts = [
            "servicio_ok" if service_match else "servicio_no_cubre_problema",
            "taller_activo" if is_active else "taller_inactivo",
            "capacidad_ok" if capacity_available else "sin_tecnico_o_transporte_disponible",
            (
                f"distancia={distance_meters}m"
                if distance_meters is not None
                else "distancia_no_disponible"
            ),
            "recomendado" if is_recommended else "opciones_no_recomendadas",
        ]

        pre_candidates.append(
            (
                WorkshopCandidateItem(
                    taller_id=int(row["taller_id"]),
                    nombre_taller=str(row["nombre_taller"]),
                    disponibilidad=str(row.get("estado") or "activo"),
                    taller_activo=is_active,
                    capacidad_disponible=capacity_available,
                    tecnicos_disponibles=available_technicians,
                    transportes_disponibles=available_transports,
                    cumple_servicio=service_match,
                    cumple_tipo_problema=service_match,
                    distancia_metros=distance_meters,
                    distancia_km=distance_km,
                    recomendado=is_recommended,
                    categoria_recomendacion=(
                        "recomendado" if is_recommended else "opciones_no_recomendadas"
                    ),
                    puntuacion=score,
                    servicios=sorted(services),
                    razon=", ".join(reason_parts),
                ),
                is_recommended,
            )
        )

    recommended = [candidate for candidate, is_recommended in pre_candidates if is_recommended]
    not_recommended = [candidate for candidate, is_recommended in pre_candidates if not is_recommended]

    recommended.sort(
        key=lambda candidate: (
            candidate.puntuacion,
            -(candidate.distancia_metros or float("inf")),
        ),
        reverse=True,
    )
    not_recommended.sort(
        key=lambda candidate: (
            candidate.puntuacion,
            -(candidate.distancia_metros or float("inf")),
        ),
        reverse=True,
    )

    # Orden final: recomendados primero; luego "Opciones no recomendadas".
    return [*recommended, *not_recommended]
