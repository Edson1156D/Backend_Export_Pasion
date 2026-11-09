from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
 
from app.api.v1 import analisis, auth, productos, dashboard, movimientos, usuarios, almacenes, ventas, inventario, comercio_exterior
from app.core.config import CORS_ORIGINS

 
app = FastAPI(title="Sistema Inventario - Backend")
 
# Permite que React (corriendo en otro puerto) pueda llamar a este backend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
 
app.include_router(auth.router, prefix="/api/v1")
app.include_router(analisis.router, prefix="/api/v1")
app.include_router(productos.router, prefix="/api/v1")   # ← línea nueva
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(movimientos.router, prefix="/api/v1")   # ← línea nueva
app.include_router(usuarios.router, prefix="/api/v1")   # ← línea nueva
app.include_router(almacenes.router, prefix="/api/v1")   # ← línea nueva
app.include_router(ventas.router, prefix="/api/v1")   # ← línea nueva
app.include_router(inventario.router, prefix="/api/v1")   # ← línea nueva
app.include_router(comercio_exterior.router, prefix="/api/v1")   # ← línea nueva

@app.get("/")
async def raiz():
    """Ruta simple para confirmar que el servidor está corriendo."""
    return {"mensaje": "El backend está funcionando 🚀"}