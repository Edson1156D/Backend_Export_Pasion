# Guía para construir el backend de EIP (Import & Export Pasión)

> **Cómo usar esta guía:** este archivo vive en `Backend_Export_Pasion/docs/GUIA_BACKEND.md` (una sola copia). Copilot trabaja en un workspace multi-root con `Backend_Export_Pasion` (se edita) y `eip-proyecto-frontend` (**solo lectura**; es un repositorio git **separado**, se conectará al backend cuando este esté listo; si no está en el workspace, sus archivos de contrato se leen en `docs/contrato-front/`). Se trabaja **fase por fase** (sección 12) con los prompts de `docs/PROMPTS_FASES.md`, y al cerrar cada fase se actualiza `docs/PROGRESO.md`. Nunca se implementa más de una fase por vez.

---

## 0. Reglas de trabajo para Copilot (léelas siempre)

1. **El front es la fuente de verdad del contrato.** Cada endpoint debe devolver exactamente los campos, nombres (camelCase), tipos y mensajes de error que el front ya espera. Antes de crear un endpoint, abre el `*.service.ts` mock correspondiente en `eip-proyecto-frontend/src/features/<módulo>/` y replica su comportamiento.
2. **No inventes reglas de negocio.** Si algo no está en el front ni en esta guía, deja un `# TODO(decisión):` y avisa en lugar de asumir.
3. **No modifiques nada de `eip-proyecto-frontend`**: solo léelo. Es un repo aparte: no hagas commits ni ramas ahí. Sus cambios los hace una persona aparte (sección 13).
4. **Una fase = una rama y un PR.** Cada fase termina con sus tests en verde.
5. **Toda operación que toque stock corre en una sola transacción.** Si algo falla, no queda nada a medias.
6. **Nunca** escribas credenciales, claves ni URLs de base de datos en el código. Todo va en `.env` (y `.env.example` sin valores reales).
7. Mantén la estructura de carpetas en español ya existente (`api`, `bd`, `core`, `esquemas`, `modelo`).
8. **Lee `docs/PROGRESO.md` al empezar** y **actualízalo al terminar** cada fase (qué se hizo, qué quedó pendiente, decisiones tomadas).
9. **No pidas ni escribas credenciales reales.** Para conocer la BD usa `docs/schema.sql`; para conectarte, el `.env` local que ya existe (no versionado).
10. Si el front y esta guía se contradicen, **gana el front**; anótalo en `docs/PROGRESO.md`.

---

## 1. Contexto del sistema

Sistema web de gestión de inventario y analítica para una empresa peruana que comercializa piedras semipreciosas (minerales, cuarzos, joyería, exportación/importación).

- **Front:** Next.js 16 (App Router), React 19, TypeScript, TanStack Query, Axios, Zod. Hoy funciona 100% con **mocks en localStorage** (`createLocalStore`). Cada `*.service.ts` es una función que hay que reemplazar por una llamada HTTP al backend.
- **Backend (actual):** FastAPI + SQLAlchemy 2 async + asyncpg + PostgreSQL (Supabase). Solo tiene `POST /login`, el modelo `Usuario`, JWT y bcrypt. El resto de archivos (`productos.py`, `movimientos.py`, `analisis.py`, `tokens.py`, `modelo/productos.py`, `modelo/movimientos.py`, `bd/base.py`) están **vacíos**.

### Roles y qué módulos usa cada uno (sacado de los grupos de rutas del front)

| Rol (API) | Valor en BD | Pantallas |
|---|---|---|
| `admin` | `ADMIN` | Dashboard, Productos, Compras, Movimientos, Comercio exterior, Ventas (todas), Usuarios, Punto de venta |
| `vendedor` | `VENDEDOR` | Punto de venta, Mis ventas |
| `taller` | `TALLER` | Entradas, Mermas, Etiquetas QR, Catálogo, Alertas |

---

## 2. Problemas del backend actual que se corrigen en la Fase 0

| # | Problema | Qué hacer |
|---|---|---|
| 1 | `bd/session.py` tiene la **URL completa de la BD con usuario y contraseña** escritos en el código. | Moverla a `.env` (`DATABASE_URL`). La contraseña de Supabase la rota el humano (se asume comprometida; también queda en el historial de git). Copilot **no** debe pedir, mostrar ni escribir la clave real en ningún archivo versionado. |
| 2 | `core/seguridad.py` tiene `SECRET_KEY` escrita en el código. | Moverla a `.env` (`SECRET_KEY`), generar una **nueva** (`openssl rand -hex 32`). Las tokens firmadas con la anterior quedan inválidas: es lo esperado. |
| 3 | CORS solo permite `http://localhost:5173` (Vite). El front es Next.js en `:3000`. | Leer los orígenes de `CORS_ORIGINS` en `.env` (`http://localhost:3000` + dominio de producción). |
| 4 | El login exige `role` en el body; **el front no lo envía** (solo `email` y `password`). | Quitar `role` del request. El rol sale de la BD. |
| 5 | El login devuelve `rol: "ADMIN"` (mayúsculas); el front usa `"admin" \| "vendedor" \| "taller"` (minúsculas). | Mapear en el esquema de respuesta: `ADMIN→admin`, `VENDEDOR→vendedor`, `TALLER→taller`. |
| 6 | `usuario.id` es `int`; el front lo tipa como `string`. | Serializar el id de usuario como `str`. |
| 7 | El login **no revisa `is_active`**. | Si está inactivo → 403 `"Tu cuenta está inactiva. Contactá a un administrador."` |
| 8 | `requiere_rol(rol)` acepta un solo rol; hay rutas para varios roles. | Crear `requiere_roles(*roles)`. |
| 9 | El router de login vive en `api/dependencias.py` (nombre confuso) y la ruta es `/login` sin prefijo. | `api/deps.py` para dependencias; `api/v1/auth.py` para login; todo bajo `/api/v1`. |
| 10 | `requirements.txt` es un `pip freeze` con paquetes que no se usan (Flask, Werkzeug, Jinja2, itsdangerous, pymongo, windows-curses…). `windows-curses` rompe el despliegue en Linux. | Dejar solo dependencias directas: `fastapi`, `uvicorn`, `sqlalchemy[asyncio]`, `asyncpg`, `alembic`, `pydantic`, `pydantic-settings`, `email-validator`, `python-jose`, `passlib`, `bcrypt==3.2.2`, y de desarrollo `pytest`, `pytest-asyncio`, `httpx`. |
| 11 | `bcrypt==3.2.2` + `passlib==1.7.4`. | **Mantener ese par de versiones**: `passlib` no es compatible con `bcrypt` ≥ 4.1. |
| 12 | Enum `RolUsuario` con nombres `DUENO/VENTAS/ALMACEN` que no coinciden con el resto del sistema. | Renombrar a `ADMIN/VENDEDOR/TALLER` (mismos valores que ya están en BD). |
| 13 | Sin manejo global de errores. | Ver sección 4 (formato de errores). |

