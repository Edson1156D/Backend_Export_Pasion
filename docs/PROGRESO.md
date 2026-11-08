# Progreso del backend EIP

> Copilot: lee este archivo al empezar cada fase y actualízalo al terminar. No borres el historial, solo agrega.

## Estado por fase

| Fase | Nombre | Estado | Rama / PR | Tests |
|---|---|---|---|---|
| 0 | Saneamiento | ✅ terminada | fase-0-saneamiento | `3 passed` |
| 1 | Base de datos | ✅ terminada | fase-1-base-de-datos | `3 passed`; upgrade local SQLite OK |
| 2 | Auth y usuarios | ✅ terminada | fase-2-auth-usuarios | `15 passed` (Fase 0 + Fase 2) |
| 3 | Catálogos y productos | ✅ terminada | fase-3-productos | `17 passed` (Fases 0, 2 y 3) |
| 4 | Motor de inventario | ✅ terminada | fase-4-motor-inventario | `14 passed` (`31` suite completa) |
| 5 | Entradas, compras y mermas | ✅ terminada | fase-5-entradas-compras-mermas | `34 passed` (suite completa) |
| 6 | Ventas | ✅ terminada | fase-6-ventas | `36 passed, 1 skipped` (suite local SQLite) |
| 7 | Movimientos | ✅ terminada | fase-7-movimientos | `38 passed, 1 skipped` (suite completa) |
| 8 | Comercio exterior | ✅ terminada | fase-8-comercio-exterior | `42 passed, 2 skipped` (suite completa) |
| 9 | Dashboard (opcional) | ✅ terminada | fase-9-dashboard | `44 passed, 2 skipped` (suite completa) |
| 10 | Cierre | ✅ terminada | fase-10-cierre | `44 passed, 2 skipped` |


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

## Tablas generadas por `alembic upgrade head` (H1)

`alembic upgrade head` crea la estructura de las tablas; no inventa registros de
negocio. Por eso, una base nueva queda inicialmente sin categorías, productos,
ventas, etc. La tabla `users` se conserva si ya existe y solo se crea cuando falta.
El seed de catálogos tampoco inserta filas sin datos autorizados.

En las tablas siguientes, `PK` significa clave primaria, `FK` significa clave
foránea, `NULL` significa que el dato es opcional y `NOT NULL` que es obligatorio.
Los tipos `NUMERIC(12,2)` representan cantidades o importes con dos decimales;
`NUMERIC(10,4)` representa tipos de cambio.

### 1. `users`

Cada fila representa un usuario que puede autenticarse en el sistema.

| Columna | Tipo | Regla | Dato que contiene |
|---|---|---|---|
| `id` | INTEGER | PK | Identificador del usuario. |
| `full_name` | VARCHAR(255) | NOT NULL | Nombre completo. |
| `email` | VARCHAR(255) | NOT NULL, único sin distinguir mayúsculas | Correo de acceso. |
| `hashed_password` | VARCHAR(255) | NOT NULL | Contraseña almacenada como hash, nunca en texto plano. |
| `role` | VARCHAR(50) | NOT NULL | `ADMIN`, `VENDEDOR` o `TALLER`. |
| `is_active` | BOOLEAN | NOT NULL | Indica si puede iniciar sesión. |
| `created_at` | TIMESTAMPTZ | NOT NULL | Fecha y hora de creación. |

### 2. `categories`

Cada fila representa una categoría o subcategoría de productos.

| Columna | Tipo | Regla | Dato que contiene |
|---|---|---|---|
| `id` | INTEGER | PK | Identificador de la categoría. |
| `parent_id` | INTEGER | FK a `categories.id`, NULL | Categoría padre; NULL indica una categoría raíz. |
| `name` | VARCHAR(150) | NOT NULL | Nombre de la categoría. |
| `description` | TEXT | NULL | Descripción adicional. |

### 3. `suppliers`

Cada fila representa un proveedor nacional utilizado en compras o entradas.

| Columna | Tipo | Regla | Dato que contiene |
|---|---|---|---|
| `id` | INTEGER | PK | Identificador del proveedor. |
| `name` | VARCHAR(255) | NOT NULL | Nombre o razón social del proveedor. |

### 4. `foreign_partners`

Cada fila representa un socio comercial del exterior, como cliente o proveedor.

