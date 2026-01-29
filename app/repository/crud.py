import bcrypt
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, extract
from datetime import datetime, timedelta  # <-- Importación corregida
from typing import Optional, Dict
from app.schema import models, schemas
from passlib.context import CryptContext
import base64
from datetime import date, datetime, timedelta

# =========================================================
# 🔐 FUNCIONES DE AUTENTICACIÓN
# =========================================================
def hashear_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verificar_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def obtener_usuario_por_username(db: Session, username: str):
    return db.query(models.Usuario).filter(models.Usuario.username == username).first()

def obtener_usuario_por_email(db: Session, email: str):
    return db.query(models.Usuario).filter(models.Usuario.email == email).first()

def obtener_usuario_por_id(db: Session, usuario_id: int):
    return db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()

def crear_usuario(db: Session, usuario: schemas.UsuarioCreate):
    hashed_password = hashear_password(usuario.password)
    db_usuario = models.Usuario(
        nombre=usuario.nombre,
        email=usuario.email,
        username=usuario.username,
        password=hashed_password
    )
    db.add(db_usuario)
    db.commit()
    db.refresh(db_usuario)
    return db_usuario

# =========================================================
# 📂 CATEGORÍAS
# =========================================================
def crear_categoria(db: Session, categoria: schemas.CategoriaCreate, usuario_id: int):
    db_categoria = models.Categoria(**categoria.model_dump(), usuario_id=usuario_id)
    db.add(db_categoria)
    db.commit()
    db.refresh(db_categoria)
    return db_categoria

def obtener_categorias(db: Session, usuario_id: int, tipo: Optional[str] = None):
    query = db.query(models.Categoria).filter(models.Categoria.usuario_id == usuario_id)
    if tipo:
        query = query.filter(models.Categoria.tipo == tipo)
    return query.all()

def obtener_categoria_por_nombre(db: Session, nombre: str, usuario_id: int):
    return db.query(models.Categoria).filter(
        and_(models.Categoria.nombre == nombre, models.Categoria.usuario_id == usuario_id)
    ).first()

# =========================================================
# 💰 INGRESOS
# =========================================================
def crear_ingreso(db: Session, ingreso: schemas.IngresoCreate, usuario_id: int):
    categoria = db.query(models.Categoria).filter_by(
        id=ingreso.categoria_id, usuario_id=usuario_id
    ).first()
    if not categoria:
        return None
    db_ingreso = models.Ingreso(**ingreso.model_dump(), usuario_id=usuario_id)
    db.add(db_ingreso)
    db.commit()
    db.refresh(db_ingreso)
    return db_ingreso

def obtener_ingreso(db: Session, ingreso_id: int):
    return db.query(models.Ingreso).filter(models.Ingreso.id == ingreso_id).first()

def actualizar_ingreso(db: Session, ingreso_id: int, ingreso: schemas.IngresoUpdate, usuario_id: int):
    db_ingreso = obtener_ingreso(db, ingreso_id)
    if not db_ingreso or db_ingreso.usuario_id != usuario_id:
        return None
    for key, value in ingreso.model_dump(exclude_unset=True).items():
        setattr(db_ingreso, key, value)
    db.commit()
    db.refresh(db_ingreso)
    return db_ingreso

def eliminar_ingreso(db: Session, ingreso_id: int):
    db_ingreso = obtener_ingreso(db, ingreso_id)
    if db_ingreso:
        db.delete(db_ingreso)
        db.commit()
    return db_ingreso

def obtener_ingresos_paginados(db, usuario_id, page=1, tipo=None, pagado=None, per_page=10):
    query = db.query(models.Ingreso).filter(models.Ingreso.usuario_id == usuario_id)

    if tipo:
        query = query.filter(models.Ingreso.tipo == tipo)
    if pagado is not None:
        query = query.filter(models.Ingreso.pagado == pagado)

    total = query.count()
    ingresos = query.offset((page - 1) * per_page).limit(per_page).all()

    return {
        "ingresos": ingresos,
        "total_pages": (total + per_page - 1) // per_page
    }


def obtener_ultimo_salario(db: Session, usuario_id: int):
    return db.query(models.Ingreso).filter(
        models.Ingreso.usuario_id == usuario_id,
    ).order_by(models.Ingreso.fecha.desc()).first()