---

## 3. Estructura de carpetas objetivo

```
Backend_Export_Pasion/
├── alembic/                      # migraciones
├── app/
│   ├── main.py                   # crea la app, CORS, handlers, include_router(prefix="/api/v1")
│   ├── core/
│   │   ├── config.py             # Settings (pydantic-settings) leyendo .env
│   │   ├── seguridad.py          # JWT, hash de contraseñas
│   │   └── errores.py            # excepciones de negocio + handlers globales
│   ├── bd/
│   │   ├── session.py            # engine, AsyncSessionLocal, get_db
│   │   └── base.py               # Base + import de todos los modelos (para Alembic)
│   ├── modelo/                   # SQLAlchemy (una tabla por archivo)
│   ├── esquemas/                 # Pydantic v2 (request/response)
│   │   └── comun.py              # CamelModel base
│   ├── servicios/                # LÓGICA DE NEGOCIO (routers delgados, servicios gordos)
│   │   ├── inventario.py         # motor FIFO + ledger (núcleo, ver sección 8)
│   │   ├── ventas.py, compras.py, mermas.py, comercio_exterior.py, ...
│   └── api/
│       ├── deps.py               # get_db, usuario_actual, requiere_roles
│       └── v1/                   # un router por módulo
├── tests/
├── .env.example
└── requirements.txt
```

Regla: los **routers no contienen lógica** de negocio; solo validan entrada, llaman a un servicio y devuelven el esquema.

---

## 4. Convenciones del contrato (críticas para que el front funcione sin tocarlo)

1. **Prefijo:** `/api/v1`. El front usará `NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1`.
2. **JSON en camelCase** (`fullName`, `productId`, `salePrice`…), aunque en Python/BD sea snake_case. Crear en `esquemas/comun.py` un `CamelModel` con `ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)` y heredar de él en todos los esquemas.
3. **Sin envoltorio.** El front hace `response.data` directo: cada endpoint devuelve el objeto o la lista tal cual, **no** `{ "data": ... }`. (El backend actual del login usa un `mensaje`; en el nuevo puede quedar como campo extra ignorable, pero no es necesario.)
4. **Números como `number`, no como string.** Pydantic v2 serializa `Decimal` como **string** en JSON. Las columnas en BD serán `NUMERIC`, pero en los esquemas de respuesta hay que devolver `float` (por ejemplo con `Annotated[Decimal, PlainSerializer(float, return_type=float, when_used="json")]`). Verificar con un test que `salePrice` llega como número.
5. **Fechas:** ISO 8601 en UTC con `Z` (`2026-09-12T04:21:22.600Z`) para `createdAt`, `fechaIngreso`. `fecha` de comercio exterior es `YYYY-MM-DD`.
6. **Formato de errores:** siempre `{"detail": "<mensaje en texto>"}`. El interceptor de Axios del front lee `error.response.data.detail` y lo muestra en un toast. Si `detail` fuera una lista (el 422 por defecto de FastAPI), el usuario vería `[object Object]`. Por eso hay que registrar un handler para `RequestValidationError` que devuelva un `detail` en texto (ej. `"salePrice: debe ser mayor o igual a 0"`).
7. **Códigos HTTP:** `400` regla de negocio simple, `401` sin token/token inválido, `403` sin permiso o cuenta inactiva, `404` no existe, `409` conflicto (duplicado, stock insuficiente, tiene registros asociados), `422` validación de esquema.
8. **Mensajes de error exactos** (el front ya los usa/espera; mantener el español y el voseo del mock):
   - `"Email o contraseña incorrectos"`
   - `"Tu cuenta está inactiva. Contactá a un administrador."`
   - `"Ya existe un usuario con ese email"`
   - `"Usuario no encontrado"` · `"Producto no encontrado"` · `"Proveedor no encontrado"` · `"Socio comercial no encontrado"`
   - `"La cantidad debe ser mayor a 0"` · `"El costo no puede ser negativo"`
   - `"Stock insuficiente: hay {disponible} y se requieren {pedido}"`
   - `"El costo de compra es obligatorio cuando el producto aún no tiene stock"`
   - `"Para activar el producto, el precio de venta debe ser mayor a 0"`
