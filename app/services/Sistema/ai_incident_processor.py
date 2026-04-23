"""Integracion IA para procesamiento inicial de incidentes.

Nucleo actual del modulo:
- Transcripcion de audio exclusivamente con Vosk (offline/local).
- Analisis de imagen con Hugging Face Inference API.
- Clasificacion heuristica del tipo de problema y prioridad.

"""

from dataclasses import dataclass
from functools import lru_cache
import json
import logging
import os
from pathlib import Path
import subprocess
from tempfile import NamedTemporaryFile
import time
import unicodedata
import wave

import httpx

from app.core.evidence_storage import resolve_local_evidence_path_from_url


logger = logging.getLogger(__name__)


@dataclass
class AIIncidentProcessingResult:
    # Resultado de preprocesamiento IA que alimenta el flujo de incidentes.
    tipo_problema: str
    prioridad: int
    informacion_suficiente: bool
    resumen_incidente: str | None
    solicitud_mas_informacion: str | None
    texto_extraido: str | None
    estado_procesamiento: str
    audio_transcripcion: str | None = None
    image_summary: str | None = None
    problem_deduced: bool = False


# Mapa de catalogo servicio -> categoria de incidente usada por el motor actual.
SERVICE_TO_PROBLEM: dict[str, str] = {
    "mecanica_general": "otros",
    "bateria": "bateria",
    "auxilio_electrico": "bateria",
    "llanta": "llanta",
    "vulcanizado": "llanta",
    "carroceria": "choque",
    "grua": "choque",
    "accidentes": "choque",
    "motor": "motor",
    "cerrajeria": "llave",
    "apertura": "llave",
}


# Palabras clave de texto (usuario + audio) por servicio.
SERVICE_TEXT_KEYWORDS: dict[str, list[str]] = {
    "mecanica_general": [
        "falla mecanica", "averia", "descompuesto", "ruido raro", "vibracion", "diagnostico",
    ],
    "bateria": [
        "bateria", "no arranca", "no enciende", "sin corriente", "sin energia", "descargad", "alternador", "arranque","batery",
    ],
    "auxilio_electrico": [
        "falla electrica", "corto", "fusible", "tablero", "luces", "electrico", "cables", "switch",
    ],
    "llanta": [
        "llanta", "neumatic", "rueda", "pinch", "ponch", "revent", "desinflad", "flat tire", "tire", "tyre",
    ],
    "vulcanizado": [
        "vulcanizado", "parche", "pinchadura", "ponchadura", "goma", "cambio de llanta",
    ],
    "carroceria": [
        "carroceria", "parachoque", "parabrisas", "guardabarros", "puerta", "abollad", "pintura", "chasis",
    ],
    "grua": [
        "grua", "remolque", "arrastre", "jalon", "traslado", "tow", "towing", "camion plataforma",
    ],
    "accidentes": [
        "choque", "colision", "accidente", "impacto", "siniestro", "atropello", "airbag", "herido", "sangre",
    ],
    "motor": [
        "motor", "humo", "sobrecal", "recalent", "radiador", "temperatura", "aceite", "correa", "piston",
    ],
    "cerrajeria": [
        "cerrajeria", "cerradura", "llave", "inmovilizador", "chip", "duplicado", "perdi la llave",
    ],
    "apertura": [
        "apertura", "auto cerrado", "bloqueado", "no abre", "llaves adentro", "abrir puerta",
    ],
}


# Palabras clave de etiquetas de imagen por servicio (labels de vision suelen venir en ingles).
SERVICE_IMAGE_KEYWORDS: dict[str, list[str]] = {
    "bateria": ["battery", "car battery", "battery terminal", "jumper cable"],
    "auxilio_electrico": ["fuse", "dashboard", "wiring", "instrument panel", "headlight"],
    "llanta": ["wheel", "car wheel", "tire", "tyre", "rim", "flat tire", "alloy wheel"],
    "vulcanizado": ["puncture", "flat tire", "tire repair", "patch"],
    "carroceria": ["bumper", "windshield", "dent", "scratched car", "damaged door"],
    "grua": ["tow truck", "truck", "vehicle transport", "roadside assistance"],
    "accidentes": ["car crash", "collision", "accident", "damaged car", "broken glass"],
    "motor": ["engine", "engine bay", "smoke", "radiator", "hood"],
    "cerrajeria": ["car key", "key", "key fob", "door lock"],
    "apertura": ["car door", "locked car", "door handle", "lock"],
    "mecanica_general": ["car", "automobile", "vehicle", "maintenance"],
}


