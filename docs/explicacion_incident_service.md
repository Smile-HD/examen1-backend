# Explicación de `incident_service.py`

Este archivo es el **núcleo de la lógica de negocio** para la gestión de incidentes vehiculares. Maneja desde que un cliente reporta una emergencia hasta que el taller finaliza el servicio.

Dado que el archivo tiene casi 2000 líneas, explicar literalmente línea por línea sería ilegible. En su lugar, aquí tienes una **explicación bloque por bloque y función por función** para que entiendas exactamente qué hace cada parte de manera sencilla.

---

## 1. Importaciones e Inicialización (Líneas 1-50 aprox)
Se importan las bibliotecas necesarias:
- `datetime`: Para manejar fechas y horas.
- `IntegrityError` y `Session` de SQLAlchemy: Para manejar la base de datos y errores de guardado.
- Modelos (`Incidente`, esquemas) y Repositorios (`IncidentRepository`).
- Servicios externos de IA (`process_incident_payload_for_ai`) y Notificaciones (`send_client_push_best_effort`).

## 2. Excepciones Personalizadas (Errores de Dominio)
Son clases que heredan de `Exception`. Sirven para identificar errores específicos del negocio y poder devolver mensajes claros al usuario en lugar de un error genérico del servidor.
- `VehicleNotOwnedError`: El vehículo no es del cliente.
- `LocationRequiredError`: Falta la ubicación.
- `IncidentNeedsMoreEvidenceError`: La IA determinó que falta información (foto, audio) para mandar a los talleres.
- `InvalidWorkshopSelectionError`, `WorkshopResourcesUnavailableError`: Errores relacionados con la elección de talleres y disponibilidad de grúas/técnicos.

## 3. Constantes Generales
- `PROBLEM_SERVICE_MAP`: Un diccionario que mapea el problema detectado (ej. "llanta") con los servicios que debe ofrecer un taller (ej. "vulcanizado").
- `MAX_INFO_RETRIES`: Límite de veces (3) que se le puede pedir más información al cliente. Si se pasa, el incidente sigue con la info que haya.

---

## 4. Funciones Privadas (Helpers)
Estas funciones empiezan con guion bajo (`_`). Son "ayudantes" que hacen tareas repetitivas para que las funciones principales estén más limpias.

- **`_apply_information_policy`**: Revisa si la IA dijo que la información enviada es suficiente o si se alcanzó el límite de reintentos (`MAX_INFO_RETRIES`).
- **`_merge_location`**: Junta la dirección de texto y la referencia en un solo campo de texto para facilitar su lectura.
- **`_persist_incident_evidence`**: Guarda en la base de datos las fotos, audios, transcripciones de audio y resúmenes que generó la IA.
- **`_build_incident_report_response`, `_build_metric_payload`, `_build_...`**: Son varias funciones que se dedican únicamente a "armar" el formato de respuesta (los objetos JSON) que se enviarán al frontend o móvil.
- **`_get_live_technician_location`**: Busca la ubicación GPS en tiempo real del técnico (mezclando datos de la memoria caché y la base de datos).
- **`_calculate_distance_km`**: Usa la fórmula matemática "Haversine" para calcular la distancia en kilómetros entre el cliente y un taller usando sus coordenadas (latitud/longitud).
- **`_score_workshop_candidate` y `_build_incident_candidates`**: Se encargan de **evaluar y calificar** a todos los talleres. Si el incidente es grave, le dan más peso a la cercanía y la capacidad. Luego devuelven una lista de los mejores talleres ordenados.

---

## 5. Funciones Principales (Flujos de Negocio / Casos de Uso)

Estas son las funciones que son llamadas directamente desde los *routers* (endpoints de la API).

### `report_incident`
Es la puerta de entrada. 
1. Valida que haya ubicación y que el vehículo sea del cliente.
2. Llama a la **Inteligencia Artificial** para procesar el texto/foto/audio y deducir cuál es el problema.
3. Evalúa si la información es suficiente.
4. Crea el incidente en la Base de Datos (`repository.create_incident`).
5. Guarda la evidencia (fotos, audios) y el historial ("Incidente reportado").
6. Devuelve el estado (si requiere más info o si pasa a pendiente).

### `resubmit_incident_evidence`
Si en el paso anterior faltaba información, el cliente manda más fotos o audios. Esta función repite el análisis de la IA sumando la nueva evidencia y actualiza el incidente.

### `list_workshop_candidates`
Verifica que el incidente esté listo y llama a la calculadora de candidatos (`_build_incident_candidates`) para devolverle al cliente móvil una lista de talleres recomendados cerca suyo.

### `select_workshops_for_incident`
El cliente marca qué talleres de la lista quiere que lo atiendan. Esta función:
1. Valida que los talleres elegidos sean válidos.
2. Crea una "solicitud" individual para cada taller y les notifica.

### `list_client_requests` y `list_workshop_incoming_requests`
Listan las solicitudes pendientes. Una es para que el cliente vea el estado de su petición y la otra es la "bandeja de entrada" de los talleres.

### `decide_workshop_request`
Es cuando un taller hace clic en **"Aceptar"** o **"Rechazar"**:
1. Si rechaza, solo se marca como rechazada.
2. Si acepta:
   - Verifica si no le ganaron "de mano" (si otro taller aceptó primero, le anula la solicitud diciendo "otro taller aceptó").
   - Busca si el taller tiene un técnico y una grúa disponibles.
   - Asigna al técnico y la grúa y los pone "en ruta" u ocupados.
   - Envía notificación Push al cliente.

### `get_incident_detail_for_client` / `get_incident_detail_for_workshop`
Traen toda la información aglomerada de un incidente (evidencias, métricas, historial, posición en tiempo real del técnico) para pintarla en las pantallas de detalle de la app/web.

### `finalize_workshop_service`
Se llama cuando el mecánico termina el trabajo.
1. Libera al técnico y al transporte (los vuelve a poner disponibles).
2. Calcula y guarda los costos totales (comisiones del 10%, tiempos en minutos, etc.).
3. Da por cerrado el incidente en el historial.

---

## Resumen del Flujo
El archivo está diseñado con una arquitectura clara: `Validación -> Lógica de IA -> Reglas de Negocio -> Base de Datos -> Notificación`. Todo lo que se repite o arma objetos visuales se manda a funciones `_privadas` arriba, dejando las funciones de abajo solo para dictar el "paso a paso" de la vida del incidente.