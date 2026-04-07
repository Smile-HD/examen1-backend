# Backend - Base simple

Estructura minima, clara y suficiente para iniciar el proyecto sin complejidad innecesaria.

## Estructura de carpetas

```text
backend/
├─ app/                 # Codigo de la API
│  └─ routers/          # Rutas/endpoints
├─ database/            # SQL y recursos de base de datos
├─ tests/               # Pruebas
├─ docs/                # Documentacion breve
├─ .env.example         # Variables de entorno de ejemplo
├─ requirements.txt     # Dependencias de Python
├─ contexto.md          # Enunciado/alcance funcional
└─ README.md
```

## Flujo recomendado

1. Crear entorno virtual.
2. Instalar dependencias.
3. Crear `.env` desde `.env.example`.
4. Crear base de datos en PostgreSQL.
5. Ejecutar el SQL inicial de `database/schema.sql`.
6. Empezar a construir endpoints en `app/routers`.
