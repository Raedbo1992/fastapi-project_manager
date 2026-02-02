from fastapi import APIRouter, Query, Request, Form, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date
import bcrypt
from starlette.status import HTTP_303_SEE_OTHER
from app.config.database import get_db
from app.schema import models, schemas
from app.repository import crud
from datetime import datetime
import os
from pathlib import Path

router = APIRouter()

# Configurar templates con path ABSOLUTO
BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Funciones de autenticación
def hashear_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verificar_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

# ========== RUTAS DE AUTENTICACIÓN ==========

@router.get("/login", response_class=HTMLResponse)
def mostrar_login(request: Request):
    """Mostrar página de login"""
    # Si ya está autenticado, redirigir a dashboard
    if "usuario_id" in request.session:
        return RedirectResponse(url="/dashboard", status_code=302)
    
    return templates.TemplateResponse("login.html", {"request": request})

@router.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Procesar inicio de sesión"""
    # Si ya está autenticado, redirigir
    if "usuario_id" in request.session:
        return RedirectResponse(url="/dashboard", status_code=302)
    
    # Buscar usuario
    usuario = crud.obtener_usuario_por_username(db, username)
    
    if usuario and verificar_password(password, usuario.password):
        # Guardar en sesión
        request.session["usuario_id"] = usuario.id
        request.session["usuario_nombre"] = usuario.nombre
        request.session["usuario_username"] = usuario.username
        
        return RedirectResponse(url="/dashboard", status_code=302)
    
    # Credenciales incorrectas
    return templates.TemplateResponse("login.html", {
        "request": request,
        "error": "Credenciales inválidas"
    })

@router.get("/logout")
def logout(request: Request):
    """Cerrar sesión"""
    request.session.clear()
    return RedirectResponse(url="/login", status_code=302)

# ========== RUTAS PROTEGIDAS ==========

def verificar_autenticacion(request: Request):
    """Verificar si el usuario está autenticado"""
    if "usuario_id" not in request.session:
        raise HTTPException(status_code=302, headers={"Location": "/login"})
    return request.session["usuario_id"]

# ========== DASHBOARD ==========

@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    """Dashboard principal"""
    try:
        usuario_id = verificar_autenticacion(request)
        
        usuario = crud.obtener_usuario_por_id(db, usuario_id)
        if not usuario:
            request.session.clear()
            return RedirectResponse(url="/login", status_code=302)
        
        # Obtener estadísticas
        stats = crud.obtener_resumen_financiero(db, usuario_id)
        
        # Si la función no existe, usar esta alternativa
        if not stats:
            stats = {
                "total_ingresos": 0,
                "total_gastos": 0,
                "saldo_disponible": 0,
                "gastos_por_categoria": {},
                "evolucion_mensual": {"labels": [], "ingresos": []}
            }
        
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "usuario": usuario,
            "stats": stats,
            "fecha_actual": datetime.now()
        })
        
    except HTTPException as e:
        if e.status_code == 302:
            return RedirectResponse(url="/login", status_code=302)
        raise e
    except Exception as e:
        print(f"Error en dashboard: {e}")
        return RedirectResponse(url="/login", status_code=302)

# ========== INGRESOS ==========

@router.get("/ingresos", response_class=HTMLResponse)
def listar_ingresos(
    request: Request, 
    db: Session = Depends(get_db), 
    page: int = 1,
    tipo: Optional[str] = None,
    pagado: Optional[bool] = None
):
    """Listar ingresos con paginación"""
    usuario_id = verificar_autenticacion(request)
    
    # Obtener ingresos
    ingresos = crud.obtener_ingresos_usuario(db, usuario_id)
    
    # Calcular totales
    total_ingresos = sum(ing.valor for ing in ingresos if ing.valor)
    
    # Paginación simple
    items_por_pagina = 10
    total_items = len(ingresos)
    total_pages = (total_items + items_por_pagina - 1) // items_por_pagina if total_items > 0 else 1
    
    if page < 1:
        page = 1
    elif page > total_pages and total_pages > 0:
        page = total_pages
    
    start_idx = (page - 1) * items_por_pagina
    end_idx = start_idx + items_por_pagina
    ingresos_pagina = ingresos[start_idx:end_idx]
    
    mensaje = request.session.pop("mensaje", None)
    
    return templates.TemplateResponse("ingresos_listado.html", {
        "request": request,
        "ingresos": ingresos_pagina,
        "total_ingresos": total_ingresos,
        "total_pages": total_pages,
        "current_page": page,
        "filtro_tipo": tipo,
        "filtro_pagado": pagado,
        "mensaje": mensaje
    })

@router.get("/ingresos/nuevo", response_class=HTMLResponse)
@router.get("/ingresos/editar/{ingreso_id}", response_class=HTMLResponse)
def formulario_ingreso(
    request: Request,
    ingreso_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Formulario para crear/editar ingreso"""
    usuario_id = verificar_autenticacion(request)
    
    ingreso = None
    if ingreso_id:
        ingreso = crud.obtener_ingreso(db, ingreso_id)
        if not ingreso or ingreso.usuario_id != usuario_id:
            raise HTTPException(status_code=404, detail="Ingreso no encontrado")
    
    return templates.TemplateResponse("ingreso_form.html", {
        "request": request,
        "ingreso": ingreso
    })