SERVICE_RANKING = [
    "accidentes",
    "motor",
    "llanta",
    "bateria",
    "cerrajeria",
    "apertura",
    "carroceria",
    "grua",
    "auxilio_electrico",
    "vulcanizado",
    "mecanica_general",
]

# Volver texto con caracteres especial a normales 
def _normalize_text(value: str | None) -> str:
    if not value:
        return ""
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return ascii_value.lower()

# Revisa si hay palabras claves en el texto 
def _has_any(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _extract_image_labels(image_summary: str | None) -> str:
    # Convierte "wheel:0.92, car:0.66" -> "wheel car" para matching por etiquetas.
    if not image_summary:
        return ""

    parts: list[str] = []
    for segment in image_summary.split(","):
        label = segment.split(":")[0].strip()
        if label:
            parts.append(label)
    return " ".join(parts)


def _is_enabled(value: str | None) -> bool:
    # Interpreta banderas de entorno en formato flexible (true/1/yes/si/on).
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "si", "on"}

# Valida el audio y imagen para que no se lentee, de manera local o en internet
def _download_binary(url: str, *, max_bytes: int, timeout_seconds: int) -> bytes | None:
    # Descarga contenido remoto con limite de tamanio para proteger el backend.
    local_path = resolve_local_evidence_path_from_url(url)
    if local_path and local_path.exists() and local_path.is_file():
        try:
            content = local_path.read_bytes()
            if len(content) > max_bytes:
                return None
            return content
        except OSError:
            return None

    try:
        with httpx.Client(follow_redirects=True, timeout=timeout_seconds) as client:
            response = client.get(url)
            response.raise_for_status()
            content = response.content
            if len(content) > max_bytes:
                return None
            return content
    except Exception:
        return None


@lru_cache(maxsize=1)
def _get_vosk_model(model_path: str):
    # Lazy-load de Vosk para transcripcion 
    from vosk import Model

    return Model(model_path)


def _transcribe_audio_with_vosk(*, audio_url: str, audio_bytes: bytes) -> str | None:
    # Transcribe audio con Vosk 
    model_path = (os.getenv("AI_VOSK_MODEL_PATH") or "").strip()
    if not model_path:
        logger.info("[IA] AI_VOSK_MODEL_PATH no configurado; transcripcion Vosk omitida.")
        return None

    sample_rate_raw = os.getenv("AI_VOSK_SAMPLE_RATE", "16000")
    try:
        sample_rate = int(sample_rate_raw)
    except ValueError:
        sample_rate = 16000

    ffmpeg_binary = os.getenv("AI_VOSK_FFMPEG_PATH", "ffmpeg")

    try:
        suffix = Path(audio_url).suffix or ".audio"
        with NamedTemporaryFile(delete=False, suffix=suffix) as src_file:
            src_file.write(audio_bytes)
            src_path = src_file.name

        with NamedTemporaryFile(delete=False, suffix=".wav") as wav_file:
            wav_path = wav_file.name

        try:
            command = [
                ffmpeg_binary,
                "-y",
                "-i",
                src_path,
                "-ac",
                "1",
                "-ar",
                str(sample_rate),
                "-f",
                "wav",
                wav_path,
            ]
            proc = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
            )
            if proc.returncode != 0:
                logger.warning("[IA] ffmpeg fallo al preparar audio para Vosk: %s", proc.stderr.strip())
                return None

            from vosk import KaldiRecognizer

            model = _get_vosk_model(model_path)
            recognizer = KaldiRecognizer(model, sample_rate)

            chunks: list[str] = []
            with wave.open(wav_path, "rb") as wav_stream:
                while True:
                    data = wav_stream.readframes(4000)
                    if not data:
                        break

                    if recognizer.AcceptWaveform(data):
                        result = json.loads(recognizer.Result())
                        text = str(result.get("text") or "").strip()
                        if text:
                            chunks.append(text)

                final_result = json.loads(recognizer.FinalResult())
                final_text = str(final_result.get("text") or "").strip()
                if final_text:
                    chunks.append(final_text)

            joined = " ".join(chunk for chunk in chunks if chunk).strip()
            return joined if joined else None
        finally:
            if os.path.exists(src_path):
                os.unlink(src_path)
            if os.path.exists(wav_path):
                os.unlink(wav_path)
    except Exception as exc:
        logger.warning("[IA] No se pudo transcribir audio con Vosk: %s", exc)
        return None

