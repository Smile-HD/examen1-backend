from __future__ import annotations

import mimetypes
import os
from pathlib import Path
from urllib.parse import urlparse

PAYMENT_ROUTE_PREFIX = "/api/v1/payments"
PAYMENT_PROOF_ROUTE_PREFIX = "/api/v1/payments/proofs/"
PAYMENT_QR_ROUTE_PREFIX = "/api/v1/payments/qr/"
COMMISSION_ROUTE_PREFIX = "/api/v1/commissions"
COMMISSION_PROOF_ROUTE_PREFIX = "/api/v1/commissions/proofs/"
PLATFORM_QR_ROUTE_PREFIX = "/api/v1/commissions/platform-qr/"

ALLOWED_PROOF_EXTENSIONS: set[str] = {".jpg", ".jpeg", ".png", ".webp"}


def resolve_payments_base_directory() -> Path:
    custom_dir = os.getenv("PAYMENT_STORAGE_DIR")
    if custom_dir:
        base_dir = Path(custom_dir)
    else:
        backend_root = Path(__file__).resolve().parents[2]
        base_dir = backend_root / "uploads" / "payments"

    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir


def resolve_payment_proofs_directory() -> Path:
    proofs_dir = resolve_payments_base_directory() / "proofs"
    proofs_dir.mkdir(parents=True, exist_ok=True)
    return proofs_dir


def resolve_payment_qr_directory() -> Path:
    qr_dir = resolve_payments_base_directory() / "qr"
    qr_dir.mkdir(parents=True, exist_ok=True)
    return qr_dir


def safe_proof_file_extension(filename: str | None, content_type: str | None) -> str:
    extension = Path(filename or "").suffix.lower()
    if extension == ".jpe":
        extension = ".jpg"

    if not extension and content_type:
        guessed_extension = mimetypes.guess_extension(content_type.split(";")[0].strip())
        if guessed_extension:
            extension = guessed_extension.lower()

    if extension not in ALLOWED_PROOF_EXTENSIONS:
        return ".jpg"
    return extension


def build_payment_proof_urls(base_url: str, file_name: str) -> tuple[str, str]:
    relative_url = f"{PAYMENT_PROOF_ROUTE_PREFIX}{file_name}"
    absolute_url = f"{base_url.rstrip('/')}{relative_url}"
    return relative_url, absolute_url


def build_payment_qr_urls(base_url: str, file_name: str) -> tuple[str, str]:
    relative_url = f"{PAYMENT_QR_ROUTE_PREFIX}{file_name}"
    absolute_url = f"{base_url.rstrip('/')}{relative_url}"
    return relative_url, absolute_url


def resolve_absolute_url(base_url: str, raw_url: str) -> str:
    parsed = urlparse(raw_url)
    if parsed.scheme and parsed.netloc:
        return raw_url
    if raw_url.startswith("/"):
        return f"{base_url.rstrip('/')}{raw_url}"
    return f"{base_url.rstrip('/')}/{raw_url}"


def save_payment_proof_image(content: bytes, file_name: str) -> Path:
    target_path = resolve_payment_proofs_directory() / file_name
    with target_path.open("wb") as output_file:
        output_file.write(content)
    return target_path


def resolve_commissions_base_directory() -> Path:
    custom_dir = os.getenv("COMMISSION_STORAGE_DIR")
    if custom_dir:
        base_dir = Path(custom_dir)
    else:
        backend_root = Path(__file__).resolve().parents[2]
        base_dir = backend_root / "uploads" / "commissions"

    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir


def resolve_commission_proofs_directory() -> Path:
    proofs_dir = resolve_commissions_base_directory() / "proofs"
    proofs_dir.mkdir(parents=True, exist_ok=True)
    return proofs_dir


def resolve_platform_qr_directory() -> Path:
    qr_dir = resolve_commissions_base_directory() / "platform_qr"
    qr_dir.mkdir(parents=True, exist_ok=True)
    return qr_dir


def build_commission_proof_urls(base_url: str, file_name: str) -> tuple[str, str]:
    relative_url = f"{COMMISSION_PROOF_ROUTE_PREFIX}{file_name}"
    absolute_url = f"{base_url.rstrip('/')}{relative_url}"
    return relative_url, absolute_url


def build_platform_qr_urls(base_url: str, file_name: str) -> tuple[str, str]:
    relative_url = f"{PLATFORM_QR_ROUTE_PREFIX}{file_name}"
    absolute_url = f"{base_url.rstrip('/')}{relative_url}"
    return relative_url, absolute_url


def save_commission_proof_image(content: bytes, file_name: str) -> Path:
    target_path = resolve_commission_proofs_directory() / file_name
    with target_path.open("wb") as output_file:
        output_file.write(content)
    return target_path


def save_platform_qr_image(content: bytes, file_name: str) -> Path:
    target_path = resolve_platform_qr_directory() / file_name
    with target_path.open("wb") as output_file:
        output_file.write(content)
    return target_path

