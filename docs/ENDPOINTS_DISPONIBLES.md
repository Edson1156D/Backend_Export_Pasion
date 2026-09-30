# Inventario de endpoints disponibles

Fecha: 2026-09-29  
Alcance: rutas definidas actualmente en `app/api/v1/`, sus tests, permisos, dependencias y forma de respuesta.

La suite completa validada al cierre de la Fase 10 fue `44 passed, 2 skipped`. Los dos skips corresponden a pruebas de concurrencia que requieren PostgreSQL real. Todos los endpoints existentes consultan la BD; no se encontraron respuestas con registros de ejemplo o datos hardcodeados en los routers ni en el servicio del dashboard.

## Auth

| Endpoint | Método | Categoría | Razón / detalle | Fase de origen |
|---|---|---|---|---|
| `/api/v1/auth/login` | POST | ✅ Conectable ya | Tests en `test_fase0.py` y `test_fase2_auth_usuarios.py` en verde. Público, body `{email,password}`, devuelve `accessToken`, `tokenType` y `usuario` con `rol` en minúsculas. Usa `users` real. No declara `response_model`, pero la forma runtime cumple camelCase, sin envoltorio y errores textuales. | Fase 2 |
| `/api/v1/auth/me` | GET | ✅ Conectable ya | Test en `test_fase2_auth_usuarios.py` en verde. `usuario_actual` valida JWT, consulta `users` y exige cuenta activa. Devuelve el usuario directo. No declara `response_model`, pero la forma runtime cumple el contrato. | Fase 2 |

## Usuarios

| Endpoint | Método | Categoría | Razón / detalle | Fase de origen |
|---|---|---|---|---|
| `/api/v1/usuarios` | GET | ✅ Conectable ya | Test de listado y permisos en verde. Solo `admin`; consulta `users`, ordena por creación y devuelve `UsuarioPublico` camelCase. | Fase 2 |
| `/api/v1/usuarios` | POST | ✅ Conectable ya | Test de alta, duplicado y permisos en verde. Solo `admin`; valida email/password/rol, normaliza email y devuelve 201 con `UsuarioPublico`. | Fase 2 |
| `/api/v1/usuarios/{usuario_id}` | PUT | ✅ Conectable ya | Test en verde. Solo `admin`; usa `users`, protege email duplicado y último administrador activo, y no cambia password vacío. | Fase 2 |
| `/api/v1/usuarios/{usuario_id}` | DELETE | ✅ Conectable ya | Tests de borrado, historial y protección del último admin en verde. Solo `admin`; devuelve 204 y usa las FKs/historial reales para decidir conflictos. | Fase 2 |

## Productos

| Endpoint | Método | Categoría | Razón / detalle | Fase de origen |
|---|---|---|---|---|
| `/api/v1/categorias` | GET | ✅ Conectable ya | Test en `test_fase3_productos.py` en verde. Todos los roles; consulta `categories`, response plano camelCase. | Fase 3 |
| `/api/v1/proveedores` | GET | ✅ Conectable ya | Test en verde. Solo `admin` y `taller`; consulta `suppliers`, response `{id,name}`. | Fase 3 |
| `/api/v1/comercio-exterior/socios-comerciales` | GET | ✅ Conectable ya | Test en verde. Solo `admin`; consulta `foreign_partners`, response `{id,nombre,pais}`. | Fase 3 |
| `/api/v1/productos` | GET | 🟡 Conectable con reserva | Tiene control para `admin`, `vendedor` y `taller` y consulta `products` real. La suite no contiene un test HTTP directo del listado; la respuesta sí usa `ProductoPublico`, camelCase y números JSON. | Fase 3 |
| `/api/v1/productos/{producto_id}` | GET | 🟡 Conectable con reserva | Tiene permisos para los tres roles, consulta `products` y devuelve 404 textual si falta. No se localizó test HTTP directo de este GET; response model y serialización cumplen el contrato. | Fase 3 |
| `/api/v1/productos` | POST | ✅ Conectable ya | Tests de alta, permisos, SKU, activación y tipos en verde. Solo `admin`; valida `categories`, fuerza stock/costo a cero y usa `products` real. | Fase 3 |
| `/api/v1/productos/{producto_id}` | PUT | 🟡 Conectable con reserva | Tiene permiso admin, usa BD y protege campos derivados. Hay test del error de activación, pero no una cobertura completa de actualización exitosa, SKU y categoría; el contrato runtime es camelCase y directo. | Fase 3 |
| `/api/v1/productos/{producto_id}` | DELETE | ✅ Conectable ya | Test en verde. Solo `admin`; comprueba historial en lotes/movimientos/ventas, devuelve 409 textual o 204. | Fase 3 |

## Inventario