| Columna | Tipo | Regla | Dato que contiene |
|---|---|---|---|
| `id` | INTEGER | PK | Identificador del socio comercial. |
| `name` | VARCHAR(255) | NOT NULL | Nombre del socio o empresa. |
| `country` | VARCHAR(120) | NOT NULL | País del socio comercial. |

### 5. `products`

Cada fila representa un producto del catálogo que puede venderse o moverse en
inventario.

| Columna | Tipo | Regla | Dato que contiene |
|---|---|---|---|
| `id` | INTEGER | PK | Identificador del producto. |
| `category_id` | INTEGER | FK a `categories.id`, NOT NULL | Categoría del producto. |
| `sku` | VARCHAR(50) | NOT NULL, único sin distinguir mayúsculas | Código interno del producto. |
| `name` | VARCHAR(150) | NOT NULL | Nombre comercial. |
| `unit_type` | VARCHAR(20) | NOT NULL | Unidad de medida, por ejemplo `UNIDAD` o `KILOGRAMO`. |
| `sale_price` | NUMERIC(12,2) | NOT NULL | Precio de venta vigente. |
| `cost_price` | NUMERIC(12,2) | NOT NULL | Costo derivado de los lotes. |
| `current_stock` | NUMERIC(12,2) | NOT NULL | Stock actual derivado de los lotes disponibles. |
| `min_stock_alert` | NUMERIC(12,2) | NOT NULL | Umbral para alertar stock bajo. |
| `is_active` | BOOLEAN | NOT NULL | Indica si el producto está habilitado para operar. |
| `created_at` | TIMESTAMPTZ | NOT NULL | Fecha y hora de creación. |

### 6. `lots`

Cada fila representa un lote de existencias de un producto. Los lotes se consumen
en orden FIFO, del más antiguo al más reciente.

| Columna | Tipo | Regla | Dato que contiene |
|---|---|---|---|
| `id` | INTEGER | PK | Identificador del lote. |
| `product_id` | INTEGER | FK a `products.id`, NOT NULL | Producto al que pertenece el lote. |
| `code` | VARCHAR(50) | NOT NULL, único | Código del lote, por ejemplo `LOTE-0001`. |
| `origin` | VARCHAR(30) | NOT NULL | Origen: `apertura`, `entrada`, `compra` o `importacion`. |
| `initial_qty` | NUMERIC(12,2) | NOT NULL | Cantidad original recibida. |
| `available_qty` | NUMERIC(12,2) | NOT NULL | Cantidad que todavía puede consumirse. |
| `unit_cost_pen` | NUMERIC(12,2) | NOT NULL | Costo unitario en soles. |
| `supplier_id` | INTEGER | FK a `suppliers.id`, NULL | Proveedor nacional, si corresponde. |
| `foreign_partner_id` | INTEGER | FK a `foreign_partners.id`, NULL | Socio exterior, si corresponde. |
| `responsable_id` | INTEGER | FK a `users.id`, NOT NULL | Usuario responsable de crear el lote. |
| `received_at` | TIMESTAMPTZ | NOT NULL | Fecha y hora de recepción; determina el orden FIFO. |

### 7. `stock_entries`

Cada fila representa un registro histórico de entrada de stock o compra.

| Columna | Tipo | Regla | Dato que contiene |
|---|---|---|---|
| `id` | INTEGER | PK | Identificador de la entrada. |
| `product_id` | INTEGER | FK a `products.id`, NOT NULL | Producto ingresado. |
| `quantity` | NUMERIC(12,2) | NOT NULL | Cantidad ingresada. |
| `supplier_id` | INTEGER | FK a `suppliers.id`, NULL | Proveedor de la entrada, si existe. |
| `responsable_id` | INTEGER | FK a `users.id`, NOT NULL | Usuario que registró la entrada. |
| `notes` | TEXT | NULL | Observaciones de la entrada. |
| `created_at` | TIMESTAMPTZ | NOT NULL | Fecha y hora del registro. |

### 8. `sales`

Cada fila representa la cabecera de una venta; sus productos se detallan en
`sale_items`.

