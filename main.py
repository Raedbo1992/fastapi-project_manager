from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from app.controller.routes import router     
from starlette.middleware.sessions import SessionMiddleware
import os
from pathlib import Path

app = FastAPI(title="Project Manager API")

# ========== CONFIGURACIÓN CRÍTICA PARA RAILWAY ==========

# Obtener path ABSOLUTO a los directorios
BASE_DIR = Path(__file__).resolve().parent  # Raíz del proyecto
STATIC_DIR = BASE_DIR / "app" / "static"
TEMPLATES_DIR = BASE_DIR / "app" / "templates"

print(f"📁 BASE_DIR: {BASE_DIR}")
print(f"📁 STATIC_DIR: {STATIC_DIR}")
print(f"📁 TEMPLATES_DIR: {TEMPLATES_DIR}")
print(f"📁 Existe static?: {STATIC_DIR.exists()}")
print(f"📁 Existe templates?: {TEMPLATES_DIR.exists()}")

# Configurar templates Jinja2
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Montar archivos estáticos CORRECTAMENTE
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    print("✅ Archivos estáticos montados en /static")
else:
    print("⚠️  Directorio static no encontrado")

# Middleware de sesión
secret_key = os.getenv("SECRET_KEY", "clave_temporal_123")
app.add_middleware(SessionMiddleware, secret_key=secret_key)

# Incluir rutas del controlador
app.include_router(router)

# ========== RUTAS PARA SERVER HTML ==========

@app.get("/", response_class=HTMLResponse)
async def serve_home(request: Request):
    """Sirve la página principal"""
    try:
        return templates.TemplateResponse(
            "dashboard.html",  # O el nombre de tu template principal
            {"request": request}
        )
    except Exception as e:
        return HTMLResponse(f"<h1>Error cargando template</h1><p>{str(e)}</p>")

@app.get("/login", response_class=HTMLResponse)
async def serve_login(request: Request):
    """Sirve página de login"""
    try:
        return templates.TemplateResponse(
            "login.html",
            {"request": request}
        )
    except:
        return HTMLResponse("<h1>Login page</h1>")

# Health check
@app.get("/health")
async def health_check(request: Request):
    import datetime
    return {
        "status": "healthy",
        "message": "FastAPI is running",
        "timestamp": datetime.datetime.now().isoformat(),
        "static_files": str(STATIC_DIR.exists()),
        "templates": str(TEMPLATES_DIR.exists()),
        "base_dir": str(BASE_DIR)
    }

print("✅ Aplicación FastAPI configurada para Railway")



@app.get("/setup-database")
async def setup_database():
    """Endpoint para configurar la base de datos"""
    import pymysql
    
    try:
        # Conectar como root
        conn = pymysql.connect(
            host='mysql.railway.internal',  # INTERNO en Railway
            user='root',
            password='xCFHuaDUxwMaJpmTUcMmahxhtCvRzUAn',
            database='mysql'  # Conectar a la BD system
        )
        
        with conn.cursor() as cursor:
            # 1. Crear base de datos si no existe
            cursor.execute("CREATE DATABASE IF NOT EXISTS project_manager")
            
            # 2. Dar permisos a root desde cualquier IP
            cursor.execute("""
                GRANT ALL PRIVILEGES ON project_manager.* 
                TO 'root'@'%' 
                IDENTIFIED BY 'xCFHuaDUxwMaJpmTUcMmahxhtCvRzUAn'
            """)
            
            # 3. Crear usuario para DBeaver
            cursor.execute("""
                CREATE USER IF NOT EXISTS 'dbeaver'@'%' 
                IDENTIFIED BY 'DbeaverPass123!'
            """)
            
            # 4. Dar permisos al usuario DBeaver
            cursor.execute("""
                GRANT ALL PRIVILEGES ON project_manager.* 
                TO 'dbeaver'@'%'
            """)
            
            # 5. Aplicar cambios
            cursor.execute("FLUSH PRIVILEGES")
            
            # 6. Crear tablas básicas
            cursor.execute("USE project_manager")
            
            # Tabla usuarios
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS usuarios (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    password VARCHAR(255) NOT NULL,
                    nombre VARCHAR(100) NOT NULL,
                    email VARCHAR(100),
                    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        
        conn.commit()
        conn.close()
        
        return {
            "status": "success",
            "message": "Base de datos configurada",
            "connections": {
                "dbeaver": {
                    "host": "gondola.proxy.rlwy.net",
                    "port": 31118,
                    "user": "dbeaver",
                    "password": "DbeaverPass123!",
                    "database": "project_manager"
                },
                "root": {
                    "host": "gondola.proxy.rlwy.net", 
                    "port": 31118,
                    "user": "root",
                    "password": "xCFHuaDUxwMaJpmTUcMmahxhtCvRzUAn",
                    "database": "project_manager"
                }
            }
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}