9. **Listas ordenadas** como el mock: entradas, ventas, mermas, movimientos y lotes → más reciente primero; lotes de un producto → FIFO (más antiguo primero); operaciones de comercio exterior → `fecha` desc, luego `id` desc.
10. **Sin paginación en la primera versión.** El front filtra y pagina en el cliente y espera la lista completa. (Más adelante se puede agregar `limit/offset` sin romper nada.)
11. **Redondeo:** el front usa `round2(n) = Math.round(n*100)/100` (mitad hacia arriba). En Python **no** usar `round()` (redondea al par). Usar `Decimal.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)` en una única función `round2` compartida.

---

## 5. Modelo de datos

**Antes de crear tablas:** la BD de Supabase **ya existe** y ya tiene al menos `users` (y probablemente más). El humano deja el volcado del esquema real en **`docs/schema.sql`** (`pg_dump --schema-only`). Copilot **debe leer ese archivo** (no puede conectarse a Supabase por sí mismo), compararlo con las tablas de abajo y usar **Alembic** para agregar/alterar sin borrar datos. Si `docs/schema.sql` no existe, detenerse y avisar. Los nombres de columna de abajo son la propuesta; si ya existen con otro nombre, se respeta el existente.

Tipos: cantidades y stock `NUMERIC(12,2)` (hay kilogramos con decimales); precios y costos `NUMERIC(12,2)`; `tipo_cambio` `NUMERIC(10,4)`; fechas `TIMESTAMPTZ`.

| Tabla | Columnas principales | Notas |
|---|---|---|
| `users` (existe) | id, full_name, email, hashed_password, role (`ADMIN/VENDEDOR/TALLER`), is_active, created_at | Índice único sobre `lower(email)`. Guardar el email en minúsculas. |
| `categories` | id, parent_id (FK propia, null = raíz), name, description | El front solo la lee. IDs no correlativos en el mock (1–6 raíces; 9, 11, 12, 24, 27 hijas): **verificar los reales en BD**. |
| `products` | id, category_id, sku, name, unit_type (`UNIDAD`/`KILOGRAMO`), sale_price, cost_price, current_stock, min_stock_alert, is_active, created_at | `sku` único sin distinguir mayúsculas (índice sobre `lower(sku)`), máx. 50; `name` 3–150. `current_stock` y `cost_price` son **derivados de los lotes** (sección 8). |
| `suppliers` | id, name | Proveedores **nacionales** (usados en compras). |
| `foreign_partners` | id, name, country | Socios comerciales del exterior (clientes/proveedores de comercio exterior). |
| `lots` | id, product_id, code (`LOTE-0001`, único), origin (`apertura/entrada/compra/importacion`), initial_qty, available_qty, unit_cost_pen, supplier_id (null) o `foreign_partner_id` (null), responsable_id, received_at | Un lote = una entrada de stock. La cantidad disponible baja con cada consumo FIFO. |
| `stock_entries` | id, product_id, quantity, supplier_id (null), responsable_id, notes, created_at | Historial de entradas y compras (lo que lista la pantalla Entradas/Compras). |
| `inventory_movements` (**ledger**) | id, product_id, responsable_id, movement_type (`entrada/venta/merma/importacion/exportacion`), quantity (con signo), reason, unit_sold_price, unit_cost_price, waste_type, sale_group_id (FK a `sales`), supplier_name, folio, unit_price_usd, exchange_rate, created_at | **Solo se inserta, nunca se edita ni se borra.** |
| `wastes` | id, product_id, quantity, reason_code (`motivo`), detail, responsable_id, created_at | Mermas. |
| `sales` | id, folio (`BLT-0001`, único), sale_type, payment_method, subtotal, total, paid_with (null), change_amount (null), responsable_id, created_at | |
| `sale_items` | id, sale_id, product_id, name, sku, unit_type, unit_price, quantity | **Snapshot** del producto al momento de vender (aunque luego cambie el nombre o el precio). |
| `foreign_trade_operations` | id, folio (`IMP-0001` / `EXP-0001`), date, type (`importacion/exportacion`), partner_id, incoterm (null), transport (null), exchange_rate, subtotal_usd, total_usd, total_pen, notes, responsable_id, created_at | Folio con contador **por tipo** (ver sección 9.10). |
| `foreign_trade_lines` | id, operation_id, product_id, name, sku, unit_type, quantity, price_usd, subtotal_usd | Snapshot del producto. |

Integridad: FK con `ON DELETE RESTRICT`. Índices en `lots(product_id, received_at, id)`, `inventory_movements(created_at)`, `sales(created_at)`.

---

## 6. Autenticación y permisos

**JWT** con `id` y `role` en el payload (ya existe `crear_token`/`leer_token`). Cambios:

- Expiración configurable: `ACCESS_TOKEN_EXPIRE_MINUTES` (por defecto 480, una jornada; hoy son 60 y el front **no tiene refresco de sesión**, así que a los 60 min el usuario se caería en pleno uso). Ver decisiones abiertas.
- La dependencia `usuario_actual` valida el token **y consulta la BD** para confirmar que el usuario sigue existiendo y activo (así, desactivar a alguien lo bloquea de inmediato).
- `requiere_roles("admin", "taller")` devuelve 403 `"No tienes permiso para acceder a esto"`.
- No revelar si el email existe: mismo 401 para email inexistente o contraseña incorrecta (ya está así).
- Contraseñas: bcrypt vía passlib, mínimo 6 caracteres (regla del front). Nunca devolver `hashed_password`.

