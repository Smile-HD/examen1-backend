FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg curl unzip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Descarga del modelo Vosk (espanol) para despliegue Linux en Render.
RUN mkdir -p /app/models \
    && curl -L -o /tmp/vosk-model-small-es-0.42.zip https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip \
    && unzip -q /tmp/vosk-model-small-es-0.42.zip -d /app/models \
    && rm -f /tmp/vosk-model-small-es-0.42.zip

COPY . .

ENV AI_ENABLE_AUDIO_TRANSCRIPTION=true \
    AI_TRANSCRIPTION_PROVIDER=vosk \
    AI_VOSK_MODEL_PATH=/app/models/vosk-model-small-es-0.42 \
    AI_VOSK_SAMPLE_RATE=16000 \
    AI_VOSK_FFMPEG_PATH=ffmpeg

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}"]
