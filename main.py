from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from app.controller.routes import router     
from starlette.middleware.sessions import SessionMiddleware
import os
from pathlib import Path
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware

app = FastAPI(title="Project Manager API")

# ========== CONFIGURACIÓN CORREGIDA PARA RAILWAY ==========

# Obtener path ABSOLUTO a los directorios
BASE_DIR = Path(__file__).resolve().parent
APP_DIR = BASE_DIR / "app"
STATIC_DIR = APP_DIR / "static"
TEMPLATES_DIR = APP_DIR / "templates"

print(f"📁 BASE_DIR: {BASE_DIR}")
print(f"📁 APP_DIR: {APP_DIR}")
print(f"📁 STATIC_DIR: {STATIC_DIR}")
print(f"📁 TEMPLATES_DIR: {TEMPLATES_DIR}")

# Configurar templates Jinja2 con contexto para URLs
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Añadir variable global para URLs base
templates.env.globals["url_base"] = os.getenv("RAILWAY_STATIC_URL", "")

# Middleware para HTTPS en producción
if os.getenv("RAILWAY_ENVIRONMENT") == "production":
    app.add_middleware(HTTPSRedirectMiddleware)

# Montar archivos estáticos
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    print("✅ Archivos estáticos montados en /static")
else:
    STATIC_DIR.mkdir(parents=True, exist_ok=True)

# Middleware de sesión
secret_key = os.getenv("SECRET_KEY")
if not secret_key:
    secret_key = "clave_temporal_123_" + os.urandom(16).hex()
    
app.add_middleware(
    SessionMiddleware, 
    secret_key=secret_key, 
    session_cookie="session",
    same_site="lax",
    https_only=True  # Importante para Railway
)

# Incluir rutas del controlador
app.include_router(router)

# ========== FUNCIÓN PARA GENERAR URLS CORRECTAS ==========

def get_base_url(request: Request):
    """Obtiene la URL base correcta (HTTPS)"""
    if os.getenv("RAILWAY_ENVIRONMENT") == "production":
        # Forzar HTTPS en producción
        base_url = str(request.base_url).replace("http://", "https://")
    else:
        base_url = str(request.base_url)
    return base_url.rstrip("/")

# ========== MIDDLEWARE PARA AÑADIR CONTEXTO ==========

@app.middleware("http")
async def add_https_context(request: Request, call_next):
    """Middleware para añadir contexto HTTPS a las plantillas"""
    response = await call_next(request)
    
    # Si es una respuesta de template, añadir variable
    if hasattr(request.state, "template_context"):
        context = request.state.template_context
        context["base_url"] = get_base_url(request)
        context["is_https"] = request.url.scheme == "https"
    
    return response

# ========== RUTAS PARA SERVER HTML ==========

@app.get("/", response_class=HTMLResponse)
async def serve_home(request: Request):
    """Redirige a login si no está autenticado"""
    if "usuario" not in request.session:
        return RedirectResponse(url="/login", status_code=303)
    
    from app.repository.crud import obtener_usuario_por_id
    from app.config.database import SessionLocal
    
    db = SessionLocal()
    usuario_id = request.session["usuario"]["id"]
    usuario = obtener_usuario_por_id(db, usuario_id)
    db.close()
    
    if usuario:
        from datetime import datetime
        from app.repository.crud import obtener_resumen_financiero
        
        db = SessionLocal()
        stats = obtener_resumen_financiero(db, usuario_id)
        db.close()
        
        # Añadir contexto para URLs
        context = {
            "request": request,
            "usuario": usuario,
            "fecha_actual": datetime.now(),
            "stats": stats,
            "base_url": get_base_url(request),
            "static_path": "/static"  # Ruta relativa directa
        }
        
        # Guardar contexto para middleware
        request.state.template_context = context
        
        return templates.TemplateResponse("dashboard.html", context)
    return RedirectResponse(url="/login")

@app.get("/login", response_class=HTMLResponse)
async def serve_login(request: Request):
    """Sirve página de login"""
    if "usuario" in request.session:
        return RedirectResponse(url="/", status_code=303)
    
    context = {
        "request": request,
        "base_url": get_base_url(request),
        "static_path": "/static"
    }
    request.state.template_context = context
    return templates.TemplateResponse("login.html", context)

# Health check
@app.get("/health")
async def health_check():
    import datetime
    import os
    
    return {
        "status": "healthy",
        "message": "FastAPI is running on Railway",
        "timestamp": datetime.datetime.now().isoformat(),
        "environment": os.getenv("RAILWAY_ENVIRONMENT", "development"),
        "https_enabled": True,
        "static_dir": str(STATIC_DIR)
    }

# ... resto del código igual ...

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
        
        # Hashear password con bcrypt (igual que en crud.py)
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

print("✅ Aplicación FastAPI configurada para Railway")