| Columna | Tipo | Regla | Dato que contiene |
|---|---|---|---|
| `id` | INTEGER | PK | Identificador interno de la venta. |
| `folio` | VARCHAR(50) | NOT NULL, único | Folio de la boleta, por ejemplo `BLT-0001`. |
| `sale_type` | VARCHAR(30) | NOT NULL | Tipo de venta. |
| `payment_method` | VARCHAR(30) | NOT NULL | Método de pago. |
| `subtotal` | NUMERIC(12,2) | NOT NULL | Suma de los importes antes de ajustes. |
| `total` | NUMERIC(12,2) | NOT NULL | Total cobrado. |
| `paid_with` | NUMERIC(12,2) | NULL | Importe entregado por el cliente, si aplica. |
| `change_amount` | NUMERIC(12,2) | NULL | Vuelto calculado, si aplica. |
| `responsable_id` | INTEGER | FK a `users.id`, NOT NULL | Usuario que registró la venta. |
| `created_at` | TIMESTAMPTZ | NOT NULL | Fecha y hora de la venta. |

### 9. `sale_items`

Cada fila representa una línea de una venta y conserva un snapshot del producto
al momento de venderlo.

| Columna | Tipo | Regla | Dato que contiene |
|---|---|---|---|
| `id` | INTEGER | PK | Identificador de la línea. |
| `sale_id` | INTEGER | FK a `sales.id`, NOT NULL | Venta a la que pertenece. |
| `product_id` | INTEGER | FK a `products.id`, NOT NULL | Producto vendido. |
| `name` | VARCHAR(150) | NOT NULL | Nombre del producto al momento de vender. |
| `sku` | VARCHAR(50) | NOT NULL | SKU al momento de vender. |
| `unit_type` | VARCHAR(20) | NOT NULL | Unidad de medida al momento de vender. |
| `unit_price` | NUMERIC(12,2) | NOT NULL | Precio unitario aplicado. |
| `quantity` | NUMERIC(12,2) | NOT NULL | Cantidad vendida. |

### 10. `inventory_movements`

Cada fila representa un movimiento del ledger de inventario. Es histórico:
se inserta y no se edita ni se borra.

| Columna | Tipo | Regla | Dato que contiene |
|---|---|---|---|
| `id` | INTEGER | PK | Identificador del movimiento. |
| `product_id` | INTEGER | FK a `products.id`, NOT NULL | Producto afectado. |
| `responsable_id` | INTEGER | FK a `users.id`, NOT NULL | Usuario responsable. |
| `movement_type` | VARCHAR(30) | NOT NULL | `entrada`, `venta`, `merma`, `importacion` o `exportacion`. |
| `quantity` | NUMERIC(12,2) | NOT NULL | Cantidad con signo: positiva al ingresar y negativa al salir. |
| `reason` | TEXT | NULL | Motivo u observación. |
| `unit_sold_price` | NUMERIC(12,2) | NULL | Precio unitario de venta, si aplica. |
| `unit_cost_price` | NUMERIC(12,2) | NULL | Costo unitario usado para el movimiento. |
| `waste_type` | VARCHAR(100) | NULL | Tipo de merma, si aplica. |
| `sale_group_id` | INTEGER | FK a `sales.id`, NULL | Venta relacionada, si aplica. |
| `supplier_name` | VARCHAR(255) | NULL | Nombre del proveedor registrado en el movimiento, si aplica. |
| `folio` | VARCHAR(50) | NULL | Folio de venta o comercio exterior, si aplica. |
| `unit_price_usd` | NUMERIC(12,2) | NULL | Precio unitario en dólares, si aplica. |
| `exchange_rate` | NUMERIC(10,4) | NULL | Tipo de cambio usado, si aplica. |
| `created_at` | TIMESTAMPTZ | NOT NULL | Fecha y hora del movimiento. |

### 11. `wastes`

Cada fila representa una merma registrada sobre un producto.

| Columna | Tipo | Regla | Dato que contiene |
|---|---|---|---|
| `id` | INTEGER | PK | Identificador de la merma. |
| `product_id` | INTEGER | FK a `products.id`, NOT NULL | Producto perdido o descartado. |
| `quantity` | NUMERIC(12,2) | NOT NULL | Cantidad mermada. |
| `reason_code` | VARCHAR(100) | NOT NULL | Código o motivo de la merma. |
| `detail` | TEXT | NULL | Explicación adicional. |
| `responsable_id` | INTEGER | FK a `users.id`, NOT NULL | Usuario que registró la merma. |
| `created_at` | TIMESTAMPTZ | NOT NULL | Fecha y hora del registro. |

### 12. `foreign_trade_operations`

