# Checklist de despliegue

## Antes de desplegar

- [ ] Usar Python 3.11+ y ejecutar `pip install -r requirements.txt`.
- [ ] Configurar `DATABASE_URL` únicamente mediante variables de entorno o un gestor de secretos; nunca incluirla en el repositorio.
- [ ] Generar un `SECRET_KEY` nuevo y privado para el entorno.
- [ ] Confirmar `ALGORITHM` y `ACCESS_TOKEN_EXPIRE_MINUTES`.
- [ ] Definir `CORS_ORIGINS` con los orígenes exactos del frontend, sin usar comodines.
- [ ] Confirmar que `.env` y cualquier archivo con secretos quedan fuera del artefacto y del control de versiones.
- [ ] Revisar una copia de seguridad antes de ejecutar `alembic upgrade head`.
- [ ] Ejecutar las migraciones desde una versión conocida y verificar su estado.
- [ ] Ejecutar `python -m scripts.verificar_consistencia` después de migrar.
- [ ] Ejecutar `pytest` en CI o en el entorno de validación.

## Supabase y pooler

- [ ] Usar el pooler de sesión de Supabase (puerto `5432`) con la URL `postgresql+asyncpg://...` cuando se requieran transacciones normales.
- [ ] Si se usa el pooler transaccional (puerto `6543`), configurar el engine con `statement_cache_size=0` y validar Alembic y concurrencia en ese entorno.
- [ ] No pegar URLs con contraseña en issues, logs, documentación ni comandos compartidos.
- [ ] Verificar que la red del servicio permite conectarse al host de Supabase.
- [ ] Confirmar backups y un procedimiento probado de restauración.

## Arranque y operación

- [ ] Ejecutar `alembic upgrade head` antes de iniciar la nueva versión.
- [ ] Iniciar con un servidor ASGI, por ejemplo: `uvicorn app.main:app --host 0.0.0.0 --port 8000`.
- [ ] Exponer HTTPS mediante el proxy o balanceador de la plataforma.
- [ ] Configurar reinicio automático y un número adecuado de workers según la capacidad de la base de datos.
- [ ] Recoger logs sin cuerpos de requests, tokens ni contraseñas.
- [ ] Vigilar respuestas 5xx, latencia, conexiones agotadas y fallos de migración.

## Smoke test posterior

- [ ] Abrir `/docs` y `/openapi.json`.
- [ ] Iniciar sesión con una cuenta de prueba de cada rol.
- [ ] Verificar que CORS permite al frontend autorizado y rechaza orígenes no autorizados.
- [ ] Crear o consultar un producto de prueba según el entorno.
- [ ] Ejecutar `python -m scripts.verificar_consistencia`.