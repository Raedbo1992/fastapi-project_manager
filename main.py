from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.controller.routes import router
from starlette.middleware.sessions import SessionMiddleware

app = FastAPI(title="Project Manager", version="1.0.0")

# Configurar templates para Jinja2
templates = Jinja2Templates(directory="app/templates")

# Montar archivos estáticos
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Middleware de sesión
app.add_middleware(
    SessionMiddleware, 
    secret_key="supersecreto1234567890abcdef",  # Mejor clave
    max_age=3600  # Sesión de 1 hora
)

# Incluir rutas
app.include_router(router)

# Pasar templates al estado de la app para acceso global
app.state.templates = templates

# Ruta de verificación de salud
@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "Server is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8032, reload=True)