Cada fila representa una operación completa de importación o exportación.

| Columna | Tipo | Regla | Dato que contiene |
|---|---|---|---|
| `id` | INTEGER | PK | Identificador de la operación. |
| `folio` | VARCHAR(50) | NOT NULL, único | Folio `IMP-####` o `EXP-####`. |
| `date` | DATE | NOT NULL | Fecha comercial de la operación. |
| `type` | VARCHAR(20) | NOT NULL | `importacion` o `exportacion`. |
| `partner_id` | INTEGER | FK a `foreign_partners.id`, NOT NULL | Socio comercial involucrado. |
| `incoterm` | VARCHAR(10) | NULL | Incoterm acordado, si aplica. |
| `transport` | VARCHAR(20) | NULL | Medio de transporte, si aplica. |
| `exchange_rate` | NUMERIC(10,4) | NOT NULL | Tipo de cambio de la operación. |
| `subtotal_usd` | NUMERIC(12,2) | NOT NULL | Subtotal antes de ajustes en dólares. |
| `total_usd` | NUMERIC(12,2) | NOT NULL | Total en dólares. |
| `total_pen` | NUMERIC(12,2) | NOT NULL | Total convertido a soles. |
| `notes` | TEXT | NULL | Observaciones. |
| `responsable_id` | INTEGER | FK a `users.id`, NOT NULL | Usuario que registró la operación. |
| `created_at` | TIMESTAMPTZ | NOT NULL | Fecha y hora de creación. |

### 13. `foreign_trade_lines`

Cada fila representa un producto incluido en una operación de comercio exterior.
También conserva un snapshot del producto.

| Columna | Tipo | Regla | Dato que contiene |
|---|---|---|---|
| `id` | INTEGER | PK | Identificador de la línea. |
| `operation_id` | INTEGER | FK a `foreign_trade_operations.id`, NOT NULL | Operación a la que pertenece. |
| `product_id` | INTEGER | FK a `products.id`, NOT NULL | Producto importado o exportado. |
| `name` | VARCHAR(150) | NOT NULL | Nombre al momento de la operación. |
| `sku` | VARCHAR(50) | NOT NULL | SKU al momento de la operación. |
| `unit_type` | VARCHAR(20) | NOT NULL | Unidad de medida. |
| `quantity` | NUMERIC(12,2) | NOT NULL | Cantidad operada. |
| `price_usd` | NUMERIC(12,2) | NOT NULL | Precio unitario en dólares. |
| `subtotal_usd` | NUMERIC(12,2) | NOT NULL | Subtotal de la línea en dólares. |

### 14. `foreign_trade_counters`

Cada fila representa un contador independiente para generar folios de comercio
exterior sin duplicados.

| Columna | Tipo | Regla | Dato que contiene |
|---|---|---|---|
| `type` | VARCHAR(20) | PK | Tipo de contador: `IMP` o `EXP`. |
| `last_number` | INTEGER | NOT NULL | Último número utilizado para ese tipo de folio. |

### Tabla técnica `alembic_version`

Cada fila representa la revisión de Alembic aplicada a la base de datos. En esta
aplicación normalmente contiene una sola fila.

| Columna | Tipo | Dato que contiene |
|---|---|---|
| `version_num` | VARCHAR(32) | Identificador de la migración aplicada, actualmente `20260928_0001`. |

Las claves foráneas usan `ON DELETE RESTRICT`: no se puede borrar un registro que
todavía tenga datos relacionados. La migración también crea índices para el correo
de usuarios, el SKU de productos, el orden FIFO de lotes, la fecha de movimientos
y la fecha de ventas.

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

## Fase 4 — Motor de inventario (2026-09-28)

- Se implementaron en `app/servicios/inventario.py` `round2` half-up, validaciones, costo promedio ponderado, costo de consumo y asignación FIFO con orden `received_at, id`; los errores conservan los mensajes exactos del contrato.
- Se añadieron `ingresar_lote`, `consumir_lotes` y `sincronizar_stock_producto`. Las consultas de lotes usan `SELECT ... FOR UPDATE`, el stock y el costo derivado se sincronizan en la misma sesión, y el costo anterior se conserva cuando el stock queda en cero.
- Los códigos se generan como `LOTE-0001`, correlativos a partir del id persistido, y se añadió `scripts/crear_aperturas.py` junto con `crear_lotes_apertura`, idempotente para productos con stock existente sin lotes.
- Se implementaron `GET /api/v1/lotes` y `GET /api/v1/lotes/producto/{productId}` para admin/taller, con filtros, orden reciente y orden FIFO, respuesta camelCase y proveedor/responsable resueltos.
- Se añadió `verificar_consistencia_stock` y cobertura async de apertura, consistencia, órdenes y permisos. Validación: `14 passed` de Fase 4 y `31 passed` en la suite completa.