### Matriz de permisos (derivada de los `RoleGuard` del front)

| Recurso | admin | vendedor | taller |
|---|:-:|:-:|:-:|
| Login / `me` | ✅ | ✅ | ✅ |
| Usuarios (CRUD) | ✅ | ❌ | ❌ |
| Categorías (leer) | ✅ | ✅ | ✅ |
| Productos: leer | ✅ | ✅ | ✅ |
| Productos: crear / editar / borrar | ✅ | ❌ | ❌ |
| Proveedores (leer) | ✅ | ❌ | ✅ |
| Lotes (leer) | ✅ | ❌ | ✅ |
| Entradas: leer | ✅ | ❌ | ✅ |
| Entrada de producción (registrar) | ❌ | ❌ | ✅ |
| Compra a proveedor (registrar) | ✅ | ❌ | ❌ |
| Mermas: leer / registrar | leer ✅ | ❌ | ✅ / ✅ |
| Ventas: registrar (POS) | ✅ | ✅ | ❌ |
| Ventas: todas | ✅ | ❌ | ❌ |
| Ventas: solo las mías | ❌ | ✅ | ❌ |
| Movimientos (ledger) | ✅ | ❌ | ❌ |
| Comercio exterior (leer / registrar) | ✅ | ❌ | ❌ |
| Dashboard | ✅ | ❌ | ❌ |

---

## 7. Endpoints (contrato completo)

`{resp}` = objeto devuelto. Todos requieren `Authorization: Bearer <token>` salvo el login.

### 7.1 Auth

| Método y ruta | Roles | Request | Response |
|---|---|---|---|
| `POST /auth/login` | público | `{ email, password }` | `{ accessToken, tokenType: "bearer", usuario: { id: string, nombre, email, rol: "admin"\|"vendedor"\|"taller" } }` |
| `GET /auth/me` | todos | — | `usuario` (mismo objeto) |

Reglas: email en minúsculas; 401 `"Email o contraseña incorrectos"`; 403 si `is_active = false`.
> **Decidido:** el token se devuelve con la clave `accessToken` (camelCase, como el resto) y `tokenType: "bearer"`. El front actual espera `Usuario { id, nombre, rol }`.

### 7.2 Usuarios (`/usuarios`) — solo admin

Tipo `User`: `{ id: string, fullName, email, role, isActive, createdAt }`.

| Método y ruta | Request | Notas |
|---|---|---|
| `GET /usuarios` | — | Lista de `User`. |
| `POST /usuarios` | `{ fullName (≥3), email, role, password (≥6), isActive }` | 409 `"Ya existe un usuario con ese email"`. |
| `PUT /usuarios/{id}` | `{ fullName, email, role, isActive, password? }` | `password` vacío u omitido = **no cambiar**. 409 si el email es de otro usuario. 404 si no existe. |
| `DELETE /usuarios/{id}` | — | 204. Ver reglas abajo. |

Reglas de `DELETE`: el mock borra sin más, pero con datos reales hay FKs. Definir: **409** si el usuario tiene ventas/movimientos (`"No se puede eliminar: tiene registros asociados. Desactívalo en su lugar."`); no permitir que un admin se elimine a sí mismo ni al último admin activo. **La misma protección aplica al `PUT`**: no se puede desactivar ni cambiar de rol al último admin activo (409 `"Debe quedar al menos un administrador activo"`).

### 7.3 Catálogos de solo lectura

| Ruta | Roles | Response |
|---|---|---|
| `GET /categorias` | todos | `[{ id, parentId: number\|null, name, description: string\|null }]` (lista plana; el front arma el árbol) |
| `GET /proveedores` | admin, taller | `[{ id, name }]` |
| `GET /comercio-exterior/socios-comerciales` | admin | `[{ id, nombre, pais }]` |

### 7.4 Productos (`/productos`)

Tipo `Product`: `{ id, categoryId, sku, name, unitType: "UNIDAD"|"KILOGRAMO", salePrice, costPrice, currentStock, minStockAlert, isActive, createdAt }`.

| Método y ruta | Roles | Request | Notas |
|---|---|---|---|
| `GET /productos` | todos | — | Lista completa. |
| `GET /productos/{id}` | todos | — | 404 `"Producto no encontrado"`. |
| `POST /productos` | admin | `{ sku, name, categoryId, unitType, salePrice, minStockAlert, isActive }` | El alta es mínima: **el servidor fuerza `currentStock = 0` y `costPrice = 0`** aunque el cliente los mande (el front hoy los manda en 0). Stock y costo llegan después vía Compras. |
| `PUT /productos/{id}` | admin | Cualquier subconjunto de `sku, name, categoryId, unitType, salePrice, minStockAlert, isActive` | **Ignorar/rechazar** `currentStock` y `costPrice`: solo los cambia el motor de inventario. |
| `DELETE /productos/{id}` | admin | — | 409 si tiene lotes, movimientos o ventas (`"No se puede eliminar: el producto tiene movimientos. Desactívalo en su lugar."`). |

Validaciones (mismas que `products/schemas.ts`): `sku` 1–50 y único (sin distinguir mayúsculas) → 409 `"Ya existe un producto con ese SKU"`; `name` 3–150; `categoryId` debe existir; `salePrice ≥ 0`; `minStockAlert ≥ 0`; **si `isActive = true` entonces `salePrice > 0`** (mensaje exacto en la sección 4). Recomendado: bloquear el cambio de `unitType` si el producto ya tiene lotes o movimientos.

### 7.5 Lotes (solo lectura; se crean internamente)

