# Prompts por fase (para pegar en Copilot Chat, modo Agent)

## Antes de empezar: el front está en otro repositorio
Opción A (recomendada): abre en VS Code un workspace multi-root con las dos carpetas (`Archivo > Agregar carpeta al área de trabajo`). Siguen siendo repos git independientes; Copilot solo lee el front.

Opción B (si no quieres abrir el front): crea `docs/contrato-front/` en el backend y copia ahí, respetando los nombres, los archivos que cada fase indica leer: los `*.service.ts`, `schemas.ts`, `utils.ts`, `types` y `adapters.ts` de `src/features/*`, y `lib/persistence.ts`. Los prompts dicen "mira en eip-proyecto-frontend/src/features/..."; en ese caso añade al final de cada prompt: *"El front no está en el workspace: lee las copias en docs/contrato-front/."*

## Cómo usarlos
1. Abre un **chat nuevo** por cada fase (así no arrastra contexto viejo).
2. Modo **Agent**, con el modelo más potente que tengas disponible.
3. Adjunta con `#file`: `docs/GUIA_BACKEND.md` y `docs/PROGRESO.md`.
4. Pega el prompt de la fase.
5. Cuando termine: revisa el diff, corre los tests tú mismo, haz commit/PR y **no pases a la siguiente fase hasta que la actual esté en verde**.
6. Si algo falla, usa el prompt de corrección del final.

Todos los prompts empiezan con el mismo encabezado (ya incluido en cada uno).

---

## Fase 0 — Saneamiento

```
Lee .github/copilot-instructions.md, docs/PROGRESO.md y docs/GUIA_BACKEND.md (secciones 0, 2, 3, 4 y 10).
Crea la rama fase-0-saneamiento e implementa SOLO la Fase 0. No toques el front.

Tareas:
1. core/config.py con pydantic-settings leyendo .env (DATABASE_URL, SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, CORS_ORIGINS). La app no arranca si faltan DATABASE_URL o SECRET_KEY.
2. Quitar del código la URL de la BD y la SECRET_KEY hardcodeadas (bd/session.py y core/seguridad.py). No imprimas ni copies sus valores en ningún archivo. Crear .env.example sin valores reales y verificar que .env está en .gitignore.
3. CORS desde CORS_ORIGINS.
4. Renombrar el enum RolUsuario a ADMIN/VENDEDOR/TALLER (mismos valores en BD).
5. Reorganizar: app/api/deps.py (get_db, usuario_actual, requiere_roles(*roles)), app/api/v1/auth.py, app/main.py con include_router(prefix="/api/v1"). Mover Base a bd/base.py.
6. get_db: rollback ante excepción; sessionmaker con expire_on_commit=False (ver sección 9.2 de la guía; NO usar db.begin()).
7. core/errores.py con excepciones de negocio y handlers globales: HTTPException, RequestValidationError (detail siempre texto) y errores no controlados (500 con detail texto).
8. Limpiar requirements.txt según el punto 10 de la sección 2 (bcrypt==3.2.2 y passlib fijos) y requirements-dev.txt con pytest, pytest-asyncio, httpx.
9. Inicializar Alembic (async) apuntando a Base.metadata y a DATABASE_URL del entorno.
10. Tests básicos: la app arranca, el 422 devuelve detail en texto, CORS correcto.

Aceptación: la app arranca solo con .env; git grep de la URL/clave vieja no devuelve nada; tests en verde.
Al terminar actualiza docs/PROGRESO.md y lista lo pendiente.
```

## Fase 1 — Base de datos

Antes: deja `docs/schema.sql` (ver instrucciones en el chat con Claude).

```
Lee .github/copilot-instructions.md, docs/PROGRESO.md y docs/GUIA_BACKEND.md (secciones 0, 4, 5 y 9).
Crea la rama fase-1-base-de-datos e implementa SOLO la Fase 1.

1. Lee docs/schema.sql (esquema real). Haz una tabla comparativa: qué tablas/columnas de la sección 5 ya existen (y con qué nombre), cuáles faltan y cuáles difieren. Respeta los nombres existentes. Pégala en docs/PROGRESO.md.
2. Crea los modelos SQLAlchemy 2 (uno por archivo en app/modelo/) y regístralos en bd/base.py.
3. Crea UNA migración Alembic que agregue/altere lo necesario SIN borrar datos: índices únicos sobre lower(email) y lower(sku), FK con ON DELETE RESTRICT, índices de la sección 5, tabla de contadores para folios de comercio exterior.
4. Seed idempotente de categorías, proveedores y socios comerciales solo si están vacíos (verifica los ids reales de categorías; no los inventes).
5. NO ejecutes migraciones contra la BD real: prueba con una copia o una BD local de prueba.

Aceptación: alembic upgrade head limpio sobre una copia; los modelos coinciden con las tablas.
Al terminar actualiza docs/PROGRESO.md y lista lo pendiente.
```

## Fase 2 — Auth y usuarios