# funcion q transcribe, pero este es como el "header"
def _transcribe_audio(audio_url: str | None) -> str | None:
    # Transcribe audio usando un unico proveedor soportado: Vosk.
    transcription_enabled_flag = os.getenv(
        "AI_ENABLE_AUDIO_TRANSCRIPTION",
        "true",
    )
    if not audio_url:
        return None
    if transcription_enabled_flag is not None and not _is_enabled(transcription_enabled_flag):
        logger.info("[IA] Transcripcion deshabilitada por AI_ENABLE_AUDIO_TRANSCRIPTION.")
        return None

    try:
        audio_bytes = _download_binary(
            audio_url,
            max_bytes=25 * 1024 * 1024,
            timeout_seconds=30,
        )
        if not audio_bytes:
            return None

        # Se conserva la variable para no romper entorno existente,
        # pero el modulo solo soporta Vosk.
        provider = (os.getenv("AI_TRANSCRIPTION_PROVIDER") or "vosk").strip().lower()
        if provider != "vosk":
            logger.warning(
                "[IA] AI_TRANSCRIPTION_PROVIDER=%s no soportado en este modulo. Se usara Vosk.",
                provider,
            )

        return _transcribe_audio_with_vosk(audio_url=audio_url, audio_bytes=audio_bytes)
    except Exception as exc:
        logger.warning("[IA] No se pudo transcribir audio: %s", exc)
        return None