| Endpoint | Método | Categoría | Razón / detalle | Fase de origen |
|---|---|---|---|---|
| `/api/v1/lotes` | GET | ✅ Conectable ya | Tests de filtros, orden y permisos en verde. `admin`/`taller`; consulta `lots` y relaciones reales, orden reciente. | Fase 4 |
| `/api/v1/lotes/producto/{producto_id}` | GET | ✅ Conectable ya | Test FIFO en verde. `admin`/`taller`; consulta `lots`, ordena por `received_at,id` ascendente y devuelve números camelCase. | Fase 4 |
| `/api/v1/entradas` | GET | ✅ Conectable ya | Tests de listado y permisos en verde. `admin`/`taller`; consulta `stock_entries` y responsable desde BD. | Fase 5 |
| `/api/v1/entradas` | POST | ✅ Conectable ya | Tests en verde. Solo `taller`; depende del motor FIFO/costo de Fase 4, que está implementado y probado, y registra lote, entrada y ledger en una transacción. | Fase 5 |
| `/api/v1/compras` | POST | ✅ Conectable ya | Tests en verde. Solo `admin`; depende del motor de inventario de Fase 4, valida proveedor/costo y actualiza `products`, `lots`, `stock_entries` y ledger de forma transaccional. | Fase 5 |
| `/api/v1/mermas` | GET | ✅ Conectable ya | Tests en verde. `admin`/`taller`; consulta `wastes` y responsables reales, orden reciente. | Fase 5 |
| `/api/v1/mermas` | POST | ✅ Conectable ya | Tests de motivos, stock insuficiente, FIFO, atomicidad y permisos en verde. Solo `taller`; usa lotes reales, ledger y rollback transaccional. | Fase 5 |

No existe `POST /api/v1/lotes`: es intencional. La guía indica que los lotes nacen internamente de compras, entradas, importaciones o apertura inicial.

## Ventas

| Endpoint | Método | Categoría | Razón / detalle | Fase de origen |
|---|---|---|---|---|
| `/api/v1/ventas` | GET | ✅ Conectable ya | Tests de listado y permisos en verde. Solo `admin`; consulta `sales`, `sale_items` y responsables reales, orden reciente. | Fase 6 |
| `/api/v1/ventas/mias` | GET | ✅ Conectable ya | Test en verde. Solo `vendedor`; filtra por `responsable_id` del JWT, no por nombre. | Fase 6 |
| `/api/v1/ventas` | POST | ✅ Conectable ya | Tests de FIFO, recalculo de precios, snapshots, atomicidad, permisos y tipos en verde. `admin`/`vendedor`; depende del motor de Fase 4 y usa `products`, `lots`, `sales`, `sale_items` y ledger reales. La concurrencia queda validada solo en PostgreSQL real, no en SQLite. | Fase 6 |

## Comercio Exterior

| Endpoint | Método | Categoría | Razón / detalle | Fase de origen |
|---|---|---|---|---|
| `/api/v1/comercio-exterior/operaciones` | GET | ✅ Conectable ya | Tests de listado, orden, permisos y tipos en verde. Solo `admin`; consulta operaciones, líneas, socios y responsables reales. | Fase 8 |
| `/api/v1/comercio-exterior/operaciones` | POST | ✅ Conectable ya | Tests de importación/exportación, FIFO, rollback, folios por tipo, permisos y números en verde. Solo `admin`; depende del motor de Fase 4 y usa contadores/BD reales. La concurrencia de folios requiere PostgreSQL real. | Fase 8 |

## Movimientos

| Endpoint | Método | Categoría | Razón / detalle | Fase de origen |
|---|---|---|---|---|
| `/api/v1/movimientos` | GET | ✅ Conectable ya | Tests de enriquecimiento, orden, folio, tipos y permisos en verde. Solo `admin`; consulta el ledger real y hace JOIN con productos/ventas, sin endpoints de escritura. | Fase 7 |

## Dashboard

| Endpoint | Método | Categoría | Razón / detalle | Fase de origen |
|---|---|---|---|---|
| `/api/v1/dashboard/resumen` | GET | 🟡 Conectable con reserva | Tests de KPIs, serie, top, alertas, permisos y periodo en verde. Solo `admin`; consulta ventas, movimientos y productos reales, sin cifras de ejemplo. La reserva es que el dashboard frontend todavía usa cifras/gráficos hardcodeados o movimientos mock y no consume este endpoint; además la Fase 9 fue opcional. | Fase 9 |

No existe `/api/v1/reportes`: la guía lo declara fuera de alcance y sin página funcional.

## Resumen de clasificación

- ✅ **Conectable ya:** 24 endpoints.
- 🟡 **Conectable con reserva:** 4 endpoints: listado de productos, detalle de producto, actualización de producto y dashboard.
- 🔴 **No conectar todavía:** ninguno. No hay rutas activas que dependan de una fase pendiente, carezcan de permisos o usen datos hardcodeados.
- ⬜ **No existe:** `/api/v1/reportes` no se implementó porque está fuera de alcance; `POST /api/v1/lotes` tampoco existe por diseño, ya que los lotes son internos.

## Se puede empezar a integrar ya

### Auth

- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`

### Usuarios

- `GET /api/v1/usuarios`
- `POST /api/v1/usuarios`
- `PUT /api/v1/usuarios/{usuario_id}`
- `DELETE /api/v1/usuarios/{usuario_id}`

### Catalogos y productos

- `GET /api/v1/categorias`
- `GET /api/v1/proveedores`
- `GET /api/v1/comercio-exterior/socios-comerciales`
- `POST /api/v1/productos`
- `DELETE /api/v1/productos/{producto_id}`

### Inventario

- `GET /api/v1/lotes`
- `GET /api/v1/lotes/producto/{producto_id}`
- `GET /api/v1/entradas`
- `POST /api/v1/entradas`
- `POST /api/v1/compras`
- `GET /api/v1/mermas`
- `POST /api/v1/mermas`

### Ventas

- `GET /api/v1/ventas`
- `GET /api/v1/ventas/mias`
- `POST /api/v1/ventas`

### Comercio exterior

- `GET /api/v1/comercio-exterior/operaciones`
- `POST /api/v1/comercio-exterior/operaciones`

### Movimientos

- `GET /api/v1/movimientos`
