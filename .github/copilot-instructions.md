# Instrucciones para Copilot — Backend EIP (Import & Export Pasión)

Proyecto: backend FastAPI + SQLAlchemy 2 async + asyncpg + PostgreSQL (Supabase) + Alembic.
El front (`eip-proyecto-frontend`, Next.js) vive en un **repositorio git separado**. Está abierto en el workspace solo como **lectura** y es la fuente de verdad del contrato. Si no está en el workspace, lee las copias en `docs/contrato-front/`.

## Documentos (léelos, no los reinventes)
- `docs/GUIA_BACKEND.md`: contrato completo, modelo de datos, motor FIFO, permisos, tests y fases.
- `docs/PROGRESO.md`: estado actual. **Léelo al empezar y actualízalo al terminar cada fase.**
- `docs/schema.sql`: esquema real de la BD.

## Reglas siempre vigentes
1. Trabaja **una fase por vez** (sección 12 de la guía). No adelantes otras fases.
2. No modifiques `eip-proyecto-frontend` ni hagas commits, ramas o cambios git en él: todo el git es **solo del repo del backend**. Solo léelo para replicar su contrato.
3. No inventes reglas de negocio: si falta información, deja `# TODO(decisión):` y avisa.
4. Nunca escribas ni pidas credenciales reales. Todo va en `.env` (no versionado) y `.env.example` sin valores.
5. Routers delgados, lógica en `app/servicios/`. Estructura de carpetas en español: `api`, `bd`, `core`, `esquemas`, `modelo`, `servicios`.
6. Todo cambio de stock ocurre en **una sola transacción** y con `SELECT ... FOR UPDATE` sobre los lotes. No uses `async with db.begin()`: el router de escritura hace `await db.commit()`; los servicios solo `flush()`.
7. Esquema de BD solo por **Alembic** (nunca `create_all`). No borres datos.
8. Cada fase termina con sus tests en verde y una rama propia (`fase-N-nombre`).

## Contrato JSON (aplica a TODOS los endpoints)
- Prefijo `/api/v1`. JSON en **camelCase** (usa `CamelModel` de `esquemas/comun.py`).
- Sin envoltorio: se devuelve el objeto o la lista directo (nada de `{ "data": ... }`).
- Números como **number**, nunca string (los `Decimal` se serializan como `float`).
- Fechas ISO 8601 UTC con `Z`; `fecha` de comercio exterior `YYYY-MM-DD`.
- Errores siempre `{"detail": "<texto>"}` (incluido el 422: `detail` debe ser texto, no lista).
- Redondeo half-up con `Decimal.quantize(..., ROUND_HALF_UP)`; nunca `round()` de Python.
- `responsable` siempre sale del token, nunca del body. Precios siempre los recalcula el servidor.
- Roles en la API: `admin`, `vendedor`, `taller` (en BD: `ADMIN`, `VENDEDOR`, `TALLER`). Ids de usuario como `str`.
- Idioma de mensajes de error: español con voseo, exactamente como en la sección 4 de la guía.

## Al terminar cualquier tarea
Ejecuta los tests, actualiza `docs/PROGRESO.md` y lista lo que quedó pendiente o dudoso.