def obtener_ingresos_mensuales(db: Session, usuario_id: int, year: int, month: int):
    return db.query(func.coalesce(func.sum(models.Ingreso.valor), 0)).filter(
        models.Ingreso.usuario_id == usuario_id,
        extract('year', models.Ingreso.fecha) == year,
        extract('month', models.Ingreso.fecha) == month
    ).scalar()

# =========================================================
# 💸 GASTOS
# =========================================================
def crear_gasto(db: Session, gasto: schemas.GastoCreate, usuario_id: int):
    categoria = db.query(models.Categoria).filter_by(
        id=gasto.categoria_id, usuario_id=usuario_id
    ).first()
    if not categoria:
        return None
    db_gasto = models.Gasto(**gasto.model_dump(), usuario_id=usuario_id)
    db.add(db_gasto)
    db.commit()
    db.refresh(db_gasto)
    return db_gasto

def obtener_gasto(db: Session, gasto_id: int):
    return db.query(models.Gasto).filter(models.Gasto.id == gasto_id).first()

def actualizar_gasto(db: Session, gasto_id: int, gasto: schemas.GastoUpdate, usuario_id: int):
    db_gasto = obtener_gasto(db, gasto_id)
    if not db_gasto or db_gasto.usuario_id != usuario_id:
        return None
    for key, value in gasto.model_dump(exclude_unset=True).items():
        setattr(db_gasto, key, value)
    db.commit()
    db.refresh(db_gasto)
    return db_gasto

def eliminar_gasto(db: Session, gasto_id: int):
    db_gasto = obtener_gasto(db, gasto_id)
    if db_gasto:
        db.delete(db_gasto)
        db.commit()
    return db_gasto

def obtener_gastos_paginados(db: Session, usuario_id: int, page: int = 1, page_size: int = 10, tipo: Optional[str] = None, pagado: Optional[bool] = None):
    query = db.query(models.Gasto).join(models.Categoria).filter(models.Gasto.usuario_id == usuario_id)
    if tipo:
        query = query.filter(models.Categoria.tipo == tipo)
    if pagado is not None:
        query = query.filter(models.Gasto.pagado == pagado)
    total_items = query.count()
    total_pages = (total_items + page_size - 1) // page_size
    gastos = query.order_by(models.Gasto.fecha_limite) \
                  .offset((page - 1) * page_size) \
                  .limit(page_size) \
                  .all()
    return {"gastos": gastos, "total_pages": total_pages, "current_page": page}

