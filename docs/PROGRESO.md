# Progreso del backend EIP

> Copilot: lee este archivo al empezar cada fase y actualízalo al terminar. No borres el historial, solo agrega.

## Estado por fase

| Fase | Nombre | Estado | Rama / PR | Tests |
|---|---|---|---|---|
| 0 | Saneamiento | ✅ terminada | fase-0-saneamiento | `3 passed` |
| 1 | Base de datos | ⬜ pendiente | | |
| 2 | Auth y usuarios | ⬜ pendiente | | |
| 3 | Catálogos y productos | ⬜ pendiente | | |
| 4 | Motor de inventario | ⬜ pendiente | | |
| 5 | Entradas, compras y mermas | ⬜ pendiente | | |
| 6 | Ventas | ⬜ pendiente | | |
| 7 | Movimientos | ⬜ pendiente | | |
| 8 | Comercio exterior | ⬜ pendiente | | |
| 9 | Dashboard (opcional) | ⬜ pendiente | | |
| 10 | Cierre | ⬜ pendiente | | |

Estados: ⬜ pendiente · 🟨 en curso · ✅ terminada (tests en verde)

## Comparativa esquema real vs. guía (Fase 1)
_(Copilot la completa en la Fase 1)_

## Decisiones tomadas durante el desarrollo
_(fecha — fase — decisión y motivo)_

## Contradicciones front vs. guía encontradas
_(el front gana; anotar aquí qué se cambió respecto a la guía)_

## Pendientes / `TODO(decisión)`
_(lista de lo que quedó abierto)_

## Fase 0 — Saneamiento (2026-09-28)

- Configuración con `pydantic-settings`, variables obligatorias desde `.env`, CORS configurable y secretos ignorados por Git.
- Sesión async con rollback ante excepción y `expire_on_commit=False`; `Base` vive en `app/bd/base.py`.
- Auth reorganizada bajo `/api/v1/auth`; roles renombrados a `ADMIN`, `VENDEDOR` y `TALLER`.
- Handlers globales para HTTP, validación 422, negocio y errores no controlados, siempre con `detail` textual.
- Alembic inicializado para SQLAlchemy async y metadata del modelo actual.
- Tests básicos de arranque, 422 y CORS: 3 passed.

Pendiente para fases siguientes: completar modelos, migraciones y endpoints de negocio según `GUIA_BACKEND.md`; no se ejecutó ninguna migración contra una base real.
