from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from app.controller.routes import router
import os
from pathlib import Path
from datetime import datetime

app = FastAPI(title="Project Manager API")

# ========== CONFIGURACIÓN CRÍTICA PARA RAILWAY ==========

# Obtener path ABSOLUTO a los directorios
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "app" / "static"
TEMPLATES_DIR = BASE_DIR / "app" / "templates"

print(f"📁 BASE_DIR: {BASE_DIR}")
print(f"📁 STATIC_DIR: {STATIC_DIR}")
print(f"📁 TEMPLATES_DIR: {TEMPLATES_DIR}")
print(f"📁 Existe static?: {STATIC_DIR.exists()}")
print(f"📁 Existe templates?: {TEMPLATES_DIR.exists()}")

# Configurar templates Jinja2
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Montar archivos estáticos ANTES de las rutas
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    print("✅ Archivos estáticos montados en /static")
else:
    print("⚠️  Directorio static no encontrado")

# Middleware de sesión
secret_key = os.getenv("SECRET_KEY", "clave_temporal_123")
app.add_middleware(SessionMiddleware, secret_key=secret_key)

# ========== RUTA RAÍZ SIMPLE ==========

@app.get("/")
async def root(request: Request):
    """Redirige al login - la lógica real está en routes.py"""
    if "usuario_id" in request.session:
        return RedirectResponse(url="/dashboard", status_code=302)
    return RedirectResponse(url="/login", status_code=302)

# ========== INCLUIR TODAS LAS RUTAS DEL ROUTER ==========
# Toda la lógica de autenticación, dashboard, ingresos, gastos, etc.
# está en app/controller/routes.py
app.include_router(router)

# ========== HEALTH CHECK ==========

@app.get("/health")
async def health_check(request: Request):
    """Health check para Railway"""
    return {
        "status": "healthy",
        "message": "FastAPI is running",
        "timestamp": datetime.now().isoformat(),
        "static_files": str(STATIC_DIR.exists()),
        "templates": str(TEMPLATES_DIR.exists()),
        "base_dir": str(BASE_DIR)
    }

# ========== ENDPOINTS DE INICIALIZACIÓN DE BD ==========

@app.get("/drop-and-recreate-db")
async def drop_and_recreate_database():
    """PELIGRO: Elimina TODAS las tablas y las recrea"""
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
        import traceback
        return {
            "error": str(e), 
            "traceback": traceback.format_exc(),
            "message": "❌ Error al recrear BD"
        }

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
        
        # Hashear password con bcrypt
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
            "email": "admin@admin.com",
            "password": "admin123"
        }
    except Exception as e:
        import traceback
        return {
            "error": str(e),
            "traceback": traceback.format_exc(),
            "message": "❌ Error al crear admin"
        }

@app.get("/debug/models")
async def debug_models():
    """Endpoint para ver la estructura de los modelos"""
    try:
        from app.schema.models import Ingreso, Gasto, Usuario, Categoria
        from sqlalchemy import inspect
        
        def get_model_info(model):
            inspector = inspect(model)
            return {
                'table_name': model.__tablename__,
                'columns': [
                    {
                        'name': c.key,
                        'type': str(c.type),
                        'nullable': c.nullable
                    }
                    for c in inspector.columns
                ]
            }
        
        return {
            "usuario": get_model_info(Usuario),
            "categoria": get_model_info(Categoria),
            "ingreso": get_model_info(Ingreso),
            "gasto": get_model_info(Gasto)
        }
    except Exception as e:
        import traceback
        return {
            "error": str(e),
            "traceback": traceback.format_exc()
        }

print("✅ Aplicación FastAPI configurada para Railway")
print("📌 Toda la lógica de negocio está en app/controller/routes.py")