# =========================================================
# 📊 ESTADÍSTICAS
# =========================================================
def obtener_estadisticas_dashboard(db: Session, usuario_id: int):
    # 1. Datos básicos
    ultimo_salario = obtener_ultimo_salario(db, usuario_id)
    salario_actual = ultimo_salario.valor if ultimo_salario else 0
    
    # 2. Totales generales
    total_gastos = db.query(func.coalesce(func.sum(models.Gasto.valor), 0)).filter(
        models.Gasto.usuario_id == usuario_id
    ).scalar() or 0

    total_ingresos = db.query(func.coalesce(func.sum(models.Ingreso.valor), 0)).filter(
        models.Ingreso.usuario_id == usuario_id
    ).scalar() or 0

    saldo_disponible = total_ingresos - total_gastos
    
    # 3. Cálculo de variaciones (mes actual vs mes anterior)
    hoy = datetime.now()
    mes_actual = hoy.month
    año_actual = hoy.year
    mes_pasado = mes_actual - 1 if mes_actual > 1 else 12
    año_pasado = año_actual if mes_actual > 1 else año_actual - 1

    # Gastos mes actual
    gastos_mes_actual = db.query(func.coalesce(func.sum(models.Gasto.valor), 0)).filter(
        and_(
            models.Gasto.usuario_id == usuario_id,
            extract('month', models.Gasto.fecha_limite) == mes_actual,
            extract('year', models.Gasto.fecha_limite) == año_actual
        )
    ).scalar() or 0

    # Gastos mes anterior
    gastos_mes_pasado = db.query(func.coalesce(func.sum(models.Gasto.valor), 0)).filter(
        and_(
            models.Gasto.usuario_id == usuario_id,
            extract('month', models.Gasto.fecha_limite) == mes_pasado,
            extract('year', models.Gasto.fecha_limite) == año_pasado
        )
    ).scalar() or 0

    # Ingresos mes actual
    ingresos_mes_actual = db.query(func.coalesce(func.sum(models.Ingreso.valor), 0)).filter(
        and_(
            models.Ingreso.usuario_id == usuario_id,
            extract('month', models.Ingreso.fecha) == mes_actual,
            extract('year', models.Ingreso.fecha) == año_actual
        )
    ).scalar() or 0

    # Ingresos mes anterior
    ingresos_mes_pasado = db.query(func.coalesce(func.sum(models.Ingreso.valor), 0)).filter(
        and_(
            models.Ingreso.usuario_id == usuario_id,
            extract('month', models.Ingreso.fecha) == mes_pasado,
            extract('year', models.Ingreso.fecha) == año_pasado
        )
    ).scalar() or 0

    # Cálculo de variaciones porcentuales
    variacion_gastos = calcular_variacion(gastos_mes_pasado, gastos_mes_actual)
    variacion_ingresos = calcular_variacion(ingresos_mes_pasado, ingresos_mes_actual)
    
    # 4. Porcentaje de ahorro
    porcentaje_ahorro = (saldo_disponible / total_ingresos * 100) if total_ingresos > 0 else 0
    
    # 5. Gastos por categoría
    gastos_por_categoria_query = db.query(
        models.Categoria.nombre,
        func.sum(models.Gasto.valor).label('total')
    ).join(models.Gasto).filter(
        models.Gasto.usuario_id == usuario_id
    ).group_by(models.Categoria.nombre).all()

    gastos_por_categoria = {categoria: total for categoria, total in gastos_por_categoria_query}
    
    # Categoría con mayor gasto
    categoria_mayor = max(gastos_por_categoria_query, key=lambda x: x[1], default=('Ninguna', 0))
    
    # 6. Gastos por tipo
    gastos_por_tipo_query = db.query(
        models.Categoria.tipo,
        func.sum(models.Gasto.valor).label('total')
    ).join(models.Gasto).filter(
        models.Gasto.usuario_id == usuario_id
    ).group_by(models.Categoria.tipo).all()

    gastos_por_tipo = {tipo: total for tipo, total in gastos_por_tipo_query}
    
    # 7. Evolución mensual (últimos 6 meses)
    evolucion_mensual = obtener_evolucion_mensual(db, usuario_id, meses=6)
    
    # 8. Cálculo de porcentajes por tipo
    total_fijos = sum(v for k, v in gastos_por_tipo.items() if k == 'fijo')
    total_variables = sum(v for k, v in gastos_por_tipo.items() if k == 'variable')
    porcentaje_fijos = (total_fijos / total_gastos * 100) if total_gastos > 0 else 0
    porcentaje_variables = (total_variables / total_gastos * 100) if total_gastos > 0 else 0
    
    # 9. Promedio mensual
    meses_con_datos = len([v for v in evolucion_mensual['gastos'] if v > 0])
    promedio_mensual = (sum(evolucion_mensual['gastos']) / meses_con_datos) if meses_con_datos > 0 else 0
    
    return schemas.DashboardStats(
        salario_actual=salario_actual,
        total_gastos=total_gastos,
        total_ingresos=total_ingresos,
        saldo_disponible=saldo_disponible,
        variacion_ingresos=variacion_ingresos,
        variacion_gastos=variacion_gastos,
        porcentaje_ahorro=round(porcentaje_ahorro, 1),
        gastos_por_categoria=gastos_por_categoria,
        gastos_por_tipo=gastos_por_tipo,
        categoria_mayor={
            'nombre': categoria_mayor[0],
            'valor': categoria_mayor[1],
            'porcentaje': round((categoria_mayor[1] / total_gastos * 100), 1) if total_gastos > 0 else 0
        },
        evolucion_mensual=evolucion_mensual,
        promedio_mensual=round(promedio_mensual, 2),
        porcentaje_fijos=round(porcentaje_fijos, 1),
        porcentaje_variables=round(porcentaje_variables, 1)
    )


def calcular_variacion(anterior: float, actual: float) -> float:
    """
    Calcula la variación porcentual entre dos valores
    
    Args:
        anterior: Valor del periodo anterior
        actual: Valor del periodo actual
    
    Returns:
        float: Porcentaje de variación (puede ser positivo o negativo)
    """
    # Caso cuando no hay datos del periodo anterior
    if anterior == 0:
        return 0.0
    
    # Fórmula: ((actual - anterior) / anterior) * 100
    variacion = ((actual - anterior) / anterior) * 100
    
    # Redondeamos a 1 decimal para mejor presentación
    return round(variacion, 1)