Tipo `Lote`: `{ id, productId, codigo, origen, cantidadInicial, cantidadDisponible, costoUnitarioSoles, proveedor?: { id, name }, responsable: string, fechaIngreso }`.

| Ruta | Roles | Notas |
|---|---|---|
| `GET /lotes?productId=&origen=` | admin, taller | Filtros opcionales. Orden: `fechaIngreso` desc. |
| `GET /lotes/producto/{productId}` | admin, taller | Orden **FIFO**: `fechaIngreso` asc, luego `id` asc. |

**No hay `POST /lotes` público**: los lotes nacen de compras, entradas, importaciones y de la apertura inicial.

### 7.6 Entradas y compras

Tipo `StockEntry`: `{ id, productId, quantity, createdAt, proveedorId?: number, responsable?: string }`.

| Método y ruta | Roles | Request | Comportamiento |
|---|---|---|---|
| `GET /entradas` | admin, taller | — | Historial, más reciente primero. |
| `POST /entradas` | taller | `{ productId, quantity, notas? }` | **Entrada de producción.** Origen `entrada`. Costo del lote = **costo promedio ponderado actual** del producto (0 si no tiene stock); no altera el costo promedio. Motivo por defecto: `"Producción del taller"`. |
| `POST /compras` | admin | `{ productId, quantity, proveedorId?, costoUnitarioSoles?, notas? }` | **Compra a proveedor nacional.** Origen `compra`. `quantity > 0`; `costoUnitarioSoles ≥ 0` si viene; si no viene **y el producto no tiene lotes** → 400 `"El costo de compra es obligatorio cuando el producto aún no tiene stock"`; si no viene y sí tiene lotes, usa el promedio ponderado. `proveedorId` inexistente → 404 `"Proveedor no encontrado"`. Motivo por defecto: `"Compra a proveedor"`. |

En ambos: `responsable` sale del **token**, no del body. Devuelven el `StockEntry` creado (201). Efectos, todo en una transacción: crear lote → crear `stock_entry` → recalcular stock y costo del producto → insertar fila en el ledger con `movementType = "entrada"` (**tanto producción como compra usan `"entrada"`** en el ledger), `quantity` positiva, `unitSoldPrice = salePrice` del producto, `unitCostPrice = costo del lote`, `proveedor = nombre del proveedor`, `reason = notas ?? "Registro de inventario"`.

### 7.7 Mermas (`/mermas`)

Tipo `Merma`: `{ id, productId, quantity, motivo, detalle?, responsable, createdAt }`.

| Método y ruta | Roles | Request |
|---|---|---|
| `GET /mermas` | admin, taller | — |
| `POST /mermas` | taller | `{ productId, quantity, motivo, detalle? }` |

Reglas: `quantity > 0`; `motivo` debe ser uno de: `"Rotura o daño durante pulido"`, `"Error de producción"`, `"Pérdida o extravío"`, `"Defecto de calidad"`, `"Otro"`. Consume stock con **FIFO**; si no alcanza → 409 `"Stock insuficiente: hay X y se requieren Y"` y **no se registra nada**. Ledger: `movementType = "merma"`, `quantity` **negativa**, `wasteType = motivo`, `reason = detalle`, `unitSoldPrice = salePrice`, `unitCostPrice = costo promedio FIFO consumido`.

### 7.8 Ventas (`/ventas`)

Tipo `Venta`:
```
{ id, folio: "BLT-0001", items: [{ productId, name, sku, unitType, unitPrice, quantity }],
  tipoVenta, metodoPago, subtotal, total, pagoCon?, vuelto?, responsable, createdAt }
```

| Método y ruta | Roles | Notas |
|---|---|---|
| `GET /ventas` | admin | Todas, más reciente primero. |
| `GET /ventas/mias` | vendedor | Solo las del usuario del token (filtrar por **id de usuario**, no por nombre). |
| `POST /ventas` | admin, vendedor | Registra la venta (abajo). |

Request de `POST /ventas`: `{ items: [{ productId, quantity }], tipoVenta, metodoPago, pagoCon? }`.
(El front hoy manda también `name`, `sku`, `unitType`, `unitPrice`, `vuelto`: **el servidor los ignora y los recalcula**; nunca confiar en un precio enviado por el cliente.)

Reglas:
1. `tipoVenta ∈ {tienda, feria, digital, otro}`; `metodoPago ∈ {efectivo, billetera-digital}`.
2. Cada producto debe existir y estar **activo**; `quantity > 0`; para `UNIDAD` recomendado exigir enteros.
3. Precio unitario = `sale_price` actual en BD. `subtotal = Σ unitPrice × quantity`; **`total = subtotal`** (hoy el front no aplica IGV; ver decisiones abiertas).
4. Si `metodoPago = "efectivo"`: `pagoCon` es obligatorio y `≥ total`; `vuelto = pagoCon − total` calculado en el servidor. Si es billetera digital: `pagoCon` y `vuelto` quedan null.
5. Por cada ítem, consumir stock con **FIFO** y calcular `unitCostPrice = costoConsumoTotal / quantity` (round2). Si un ítem no alcanza → 409 `"Stock insuficiente: ..."` y **no se guarda nada** (todo o nada).
6. Guardar `sale_items` como snapshot. Ledger: **una fila por ítem**, `movementType = "venta"`, `quantity` **negativa**, `unitSoldPrice = unitPrice`, `unitCostPrice` FIFO, `saleGroupId = id de la venta`.
7. `folio = "BLT-" + id con 4 dígitos` (ej. `BLT-0004`), único. Insertar la venta, `flush()` para obtener el id y asignar el folio dentro de la misma transacción.
8. `responsable` = nombre del usuario del token.

