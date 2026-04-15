# Integracion IA CU5 (Transcripcion + Hugging Face)

Este backend ya incluye integracion opcional en `app/services/ai_incident_processor.py`.

## Flujo actual

1. `POST /api/v1/incidentes/reportar` recibe `imagen_url`, `audio_url`, `texto_usuario`.
2. `incident_service.report_incident` llama a `process_incident_payload_for_ai`.
3. El procesador IA intenta:
   - Transcribir audio con proveedor configurable (`vosk`, `api` o `local`).
   - Analizar imagen con Hugging Face Inference API (si esta habilitado).
4. El sistema guarda evidencias:
   - `tipo=imagen`: URL + resumen de etiquetas de imagen (si existe).
   - `tipo=audio`: URL + transcripcion de audio (si existe).
   - `tipo=texto`: consolidado multimodal para trazabilidad.
   - `tipo=resumen`: resumen estructurado del incidente.

## Regla de suficiencia (nuevo)

Antes de enviar a talleres, el backend decide si la informacion es suficiente:

- Si es suficiente: estado `pendiente`.
- Si no es suficiente: estado `requiere_info` y se devuelve mensaje para reenviar evidencia.

La prioridad se calcula con reglas estaticas en backend (`1=baja`, `2=media`, `3=alta`) segun tipo de problema y palabras de riesgo.

### Politica de reintentos

- El backend contabiliza intentos insuficientes en `info_reintentos`.
- Si llega a 3 intentos insuficientes, el incidente continua de todas formas con informacion parcial.
- En ese caso, el estado pasa a `pendiente` para habilitar fase de candidatos.

## Endpoints nuevos (flujo completo)

- `POST /api/v1/incidentes/reportar`
   - Registra incidente inicial y ejecuta procesamiento IA.
- `POST /api/v1/incidentes/{incidente_id}/reenviar-evidencia`
   - Reprocesa incidente cuando quedo en `requiere_info`.
- `GET /api/v1/incidentes/{incidente_id}/candidatos`
   - Devuelve lista de talleres candidatos ordenada por score.
- `POST /api/v1/incidentes/{incidente_id}/seleccionar-talleres`
   - Crea solicitudes solo para talleres marcados por el cliente.
- `GET /api/v1/incidentes/mis-solicitudes`
   - Cliente ve solicitudes enviadas y su estado.
- `GET /api/v1/incidentes/taller/solicitudes`
   - Taller ve bandeja con toda la informacion del incidente:
     ubicacion, vehiculo, imagenes y transcripciones.
- `POST /api/v1/incidentes/taller/solicitudes/{solicitud_id}/decision`
   - Taller acepta o rechaza.
   - Si acepta, se asigna tecnico y transporte.
   - Solo la primera aceptacion es valida; las demas pasan a `otro_taller_acepto`.
- `GET /api/v1/incidentes/{incidente_id}/detalle`
   - Cliente ve detalle completo: evidencias, historial y asignacion actual.
- `GET /api/v1/incidentes/taller/incidentes/{incidente_id}/detalle`
   - Taller participante ve detalle completo del incidente.
- `POST /api/v1/incidentes/taller/solicitudes/{solicitud_id}/finalizar`
   - Cierra servicio, marca incidente en `atendido` y libera tecnico/transporte a `disponible`.

## Variables de entorno (.env)

- `AI_ENABLE_AUDIO_TRANSCRIPTION=true|false`
- `AI_TRANSCRIPTION_PROVIDER=vosk|api|local`
- `AI_VOSK_MODEL_PATH=./models/vosk-model-small-es-0.42`
- `AI_VOSK_SAMPLE_RATE=16000`
- `AI_VOSK_FFMPEG_PATH=ffmpeg`
- `AI_ENABLE_WHISPER=true|false` (legacy, fallback)
- `AI_WHISPER_PROVIDER=api|local` (legacy, fallback)
- `AI_WHISPER_API_URL=https://api.openai.com/v1/audio/transcriptions`
- `AI_WHISPER_API_MODEL=whisper-1`
- `AI_WHISPER_API_KEY=<tu API key de Whisper/OpenAI>`
- `AI_WHISPER_API_LANGUAGE=es` (opcional)
- `AI_WHISPER_API_TIMEOUT_SECONDS=60` (opcional)
- `AI_WHISPER_API_MAX_RETRIES=2` (opcional, para 429)
- `AI_WHISPER_API_RETRY_BACKOFF_SECONDS=2` (opcional, para 429)
- `AI_WHISPER_MODEL=small|medium|large-v3`
- `AI_WHISPER_COMPUTE_TYPE=int8|float16`
- `AI_WHISPER_DEVICE=cpu|cuda`
- `AI_ENABLE_HF_IMAGE=true|false`
- `AI_HF_IMAGE_MODEL=microsoft/resnet-50` (u otro modelo compatible)
- `AI_HF_IMAGE_MODEL_FALLBACK=google/vit-base-patch16-224` (opcional)
- `AI_HF_MAX_RETRIES=2` (opcional, para 429)
- `AI_HF_RETRY_BACKOFF_SECONDS=2` (opcional, para 429)
- `AI_HF_TOKEN=<tu token de Hugging Face>`

Si `AI_ENABLE_AUDIO_TRANSCRIPTION=false`, no falla el registro del incidente.
Si el proveedor de transcripcion no esta disponible (modelo/lib/binario), tampoco falla el registro.
Si `AI_ENABLE_HF_IMAGE=false` o no hay token, tampoco falla el registro.

## Instalacion opcional para transcripcion local

Si usas `AI_TRANSCRIPTION_PROVIDER=vosk`:

```
pip install vosk
```

Si usas `AI_TRANSCRIPTION_PROVIDER=local`:

Instalar manualmente en tu entorno virtual:

```
pip install faster-whisper
```

Nota: para mejor compatibilidad de formatos de audio, instala `ffmpeg` en el sistema operativo.

## Estados de procesamiento

- `procesado_ia`: hubo salida real de transcripcion o de analisis de imagen.
- `pendiente_modelo_ia`: se envio audio/imagen, pero no hubo salida de IA (deshabilitada, sin token o error).
- `solo_texto_usuario`: solo llego texto sin audio/imagen.
- `requiere_mas_informacion`: el backend detecto evidencia insuficiente para continuar a asignacion.
