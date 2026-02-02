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
        from app.schema.models import Ingreso, Gasto, Categoria
        from sqlalchemy import func, extract
        from datetime import datetime
        
        db = SessionLocal()
        
        # Obtener mes y año actual
        now = datetime.now()
        mes_actual = now.month
        anio_actual = now.year
        
        print(f"📊 Calculando stats para usuario {user.username} (ID: {user.id})")
        print(f"📅 Mes actual: {mes_actual}, Año: {anio_actual}")
        
        # ========================================
        # CALCULAR TOTALES DEL MES ACTUAL
        # Nota: La columna es 'valor', NO 'monto'
        # ========================================
        
        total_ingresos = db.query(func.sum(Ingreso.valor)).filter(
            Ingreso.usuario_id == user.id,
            extract('month', Ingreso.fecha) == mes_actual,
            extract('year', Ingreso.fecha) == anio_actual
        ).scalar() or 0
        
        print(f"✅ Total ingresos mes actual: ${total_ingresos}")
        
        # Para Gasto, la columna es 'valor' y la fecha es 'fecha_limite'
        total_gastos = db.query(func.sum(Gasto.valor)).filter(
            Gasto.usuario_id == user.id,
            extract('month', Gasto.fecha_limite) == mes_actual,
            extract('year', Gasto.fecha_limite) == anio_actual
        ).scalar() or 0
        
        print(f"✅ Total gastos mes actual: ${total_gastos}")
        
        saldo_disponible = total_ingresos - total_gastos
        print(f"✅ Saldo disponible: ${saldo_disponible}")
        
        # ========================================
        # GASTOS POR CATEGORÍA
        # ========================================
        
        gastos_categoria = db.query(
            Categoria.nombre,
            func.sum(Gasto.valor).label('total')
        ).join(
            Gasto, Gasto.categoria_id == Categoria.id
        ).filter(
            Gasto.usuario_id == user.id,
            extract('month', Gasto.fecha_limite) == mes_actual,
            extract('year', Gasto.fecha_limite) == anio_actual
        ).group_by(Categoria.nombre).all()
        
        gastos_por_categoria = {cat: float(total) for cat, total in gastos_categoria}
        
        if not gastos_por_categoria:
            gastos_por_categoria = {"Sin gastos": 0}
        
        print(f"✅ Gastos por categoría: {gastos_por_categoria}")
        
        # ========================================
        # EVOLUCIÓN MENSUAL (últimos 6 meses)
        # ========================================
        
        labels = []
        ingresos_evolucion = []
        gastos_evolucion = []
        
        try:
            from dateutil.relativedelta import relativedelta
            
            for i in range(5, -1, -1):
                fecha = now - relativedelta(months=i)
                mes_nombre = fecha.strftime('%B')[:3]  # Ene, Feb, Mar...
                labels.append(mes_nombre)
                
                # Ingresos del mes
                total_ing_mes = db.query(func.sum(Ingreso.valor)).filter(
                    Ingreso.usuario_id == user.id,
                    extract('month', Ingreso.fecha) == fecha.month,
                    extract('year', Ingreso.fecha) == fecha.year
                ).scalar() or 0
                
                ingresos_evolucion.append(float(total_ing_mes))
                
                # Gastos del mes
                total_gas_mes = db.query(func.sum(Gasto.valor)).filter(
                    Gasto.usuario_id == user.id,
                    extract('month', Gasto.fecha_limite) == fecha.month,
                    extract('year', Gasto.fecha_limite) == fecha.year
                ).scalar() or 0
                
                gastos_evolucion.append(float(total_gas_mes))
            
            print(f"✅ Evolución mensual calculada: {labels}")
            
        except Exception as e:
            print(f"⚠️  Error calculando evolución: {e}")
            labels = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun']
            ingresos_evolucion = [0, 0, 0, 0, 0, 0]
            gastos_evolucion = [0, 0, 0, 0, 0, 0]
        
        db.close()
        
        # ========================================
        # PREPARAR CONTEXTO PARA EL TEMPLATE
        # ========================================
        
        stats = {
            'total_ingresos': float(total_ingresos),
            'total_gastos': float(total_gastos),
            'saldo_disponible': float(saldo_disponible),
            'gastos_por_categoria': gastos_por_categoria,
            'evolucion_mensual': {
                'labels': labels,
                'ingresos': ingresos_evolucion,
                'gastos': gastos_evolucion
            }
        }
        
        print("✅ Stats preparados correctamente")
        print(f"📊 Dashboard renderizado para {user.nombre}")
        
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
        
        # Retornar dashboard con datos vacíos en caso de error
        stats = {
            'total_ingresos': 0,
            'total_gastos': 0,
            'saldo_disponible': 0,
            'gastos_por_categoria': {"Sin datos": 0},
            'evolucion_mensual': {
                'labels': ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun'],
                'ingresos': [0, 0, 0, 0, 0, 0],
                'gastos': [0, 0, 0, 0, 0, 0]
            }
        }
        
        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "usuario": user,
                "stats": stats,
                "fecha_actual": datetime.now(),
                "error": f"Error cargando datos completos"
            }
        )

# Incluir rutas del controlador (ingresos, gastos, etc.)
app.include_router(router)

# ========== ENDPOINT PARA INSPECCIONAR MODELOS ==========

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