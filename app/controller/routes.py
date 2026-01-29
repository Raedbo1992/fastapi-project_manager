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
router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# Funciones de autenticación
def hashear_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verificar_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

# Rutas de autenticación
@router.get("/", response_class=HTMLResponse)
def root(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

# Muestra login directamente (útil si rediriges desde otras vistas)
@router.get("/login", response_class=HTMLResponse)
def mostrar_login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

# Proceso de login
@router.post("/login")
async def login(
    request: Request,
    username: str = Form(...),  # O cambia a email si prefieres
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    # Buscar por username (o email si cambiaste el parámetro)
    usuario = crud.obtener_usuario_por_username(db, username)
    
    if usuario and verificar_password(password, usuario.password):
        # ✅ Guardar usuario en sesión
        request.session["usuario_id"] = usuario.id

        return RedirectResponse(url="/dashboard", status_code=HTTP_303_SEE_OTHER)

    return templates.TemplateResponse("login.html", {
        "request": request,
        "error": "Credenciales inválidas"
    })



@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)

# Dashboard
@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        return RedirectResponse(url="/login", status_code=303)
    
    usuario = crud.obtener_usuario_por_id(db, usuario_id)
    if not usuario:
        return RedirectResponse(url="/login", status_code=303)

    stats = crud.obtener_estadisticas_dashboard(db, usuario_id)
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "usuario": usuario,
        "stats": stats,
        "fecha_actual": datetime.now()  # Añade la fecha actual
    })