@router.post("/ingresos/guardar")
async def guardar_ingreso(
    request: Request,
    id: Optional[int] = Form(None),
    valor: float = Form(...),
    fecha: str = Form(...),
    notas: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Guardar ingreso (crear o actualizar)"""
    usuario_id = verificar_autenticacion(request)
    
    try:
        fecha_dt = date.fromisoformat(fecha) if fecha else date.today()
        
        ingreso_data = schemas.IngresoCreate(
            valor=valor,
            fecha=fecha_dt,
            notas=notas
        )
        
        if id:
            # Actualizar
            crud.actualizar_ingreso(db, ingreso_id=int(id), ingreso=ingreso_data, usuario_id=usuario_id)
            mensaje = "Ingreso actualizado correctamente"
        else:
            # Crear nuevo
            crud.crear_ingreso(db, ingreso=ingreso_data, usuario_id=usuario_id)
            mensaje = "Ingreso creado correctamente"
        
        request.session['mensaje'] = {
            'tipo': 'exito',
            'titulo': '¡Éxito!',
            'texto': mensaje
        }
    except Exception as e:
        request.session['mensaje'] = {
            'tipo': 'error',
            'titulo': 'Error',
            'texto': f'Ocurrió un error: {str(e)}'
        }
    
    return RedirectResponse(url="/ingresos", status_code=303)

@router.get("/ingresos/eliminar/{ingreso_id}")
def eliminar_ingreso(
    request: Request,
    ingreso_id: int,
    db: Session = Depends(get_db)
):
    """Eliminar ingreso"""
    usuario_id = verificar_autenticacion(request)
    
    ingreso = crud.obtener_ingreso(db, ingreso_id)
    if not ingreso or ingreso.usuario_id != usuario_id:
        raise HTTPException(status_code=404, detail="Ingreso no encontrado")
    
    crud.eliminar_ingreso(db, ingreso_id)
    
    request.session["mensaje"] = {
        "tipo": "exito",
        "titulo": "¡Eliminado!",
        "texto": "Ingreso eliminado correctamente"
    }
    
    return RedirectResponse(url="/ingresos", status_code=303)

# ========== GASTOS ==========

@router.get("/gastos", response_class=HTMLResponse)
def listar_gastos(
    request: Request, 
    db: Session = Depends(get_db), 
    page: int = 1,
    tipo: Optional[str] = None,
    pagado: Optional[bool] = None
):
    """Listar gastos con paginación"""
    usuario_id = verificar_autenticacion(request)
    
    # Obtener gastos
    gastos = crud.obtener_gastos_usuario(db, usuario_id)
    
    # Calcular totales
    total_gastos = sum(g.valor for g in gastos if g.valor)
    total_pagados = sum(g.valor for g in gastos if g.valor and g.pagado)
    total_pendientes = total_gastos - total_pagados
    
    # Paginación simple
    items_por_pagina = 10
    total_items = len(gastos)
    total_pages = (total_items + items_por_pagina - 1) // items_por_pagina if total_items > 0 else 1
    
    if page < 1:
        page = 1
    elif page > total_pages and total_pages > 0:
        page = total_pages
    
    start_idx = (page - 1) * items_por_pagina
    end_idx = start_idx + items_por_pagina
    gastos_pagina = gastos[start_idx:end_idx]
    
    mensaje = request.session.pop("mensaje", None)
    
    return templates.TemplateResponse("gastos_listado.html", {
        "request": request,
        "gastos": gastos_pagina,
        "total_gastos": total_gastos,
        "total_pagados": total_pagados,
        "total_pendientes": total_pendientes,
        "total_pages": total_pages,
        "current_page": page,
        "filtro_tipo": tipo,
        "filtro_pagado": pagado,
        "mensaje": mensaje
    })

@router.get("/gastos/nuevo", response_class=HTMLResponse)
@router.get("/gastos/editar/{gasto_id}", response_class=HTMLResponse)
def formulario_gasto(
    request: Request,
    gasto_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Formulario para crear/editar gasto"""
    usuario_id = verificar_autenticacion(request)
    
    gasto = None
    if gasto_id:
        gasto = crud.obtener_gasto(db, gasto_id)
        if not gasto or gasto.usuario_id != usuario_id:
            raise HTTPException(status_code=404, detail="Gasto no encontrado")
    
    categorias = crud.obtener_categorias(db, usuario_id)
    
    return templates.TemplateResponse("gasto_form.html", {
        "request": request,
        "gasto": gasto,
        "categorias": categorias
    })

@router.post("/gastos/guardar")
async def guardar_gasto(
    request: Request,
    id: Optional[int] = Form(None),
    categoria_nombre: str = Form(...),
    valor: float = Form(...),
    fecha_limite: Optional[str] = Form(None),
    pagado: bool = Form(False),
    notas: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Guardar gasto (crear o actualizar)"""
    usuario_id = verificar_autenticacion(request)
    
    try:
        # Buscar o crear categoría
        categoria = crud.obtener_categoria_por_nombre(db, categoria_nombre.strip(), usuario_id)
        if not categoria:
            categoria_data = schemas.CategoriaCreate(
                nombre=categoria_nombre.strip(),
                tipo="variable"
            )
            categoria = crud.crear_categoria(db, categoria_data, usuario_id)
        
        # Convertir fecha
        fecha_limite_dt = date.fromisoformat(fecha_limite) if fecha_limite else None
        
        # Crear datos del gasto
        gasto_data = schemas.GastoCreate(
            categoria_id=categoria.id,
            valor=valor,
            fecha_limite=fecha_limite_dt,
            pagado=pagado,
            notas=notas
        )
        
        if id:
            crud.actualizar_gasto(db, gasto_id=int(id), gasto=gasto_data, usuario_id=usuario_id)
            mensaje = "Gasto actualizado correctamente"
        else:
            crud.crear_gasto(db, gasto=gasto_data, usuario_id=usuario_id)
            mensaje = "Gasto creado correctamente"
        
        request.session['mensaje'] = {
            'tipo': 'exito',
            'titulo': '¡Éxito!',
            'texto': mensaje
        }
    except Exception as e:
        request.session['mensaje'] = {
            'tipo': 'error',
            'titulo': 'Error',
            'texto': f'Ocurrió un error: {str(e)}'
        }
    
    return RedirectResponse(url="/gastos", status_code=303)

@router.get("/gastos/eliminar/{gasto_id}")
def eliminar_gasto(
    request: Request,
    gasto_id: int,
    db: Session = Depends(get_db)
):
    """Eliminar gasto"""
    usuario_id = verificar_autenticacion(request)
    
    gasto = crud.obtener_gasto(db, gasto_id)
    if not gasto or gasto.usuario_id != usuario_id:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")
    
    crud.eliminar_gasto(db, gasto_id)
    
    request.session["mensaje"] = {
        "tipo": "exito",
        "titulo": "¡Eliminado!",
        "texto": "Gasto eliminado correctamente"
    }
    
    return RedirectResponse(url="/gastos", status_code=303)

# ========== PENDIENTES ==========

@router.get("/pendientes", response_class=HTMLResponse)
async def listar_pendientes(
    request: Request,
    estado: Optional[str] = None,
    prioridad: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Listar pendientes"""
    usuario_id = verificar_autenticacion(request)
    
    pendientes = crud.get_pendientes_by_filters(
        db,
        usuario_id=usuario_id,
        estado=estado,
        prioridad=prioridad
    )
    
    ahora = datetime.now()
    recordatorios_vencidos = [
        p for p in pendientes if p.recordatorio and p.recordatorio <= ahora
    ]
    
    return templates.TemplateResponse("pendientes.html", {
        "request": request,
        "pendientes": pendientes,
        "recordatorios_vencidos": recordatorios_vencidos,
        "now": ahora
    })

@router.get("/pendientes/nuevo", response_class=HTMLResponse)
@router.get("/pendientes/editar/{pendiente_id}", response_class=HTMLResponse)
async def form_pendiente(
    request: Request,
    pendiente_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Formulario para crear/editar pendiente"""
    usuario_id = verificar_autenticacion(request)
    
    pendiente = None
    if pendiente_id:
        pendiente = crud.get_pendiente(db, pendiente_id)
        if not pendiente or pendiente.usuario_id != usuario_id:
            raise HTTPException(status_code=404, detail="Pendiente no encontrado")
    
    return templates.TemplateResponse("pendientes_form.html", {
        "request": request,
        "pendiente": pendiente
    })

@router.post("/pendientes/guardar")
async def guardar_pendiente(
    request: Request,
    id: Optional[int] = Form(None),
    titulo: str = Form(...),
    descripcion: Optional[str] = Form(None),
    estado: str = Form(...),
    prioridad: str = Form(...),
    fecha_limite: Optional[str] = Form(None),
    recordatorio: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Guardar pendiente (crear o actualizar)"""
    usuario_id = verificar_autenticacion(request)
    
    try:
        fecha_limite_dt = datetime.fromisoformat(fecha_limite) if fecha_limite else None
        recordatorio_dt = datetime.fromisoformat(recordatorio) if recordatorio else None
        
        pendiente_data = schemas.PendienteCreate(
            titulo=titulo,
            descripcion=descripcion,
            estado=estado,
            prioridad=prioridad,
            fecha_limite=fecha_limite_dt,
            recordatorio=recordatorio_dt
        )
        
        if id:
            crud.update_pendiente(db, pendiente_id=id, pendiente=pendiente_data)
            mensaje = "Pendiente actualizado correctamente"
        else:
            crud.create_pendiente(db, pendiente=pendiente_data, usuario_id=usuario_id)
            mensaje = "Pendiente creado correctamente"
        
        request.session['mensaje'] = {
            'tipo': 'exito',
            'titulo': '¡Éxito!',
            'texto': mensaje
        }
    except Exception as e:
        request.session['mensaje'] = {
            'tipo': 'error',
            'titulo': 'Error',
            'texto': f'Ocurrió un error: {str(e)}'
        }
    
    return RedirectResponse(url="/pendientes", status_code=303)

@router.get("/pendientes/eliminar/{pendiente_id}")
async def eliminar_pendiente(
    request: Request,
    pendiente_id: int,
    db: Session = Depends(get_db)
):
    """Eliminar pendiente"""
    usuario_id = verificar_autenticacion(request)
    
    pendiente = crud.get_pendiente(db, pendiente_id)
    if not pendiente or pendiente.usuario_id != usuario_id:
        raise HTTPException(status_code=404, detail="Pendiente no encontrado")
    
    crud.delete_pendiente(db, pendiente_id)
    
    request.session["mensaje"] = {
        "tipo": "exito",
        "titulo": "¡Eliminado!",
        "texto": "Pendiente eliminado correctamente"
    }
    
    return RedirectResponse(url="/pendientes", status_code=303)

# ========== CONTRASEÑAS ==========

@router.get("/contrasenas", response_class=HTMLResponse)
def listar_contrasenas(
    request: Request,
    db: Session = Depends(get_db),
    page: int = 1,
    items_per_page: int = 10
):
    """Listar contraseñas"""
    usuario_id = verificar_autenticacion(request)
    
    contrasenas = crud.obtener_contrasenas_usuario(db, usuario_id)
    
    # Paginación
    total_items = len(contrasenas)
    total_pages = (total_items + items_per_page - 1) // items_per_page if total_items > 0 else 1
    
    if page < 1:
        page = 1
    elif page > total_pages and total_pages > 0:
        page = total_pages
    
    start_idx = (page - 1) * items_per_page
    end_idx = start_idx + items_per_page
    contrasenas_pagina = contrasenas[start_idx:end_idx]
    
    mensaje = request.session.pop("mensaje", None)
    
    return templates.TemplateResponse("contrasenas_listado.html", {
        "request": request,
        "contrasenas": contrasenas_pagina,
        "total_pages": total_pages,
        "current_page": page,
        "items_per_page": items_per_page,
        "total_items": total_items,
        "mensaje": mensaje
    })

@router.get("/contrasenas/nuevo", response_class=HTMLResponse)
@router.get("/contrasenas/editar/{contrasena_id}", response_class=HTMLResponse)
def formulario_contrasena(
    request: Request,
    contrasena_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Formulario para crear/editar contraseña"""
    usuario_id = verificar_autenticacion(request)
    
    contrasena = None
    if contrasena_id:
        contrasena = crud.obtener_contrasena(db, contrasena_id)
        if not contrasena or contrasena.usuario_id != usuario_id:
            raise HTTPException(status_code=404, detail="Contraseña no encontrada")
    
    return templates.TemplateResponse("contrasenas_form.html", {
        "request": request,
        "contrasena": contrasena
    })

@router.post("/contrasenas/guardar")
async def guardar_contrasena(
    request: Request,
    id: Optional[int] = Form(None),
    servicio: str = Form(...),
    usuario: str = Form(...),
    contrasena: str = Form(...),
    url: Optional[str] = Form(None),
    notas: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Guardar contraseña (crear o actualizar)"""
    usuario_id = verificar_autenticacion(request)
    
    try:
        contrasena_data = schemas.ContrasenaCreate(
            servicio=servicio,
            usuario=usuario,
            contrasena=contrasena,
            url=url,
            notas=notas
        )
        
        if id:
            # Actualizar
            contrasena_update = schemas.ContrasenaUpdate(
                servicio=servicio,
                usuario=usuario,
                contrasena=contrasena,
                url=url,
                notas=notas
            )
            crud.actualizar_contrasena(db, contrasena_id=int(id), contrasena=contrasena_update, usuario_id=usuario_id)
            mensaje = "Contraseña actualizada correctamente"
        else:
            # Crear nueva
            crud.crear_contrasena(db, contrasena=contrasena_data, usuario_id=usuario_id)
            mensaje = "Contraseña creada correctamente"
        
        request.session['mensaje'] = {
            'tipo': 'exito',
            'titulo': '¡Éxito!',
            'texto': mensaje
        }
    except Exception as e:
        request.session['mensaje'] = {
            'tipo': 'error',
            'titulo': 'Error',
            'texto': f'Ocurrió un error: {str(e)}'
        }
    
    return RedirectResponse(url="/contrasenas", status_code=303)

@router.get("/contrasenas/eliminar/{contrasena_id}")
def eliminar_contrasena(
    request: Request,
    contrasena_id: int,
    db: Session = Depends(get_db)
):
    """Eliminar contraseña"""
    usuario_id = verificar_autenticacion(request)
    
    contrasena = crud.obtener_contrasena(db, contrasena_id)
    if not contrasena or contrasena.usuario_id != usuario_id:
        raise HTTPException(status_code=404, detail="Contraseña no encontrada")
    
    crud.eliminar_contrasena(db, contrasena_id, usuario_id)
    
    request.session["mensaje"] = {
        "tipo": "exito",
        "titulo": "¡Eliminado!",
        "texto": "Contraseña eliminada correctamente"
    }
    
    return RedirectResponse(url="/contrasenas", status_code=303)

@router.get("/contrasenas/obtener/{contrasena_id}")
def obtener_contrasena_desencriptada(
    request: Request,
    contrasena_id: int,
    db: Session = Depends(get_db)
):
    """Obtener contraseña desencriptada"""
    usuario_id = verificar_autenticacion(request)
    
    contrasena_texto = crud.desencriptar_contrasena_db(db, contrasena_id, usuario_id)
    
    if not contrasena_texto:
        return JSONResponse(
            content={"status": "error", "mensaje": "Contraseña no encontrada"}, 
            status_code=404
        )
    
    return JSONResponse(content={
        "status": "success",
        "contrasena": contrasena_texto
    })

# ========== CUMPLEAÑOS ==========

@router.get("/cumpleanos", response_class=HTMLResponse)
async def listar_cumpleanos(
    request: Request,
    page: int = 1,
    relacion: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Listar cumpleaños"""
    usuario_id = verificar_autenticacion(request)
    
    resultado = crud.obtener_cumpleanos_paginados(
        db, 
        usuario_id=usuario_id, 
        page=page, 
        per_page=10,
        relacion=relacion
    )
    
    # Calcular días, edad y próximo cumpleaños
    for cumple in resultado["cumpleanos"]:
        cumple.dias_hasta_cumpleanos = crud.calcular_dias_hasta_cumpleanos(cumple.fecha_nacimiento)
        cumple.edad = crud.calcular_edad(cumple.fecha_nacimiento)
        cumple.proximo_cumple = crud.calcular_proximo_cumple(cumple.fecha_nacimiento)
    
    return templates.TemplateResponse("cumpleanos_listado.html", {
        "request": request,
        "cumpleanos": resultado["cumpleanos"],
        "current_page": resultado["current_page"],
        "total_pages": resultado["total_pages"],
        "filtro_relacion": relacion
    })

@router.get("/cumpleanos/nuevo", response_class=HTMLResponse)
async def formulario_nuevo_cumpleano(request: Request):
    """Formulario para nuevo cumpleaño"""
    usuario_id = verificar_autenticacion(request)
    
    return templates.TemplateResponse("cumpleanos_form.html", {
        "request": request,
        "cumpleano": None
    })

@router.get("/cumpleanos/editar/{cumpleano_id}", response_class=HTMLResponse)
async def formulario_editar_cumpleano(
    request: Request,
    cumpleano_id: int,
    db: Session = Depends(get_db)
):
    """Formulario para editar cumpleaño"""
    usuario_id = verificar_autenticacion(request)
    
    cumpleano = crud.obtener_cumpleano(db, cumpleano_id)
    if not cumpleano or cumpleano.usuario_id != usuario_id:
        return RedirectResponse("/cumpleanos", status_code=302)
    
    return templates.TemplateResponse("cumpleanos_form.html", {
        "request": request,
        "cumpleano": cumpleano
    })

@router.post("/cumpleanos/guardar")
async def guardar_cumpleano(
    request: Request,
    db: Session = Depends(get_db)
):
    """Guardar cumpleaño (crear o actualizar)"""
    usuario_id = verificar_autenticacion(request)
    
    form_data = await request.form()
    cumpleano_id = form_data.get("id")
    
    try:
        cumpleano_data = schemas.CumpleanoCreate(
            nombre_persona=form_data.get("nombre_persona"),
            fecha_nacimiento=datetime.strptime(form_data.get("fecha_nacimiento"), "%Y-%m-%d").date(),
            telefono=form_data.get("telefono") or None,
            email=form_data.get("email") or None,
            relacion=form_data.get("relacion") or None,
            notas=form_data.get("notas") or None,
            notificar_dias_antes=int(form_data.get("notificar_dias_antes", 7))
        )
        
        if cumpleano_id:
            # Actualizar
            crud.actualizar_cumpleano(db, int(cumpleano_id), schemas.CumpleanoUpdate(**cumpleano_data.model_dump()), usuario_id)
            mensaje = "Cumpleaños actualizado correctamente"
        else:
            # Crear nuevo
            crud.crear_cumpleano(db, cumpleano_data, usuario_id)
            mensaje = "Cumpleaños creado correctamente"
        
        request.session['mensaje'] = {
            'tipo': 'exito',
            'titulo': '¡Éxito!',
            'texto': mensaje
        }
    except Exception as e:
        request.session['mensaje'] = {
            'tipo': 'error',
            'titulo': 'Error',
            'texto': f'Ocurrió un error: {str(e)}'
        }
    
    return RedirectResponse("/cumpleanos", status_code=303)

@router.get("/cumpleanos/eliminar/{cumpleano_id}")
async def eliminar_cumpleano(
    request: Request,
    cumpleano_id: int,
    db: Session = Depends(get_db)
):
    """Eliminar cumpleaño"""
    usuario_id = verificar_autenticacion(request)
    
    crud.eliminar_cumpleano(db, cumpleano_id, usuario_id)
    
    request.session['mensaje'] = {
        'tipo': 'exito',
        'titulo': '¡Eliminado!',
        'texto': 'Cumpleaños eliminado correctamente'
    }
    
    return RedirectResponse("/cumpleanos", status_code=303)