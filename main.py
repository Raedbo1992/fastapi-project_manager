from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
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

# ========== FUNCIÓN AUXILIAR PARA VERIFICAR SESIÓN ==========
def get_current_user(request: Request):
    """Verifica si hay usuario en sesión"""
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    
    from app.config.database import SessionLocal
    from app.schema.models import Usuario
    
    db = SessionLocal()
    user = db.query(Usuario).filter(Usuario.id == user_id).first()
    db.close()
    return user

# ========== RUTAS DE AUTENTICACIÓN ==========

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Redirige al login o dashboard según sesión"""
    user = get_current_user(request)
    if user:
        return RedirectResponse(url="/dashboard", status_code=302)
    return RedirectResponse(url="/login", status_code=302)

@app.get("/login", response_class=HTMLResponse)
async def serve_login(request: Request):
    """Sirve página de login"""
    try:
        return templates.TemplateResponse(
            "login.html",
            {"request": request}
        )
    except Exception as e:
        return HTMLResponse(f"<h1>Error cargando login</h1><p>{str(e)}</p>")

@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    """Procesa el login"""
    from app.config.database import SessionLocal
    from app.schema.models import Usuario
    import bcrypt
    
    db = SessionLocal()
    
    try:
        # Buscar usuario
        user = db.query(Usuario).filter(Usuario.username == username).first()
        
        if not user:
            db.close()
            return templates.TemplateResponse(
                "login.html",
                {"request": request, "error": "Usuario no encontrado"}
            )
        
        # Verificar password
        if not bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
            db.close()
            return templates.TemplateResponse(
                "login.html",
                {"request": request, "error": "Contraseña incorrecta"}
            )
        
        # Guardar en sesión
        request.session["user_id"] = user.id
        request.session["username"] = user.username
        
        db.close()
        return RedirectResponse(url="/dashboard", status_code=302)
        
    except Exception as e:
        db.close()
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": f"Error: {str(e)}"}
        )

@app.get("/logout")
async def logout(request: Request):
    """Cierra sesión"""
    request.session.clear()
    return RedirectResponse(url="/login", status_code=302)

# ========== DASHBOARD ==========

@app.get("/dashboard", response_class=HTMLResponse)
async def serve_dashboard(request: Request):
    """Sirve el dashboard con datos reales"""
    user = get_current_user(request)
    
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    try:
        from app.config.database import SessionLocal
        from app.schema.models import Ingreso, Gasto
        from sqlalchemy import func, extract
        from datetime import datetime
        
        db = SessionLocal()
        
        # Obtener mes y año actual
        now = datetime.now()
        mes_actual = now.month
        anio_actual = now.year
        
        # Calcular totales del mes actual
        total_ingresos = db.query(func.sum(Ingreso.monto)).filter(
            Ingreso.usuario_id == user.id,
            extract('month', Ingreso.fecha) == mes_actual,
            extract('year', Ingreso.fecha) == anio_actual
        ).scalar() or 0
        
        total_gastos = db.query(func.sum(Gasto.monto)).filter(
            Gasto.usuario_id == user.id,
            extract('month', Gasto.fecha) == mes_actual,
            extract('year', Gasto.fecha) == anio_actual
        ).scalar() or 0
        
        saldo_disponible = total_ingresos - total_gastos
        
        # Gastos por categoría
        gastos_categoria = db.query(
            Gasto.categoria,
            func.sum(Gasto.monto).label('total')
        ).filter(
            Gasto.usuario_id == user.id,
            extract('month', Gasto.fecha) == mes_actual,
            extract('year', Gasto.fecha) == anio_actual
        ).group_by(Gasto.categoria).all()
        
        gastos_por_categoria = {cat: float(total) for cat, total in gastos_categoria}
        
        # Evolución mensual (últimos 6 meses)
        from dateutil.relativedelta import relativedelta
        labels = []
        ingresos_evolucion = []
        
        for i in range(5, -1, -1):
            fecha = now - relativedelta(months=i)
            mes_nombre = fecha.strftime('%B')
            labels.append(mes_nombre)
            
            total_mes = db.query(func.sum(Ingreso.monto)).filter(
                Ingreso.usuario_id == user.id,
                extract('month', Ingreso.fecha) == fecha.month,
                extract('year', Ingreso.fecha) == fecha.year
            ).scalar() or 0
            
            ingresos_evolucion.append(float(total_mes))
        
        db.close()
        
        # Preparar contexto
        stats = {
            'total_ingresos': float(total_ingresos),
            'total_gastos': float(total_gastos),
            'saldo_disponible': float(saldo_disponible),
            'gastos_por_categoria': gastos_por_categoria,
            'evolucion_mensual': {
                'labels': labels,
                'ingresos': ingresos_evolucion
            }
        }
        
        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "usuario": user,
                "stats": stats,
                "fecha_actual": now
            }
        )
        
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"❌ Error en dashboard: {error_detail}")
        return HTMLResponse(f"<h1>Error cargando dashboard</h1><pre>{error_detail}</pre>")

# Incluir rutas del controlador (ingresos, gastos, etc.)
app.include_router(router)

# ========== HEALTH CHECK ==========

@app.get("/health")
async def health_check(request: Request):
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

print("✅ Aplicación FastAPI configurada para Railway")