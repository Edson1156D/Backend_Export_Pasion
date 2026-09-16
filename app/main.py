from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
 
from app.api import dependencias as login

 
app = FastAPI(title="Sistema Inventario - Backend")
 
# Permite que React (corriendo en otro puerto) pueda llamar a este backend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # dirección típica de Vite
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
 
app.include_router(login.router)

 
 
@app.get("/")
async def raiz():
    """Ruta simple para confirmar que el servidor está corriendo."""
    return {"mensaje": "El backend está funcionando 🚀"}