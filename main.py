from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.controller.routes import router     
from starlette.middleware.sessions import SessionMiddleware
app = FastAPI()

# Montar carpeta estática
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# 🔐 Clave secreta para cifrar la sesión (cámbiala por algo más seguro en producción)
app.add_middleware(SessionMiddleware, secret_key='supersecreto123')
# Incluir rutas
app.include_router(router)
 