def _analyze_image_with_hf(image_url: str | None) -> str | None:
    # Consulta modelo de clasificacion de imagen en Hugging Face Inference API.
    if not image_url or not _is_enabled(os.getenv("AI_ENABLE_HF_IMAGE")):
        return None

    token = os.getenv("AI_HF_TOKEN")
    if not token:
        logger.info("[IA] AI_HF_TOKEN no configurado; analisis de imagen omitido.")
        return None

    image_bytes = _download_binary(
        image_url,
        max_bytes=15 * 1024 * 1024,
        timeout_seconds=30,
    )
    if not image_bytes:
        return None

    model = os.getenv("AI_HF_IMAGE_MODEL", "microsoft/resnet-50")
    fallback_model = os.getenv("AI_HF_IMAGE_MODEL_FALLBACK", "google/vit-base-patch16-224")

    retries_raw = os.getenv("AI_HF_MAX_RETRIES", "2")
    backoff_raw = os.getenv("AI_HF_RETRY_BACKOFF_SECONDS", "2")
    try:
        max_retries = max(0, int(retries_raw))
    except ValueError:
        max_retries = 2
    try:
        backoff_seconds = float(backoff_raw)
    except ValueError:
        backoff_seconds = 2.0

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/octet-stream",
    }

    endpoint_templates = [
        "https://api-inference.huggingface.co/models/{model}",
        "https://router.huggingface.co/hf-inference/models/{model}",
    ]

    candidate_models: list[str] = []
    for candidate in [model, fallback_model]:
        cleaned = (candidate or "").strip()
        if cleaned and cleaned not in candidate_models:
            candidate_models.append(cleaned)

    for candidate_model in candidate_models:
        for endpoint_template in endpoint_templates:
            endpoint = endpoint_template.format(model=candidate_model)
            attempt = 0
            while attempt <= max_retries:
                attempt += 1
                try:
                    with httpx.Client(timeout=45) as client:
                        response = client.post(endpoint, headers=headers, content=image_bytes)
                        response.raise_for_status()

                    payload = response.json()
                    if not isinstance(payload, list):
                        return None

                    labels: list[tuple[str, float]] = []
                    for item in payload:
                        if not isinstance(item, dict):
                            continue

                        label = item.get("label")
                        score = item.get("score")
                        if isinstance(label, str) and isinstance(score, (float, int)):
                            labels.append((label.strip().lower(), float(score)))

                    if not labels:
                        return None

                    labels.sort(key=lambda row: row[1], reverse=True)
                    top_labels = labels[:3]
                    return ", ".join(f"{label}:{score:.2f}" for label, score in top_labels)
                except httpx.HTTPStatusError as exc:
                    status_code = exc.response.status_code
                    if status_code == 429 and attempt <= max_retries:
                        wait_seconds = backoff_seconds * attempt
                        logger.warning(
                            "[IA] Hugging Face con limite (429). Reintento %s/%s en %.1fs.",
                            attempt,
                            max_retries,
                            wait_seconds,
                        )
                        time.sleep(wait_seconds)
                        continue

                    if status_code == 404:
                        logger.warning(
                            "[IA] Modelo/endpoint HF no encontrado (%s). Probando fallback...",
                            endpoint,
                        )
                        break

                    logger.warning("[IA] Hugging Face devolvio estado %s para %s.", status_code, endpoint)
                    return None
                except Exception as exc:
                    logger.warning("[IA] No se pudo analizar imagen con Hugging Face: %s", exc)
                    return None

    return None


# IMPORTANTE, FUNCION PRINCIPAL DE DECISION

def _infer_problem_type(*sources: str | None) -> str | None:
    # Clasificador heuristico multimodal con deduccion por catalogo de servicios.
    user_text = sources[0] if len(sources) > 0 else None
    audio_text = sources[1] if len(sources) > 1 else None
    image_summary = sources[2] if len(sources) > 2 else None

    text_blob = _normalize_text(" ".join(part for part in [user_text, audio_text] if part))
    image_blob = _normalize_text(_extract_image_labels(image_summary))
    merged_blob = f"{text_blob} {image_blob}".strip()
    if not merged_blob:
        return None

    service_scores = {service: 0 for service in SERVICE_TO_PROBLEM}

    # Peso mayor para audio/texto; imagen apoya la decision.
    for service, keywords in SERVICE_TEXT_KEYWORDS.items():
        if _has_any(text_blob, keywords):
            service_scores[service] += 3

    for service, keywords in SERVICE_IMAGE_KEYWORDS.items():
        if _has_any(image_blob, keywords):
            service_scores[service] += 2

    # Reglas combinadas especificas (audio+imagen o texto+imagen).
    wheel_signal = _has_any(merged_blob, ["wheel", "tire", "tyre", "rueda", "llanta", "neumatic"])
    puncture_signal = _has_any(merged_blob, ["pinch", "ponch", "pinchado", "ponchado", "revent", "desinflad", "flat"])
    if wheel_signal and puncture_signal:
        service_scores["llanta"] += 5
        service_scores["vulcanizado"] += 4

    if _has_any(text_blob, ["no arranca", "no enciende", "sin bateria", "sin corriente", "descargada"]) and not _has_any(
        text_blob,
        ["humo", "sobrecal", "accidente", "choque"],
    ):
        service_scores["bateria"] += 3
        service_scores["auxilio_electrico"] += 2

    if _has_any(text_blob, ["llave", "cerradura", "cerrado", "bloqueado", "inmovilizador"]) and _has_any(
        text_blob,
        ["perdi", "adentro", "no abre", "atascad", "abrir"],
    ):
        service_scores["cerrajeria"] += 4
        service_scores["apertura"] += 3

    if _has_any(text_blob, ["choque", "colision", "accidente", "impacto", "airbag"]):
        service_scores["accidentes"] += 4
        service_scores["carroceria"] += 3

    if _has_any(text_blob, ["remolque", "grua", "arrastre", "tow", "towing", "plataforma"]):
        service_scores["grua"] += 4

    if _has_any(text_blob, ["humo", "sobrecal", "temperatura alta", "radiador", "motor"]):
        service_scores["motor"] += 4

    # Fallback suave a mecanica_general cuando hay evidencia vaga.
    if _has_any(text_blob, ["falla", "averia", "mecanico", "revision"]) and max(service_scores.values()) == 0:
        service_scores["mecanica_general"] += 2

    best_service = ""
    best_score = 0
    for service in SERVICE_RANKING:
        score = service_scores.get(service, 0)
        if score > best_score:
            best_service = service
            best_score = score

    if not best_service or best_score <= 0:
        return "otros"

    return SERVICE_TO_PROBLEM.get(best_service, "otros")