# Mostrar formulario para nuevo ingreso o editar
@router.get("/ingresos/nuevo", response_class=HTMLResponse)
@router.get("/ingresos/editar/{ingreso_id}", response_class=HTMLResponse)
def formulario_ingreso(
    request: Request,
    ingreso_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        return RedirectResponse(url="/login", status_code=303)

    ingreso = None
    if ingreso_id:
        ingreso = crud.obtener_ingreso(db, ingreso_id)
        if not ingreso or ingreso.usuario_id != usuario_id:
            raise HTTPException(status_code=404, detail="Ingreso no encontrado")

    return templates.TemplateResponse("ingreso_form.html", {
        "request": request,
        "ingreso": ingreso
    })


# Guardar ingreso (crear o actualizar)
@router.post("/ingresos/guardar")
def guardar_ingreso(
    request: Request,
    id: Optional[int] = Form(None),
    valor: float = Form(...),
    fecha: str = Form(...),
    notas: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        return RedirectResponse(url="/login", status_code=303)

    fecha_dt = date.fromisoformat(fecha) if fecha else None

    # Crear o obtener una categoría por defecto para ingresos
    categoria = crud.obtener_categoria_por_nombre(db, "Ingresos", usuario_id)
    if not categoria:
        categoria = crud.crear_categoria(db, schemas.CategoriaCreate(nombre="Ingresos", tipo="variable"), usuario_id)

    ingreso_data = schemas.IngresoCreate(
        valor=valor,
        fecha=fecha_dt,
        notas=notas
    )

    try:
        if id:
            crud.actualizar_ingreso(db, ingreso_id=int(id), ingreso=ingreso_data, usuario_id=usuario_id)
            mensaje = "Ingreso actualizado correctamente"
        else:
            # Modificar para incluir la categoría
            db_ingreso = models.Ingreso(
                valor=valor,
                fecha=fecha_dt,
                notas=notas,
                usuario_id=usuario_id,
                categoria_id=categoria.id
            )
            db.add(db_ingreso)
            db.commit()
            db.refresh(db_ingreso)
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


# Lisstar Ingresoss
@router.get("/ingresos")
def listar_gastos(
    request: Request, 
    db: Session = Depends(get_db), 
    page: int = 1,
    tipo: Optional[str] = None,
    pagado: Optional[bool] = None
):
    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        return RedirectResponse(url="/login", status_code=303)
    
    data = crud.obtener_ingresos_paginados(
        db, 
        usuario_id, 
        page=page, 
        tipo=tipo,
        pagado=pagado
    )
    mensaje = request.session.pop("mensaje", None)  # Leer y borrar el mensaje
    
    return templates.TemplateResponse(
        "ingresos_listado.html",
        {
            "request": request,
            "ingresos": data["ingresos"],
            "total_pages": data["total_pages"],
            "current_page": page,  # Asegúrate de pasar esto
            "filtro_tipo": tipo,
            "filtro_pagado": pagado,
            "mensaje": mensaje  # Pasar el mensaje a la plantilla
        }
    )


@router.get("/ingresos/eliminar/{ingreso_id}")
def eliminar_ingreso(
    request: Request,
    ingreso_id: int,
    db: Session = Depends(get_db)
):
    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        return RedirectResponse(url="/login", status_code=303)

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

# LISTAR GASTOS con paginación y filtros

# ... (código existente)

@router.get("/gastos")
def listar_gastos(
    request: Request, 
    db: Session = Depends(get_db), 
    page: int = 1,
    tipo: Optional[str] = None,
    pagado: Optional[bool] = None
):
    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        return RedirectResponse(url="/login", status_code=303)
    
    data = crud.obtener_gastos_paginados(
        db, 
        usuario_id, 
        page=page, 
        tipo=tipo,
        pagado=pagado
    )
    mensaje = request.session.pop("mensaje", None)
    
    return templates.TemplateResponse(
        "gastos_listado.html",
        {
            "request": request,
            "gastos": data["gastos"],
            "total_pages": data["total_pages"],
            "current_page": page,  # Asegúrate de pasar esto
            "filtro_tipo": tipo,
            "filtro_pagado": pagado,
            "mensaje": mensaje
        }
    )

@router.get("/gastos/nuevo", response_class=HTMLResponse)
@router.get("/gastos/editar/{gasto_id}", response_class=HTMLResponse)
def formulario_gasto(
    request: Request,
    gasto_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        return RedirectResponse(url="/login", status_code=303)

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
def guardar_gasto(
    request: Request,
    id: Optional[int] = Form(None),
    categoria_nombre: str = Form(...),
    valor: float = Form(...),
    fecha_limite: Optional[str] = Form(None),
    pagado: bool = Form(False),
    notas: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        return RedirectResponse(url="/login", status_code=303)

    # Buscar o crear la categoría
    categoria = crud.obtener_categoria_por_nombre(db, categoria_nombre.strip(), usuario_id)
    if not categoria:
        # Crear nueva categoría con tipo por defecto
        nueva_categoria = schemas.CategoriaCreate(
            nombre=categoria_nombre.strip(),
            tipo="variable"  # Puedes cambiarlo o hacerlo configurable
        )
        categoria = crud.crear_categoria(db, nueva_categoria, usuario_id)

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

    try:
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
    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        return RedirectResponse(url="/login", status_code=303)

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

# Rutas para categorías (similares a las de gastos)
# ...

# Rutas para ingresos (similares a las de gastos)
# ...

@router.get("/pendientes", response_class=HTMLResponse)
async def listar_pendientes(
    request: Request,
    estado: Optional[str] = None,
    prioridad: Optional[str] = None,
    db: Session = Depends(get_db)
):
    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        return RedirectResponse(url="/login", status_code=HTTP_303_SEE_OTHER)

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

    return templates.TemplateResponse(
        "pendientes.html",
        {
            "request": request,
            "pendientes": pendientes,
            "recordatorios_vencidos": recordatorios_vencidos,
            "now": ahora
        }
    )


@router.get("/pendientes/nuevo", response_class=HTMLResponse)
@router.get("/pendientes/editar/{pendiente_id}", response_class=HTMLResponse)
async def form_pendiente(
    request: Request,
    pendiente_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        return RedirectResponse(url="/login", status_code=HTTP_303_SEE_OTHER)

    pendiente = None
    if pendiente_id:
        pendiente = crud.get_pendiente(db, pendiente_id)
        if not pendiente or pendiente.usuario_id != usuario_id:
            raise HTTPException(status_code=404, detail="Pendiente no encontrado")

    return templates.TemplateResponse(
        "pendientes_form.html",
        {
            "request": request,
            "pendiente": pendiente
        }
    )


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
    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        return RedirectResponse(url="/login", status_code=HTTP_303_SEE_OTHER)

    fecha_limite_dt = datetime.fromisoformat(fecha_limite) if fecha_limite else None
    recordatorio_dt = datetime.fromisoformat(recordatorio) if recordatorio else None

    pendiente_data = schemas.PendienteCreate(
        titulo=titulo,
        descripcion=descripcion,
        estado=estado,
        prioridad=prioridad,
        fecha_limite=fecha_limite_dt,
        recordatorio=recordatorio_dt
        # proyecto_id eliminado
    )

    try:
        if id:
            pendiente = crud.update_pendiente(db, pendiente_id=id, pendiente=pendiente_data)
            mensaje = "Pendiente actualizado correctamente"
        else:
            pendiente = crud.create_pendiente(db, pendiente=pendiente_data, usuario_id=usuario_id)
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

    return RedirectResponse(url="/pendientes", status_code=HTTP_303_SEE_OTHER)



@router.get("/pendientes/eliminar/{pendiente_id}")
async def eliminar_pendiente(
    request: Request,
    pendiente_id: int,
    db: Session = Depends(get_db)
):
    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        return RedirectResponse(url="/login", status_code=HTTP_303_SEE_OTHER)

    pendiente = crud.get_pendiente(db, pendiente_id)
    if not pendiente or pendiente.usuario_id != usuario_id:
        raise HTTPException(status_code=404, detail="Pendiente no encontrado")

    crud.delete_pendiente(db, pendiente_id)
    request.session["mensaje"] = {
        "tipo": "exito",
        "titulo": "¡Eliminado!",
        "texto": "Pendiente eliminado correctamente"
    }
    return RedirectResponse(url="/pendientes", status_code=HTTP_303_SEE_OTHER)




@router.post("/pendientes/recordatorio/{pendiente_id}")
async def guardar_recordatorio(
    pendiente_id: int,
    recordatorio: str = Form(...),
    request: Request = None,
    db: Session = Depends(get_db)
):
    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        return JSONResponse(content={"status": "error", "mensaje": "No autenticado"}, status_code=403)

    pendiente = crud.get_pendiente(db, pendiente_id)
    if not pendiente or pendiente.usuario_id != usuario_id:
        return JSONResponse(content={"status": "error", "mensaje": "No autorizado"}, status_code=403)

    try:
        recordatorio_dt = datetime.fromisoformat(recordatorio)
        crud.agregar_recordatorio(db, pendiente_id, recordatorio_dt)
        return JSONResponse(content={"status": "success"})
    except Exception as e:
        return JSONResponse(content={"status": "error", "mensaje": str(e)}, status_code=400)



# Mostrar formulario para nueva contraseña o editar
# ... (código anterior)

# Mostrar formulario para nueva contraseña o editar
@router.get("/contrasenas/nuevo", response_class=HTMLResponse)
@router.get("/contrasenas/editar/{contrasena_id}", response_class=HTMLResponse)
def formulario_contrasena(
    request: Request,
    contrasena_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        return RedirectResponse(url="/login", status_code=303)
    
    contrasena = None
    if contrasena_id:
        contrasena = crud.obtener_contrasena(db, contrasena_id)
        if not contrasena or contrasena.usuario_id != usuario_id:
            raise HTTPException(status_code=404, detail="Contraseña no encontrada")
    
    return templates.TemplateResponse("contrasenas_form.html", {
        "request": request,
        "contrasena": contrasena
    })

# Guardar contraseña (crear o actualizar)
@router.post("/contrasenas/guardar")
def guardar_contrasena(
    request: Request,
    id: Optional[int] = Form(None),
    servicio: str = Form(...),
    usuario: str = Form(...),
    contrasena: str = Form(...),
    url: Optional[str] = Form(None),
    notas: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        return RedirectResponse(url="/login", status_code=303)
    
    contrasena_data = schemas.ContrasenaCreate(
        servicio=servicio,
        usuario=usuario,
        contrasena=contrasena,
        url=url,
        notas=notas
    )
    
    try:
        if id:
            # Actualizar contraseña existente
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
            # Crear nueva contraseña
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

# Listar contraseñas
@router.get("/contrasenas", response_class=HTMLResponse)
def listar_contrasenas(
    request: Request,
    db: Session = Depends(get_db),
    page: int = 1,
    items_per_page: int = 10
):
    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        return RedirectResponse(url="/login", status_code=303)
    
    # Obtener todas las contraseñas del usuario
    contrasenas = crud.obtener_contrasenas_usuario(db, usuario_id)
    
    # Calcular paginación
    total_items = len(contrasenas)
    total_pages = (total_items + items_per_page - 1) // items_per_page if total_items > 0 else 1
    
    # Ajustar página si es necesario
    if page < 1:
        page = 1
    elif page > total_pages and total_pages > 0:
        page = total_pages
    
    # Obtener elementos para la página actual
    start_idx = (page - 1) * items_per_page
    end_idx = start_idx + items_per_page
    contrasenas_pagina = contrasenas[start_idx:end_idx]
    
    mensaje = request.session.pop("mensaje", None)
    
    return templates.TemplateResponse(
        "contrasenas_listado.html",
        {
            "request": request,
            "contrasenas": contrasenas_pagina,
            "total_pages": total_pages,
            "current_page": page,
            "items_per_page": items_per_page,
            "total_items": total_items,
            "mensaje": mensaje
        }
    )

# Eliminar contraseña
@router.get("/contrasenas/eliminar/{contrasena_id}")
def eliminar_contrasena(
    request: Request,
    contrasena_id: int,
    db: Session = Depends(get_db)
):
    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        return RedirectResponse(url="/login", status_code=303)
    
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
    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        return JSONResponse(content={"status": "error", "mensaje": "No autenticado"}, status_code=401)
    
    # Obtener la contraseña desencriptada
    contrasena_texto = crud.desencriptar_contrasena_db(db, contrasena_id, usuario_id)
    
    if not contrasena_texto:
        return JSONResponse(content={"status": "error", "mensaje": "Contraseña no encontrada"}, status_code=404)
    
    return JSONResponse(content={
        "status": "success",
        "contrasena": contrasena_texto
    })


# Agregar estas rutas al archivo app/main.py

# =========================================================
# 🎂 RUTAS DE CUMPLEAÑOS
# =========================================================

@router.get("/cumpleanos", response_class=HTMLResponse)
async def listar_cumpleanos(
    request: Request,
    page: int = 1,
    relacion: Optional[str] = None,
    db: Session = Depends(get_db)
):
    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        return RedirectResponse("/", status_code=303)
    
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
    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        return RedirectResponse("/", status_code=303)
    
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
    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        return RedirectResponse("/", status_code=303)
    
    cumpleano = crud.obtener_cumpleano(db, cumpleano_id)
    if not cumpleano or cumpleano.usuario_id != usuario_id:
        return RedirectResponse("/cumpleanos", status_code=303)
    
    return templates.TemplateResponse("cumpleanos_form.html", {
        "request": request,
        "cumpleano": cumpleano
    })

@router.post("/cumpleanos/guardar")
async def guardar_cumpleano(
    request: Request,
    db: Session = Depends(get_db)
):
    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        return RedirectResponse("/", status_code=303)
    
    form_data = await request.form()
    cumpleano_id = form_data.get("id")
    
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
    else:
        # Crear nuevo
        crud.crear_cumpleano(db, cumpleano_data, usuario_id)
    
    return RedirectResponse("/cumpleanos", status_code=303)

@router.get("/cumpleanos/eliminar/{cumpleano_id}")
async def eliminar_cumpleano(
    request: Request,
    cumpleano_id: int,
    db: Session = Depends(get_db)
):
    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        return RedirectResponse("/", status_code=303)
    
    crud.eliminar_cumpleano(db, cumpleano_id, usuario_id)
    return RedirectResponse("/cumpleanos", status_code=303)