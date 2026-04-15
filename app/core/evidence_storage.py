from __future__ import annotations

import mimetypes
import os
from pathlib import Path
from urllib.parse import urlparse

EVIDENCE_ROUTE_PREFIX = "/api/v1/incidentes/evidencias/"

ALLOWED_EXTENSIONS_BY_KIND: dict[str, set[str]] = {
    "imagen": {".jpg", ".jpeg", ".png", ".webp"},
    "audio": {".mp3", ".m4a", ".wav", ".aac", ".ogg", ".webm"},
}


def resolve_evidence_directory() -> Path:
    custom_dir = os.getenv("EVIDENCE_STORAGE_DIR")
    if custom_dir:
        base_dir = Path(custom_dir)
    else:
        backend_root = Path(__file__).resolve().parents[2]
        base_dir = backend_root / "uploads" / "evidencias"

    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir


def allowed_extensions_for_kind(kind: str) -> set[str]:
    normalized_kind = kind.strip().lower()
    allowed = ALLOWED_EXTENSIONS_BY_KIND.get(normalized_kind)
    if not allowed:
        raise ValueError("Tipo de evidencia invalido. Usa 'imagen' o 'audio'.")
    return allowed


def safe_file_extension(filename: str | None, content_type: str | None, kind: str) -> str:
    extension = Path(filename or "").suffix.lower()
    if extension == ".jpe":
        extension = ".jpg"

    if not extension and content_type:
        guessed_extension = mimetypes.guess_extension(content_type.split(";")[0].strip())
        if guessed_extension:
            extension = guessed_extension.lower()

    allowed = allowed_extensions_for_kind(kind)
    if extension not in allowed:
        return ".jpg" if kind == "imagen" else ".mp3"

    return extension


def build_evidence_urls(base_url: str, file_name: str) -> tuple[str, str]:
    relative_url = f"{EVIDENCE_ROUTE_PREFIX}{file_name}"
    absolute_url = f"{base_url.rstrip('/')}{relative_url}"
    return relative_url, absolute_url


def resolve_local_evidence_path_from_url(url: str | None) -> Path | None:
    if not url:
        return None

    parsed = urlparse(url)
    path = parsed.path or ""
    if not path.startswith(EVIDENCE_ROUTE_PREFIX):
        return None

    file_name = Path(path).name
    if not file_name:
        return None

    return resolve_evidence_directory() / file_name
