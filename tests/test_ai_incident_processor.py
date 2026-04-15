from app.services import ai_incident_processor
import pytest


def test_classifies_llanta_from_wheel_plus_pinchado(monkeypatch) -> None:
    # Imagen: wheel, Audio: pinchado => debe deducir llanta por regla estatica multimodal.
    monkeypatch.setattr(
        ai_incident_processor,
        "_transcribe_audio_with_whisper",
        lambda _audio_url: "Se escucha que esta pinchado el neumatico delantero",
    )
    monkeypatch.setattr(
        ai_incident_processor,
        "_analyze_image_with_hf",
        lambda _image_url: "wheel:0.98, car:0.80",
    )

    result = ai_incident_processor.process_incident_payload_for_ai(
        image_url="http://cdn.local/incidente.jpg",
        audio_url="http://cdn.local/incidente.m4a",
        user_text=None,
    )

    assert result.tipo_problema == "llanta"
    assert result.prioridad == 2
    assert result.informacion_suficiente is True


def test_classifies_bateria_from_start_issue_text_only() -> None:
    result = ai_incident_processor.process_incident_payload_for_ai(
        image_url=None,
        audio_url=None,
        user_text="El auto no arranca y parece sin bateria",
    )

    assert result.tipo_problema == "bateria"
    assert result.prioridad == 2


@pytest.mark.parametrize(
    "text_input, expected_type",
    [
        ("La rueda trasera esta ponchada y necesito cambio de llanta", "llanta"),
        ("Tuve un choque fuerte y el parachoque quedo destruido", "choque"),
        ("El motor echa humo y se recalienta en subida", "motor"),
        ("Perdi la llave y el auto esta bloqueado, no abre", "llave"),
        ("Necesito remolque con grua, el auto quedo varado", "choque"),
        ("Hay una falla electrica y el tablero no enciende", "bateria"),
    ],
)
def test_classifies_service_like_synonyms(text_input: str, expected_type: str) -> None:
    result = ai_incident_processor.process_incident_payload_for_ai(
        image_url=None,
        audio_url=None,
        user_text=text_input,
    )

    assert result.tipo_problema == expected_type


def test_classifies_llave_from_key_image_plus_locked_audio(monkeypatch) -> None:
    # Debe deducir tipo llave usando imagen (key) y audio/texto de bloqueo.
    monkeypatch.setattr(
        ai_incident_processor,
        "_transcribe_audio_with_whisper",
        lambda _audio_url: "El auto esta bloqueado y perdi la llave",
    )
    monkeypatch.setattr(
        ai_incident_processor,
        "_analyze_image_with_hf",
        lambda _image_url: "car key:0.95, car door:0.71",
    )

    result = ai_incident_processor.process_incident_payload_for_ai(
        image_url="http://cdn.local/key.jpg",
        audio_url="http://cdn.local/key.m4a",
        user_text=None,
    )

    assert result.tipo_problema == "llave"
