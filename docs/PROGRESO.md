# Progreso del backend EIP

> Copilot: lee este archivo al empezar cada fase y actualízalo al terminar. No borres el historial, solo agrega.

## Estado por fase

| Fase | Nombre | Estado | Rama / PR | Tests |
|---|---|---|---|---|
| 0 | Saneamiento | ✅ terminada | fase-0-saneamiento | `3 passed` |
| 1 | Base de datos | ✅ terminada | fase-1-base-de-datos | `3 passed`; upgrade local SQLite OK |
| 2 | Auth y usuarios | ✅ terminada | fase-2-auth-usuarios | `15 passed` (Fase 0 + Fase 2) |
| 3 | Catálogos y productos | ✅ terminada | fase-3-productos | `17 passed` (Fases 0, 2 y 3) |
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

## Fase 2 — Auth y usuarios (2026-09-28)

- Se implementaron `POST /api/v1/auth/login` y `GET /api/v1/auth/me` con `accessToken`, `tokenType`, roles en minúsculas e ids serializados como texto.
- El login conserva el mismo 401 para email inexistente o contraseña incorrecta y devuelve 403 para cuentas inactivas. `usuario_actual` valida el JWT y consulta nuevamente la cuenta activa en la base de datos.
- Se añadió `requiere_roles(*roles)` y el CRUD protegido de `/api/v1/usuarios` para administradores, con validación de email, contraseña, duplicados, borrado con historial y protección del último administrador activo.
- Se centralizó el contexto bcrypt en `app/core/seguridad.py` y se añadió `CamelModel` para respuestas y requests camelCase.
- Validación: `15 passed` ejecutando Fase 0 y Fase 2 contra SQLite en memoria; se cubrieron login por rol, credenciales inválidas, inactividad, token expirado, permisos, formato y reglas de borrado/último administrador.

Pendiente para fases siguientes: catálogos y productos (Fase 3), motor de inventario (Fase 4) y el resto de endpoints de negocio. La integración con el front sigue pendiente hasta reemplazar sus servicios mock por llamadas HTTP.

## Fase 3 — Catálogos y productos (2026-09-28)

- Se añadieron `GET /api/v1/categorias`, `GET /api/v1/proveedores` y `GET /api/v1/comercio-exterior/socios-comerciales` con los permisos de la matriz y los nombres camelCase del contrato.
- Se implementó el CRUD protegido de `/api/v1/productos`: lectura para los tres roles y escritura solo para administradores.
- El alta fuerza `currentStock = 0` y `costPrice = 0`; el esquema de actualización no acepta esos campos, por lo que el stock y el costo quedan bajo control de las fases de inventario.
- Se validan categorías existentes, SKU sin distinguir mayúsculas, rangos del formulario del front, activación con precio mayor que cero y borrado con historial (`409`).
- `costPrice`, `currentStock`, `salePrice` y `minStockAlert` se serializan como números JSON mediante un único esquema `ProductoPublico`, manteniendo `costPrice` visible para todos los roles según la decisión abierta B.
- Validación: `17 passed` ejecutando la suite completa contra SQLite en memoria; la prueba de Fase 3 cubre catálogos, permisos, CRUD, duplicado de SKU, activación, historial y tipos numéricos.

Pendiente para fases siguientes: motor FIFO y lotes (Fase 4), entradas/compras/mermas (Fase 5), ventas (Fase 6), movimientos (Fase 7) y comercio exterior (Fase 8). La integración con el front continúa pendiente hasta reemplazar sus servicios mock por llamadas HTTP.
