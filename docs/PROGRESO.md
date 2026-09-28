# Progreso del backend EIP

> Copilot: lee este archivo al empezar cada fase y actualízalo al terminar. No borres el historial, solo agrega.

## Estado por fase

| Fase | Nombre | Estado | Rama / PR | Tests |
|---|---|---|---|---|
| 0 | Saneamiento | ✅ terminada | fase-0-saneamiento | `3 passed` |
| 1 | Base de datos | ✅ terminada | fase-1-base-de-datos | `3 passed`; upgrade local SQLite OK |
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

`docs/schema.sql` contiene únicamente `public.users`; no contiene filas de catálogos
ni las tablas operativas de la sección 5.

| Tabla de la guía | Estado en schema.sql | Acción Fase 1 |
|---|---|---|
| `users` | Existe con `id`, `full_name`, `email`, `hashed_password`, `role`, `is_active`, `created_at`; `email` tiene UNIQUE simple. | Se conserva; se agrega índice UNIQUE sobre `lower(email)`. |
| `categories` | Falta. | Se crea con `parent_id` autorreferente y FK `RESTRICT`. |
| `products` | Falta. | Se crea con stock/costo `NUMERIC(12,2)` e índice UNIQUE sobre `lower(sku)`. |
| `suppliers` | Falta. | Se crea. |
| `foreign_partners` | Falta. | Se crea. |
| `lots` | Falta. | Se crea con FKs a producto, proveedor, socio y responsable; índice FIFO `(product_id, received_at, id)`. |
| `stock_entries` | Falta. | Se crea con FKs a producto, proveedor y responsable. |
| `inventory_movements` | Falta. | Se crea como ledger con FK a producto, responsable y venta; índice por `created_at`. |
| `wastes` | Falta. | Se crea con FKs a producto y responsable. |
| `sales` | Falta. | Se crea con folio UNIQUE e índice por `created_at`. |
| `sale_items` | Falta. | Se crea con snapshots y FKs a venta y producto. |
| `foreign_trade_operations` | Falta. | Se crea con FK a socio y responsable. |
| `foreign_trade_lines` | Falta. | Se crea con FKs a operación y producto. |
| `foreign_trade_counters` | Falta; tabla de soporte de la decisión de folios por tipo. | Se crea con `type` como PK y `last_number`. |

No hay columnas con nombres alternativos que adaptar en `schema.sql`. La migración
detecta `users` existente para no recrearla ni borrar datos, y también puede crearla
en una base local vacía.

## Decisiones tomadas durante el desarrollo
- 2026-09-28 — Fase 1 — Se mantuvieron los nombres de `users` definidos en `schema.sql`; es la única tabla real disponible.
- 2026-09-28 — Fase 1 — No se inventaron categorías, proveedores ni socios: el esquema no aporta nombres ni IDs reales. Se dejó `seed_catalogos` idempotente para insertar filas explícitas solo cuando cada tabla esté vacía.
- 2026-09-28 — Fase 1 — Se añadió una ruta SQLite exclusiva para validar migraciones localmente; PostgreSQL continúa usando el flujo async.

## Contradicciones front vs. guía encontradas
_(el front gana; anotar aquí qué se cambió respecto a la guía)_

## Pendientes / `TODO(decisión)`
- Ejecutar `alembic upgrade head` sobre una copia PostgreSQL real cuando el humano la proporcione; no se usó Supabase ni ninguna URL de producción.
- Proporcionar los datos autorizados de categorías, proveedores y socios para ejecutar el seed; no existen en `docs/schema.sql`.

## Fase 0 — Saneamiento (2026-09-28)

- Configuración con `pydantic-settings`, variables obligatorias desde `.env`, CORS configurable y secretos ignorados por Git.
- Sesión async con rollback ante excepción y `expire_on_commit=False`; `Base` vive en `app/bd/base.py`.
- Auth reorganizada bajo `/api/v1/auth`; roles renombrados a `ADMIN`, `VENDEDOR` y `TALLER`.
- Handlers globales para HTTP, validación 422, negocio y errores no controlados, siempre con `detail` textual.
- Alembic inicializado para SQLAlchemy async y metadata del modelo actual.
- Tests básicos de arranque, 422 y CORS: 3 passed.

Pendiente para fases siguientes: completar modelos, migraciones y endpoints de negocio según `GUIA_BACKEND.md`; no se ejecutó ninguna migración contra una base real.

## Fase 1 — Base de datos (2026-09-28)

- Se comparó `docs/schema.sql`: `users` coincide en nombres y las otras tablas faltan.
- Se crearon los modelos SQLAlchemy 2 para usuarios, catálogos, productos, lotes, entradas, ledger, mermas, ventas y comercio exterior.
- Se creó una única revisión Alembic (`20260928_0001`) sin operaciones destructivas, con FKs `ON DELETE RESTRICT`, índices requeridos, índices únicos case-insensitive y contadores por tipo de folio.
- Se añadió seed idempotente parametrizable; no inserta datos porque no hay catálogo autorizado en el esquema real.
- Validación: `3 passed`; `alembic upgrade head` ejecutado en SQLite temporal local y SQL offline PostgreSQL generado correctamente.