def _infer_priority(problem_type: str, *sources: str | None) -> int:
    # Priorizacion estatica: 1=baja, 2=media, 3=alta.
    base_by_problem = {
        "llave": 1,
        "bateria": 2,
        "llanta": 2,
        "otros": 2,
        "motor": 3,
        "choque": 3,
    }
    priority = base_by_problem.get(problem_type, 2)

    merged = " ".join(source for source in sources if source).lower()
    high_risk_keywords = ["humo", "fuego", "accidente", "sangre", "herido", "volco"]
    if any(keyword in merged for keyword in high_risk_keywords):
        priority = 3

    return max(1, min(priority, 3))


def _is_information_sufficient(
    *,
    deduced_problem: bool,
    problem_type: str,
    audio_url: str | None,
    image_url: str | None,
    user_text: str | None,
    audio_transcription: str | None,
    image_summary: str | None,
) -> tuple[bool, str | None]:
    # Define si hay datos minimos para continuar a etapa de busqueda de talleres.
    has_transcribed_audio = bool(audio_transcription and len(audio_transcription) >= 8)
    has_user_text = bool(user_text and len(user_text) >= 10)
    image_analysis_enabled = _is_enabled(os.getenv("AI_ENABLE_HF_IMAGE"))
    has_image_signal = bool(image_url and (image_summary or not image_analysis_enabled))
    has_three_modalities = bool(
        audio_url
        and image_url
        and (has_user_text or has_transcribed_audio)
    )

    if not deduced_problem:
        if has_three_modalities:
            return (
                True,
                "No se pudo deducir el tipo exacto del problema incluso con evidencia completa (audio, imagen y texto). El incidente continuara con clasificacion general.",
            )
        return (
            False,
            "No se pudo deducir el tipo de problema. Envia evidencia mas clara (audio, imagen y descripcion) para continuar.",
        )

    if image_url and image_analysis_enabled and not image_summary:
        return (
            False,
            "No se pudo analizar la imagen. Reenvia una foto mas clara o agrega mas detalle por texto.",
        )

    if problem_type == "otros" and not has_user_text and not has_transcribed_audio:
        contexto_fuente = "imagen" if image_url else "información"
        return (
            False,
            f"No logramos interpretar un problema vehicular claro a partir de la {contexto_fuente} proporcionada. Por favor, sé más específico o agrega texto.",
        )

    if not has_transcribed_audio and not has_user_text and not has_image_signal:
        return (
            False,
            "No hay descripcion textual, audio comprensible ni imagen útil. Provea evidencia clara.",
        )

    if audio_url and not has_transcribed_audio and not has_user_text and not has_image_signal:
        return (
            False,
            "El audio no fue comprensible. Reenvia audio o agrega descripcion por texto.",
        )

    return (True, None)


