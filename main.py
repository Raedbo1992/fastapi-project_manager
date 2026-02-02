from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from app.controller.routes import router     
from starlette.middleware.sessions import SessionMiddleware
import os
from pathlib import Path

app = FastAPI(title="Project Manager API")

# ========== CONFIGURACIÓN BÁSICA ==========

# Obtener path ABSOLUTO a los directorios
BASE_DIR = Path(__file__).resolve().parent
APP_DIR = BASE_DIR / "app"
STATIC_DIR = APP_DIR / "static"
TEMPLATES_DIR = APP_DIR / "templates"

print(f"📁 BASE_DIR: {BASE_DIR}")
print(f"📁 APP_DIR: {APP_DIR}")
print(f"📁 STATIC_DIR: {STATIC_DIR}")
print(f"📁 TEMPLATES_DIR: {TEMPLATES_DIR}")

# Configurar templates Jinja2
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Montar archivos estáticos
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    print("✅ Archivos estáticos montados en /static")
else:
    STATIC_DIR.mkdir(parents=True, exist_ok=True)

# Middleware de sesión
secret_key = os.getenv("SECRET_KEY", "clave_temporal_123456")
app.add_middleware(
    SessionMiddleware, 
    secret_key=secret_key, 
    session_cookie="session",
    max_age=3600
)

# Incluir TODAS las rutas del controlador
app.include_router(router)

# ========== RUTAS BÁSICAS SIN DUPLICACIÓN ==========

@app.get("/", response_class=HTMLResponse)
async def serve_home(request: Request):
    """Redirige a login"""
    return RedirectResponse(url="/login", status_code=302)

# Health check
@app.get("/health")
async def health_check():
    import datetime
    return {
        "status": "healthy",
        "message": "FastAPI is running on Railway",
        "timestamp": datetime.datetime.now().isoformat(),
        "environment": os.getenv("RAILWAY_ENVIRONMENT", "development")
    }

# ========== ENDPOINTS DE INICIALIZACIÓN ==========

@app.get("/create-admin")
async def create_admin():
    """Crear usuario administrador inicial"""
    try:
        from app.config.database import SessionLocal
        from app.schema.models import Usuario
        import bcrypt
        
        db = SessionLocal()
        
        # Verificar si ya existe
        existing = db.query(Usuario).filter(Usuario.email == "admin@admin.com").first()
        if existing:
            db.close()
            return {"message": "⚠️ Usuario admin ya existe"}
        
        # Hashear password
        hashed_password = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Crear admin
        admin = Usuario(
            nombre="Administrador",
            email="admin@admin.com",
            username="admin",
            password=hashed_password,
            rol="admin"
        )
        db.add(admin)
        db.commit()
        db.close()
        
        return {
            "message": "✅ Usuario administrador creado",
            "username": "admin",
            "password": "admin123"
        }
    except Exception as e:
        import traceback
        return {
            "error": str(e),
            "message": "❌ Error al crear admin"
        }

@app.get("/drop-and-recreate-db")
async def drop_and_recreate_database():
    """Eliminar y recrear todas las tablas"""
    try:
        from app.config.database import Base, engine
        from sqlalchemy import text
        
        # Desactivar verificación de foreign keys
        with engine.connect() as connection:
            connection.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
            connection.commit()
        
        # Eliminar todas las tablas
        Base.metadata.drop_all(bind=engine)
        
        # Reactivar verificación de foreign keys
        with engine.connect() as connection:
            connection.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))
            connection.commit()
        
        # Recrear todas las tablas
        Base.metadata.create_all(bind=engine)
        
        return {"message": "✅ Base de datos eliminada y recreada correctamente"}
    except Exception as e:
        return {
            "error": str(e), 
            "message": "❌ Error al recrear BD"
        }

print("✅ Aplicación FastAPI configurada correctamente")