### 7.9 Movimientos (`GET /movimientos`) — solo admin

Devuelve el ledger enriquecido (`InventoryMovement`):
```
{ id, productId, responsable, movementType, quantity, createdAt, reason?, unitSoldPrice?, unitCostPrice?,
  wasteType?, saleGroupId?, proveedor?, folio?, unitPriceUSD?, tipoCambio?,
  productName, sku, unitType, tipoVenta? }
```
- `productName`, `sku`, `unitType` vienen de un JOIN con `products` (si el producto ya no existe: `"Producto no disponible"`, `"—"`, `"UNIDAD"`).
- `tipoVenta`: para movimientos de venta, el mock lo devuelve **como etiqueta legible** (`"Tienda"`, `"Feria"`, `"Digital"`, `"Otro"`). Mantener eso para no tocar el front. `folio`: el del movimiento o el de la venta asociada.
- Orden: `createdAt` desc. Sin paginación en v1.
- **Solo lectura.** No existen `POST/PUT/DELETE` sobre el ledger; solo lo escriben los servicios de inventario.

### 7.10 Comercio exterior (`/comercio-exterior`) — solo admin

Tipo `OperacionComercioExterior`:
```
{ id, folio, fecha, tipo: "importacion"|"exportacion",
  socioComercial: { id, nombre, pais }, incoterm?, medioTransporte?, tipoCambio,
  lineas: [{ producto: { id, name, sku, unitType }, cantidad, precioUSD, subtotalUSD }],
  subtotalUSD, totalUSD, totalPEN, responsable, notas?, createdAt }
```

| Método y ruta | Notas |
|---|---|
| `GET /comercio-exterior/operaciones` | `fecha` desc, luego `id` desc. |
| `POST /comercio-exterior/operaciones` | Body: `{ fecha (YYYY-MM-DD), tipo, socioComercialId, incoterm?, medioTransporte?, tipoCambio (>0), notas?, lineas: [{ productoId, cantidad (>0), precioUSD (≥0) }] (mínimo 1) }`. El front manda además `responsable`: **ignorarlo y usar el usuario del token**. |

Reglas:
- `incoterm ∈ {EXW, FOB, CIF, DAP, DDP}`; `medioTransporte ∈ {maritimo, aereo, terrestre}`.
- Cálculo: `subtotalUSD` por línea = `cantidad × precioUSD`; `subtotalUSD` total = suma; `totalUSD = subtotalUSD`; `totalPEN = totalUSD × tipoCambio`. **Replicar exactamente** `calcularSubtotalLinea` y `calcularTotales` de `features/comercio-exterior/utils.ts`.
- **Importación:** por cada línea, crear un lote origen `importacion` con costo `round2(precioUSD × tipoCambio)`, socio como proveedor; ledger `movementType = "importacion"`, `quantity` **positiva**, `unitSoldPrice = salePrice`, `unitCostPrice = round2(precioUSD × tipoCambio)`, `proveedor = socio.nombre`, `reason = socio.pais`, `folio`, `unitPriceUSD`, `tipoCambio`.
- **Exportación:** por cada línea, consumir FIFO; ledger `movementType = "exportacion"`, `quantity` **negativa**, `unitSoldPrice = round2(precioUSD × tipoCambio)`, `unitCostPrice = costo FIFO`, mismos `proveedor/reason/folio/unitPriceUSD/tipoCambio`. Si alguna línea no alcanza → 409 y **no se guarda nada**.
- Recalcular stock y costo de cada producto afectado. Respuesta 201 con la operación completa.

### 7.11 Lo que NO necesita endpoint (por ahora)

- **Alertas:** el front las calcula desde `GET /productos` (stock bajo, agotado, inactivo).
- **Etiquetas QR:** se generan en el navegador; el QR codifica el **SKU**. El POS busca el producto por SKU en la lista ya cargada.
- **Reportes** (`/reportes` está en el menú del admin pero **no tiene página**): fuera del alcance.
- **Dashboard:** hoy calcula KPIs desde `GET /movimientos` y **tiene cifras y gráficos hardcodeados** (ventas de sept, top 5, evolución semanal). Ver Fase 9 (opcional).

---

## 8. Motor de inventario (núcleo del sistema)

Es lo más delicado. Va en `servicios/inventario.py` como funciones puras + funciones transaccionales, y es lo primero que se prueba. Replica `features/inventario/utils.ts` y `services/lotes.service.ts`.

**Conceptos**
- Cada ingreso de stock crea un **lote** (`initial_qty`, `available_qty`, `unit_cost_pen`, `received_at`).
- El stock del producto **siempre** es `Σ available_qty` de sus lotes (redondeado a 2 decimales). `products.current_stock` es una copia derivada: se recalcula **en la misma transacción** tras cada cambio de lotes.
- `products.cost_price` = **costo promedio ponderado** de los lotes con stock disponible: `Σ(available × unit_cost) / Σ available`. Si el stock queda en 0, el `cost_price` **no se modifica**.

**Funciones a implementar (equivalentes a las del front)**
- `round2(x)` — half-up, con `Decimal`.
- `validar_cantidad_positiva(q)` — error `"La cantidad debe ser mayor a 0"`.
- `validar_costo_no_negativo(c)` — error `"El costo no puede ser negativo"`.
- `costo_promedio_ponderado(lotes)`.
- `asignar_consumo_fifo(lotes, cantidad)` → lista de `{ lote_id, cantidad, costo_unitario }`; lotes ordenados por `received_at` asc, luego `id` asc; ignora lotes con `available_qty = 0`.
- `costo_consumo_total(detalle)` = `round2(Σ cantidad × costo_unitario)`.
- `ingresar_lote(...)`, `consumir_lotes(producto_id, cantidad)`, `sincronizar_stock_producto(producto_id)`.