```
Lee .github/copilot-instructions.md, docs/PROGRESO.md y docs/GUIA_BACKEND.md (secciones 0, 4, 6, 7.1 y 7.2).
Mira en eip-proyecto-frontend/src/features/auth y features/users (o el módulo equivalente) cómo se usan los tipos Usuario y User.
Crea la rama fase-2-auth-usuarios e implementa SOLO la Fase 2.

- POST /auth/login y GET /auth/me (sin `role` en el request; accessToken/tokenType; rol en minúsculas; id como string; 403 si inactivo; mismo 401 para email inexistente o clave incorrecta).
- usuario_actual valida token Y consulta la BD (existe y activo). requiere_roles(*roles) con 403 "No tienes permiso para acceder a esto".
- CRUD /usuarios solo admin, con todas las reglas de 7.2 (incluida la protección del último admin en PUT y DELETE).
- Tests: login por cada rol, 401, 403 inactivo, token expirado, matriz de permisos parametrizada de estos endpoints, formato de errores.

Aceptación: tests de esta fase en verde.
Al terminar actualiza docs/PROGRESO.md y lista lo pendiente.
```

## Fase 3 — Catálogos y productos

```
Lee .github/copilot-instructions.md, docs/PROGRESO.md y docs/GUIA_BACKEND.md (secciones 0, 4, 7.3, 7.4 y 14).
Mira en eip-proyecto-frontend/src/features/products (schemas.ts y el service) para replicar validaciones y mensajes.
Crea la rama fase-3-productos e implementa SOLO la Fase 3.

- GET /categorias, GET /proveedores, GET /comercio-exterior/socios-comerciales.
- CRUD /productos con permisos de la matriz. Alta fuerza currentStock=0 y costPrice=0; PUT ignora/rechaza currentStock y costPrice; SKU único sin distinguir mayúsculas; activar con precio 0 falla; DELETE con historial → 409.
- Los números (salePrice, costPrice, currentStock, minStockAlert) salen como number.
- costPrice: comportamiento por defecto de la decisión abierta B, centralizado en un solo esquema de respuesta.
- Tests: el 3 de la sección 11 + formato numérico.

Aceptación: tests en verde.
Al terminar actualiza docs/PROGRESO.md y lista lo pendiente.
```

## Fase 4 — Motor de inventario (la más importante)

```
Lee .github/copilot-instructions.md, docs/PROGRESO.md y docs/GUIA_BACKEND.md (secciones 0, 4, 7.5, 8, 9 y 11).
Lee en eip-proyecto-frontend/src/features/inventario: utils.ts y services/lotes.service.ts (y el ledger.service.ts). Replica su lógica exacta.
Crea la rama fase-4-motor-inventario e implementa SOLO la Fase 4.

Orden obligatorio:
1. Primero escribe los tests unitarios (sin BD) de: round2 half-up, FIFO con 2 y 3 lotes (cruza lotes, más antiguo primero), FIFO con stock insuficiente, costo promedio ponderado, stock cero conserva el último costo, validaciones y sus mensajes exactos.
2. Luego servicios/inventario.py: funciones puras + ingresar_lote, consumir_lotes, sincronizar_stock_producto, con SELECT ... FOR UPDATE ordenado por product_id y luego received_at, id. Códigos LOTE-0001 correlativos y únicos.
3. Migración/script IDEMPOTENTE de apertura: un lote "apertura" por producto con stock existente (responsable "Sistema", costo = cost_price actual).
4. GET /lotes y GET /lotes/producto/{productId} con sus órdenes y permisos.
5. Script/test de consistencia: current_stock == Σ lots.available_qty para todos los productos.

Aceptación: tests del motor y de consistencia en verde. Sin esto no se avanza.
Al terminar actualiza docs/PROGRESO.md y lista lo pendiente.
```

## Fase 5 — Entradas, compras y mermas

```
Lee .github/copilot-instructions.md, docs/PROGRESO.md y docs/GUIA_BACKEND.md (secciones 0, 4, 7.6, 7.7 y 8).
Mira los services de entradas, compras y mermas en eip-proyecto-frontend/src/features/.
Crea la rama fase-5-entradas-compras-mermas e implementa SOLO la Fase 5, usando servicios/inventario.py (no dupliques lógica FIFO).

- GET /entradas, POST /entradas (taller), POST /compras (admin), GET/POST /mermas con permisos exactos.
- Todo en una transacción: lote + stock_entry + recalcular stock/costo + fila en el ledger (movementType "entrada" para producción Y compra).
- responsable siempre desde el token. Mensajes de error exactos.
- Tests 4, 5 y 7 de la sección 11.

Aceptación: tests en verde.
Al terminar actualiza docs/PROGRESO.md y lista lo pendiente.
```

## Fase 6 — Ventas