Pendiente para fases siguientes: entradas/compras/mermas (Fase 5), ventas (Fase 6), movimientos (Fase 7) y comercio exterior (Fase 8). La integración con el front continúa pendiente hasta reemplazar sus servicios mock por llamadas HTTP. La apertura debe ejecutarse con `python -m scripts.crear_aperturas` en una base real después de revisar sus datos existentes.

## Fase 5 — Entradas, compras y mermas (2026-09-28)

- Se añadieron `GET/POST /api/v1/entradas`, `POST /api/v1/compras` y `GET/POST /api/v1/mermas` con los permisos de la matriz: admin/taller para lectura, taller para producción y mermas, y admin para compras.
- Las operaciones de escritura reutilizan `servicios/inventario.py`: cada ingreso crea lote, historial de entrada, sincroniza stock/costo y agrega una fila `entrada` al ledger en la misma transacción. Las mermas consumen FIFO y agregan una fila `merma` con costo FIFO.
- El responsable se obtiene del token; se aplican los mensajes de producto/proveedor inexistente, costo obligatorio sin stock, stock insuficiente y motivos permitidos del contrato.
- Se añadieron pruebas de compra, entrada de producción, permisos, costo promedio, tipos numéricos y atomicidad de mermas. Validación: `34 passed` en la suite completa.

Pendiente para fases siguientes: ventas (Fase 6), movimientos (Fase 7) y comercio exterior (Fase 8). Sigue pendiente ejecutar Alembic contra una copia PostgreSQL real y conectar el frontend, que permanece sin modificaciones.

## Fase 6 — Ventas (2026-09-28)

- Se implementaron `POST /api/v1/ventas`, `GET /api/v1/ventas` para admin y `GET /api/v1/ventas/mias` para vendedor, con permisos de la matriz.
- El servidor recalcula productos, precios, totales y vuelto; ignora snapshots/precios enviados por el cliente, guarda snapshots en `sale_items` y genera folio `BLT-####` después de `flush()`.
- Cada ítem consume lotes FIFO y escribe una fila negativa en el ledger con `saleGroupId`, costo FIFO y folio. La transacción es todo o nada; la adquisición de locks se ordena por producto para reducir deadlocks.
- Se añadieron pruebas de recalculo, FIFO, atomicidad, permisos, listados y números JSON. Validación local: `36 passed, 1 skipped`; la prueba concurrente queda omitida porque SQLite ignora `SELECT ... FOR UPDATE` y debe ejecutarse contra PostgreSQL.

Pendiente para fases siguientes: movimientos (Fase 7), comercio exterior (Fase 8) y, opcionalmente, dashboard (Fase 9). Sigue pendiente ejecutar la prueba de concurrencia y Alembic contra una copia PostgreSQL real, además de conectar el frontend, que permanece sin modificaciones.

## Fase 7 — Movimientos (2026-09-28)

- Se implementó `GET /api/v1/movimientos`, protegido exclusivamente para administradores y sin endpoints de escritura sobre el ledger.
- El listado usa un `LEFT OUTER JOIN` con productos para conservar movimientos aunque el producto ya no exista, y resuelve `productName`, `sku` y `unitType` con los valores de fallback del contrato.
- Se enriquecieron los movimientos de venta con `tipoVenta` legible y el folio propio o el de la venta asociada. El orden es `createdAt` descendente y luego `id` descendente.
- Los campos numéricos se convierten explícitamente a `float` antes de serializarse como JSON.
- Validación: `38 passed, 1 skipped` en la suite completa; se añadió cobertura enfocada de permisos, enriquecimiento, orden, folio y tipos numéricos.

Pendiente para fases siguientes: comercio exterior (Fase 8) y, opcionalmente, dashboard (Fase 9). Sigue pendiente ejecutar la prueba de concurrencia y Alembic contra una copia PostgreSQL real, además de conectar el frontend, que permanece sin modificaciones.