**Concurrencia (obligatorio):** dos ventas simultáneas no pueden gastar el mismo stock. Dentro de la transacción, bloquear los lotes involucrados con `SELECT ... FOR UPDATE`, ordenados por `product_id` (evita deadlocks al vender varios productos) y luego por `received_at, id`.

**Apertura inicial:** para los productos que ya existan en BD con stock, crear un lote `apertura` por producto (código `LOTE-000N`, responsable `"Sistema"`, costo = `cost_price` actual) mediante una migración de datos o un script idempotente, de modo que `current_stock = Σ lotes` desde el primer día.

**Códigos de lote:** `LOTE-0001`, `LOTE-0002`… correlativo global, único.

**Prueba de consistencia:** un test/script que verifique que, para todos los productos, `current_stock == Σ lots.available_qty`.

---

## 9. Decisiones de implementación y trampas conocidas

1. **Estado del stock "derivado":** el cliente nunca escribe `currentStock`/`costPrice`.
2. **Transacción por request de escritura:** una sola `AsyncSession` por request. **No usar `async with db.begin()`**: `usuario_actual` ya consultó la BD con esa sesión y SQLAlchemy 2 abre la transacción automáticamente (daría `A transaction is already begun`). En su lugar: los servicios **no hacen `commit`** (usan `flush()` cuando necesitan ids); el router de escritura hace `await db.commit()` explícito tras llamar al servicio y antes de devolver la respuesta; `get_db` hace `rollback` ante cualquier excepción. Crear el sessionmaker con `expire_on_commit=False` para poder serializar los objetos después del commit. Los `SELECT ... FOR UPDATE` viven en esa misma transacción.
3. **`get_db`** ya existe; no crear sesiones nuevas dentro de los servicios.
4. **Supabase pooler:** la URL actual usa el puerto 5432 (session pooler), compatible con asyncpg. Si se cambia al 6543 (transaction pooler), hay que crear el engine con `connect_args={"statement_cache_size": 0}`.
5. **`declarative_base` está en `bd/session.py` y `bd/base.py` está vacío:** mover `Base` a `bd/base.py`, importar allí todos los modelos y apuntar Alembic a `Base.metadata`.
6. **No usar `Base.metadata.create_all`** en producción; todo por Alembic.
7. **Ids de usuario como string** en las respuestas (el mock usa UUID string; la BD real usa entero).
8. **`responsable` siempre desde el token**, nunca desde el body, en entradas, compras, mermas, ventas y comercio exterior.
9. **Snapshots:** `sale_items` y `foreign_trade_lines` guardan nombre/SKU/unidad/precio al momento de la operación.
10. **Folios:** boletas `BLT-####` = id de la venta. Comercio exterior: el mock **es inconsistente** (los datos de ejemplo usan contador por tipo: EXP-0001, IMP-0001, EXP-0002, IMP-0002; pero al registrar usa el id global). Propuesta: **contador independiente por tipo** con `SELECT ... FOR UPDATE` sobre una tabla de contadores, para que EXP e IMP tengan su propia secuencia sin duplicados.
11. **Email y SKU** se comparan sin distinguir mayúsculas (índices únicos sobre `lower(...)`).
12. **Costo visible para el vendedor:** `Product` incluye `costPrice` y el vendedor/taller puede leer productos. Ver decisiones abiertas.
13. **Zona horaria:** guardar todo en UTC. El "hoy" y "esta semana" de las métricas los calcula el front en hora local.

---

## 10. Configuración (`.env.example`)

```
DATABASE_URL=postgresql+asyncpg://USUARIO:CLAVE@HOST:5432/postgres
SECRET_KEY=
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=480
CORS_ORIGINS=http://localhost:3000
```

`core/config.py` con `pydantic-settings`; la app **no arranca** si falta `DATABASE_URL` o `SECRET_KEY`. Verificar que `.env` esté en `.gitignore`.

---

## 11. Pruebas mínimas obligatorias

Usar `pytest` + `pytest-asyncio` + `httpx.AsyncClient`, con una BD de prueba separada (nunca la de producción).

**Motor de inventario (unitarias, sin BD):** `round2` half-up; FIFO con 2 y 3 lotes (consume el más antiguo primero y cruza lotes); FIFO con stock insuficiente; costo promedio ponderado; stock cero conserva el último costo.

**Integración:**
1. Login correcto por cada rol; email/contraseña mal → 401; usuario inactivo → 403; token expirado → 401.
2. Matriz de permisos (sección 6): un test parametrizado que verifica 403 para cada combinación rol/endpoint no permitida.
3. Producto: crear (stock y costo forzados a 0), SKU duplicado → 409, activar con precio 0 → error, borrar con movimientos → 409.
4. Compra de un producto sin stock y sin costo → 400 con el mensaje exacto; con costo → crea lote, stock y costo actualizados, fila `entrada` en el ledger.
5. Entrada de producción usa el costo promedio y no lo altera.
6. Venta: descuenta stock FIFO, `unitCostPrice` correcto, una fila de ledger por ítem, `saleGroupId`, folio; efectivo con `pagoCon < total` → error; **stock insuficiente en el 2.º ítem no descuenta el 1.º** (atomicidad).
7. Merma con motivo inválido → error; merma que excede stock → 409.
8. Importación crea lote con costo `precioUSD × tipoCambio`; exportación descuenta y guarda `unitSoldPrice` en soles.
9. `GET /ventas/mias` solo devuelve las del usuario.
10. **Concurrencia:** dos ventas simultáneas del último stock → una funciona, la otra 409.
11. **Formato:** ningún número llega como string; todos los errores tienen `detail` de tipo texto (incluido el 422).