```
Lee .github/copilot-instructions.md, docs/PROGRESO.md y docs/GUIA_BACKEND.md (secciones 0, 4, 7.8, 8, 11 y 14).
Mira el módulo de ventas/POS en eip-proyecto-frontend/src/features/.
Crea la rama fase-6-ventas e implementa SOLO la Fase 6.

- POST /ventas (admin, vendedor): solo productId y quantity por ítem; el servidor ignora nombre/sku/precio/vuelto enviados y los recalcula; productos activos; UNIDAD con cantidades enteras; efectivo exige pagoCon >= total y calcula vuelto; FIFO por ítem; snapshot en sale_items; una fila de ledger por ítem con quantity negativa y saleGroupId; folio BLT-#### (insert, flush, asignar folio).
- Todo o nada: si el 2.º ítem no alcanza, el 1.º NO se descuenta.
- GET /ventas (admin) y GET /ventas/mias (vendedor, filtrando por id de usuario).
- IGV: comportamiento por defecto de la decisión abierta A.
- Tests 6, 9 y 10 de la sección 11 (incluida concurrencia: dos ventas simultáneas del último stock → una OK, otra 409).

Aceptación: tests en verde.
Al terminar actualiza docs/PROGRESO.md y lista lo pendiente.
```

## Fase 7 — Movimientos

```
Lee .github/copilot-instructions.md, docs/PROGRESO.md y docs/GUIA_BACKEND.md (secciones 0, 4 y 7.9).
Mira el módulo de movimientos y el dashboard en eip-proyecto-frontend/src/features/ para ver qué campos consume.
Crea la rama fase-7-movimientos e implementa SOLO la Fase 7.

GET /movimientos (solo admin), solo lectura, con JOIN a products (productName, sku, unitType; "Producto no disponible"/"—"/"UNIDAD" si no existe), tipoVenta como etiqueta legible ("Tienda", "Feria", "Digital", "Otro") y folio del movimiento o de la venta asociada. Orden createdAt desc. No existen POST/PUT/DELETE sobre el ledger.
Tests: el listado coincide con lo que dejan las fases 5 y 6; ningún número llega como string.

Aceptación: tests en verde.
Al terminar actualiza docs/PROGRESO.md y lista lo pendiente.
```

## Fase 8 — Comercio exterior

```
Lee .github/copilot-instructions.md, docs/PROGRESO.md y docs/GUIA_BACKEND.md (secciones 0, 4, 7.10, 8 y 14).
Lee en eip-proyecto-frontend/src/features/comercio-exterior: utils.ts (calcularSubtotalLinea, calcularTotales) y el service. Replica los cálculos exactos.
Crea la rama fase-8-comercio-exterior e implementa SOLO la Fase 8.

- GET y POST /comercio-exterior/operaciones (solo admin). responsable del token (ignora el del body).
- Importación: lote origen "importacion" con costo round2(precioUSD × tipoCambio). Exportación: FIFO; si alguna línea no alcanza → 409 y no se guarda nada. Ledger con todos los campos de 7.10.
- Folios EXP-0001 / IMP-0001 con contador independiente por tipo (SELECT ... FOR UPDATE sobre la tabla de contadores).
- Tests: el 8 de la sección 11 + folios sin duplicados en concurrencia.

Aceptación: tests en verde.
Al terminar actualiza docs/PROGRESO.md y lista lo pendiente.
```

## Fase 9 — Dashboard (opcional; primero hay que definir el contrato con el front)

```
Lee .github/copilot-instructions.md, docs/PROGRESO.md y docs/GUIA_BACKEND.md (secciones 0, 4 y 7.11).
Lee el dashboard en eip-proyecto-frontend/src/features/ y PROPÓN por escrito (sin implementar todavía) el contrato de GET /dashboard/resumen?periodo=: ventas del mes, promedio por venta, piezas vendidas, margen bruto, serie semanal, top 5 productos y alertas de stock. Espera mi aprobación antes de programar.
```

## Fase 10 — Cierre

```
Lee .github/copilot-instructions.md, docs/PROGRESO.md y docs/GUIA_BACKEND.md (secciones 0, 10, 11 y 12).
Crea la rama fase-10-cierre e implementa SOLO la Fase 10: revisar la documentación OpenAPI, escribir un README real (levantar todo desde cero: venv, .env, alembic upgrade head, uvicorn, tests), script de consistencia de inventario, checklist de despliegue (variables de entorno, CORS, pooler de Supabase) y logging básico sin datos sensibles.
Ejecuta la suite completa y reporta el resultado.
```

---

## Prompt de corrección (cuando algo falla)

```
Los tests de esta fase fallan (pego la salida abajo). Corrige SOLO lo necesario para que pasen, sin cambiar el contrato de docs/GUIA_BACKEND.md ni modificar los tests para forzar el verde. Explica la causa raíz antes de tocar código.

<pega aquí la salida de pytest>
```

## Prompt de revisión al cerrar cada fase (opcional, chat nuevo)

```
Actúa como revisor. Compara lo implementado en la Fase N contra docs/GUIA_BACKEND.md (secciones 4, 6 y las de la fase) y contra el front. Lista: (1) campos, nombres o mensajes que no coinciden, (2) endpoints sin control de rol, (3) operaciones de stock fuera de transacción, (4) números que salgan como string. No cambies código; solo reporta.
```

## Prueba de humo final (con el front conectado)
Login con los 3 roles → crear producto → compra → entrada de taller → venta en efectivo con vuelto → venta con billetera digital → merma → importación y exportación → revisar Movimientos y que el stock de cada producto cuadre.