## Fase 8 — Comercio exterior (2026-09-28)

- Se implementaron `GET/POST /api/v1/comercio-exterior/operaciones`, protegidos exclusivamente para administradores. El responsable siempre se toma del token y el valor enviado en el body se ignora.
- Las importaciones crean lotes `importacion` asociados al socio comercial y registran el ledger positivo; las exportaciones consumen FIFO y registran el ledger negativo con costo FIFO. El rollback de la sesión conserva la atomicidad cuando falta stock.
- Se implementaron folios `IMP-####` y `EXP-####` con contadores independientes y bloqueo `SELECT ... FOR UPDATE`; para bases existentes se inicializa la fila del contador de forma idempotente.
- Se replicaron los cálculos del frontend: subtotal de línea, subtotal/total USD y total PEN con redondeo half-up. Se añadieron aliases explícitos para las claves contractuales `precioUSD`, `subtotalUSD`, `totalUSD` y `totalPEN`.
- Se añadieron pruebas de importación, exportación FIFO, atomicidad, permisos, tipos numéricos y secuencias independientes. Validación: `42 passed, 2 skipped` en la suite completa.

Pendiente para fases siguientes: dashboard (Fase 9, opcional) y cierre (Fase 10). Sigue pendiente ejecutar la prueba de concurrencia de folios y la de inventario contra PostgreSQL real, ejecutar Alembic sobre una copia PostgreSQL real y conectar el frontend, que permanece sin modificaciones.

## Fase 9 — Dashboard (2026-09-29)

- Se implementó `GET /api/v1/dashboard/resumen?periodo=dia|semana|mes`, exclusivo para administradores, con `mes` como valor predeterminado y respuesta directa en camelCase.
- El resumen devuelve ventas totales, cantidad de ventas, promedio por venta, piezas vendidas y margen bruto. El margen usa el costo FIFO persistido en cada movimiento de venta, no el costo actual del producto.
- Se añadió una serie de las últimas ocho semanas con ventas, piezas y margen, además del top 5 de productos ordenado por ventas y piezas.
- Las alertas se calculan con las mismas reglas del frontend: agotado, stock bajo e inactivo. No se modificó ningún archivo del repositorio frontend.
- Se usa UTC-05:00 fijo para los límites de calendario de Perú, sin agregar la dependencia `tzdata`; todos los números se serializan como JSON `number`.
- Validación: `44 passed, 2 skipped` en la suite completa; la prueba enfocada de Fase 9 cubre KPIs, serie, top, alertas, permisos y validación textual de `periodo`.

Pendiente para Fase 10: revisar OpenAPI/README, ejecutar Alembic sobre una copia PostgreSQL real y ejecutar las pruebas de concurrencia contra PostgreSQL.

## Fase 10 — Cierre (2026-09-29)

- Se revisó y documentó el contrato OpenAPI expuesto por FastAPI (`/docs`, `/redoc` y `/openapi.json`) con nombre, descripción, versión y tags ordenados por recurso.
- Se añadieron resúmenes, descripciones y respuestas de error documentadas a las 28 rutas de negocio, además de ejemplos JSON realistas para todos los esquemas Pydantic propios.
- Se verificó el esquema Bearer/JWT generado por `HTTPBearer`: Swagger UI muestra el botón `Authorize` y las rutas protegidas declaran el esquema de seguridad.
- Se reemplazó el README mínimo por una guía reproducible para crear el entorno virtual, instalar dependencias, configurar `.env`, ejecutar Alembic, levantar Uvicorn y correr tests.
- Se añadió `python -m scripts.verificar_consistencia`, que compara el stock derivado de productos con la suma de lotes y devuelve código de salida no cero ante inconsistencias.
- Se añadió `docs/DEPLOYMENT_CHECKLIST.md` con variables de entorno, CORS, migraciones, operación y diferencias entre los poolers de Supabase.
- Se incorporó logging HTTP básico con método, ruta, estado y duración; no se registran cuerpos, tokens, contraseñas ni cabeceras.
- Validación final: `/docs` y `/openapi.json` se generan correctamente; `44 passed, 2 skipped`.
- Pendiente externo: ejecutar `alembic upgrade head` y las pruebas de concurrencia contra una copia PostgreSQL real; el frontend continúa pendiente de conexión y no fue modificado.