---

## 12. Plan de trabajo por fases (prompts para Copilot)

> Plantilla para cada fase: *"Lee `docs/GUIA_BACKEND.md` (secciones 0, 4 y las que se indican) y los archivos del front citados. Implementa SOLO la Fase N. No toques otras fases. Al terminar, ejecuta los tests y lista qué quedó pendiente."*

| Fase | Contenido | Secciones | Aceptación |
|---|---|---|---|
| **0. Saneamiento** | Config por `.env`, rotar credenciales, CORS, limpiar `requirements.txt`, renombrar enum de roles, reorganizar carpetas (`api/deps.py`, `api/v1/auth.py`), Alembic inicializado, handlers de errores (`detail` siempre texto). | 2, 3, 4, 10 | La app arranca solo con `.env`; no queda ningún secreto en el código (`git grep` de la clave y de la URL vieja devuelve vacío; el historial de git no se reescribe, por eso el humano rota las credenciales). |
| **1. Base de datos** | Lectura de `docs/schema.sql` (esquema real); modelos SQLAlchemy y migración Alembic de las tablas de la sección 5 sin borrar datos; seed de categorías/proveedores/socios si faltan. | 5 | `alembic upgrade head` limpio sobre una copia de la BD; modelos coinciden con las tablas. |
| **2. Auth y usuarios** | `POST /auth/login`, `GET /auth/me`, `requiere_roles`, CRUD `/usuarios` con reglas de borrado. | 6, 7.1, 7.2 | Tests 1 y matriz de permisos de estos endpoints en verde. El front puede iniciar sesión con los 3 roles. |
| **3. Catálogos y productos** | `/categorias`, `/proveedores`, `/comercio-exterior/socios-comerciales`, CRUD `/productos`. | 7.3, 7.4 | Test 3 en verde; pantalla Productos del front funciona contra el backend. |
| **4. Motor de inventario** | `servicios/inventario.py` completo + tests unitarios + migración de apertura + `GET /lotes`. | 8, 7.5 | Tests de motor y de consistencia en verde. **No se avanza sin esto.** |
| **5. Entradas, compras y mermas** | `/entradas`, `/compras`, `/mermas` con ledger. | 7.6, 7.7 | Tests 4, 5, 7 en verde. |
| **6. Ventas** | `/ventas`, `/ventas/mias`, folio, snapshot, atomicidad y concurrencia. | 7.8 | Tests 6, 9, 10 en verde; el POS registra ventas reales. |
| **7. Movimientos** | `GET /movimientos` con el enriquecimiento descrito. | 7.9 | El listado coincide con lo que dejan las fases 5 y 6. |
| **8. Comercio exterior** | Operaciones de importación/exportación, folios por tipo. | 7.10 | Test 8 en verde. |
| **9. Dashboard (opcional)** | `GET /dashboard/resumen?periodo=` con ventas del mes, promedio por venta, piezas vendidas, margen bruto, serie semanal, top 5 productos, alertas de stock. Definir el contrato **junto con el front** antes de programar. | 7.11 | El dashboard deja de usar cifras fijas. |
| **10. Cierre** | Documentación OpenAPI revisada, README real, script de consistencia, checklist de despliegue, logs. | — | README permite levantar todo desde cero. |

**Prueba de humo final (con el front conectado):** login con los 3 roles → crear producto → compra → entrada de taller → venta en efectivo con vuelto → venta con billetera digital → merma → importación y exportación → revisar `Movimientos` y que el stock de cada producto cuadre.

---

## 13. Front: no se modifica desde este repositorio

Copilot **no toca** `eip-proyecto-frontend`. Los cambios del front (Axios con Bearer, AuthProvider, reemplazo de mocks) los hace una persona aparte cuando el backend esté listo; están listados en `docs/FRONT_CAMBIOS_PENDIENTES.md`.

---

## 14. Decisiones

### Ya decididas (Copilot las aplica sin preguntar)

| # | Tema | Decisión |
|---|---|---|
| 1 | Borrado | Usuarios y productos con historial **no se borran** (409); se desactivan. |
| 2 | Sesión | JWT de 480 min, sin refresh token. |
| 3 | Folios de comercio exterior | Contador independiente por tipo (`EXP-0001`, `IMP-0001`) con `SELECT ... FOR UPDATE`. |
| 4 | Login | Clave `accessToken` y `tokenType`. |
| 5 | Esquema de BD | Se toma de `docs/schema.sql`. |
| 6 | Cantidades en `UNIDAD` | Deben ser enteras. |

### Abiertas (no bloquean: implementar el comportamiento por defecto y dejar `# TODO(decisión):`)

| # | Tema | Comportamiento por defecto |
|---|---|---|
| A | IGV en ventas | `total = subtotal` (sin impuesto), como el front. La boleta es un comprobante **interno**, no comprobante electrónico SUNAT. |
| B | `costPrice` visible a vendedor y taller | Se devuelve a todos los roles (igual que el front). Centralizarlo en **un solo esquema de respuesta** para poder ocultarlo después con un cambio mínimo. |
