# Backend EIP Import & Export Pasion

Backend de gestión de inventario, ventas, mermas y comercio exterior construido
con FastAPI, SQLAlchemy async, PostgreSQL y Alembic.

## Requisitos

- Python 3.11 o superior
- PostgreSQL compatible con `asyncpg` (Supabase funciona con la configuración adecuada del pooler)

## Levantar desde cero

Ejecuta todos los comandos desde `Backend_Export_Pasion/`.

### 1. Crear y activar el entorno

PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Instalar dependencias

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 3. Configurar el entorno

```powershell
Copy-Item .env.example .env
```

Edita `.env` y define `DATABASE_URL` y `SECRET_KEY`. El archivo `.env` no se versiona.
No uses credenciales de producción en una base de pruebas.

### 4. Aplicar migraciones

```bash
alembic upgrade head
```

La migración no reemplaza ni elimina datos existentes. Revisa la base real y ejecuta el script de aperturas únicamente cuando corresponda:

```bash
python -m scripts.crear_aperturas
```

### 5. Iniciar la API

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Documentación interactiva:

- Swagger UI: <http://localhost:8000/docs>
- ReDoc: <http://localhost:8000/redoc>
- Esquema OpenAPI: <http://localhost:8000/openapi.json>

La API usa el prefijo `/api/v1`. El frontend debe usar `http://localhost:8000/api/v1` como URL base.

## Tests

Con el entorno virtual activo:

```bash
pytest
```

Los tests usan una base SQLite aislada en memoria o temporal; nunca apuntes la configuración de pruebas a la base de producción.

## Consistencia del inventario

El script compara `products.current_stock` con la suma de `lots.available_qty` por producto. Usa la misma configuración de base de datos del `.env`:

```bash
python -m scripts.verificar_consistencia
```

Devuelve código `0` si todo cuadra y código `1` si encuentra productos inconsistentes.

## Configuración y seguridad

| Variable | Uso |
|---|---|
| `DATABASE_URL` | URL async de PostgreSQL |
| `SECRET_KEY` | Firma de JWT; usa un secreto nuevo y aleatorio |
| `ALGORITHM` | Algoritmo JWT, normalmente `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Duración del token, por defecto 480 |
| `CORS_ORIGINS` | Orígenes permitidos separados por comas |

Para despliegue, consulta [docs/DEPLOYMENT_CHECKLIST.md](docs/DEPLOYMENT_CHECKLIST.md).
Los logs registran método, ruta, estado y duración, pero no cuerpos, tokens, contraseñas ni cabeceras de autenticación.

## Estructura útil

- `app/api/v1/`: routers HTTP
- `app/servicios/`: reglas de negocio y transacciones
- `app/modelo/`: modelos SQLAlchemy
- `app/esquemas/`: contratos Pydantic camelCase
- `alembic/`: migraciones
- `tests/`: suite de integración y unidad