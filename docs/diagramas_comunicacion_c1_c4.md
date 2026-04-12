DIAGRAMAS DE COMUNICACION (C1, C2, C3, C4)

Base usada para construir estos diagramas:
- Flujo real de UI movil en mobile/lib
- Rutas y logica real en backend/app
- Tablas ORM reales en backend/app/models

==================================================
C1. REGISTRAR USUARIO (CLIENTE)
==================================================

Participantes (de izquierda a derecha):
1) Actor iniciador: Cliente
2) Interfaz: RegisterScreen (mobile/lib/register_screen.dart)
3) Backend (logica): register_user (backend/app/services/user_service.py)
4) Tablas vinculadas:
   - usuario
   - rol
   - rol_usuario
   - cliente
   - taller (solo si tipo_usuario=taller)

Comunicacion numerada:
1. Cliente -> RegisterScreen: Completa nombre/correo/password/telefono.
1.1 RegisterScreen: Valida formato de campos localmente.
1.2 RegisterScreen -> API /api/v1/usuarios/registro: Envia payload JSON.
1.3 Router/Controller -> register_user: Deriva al servicio de CU1.
1.4 register_user -> UserRepository.get_user_by_email: Verifica correo existente.
1.5 register_user -> UserRepository.create_user: Inserta usuario base.
1.6 register_user -> UserRepository.get_or_create_role: Obtiene o crea rol.
1.7 register_user -> UserRepository.assign_role_to_user: Inserta rol_usuario.
1.8 register_user -> UserRepository.create_cliente_profile o create_taller_profile: Inserta especializacion.
1.9 register_user: Confirma transaccion.
2.0 API -> RegisterScreen: Retorna registro exitoso (201).
2.1 RegisterScreen -> Cliente: Muestra mensaje de exito.


==================================================
C2. INICIAR SESION
==================================================

Participantes (de izquierda a derecha):
1) Actor iniciador: Cliente movil (y tambien taller/tecnico para canal web)
2) Interfaz: LoginScreen (mobile/lib/login_screen.dart)
3) Backend (logica): authenticate_user (backend/app/services/auth_service.py)
4) Tablas vinculadas:
   - usuario
   - rol
   - rol_usuario
   - cliente
   - taller
   - tecnico

Comunicacion numerada:
1. Actor -> LoginScreen: Ingresa correo y password.
1.1 LoginScreen -> API /api/v1/auth/login: Envia correo/password/canal.
1.2 Router/Controller: Parsea request JSON o form.
1.3 Controller -> authenticate_user: Ejecuta CU2.
1.4 authenticate_user -> UserRepository.get_user_by_email: Busca usuario.
1.5 authenticate_user: Verifica password hash.
1.6 authenticate_user -> UserRepository.get_role_names_by_user_id: Obtiene roles catalogo.
1.7 authenticate_user -> UserRepository.get_specialization_flags: Obtiene perfiles cliente/taller/tecnico.
1.8 authenticate_user: Aplica regla de canal (mobile solo cliente, web taller o tecnico).
1.9 authenticate_user: Emite JWT con roles y canal.
2.0 API -> LoginScreen: Retorna token y datos de sesion (200).
2.1 LoginScreen -> Actor: Muestra mensaje y navega a dashboard.


==================================================
C3. REGISTRAR VEHICULO
==================================================

Participantes (de izquierda a derecha):
1) Actor iniciador: Cliente autenticado
2) Interfaz: VehicleRegistrationScreen (mobile/lib/vehicle_registration_screen.dart)
3) Backend (logica): register_vehicle (backend/app/services/vehicle_service.py)
4) Tablas vinculadas:
   - vehiculo
   - cliente (FK vehiculo.cliente_id)

Comunicacion numerada:
1. Cliente -> VehicleRegistrationScreen: Ingresa placa, marca, modelo, anio y tipo.
1.1 VehicleRegistrationScreen -> API /api/v1/vehiculos/registro: Envia JSON + token Bearer.
1.2 Dependencia auth: Valida JWT y precondicion de cliente mobile.
1.3 Router/Controller -> register_vehicle: Ejecuta CU3.
1.4 register_vehicle -> VehicleRepository.get_by_plate: Verifica unicidad de placa.
1.5 register_vehicle -> VehicleRepository.create: Inserta vehiculo asociado al cliente.
1.6 register_vehicle: Confirma transaccion.
1.7 API -> VehicleRegistrationScreen: Retorna confirmacion (201).
1.8 VehicleRegistrationScreen -> Cliente: Muestra mensaje de exito.


==================================================
C4. REPORTAR EMERGENCIA
==================================================

Participantes (de izquierda a derecha):
1) Actor iniciador: Cliente autenticado
2) Interfaz: IncidentReportScreen (mobile/lib/incident_report_screen.dart)
3) Backend (logica): report_incident (backend/app/services/incident_service.py)
4) Tablas vinculadas:
   - vehiculo (verificacion de pertenencia)
   - estado_servicio
   - incidente
   - evidencia
   - historial

Comunicacion numerada:
1. Cliente -> IncidentReportScreen: Selecciona vehiculo y adjunta datos (ubicacion, imagen, audio, texto).
1.1 IncidentReportScreen -> API /api/v1/vehiculos/mis-vehiculos: Consulta vehiculos del cliente.
1.2 IncidentReportScreen: Obtiene geolocalizacion del dispositivo.
1.3 IncidentReportScreen -> API /api/v1/incidentes/reportar: Envia solicitud + token Bearer.
1.4 Dependencia auth: Valida JWT y rol cliente en canal mobile.
1.5 Router/Controller -> report_incident: Ejecuta CU4.
1.6 report_incident -> IncidentRepository.get_vehicle_for_client: Valida que la placa pertenezca al cliente.
1.7 report_incident -> IncidentRepository.get_or_create_service_state: Obtiene/crea estado "pendiente".
1.8 report_incident -> ai_incident_processor: Realiza preprocesamiento IA inicial.
1.9 report_incident -> IncidentRepository.create_incident: Inserta incidente.
2.0 report_incident -> IncidentRepository.create_evidence: Inserta evidencias (imagen/texto extraido).
2.1 report_incident -> IncidentRepository.create_history: Inserta trazabilidad (3 eventos iniciales).
2.2 report_incident: Confirma transaccion.
2.3 API -> IncidentReportScreen: Retorna incidente registrado (201).
2.4 IncidentReportScreen -> Cliente: Muestra confirmacion de envio.


==================================================
RESUMEN RAPIDO DE ARCHIVOS CLAVE
==================================================
- UI movil:
  - mobile/lib/register_screen.dart
  - mobile/lib/login_screen.dart
  - mobile/lib/vehicle_registration_screen.dart
  - mobile/lib/incident_report_screen.dart

- Backend servicios (logica de negocio principal):
  - backend/app/services/user_service.py
  - backend/app/services/auth_service.py
  - backend/app/services/vehicle_service.py
  - backend/app/services/incident_service.py

- Tablas ORM referenciadas:
  - backend/app/models/user.py
  - backend/app/models/vehicle.py
  - backend/app/models/incident.py