def obtener_evolucion_mensual(db: Session, usuario_id: int, meses: int = 6) -> Dict[str, list]:
    """
    Obtiene la evolución histórica de ingresos y gastos por mes
    
    Args:
        db: Sesión de base de datos
        usuario_id: ID del usuario
        meses: Cantidad de meses históricos a incluir (por defecto 6)
    
    Returns:
        Dict: {
            'labels': [meses],
            'ingresos': [valores],
            'gastos': [valores]
        }
    """
    hoy = datetime.now()
    resultado = {
        'labels': [],
        'ingresos': [],
        'gastos': []
    }
    
    # Recorremos los últimos N meses en orden cronológico
    for i in range(meses, 0, -1):
        # Calculamos la fecha de referencia para cada mes
        fecha_referencia = hoy - timedelta(days=30*i)
        mes = fecha_referencia.month
        año = fecha_referencia.year
        
        # Consulta para ingresos del mes
        ingresos = db.query(
            func.coalesce(func.sum(models.Ingreso.valor), 0)
        ).filter(
            models.Ingreso.usuario_id == usuario_id,
            extract('month', models.Ingreso.fecha) == mes,
            extract('year', models.Ingreso.fecha) == año
        ).scalar() or 0
        
        # Consulta para gastos del mes
        gastos = db.query(
            func.coalesce(func.sum(models.Gasto.valor), 0)
        ).filter(
            models.Gasto.usuario_id == usuario_id,
            extract('month', models.Gasto.fecha_limite) == mes,
            extract('year', models.Gasto.fecha_limite) == año
        ).scalar() or 0
        
        # Formateamos el label (ej: "Ene 2023")
        nombre_mes = fecha_referencia.strftime('%b')  # Abreviatura del mes
        resultado['labels'].append(f"{nombre_mes} {año}")
        resultado['ingresos'].append(float(ingresos))
        resultado['gastos'].append(float(gastos))
    
    return resultado

# =========================================================
# 📅 PENDIENTES
# =========================================================
def get_pendiente(db: Session, pendiente_id: int):
    return db.query(models.Pendiente).filter(models.Pendiente.id == pendiente_id).first()

def get_pendientes(db: Session, usuario_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.Pendiente).filter(models.Pendiente.usuario_id == usuario_id).offset(skip).limit(limit).all()

def get_pendientes_by_filters(db: Session, usuario_id: int, estado: Optional[str] = None, prioridad: Optional[str] = None):
    query = db.query(models.Pendiente).filter(models.Pendiente.usuario_id == usuario_id)
    if estado:
        query = query.filter(models.Pendiente.estado == estado)
    if prioridad:
        query = query.filter(models.Pendiente.prioridad == prioridad)
    return query.all()

def create_pendiente(db: Session, pendiente: schemas.PendienteCreate, usuario_id: int):
    db_pendiente = models.Pendiente(**pendiente.model_dump(), usuario_id=usuario_id)
    db.add(db_pendiente)
    db.commit()
    db.refresh(db_pendiente)
    return db_pendiente

def update_pendiente(db: Session, pendiente_id: int, pendiente: schemas.PendienteUpdate):
    db_pendiente = get_pendiente(db, pendiente_id)
    if db_pendiente:
        for key, value in pendiente.model_dump(exclude_unset=True).items():
            setattr(db_pendiente, key, value)
        db.commit()
        db.refresh(db_pendiente)
    return db_pendiente

def delete_pendiente(db: Session, pendiente_id: int):
    db_pendiente = get_pendiente(db, pendiente_id)
    if db_pendiente:
        db.delete(db_pendiente)
        db.commit()
    return db_pendiente

def cambiar_estado_pendiente(db: Session, pendiente_id: int, estado: str):
    db_pendiente = get_pendiente(db, pendiente_id)
    if db_pendiente:
        db_pendiente.estado = estado
        db.commit()
        db.refresh(db_pendiente)
    return db_pendiente

def agregar_recordatorio(db: Session, pendiente_id: int, recordatorio: datetime):
    db_pendiente = get_pendiente(db, pendiente_id)
    if db_pendiente:
        db_pendiente.recordatorio = recordatorio
        db.commit()
        db.refresh(db_pendiente)
    return db_pendiente


# =========================================================
# 🔐 FUNCIONES PARA CONTRASEÑAS ENCRIPTADAS
# =========================================================
from cryptography.fernet import Fernet
import base64
import os
from passlib.context import CryptContext

