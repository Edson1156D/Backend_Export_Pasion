# Cambios pendientes en el front (los hace una persona, NO Copilot del backend)

El front es un repositorio separado del backend. Estos cambios se hacen en **su** repo, en una rama propia, cuando el backend esté listo (idealmente después de la Fase 6 para probar el POS real).

1. `lib/axios.ts`: adjuntar `Authorization: Bearer <token>` (hoy está comentado) y, ante un **401**, cerrar sesión y redirigir a `/login`.
2. `AuthProvider`: guardar también el token (hoy solo guarda el usuario en `localStorage`).
3. `features/auth/services/auth.service.ts`: llamar a `POST /auth/login` (hoy usa el mock de usuarios) y leer `accessToken`.
4. Reemplazar cada `*.service.ts` mock por llamadas Axios **manteniendo las mismas firmas** (los hooks no cambian).
5. Eliminar la lógica que hoy corre en el cliente y pasa al servidor: motor de lotes/FIFO, `ledger.service.ts`, `adapters.ts` y `lib/persistence.ts`.
6. `POST /ventas`: enviar solo `productId` y `quantity` por ítem.
7. Mis ventas: usar `GET /ventas/mias` en lugar de filtrar por nombre en el cliente.
8. `.env.local`: `NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1`.
9. Dashboard: conectarlo al endpoint real cuando exista (Fase 9).
10. Backend desplegado: agregar el dominio del front a `CORS_ORIGINS` del backend y apuntar `NEXT_PUBLIC_API_URL` al dominio real del API.
11. Si se decide ocultar `costPrice` a vendedor/taller (decisión abierta B), ajustar el tipo `Product`.