def _build_summary(
    *,
    problem_type: str,
    problem_deduced: bool,
    priority: int,
    audio_transcription: str | None,
    user_text: str | None,
    image_summary: str | None,
) -> str:
    # Resumen estructurado en codigo sin depender de un LLM externo.
    lines: list[str] = [
        f"tipo={problem_type}",
        f"tipo_deducido={problem_deduced}",
        f"prioridad={priority}",
    ]

    if audio_transcription:
        lines.append(f"audio={audio_transcription[:220]}")
    if user_text:
        lines.append(f"texto={user_text[:220]}")
    if image_summary:
        lines.append(f"imagen={image_summary[:220]}")

    return " | ".join(lines)


def _compose_extracted_text(
    *,
    audio_url: str | None,
    user_text: str | None,
    audio_transcription: str | None,
    image_summary: str | None,
) -> str | None:
    # Para evidencia de texto priorizamos contenido legible para UI y auditoria.
    if user_text and user_text.strip():
        return user_text.strip()

    if audio_transcription and audio_transcription.strip():
        return f"Transcripcion audio: {audio_transcription.strip()}"

    if image_summary and image_summary.strip():
        return f"Analisis imagen: {image_summary.strip()}"

    if audio_url and audio_url.strip():
        return f"Referencia de audio: {audio_url.strip()}"

    return None


def process_incident_payload_for_ai(
    *,
    image_url: str | None,
    audio_url: str | None,
    user_text: str | None,
) -> AIIncidentProcessingResult:
    # Orquesta el pipeline IA sin bloquear el alta del incidente en caso de fallas.
    # Flujo: transcripcion (Vosk) -> analisis de imagen (HF) -> inferencias heuristicas.
    audio_transcription = _transcribe_audio(audio_url)
    image_summary = _analyze_image_with_hf(image_url)
    logger.info("[IA] Audio transcripcion: %s", audio_transcription)
    logger.info("[IA] Imagen resumen: %s", image_summary)

    inferred_problem = _infer_problem_type(user_text, audio_transcription, image_summary)
    if inferred_problem is None and user_text:
        inferred_problem = _infer_problem_type(user_text)

    problem_deduced = inferred_problem is not None
    tipo_problema = inferred_problem or "otros"
    logger.info("[IA] Tipo deducido: %s | tipo_problema=%s", problem_deduced, tipo_problema)

    prioridad = _infer_priority(
        tipo_problema,
        audio_transcription,
        user_text,
        image_summary,
    )

    informacion_suficiente, solicitud_mas_informacion = _is_information_sufficient(
        deduced_problem=problem_deduced,
        problem_type=tipo_problema,
        audio_url=audio_url,
        image_url=image_url,
        user_text=user_text,
        audio_transcription=audio_transcription,
        image_summary=image_summary,
    )

    resumen_incidente = _build_summary(
        problem_type=tipo_problema,
        problem_deduced=problem_deduced,
        priority=prioridad,
        audio_transcription=audio_transcription,
        user_text=user_text,
        image_summary=image_summary,
    )

    # Generamos texto combinado para persistir contexto base en evidencia.
    texto_extraido = _compose_extracted_text(
        audio_url=audio_url,
        user_text=user_text,
        audio_transcription=audio_transcription,
        image_summary=image_summary,
    )

    if audio_transcription or image_summary:
        processing_state = "procesado_ia"
    elif audio_url or image_url:
        processing_state = "evidencia_recibida_sin_extraccion"
    else:
        processing_state = "solo_texto_usuario"

    if not informacion_suficiente:
        processing_state = "requiere_mas_informacion"

    return AIIncidentProcessingResult(
        tipo_problema=tipo_problema,
        prioridad=prioridad,
        informacion_suficiente=informacion_suficiente,
        resumen_incidente=resumen_incidente,
        solicitud_mas_informacion=solicitud_mas_informacion,
        texto_extraido=texto_extraido,
        estado_procesamiento=processing_state,
        audio_transcripcion=audio_transcription,
        image_summary=image_summary,
        problem_deduced=problem_deduced,
    )