# Configuración para hashing de contraseñas (SOLO para autenticación de usuarios)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Configuración para encriptación de contraseñas almacenadas (para servicios)
ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY", "default_key_should_be_changed_in_production_")
# Asegurar que la clave tenga 32 bytes en base64
fernet_key = base64.urlsafe_b64encode(ENCRYPTION_KEY.ljust(32)[:32].encode())
cipher_suite = Fernet(fernet_key)

def encriptar_contrasena(contrasena: str) -> str:
    """Encripta una contraseña usando Fernet (encriptación simétrica)"""
    return cipher_suite.encrypt(contrasena.encode()).decode()

def desencriptar_contrasena(contrasena_encriptada: str) -> str:
    """Desencripta una contraseña usando Fernet"""
    return cipher_suite.decrypt(contrasena_encriptada.encode()).decode()

# ELIMINA esta función de verificación para contraseñas de servicios
# (solo se usa para autenticación de usuarios)
# def verificar_contrasena(contrasena_plana: str, contrasena_encriptada: str) -> bool:
#     """Verifica si una contraseña coincide con su versión encriptada"""
#     return pwd_context.verify(contrasena_plana, contrasena_encriptada)

def obtener_contrasenas_usuario(db: Session, usuario_id: int, skip: int = 0, limit: int = 100):
    """Obtiene todas las contraseñas de un usuario"""
    return db.query(models.Contrasena).filter(
        models.Contrasena.usuario_id == usuario_id
    ).order_by(models.Contrasena.servicio).offset(skip).limit(limit).all()

def obtener_contrasena(db: Session, contrasena_id: int):
    """Obtiene una contraseña específica por ID"""
    return db.query(models.Contrasena).filter(
        models.Contrasena.id == contrasena_id
    ).first()

def crear_contrasena(db: Session, contrasena: schemas.ContrasenaCreate, usuario_id: int):
    """Crea una nueva contraseña encriptada"""
    contrasena_encriptada = encriptar_contrasena(contrasena.contrasena)
    db_contrasena = models.Contrasena(
        servicio=contrasena.servicio,
        usuario=contrasena.usuario,
        contrasena_encriptada=contrasena_encriptada,  # Usar Fernet, no bcrypt
        url=contrasena.url,
        notas=contrasena.notas,
        usuario_id=usuario_id
    )
    db.add(db_contrasena)
    db.commit()
    db.refresh(db_contrasena)
    return db_contrasena

def actualizar_contrasena(db: Session, contrasena_id: int, contrasena: schemas.ContrasenaUpdate, usuario_id: int):
    """Actualiza una contraseña existente"""
    db_contrasena = obtener_contrasena(db, contrasena_id)
    if not db_contrasena or db_contrasena.usuario_id != usuario_id:
        return None
    
    if contrasena.servicio is not None:
        db_contrasena.servicio = contrasena.servicio
    if contrasena.usuario is not None:
        db_contrasena.usuario = contrasena.usuario
    if contrasena.contrasena is not None:
        db_contrasena.contrasena_encriptada = encriptar_contrasena(contrasena.contrasena)
    if contrasena.url is not None:
        db_contrasena.url = contrasena.url
    if contrasena.notas is not None:
        db_contrasena.notas = contrasena.notas
    
    db.commit()
    db.refresh(db_contrasena)
    return db_contrasena

def eliminar_contrasena(db: Session, contrasena_id: int, usuario_id: int):
    """Elimina una contraseña"""
    db_contrasena = obtener_contrasena(db, contrasena_id)
    if not db_contrasena or db_contrasena.usuario_id != usuario_id:
        return False
    
    db.delete(db_contrasena)
    db.commit()
    return True

def desencriptar_contrasena_db(db: Session, contrasena_id: int, usuario_id: int):
    """
    Obtiene una contraseña desencriptada para mostrarla al usuario
    """
    contrasena = obtener_contrasena(db, contrasena_id)
    if not contrasena or contrasena.usuario_id != usuario_id:
        return None
    
    try:
        return desencriptar_contrasena(contrasena.contrasena_encriptada)
    except Exception as e:
        print(f"Error al desencriptar contraseña ID {contrasena_id}: {e}")
        return None
    


# =========================================================
# 🎂 CUMPLEAÑOS
# =========================================================

def crear_cumpleano(db: Session, cumpleano: schemas.CumpleanoCreate, usuario_id: int):
    """Crea un nuevo registro de cumpleaños"""
    db_cumpleano = models.Cumpleano(**cumpleano.model_dump(), usuario_id=usuario_id)
    db.add(db_cumpleano)
    db.commit()
    db.refresh(db_cumpleano)
    return db_cumpleano

