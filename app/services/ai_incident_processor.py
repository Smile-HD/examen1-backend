# Servicio puente para integrar IA de clasificación de incidentes.

from dataclasses import dataclass


@dataclass
class AIIncidentProcessingResult:
    # Resultado de preprocesamiento IA que alimenta el flujo de incidentes.
    tipo_problema: str
    texto_extraido: str | None
    estado_procesamiento: str


def _compose_extracted_text(audio_url: str | None, user_text: str | None) -> str | None:
    # Unifica texto transcrito de audio (futuro) con texto escrito por el usuario.
    parts: list[str] = []

    if audio_url:
        # Placeholder: por ahora guardamos referencia de audio pendiente de transcripción.
        parts.append(f"[audio_ref]{audio_url}")

    if user_text:
        # Conservamos el texto del usuario para enriquecer el contexto del incidente.
        parts.append(f"[texto_usuario]{user_text}")

    if not parts:
        return None

    return "\n".join(parts)


def process_incident_payload_for_ai(
    *,
    image_url: str | None,
    audio_url: str | None,
    user_text: str | None,
) -> AIIncidentProcessingResult:
    # Punto único de integración IA para sustituir con modelo real más adelante.
    _ = image_url

    # Placeholder actual: marcamos que la clasificación está pendiente de IA real.
    tipo_problema = "pendiente_clasificacion_ia"

    # Generamos texto combinado para persistir contexto base en evidencia.
    texto_extraido = _compose_extracted_text(audio_url, user_text)

    return AIIncidentProcessingResult(
        tipo_problema=tipo_problema,
        texto_extraido=texto_extraido,
        estado_procesamiento="pendiente_modelo_ia",
    )