def obtener_cumpleano(db: Session, cumpleano_id: int):
    """Obtiene un cumpleaños por ID"""
    return db.query(models.Cumpleano).filter(models.Cumpleano.id == cumpleano_id).first()

def obtener_cumpleanos_usuario(db: Session, usuario_id: int, skip: int = 0, limit: int = 100):
    """Obtiene todos los cumpleaños de un usuario"""
    return db.query(models.Cumpleano).filter(
        models.Cumpleano.usuario_id == usuario_id
    ).order_by(models.Cumpleano.fecha_nacimiento).offset(skip).limit(limit).all()

def obtener_cumpleanos_paginados(db: Session, usuario_id: int, page: int = 1, per_page: int = 10, relacion: Optional[str] = None):
    """Obtiene cumpleaños con paginación y filtros"""
    query = db.query(models.Cumpleano).filter(models.Cumpleano.usuario_id == usuario_id)
    
    if relacion:
        query = query.filter(models.Cumpleano.relacion == relacion)
    
    total = query.count()
    cumpleanos = query.order_by(models.Cumpleano.fecha_nacimiento).offset((page - 1) * per_page).limit(per_page).all()
    
    return {
        "cumpleanos": cumpleanos,
        "total_pages": (total + per_page - 1) // per_page,
        "current_page": page
    }

def actualizar_cumpleano(db: Session, cumpleano_id: int, cumpleano: schemas.CumpleanoUpdate, usuario_id: int):
    """Actualiza un cumpleaños existente"""
    db_cumpleano = obtener_cumpleano(db, cumpleano_id)
    if not db_cumpleano or db_cumpleano.usuario_id != usuario_id:
        return None
    
    for key, value in cumpleano.model_dump(exclude_unset=True).items():
        setattr(db_cumpleano, key, value)
    
    db.commit()
    db.refresh(db_cumpleano)
    return db_cumpleano

def eliminar_cumpleano(db: Session, cumpleano_id: int, usuario_id: int):
    """Elimina un cumpleaños"""
    db_cumpleano = obtener_cumpleano(db, cumpleano_id)
    if not db_cumpleano or db_cumpleano.usuario_id != usuario_id:
        return False
    
    db.delete(db_cumpleano)
    db.commit()
    return True

def obtener_proximos_cumpleanos(db: Session, usuario_id: int, dias: int = 30):
    """Obtiene los cumpleaños próximos dentro de X días"""
    hoy = date.today()
    cumpleanos = db.query(models.Cumpleano).filter(
        models.Cumpleano.usuario_id == usuario_id
    ).all()
    
    proximos = []
    for cumple in cumpleanos:
        dias_hasta = calcular_dias_hasta_cumpleanos(cumple.fecha_nacimiento)
        if 0 <= dias_hasta <= dias:
            proximos.append({
                "cumpleano": cumple,
                "dias_hasta": dias_hasta,
                "edad": calcular_edad(cumple.fecha_nacimiento)
            })
    
    # Ordenar por días hasta cumpleaños
    proximos.sort(key=lambda x: x['dias_hasta'])
    return proximos

def calcular_dias_hasta_cumpleanos(fecha_nacimiento: date) -> int:
    """Calcula cuántos días faltan para el próximo cumpleaños"""
    hoy = date.today()
    proximo_cumple = date(hoy.year, fecha_nacimiento.month, fecha_nacimiento.day)
    
    if proximo_cumple < hoy:
        proximo_cumple = date(hoy.year + 1, fecha_nacimiento.month, fecha_nacimiento.day)
    
    return (proximo_cumple - hoy).days

def calcular_edad(fecha_nacimiento: date) -> int:
    """Calcula la edad actual o la que cumplirá"""
    hoy = date.today()
    edad = hoy.year - fecha_nacimiento.year
    
    # Ajustar si aún no ha cumplido años este año
    if (hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day):
        edad -= 1
    
    return edad + 1  # +1 porque será la edad que cumplirá

def calcular_proximo_cumple(fecha_nacimiento: date) -> date:
    hoy = date.today()
    proximo = date(hoy.year, fecha_nacimiento.month, fecha_nacimiento.day)

    if proximo < hoy:
        proximo = date(hoy.year + 1, fecha_nacimiento.month, fecha_nacimiento.day)

    return proximo