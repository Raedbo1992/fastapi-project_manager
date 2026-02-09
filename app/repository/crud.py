import bcrypt
import base64
import os
from datetime import date, datetime, timedelta
from typing import Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, extract, or_
from cryptography.fernet import Fernet
from passlib.context import CryptContext

from app.schema import models, schemas

# ============================================================================
# 🔐 CONFIGURACIÓN DE ENCRIPTACIÓN
# ============================================================================

# Configuración para hashing de contraseñas de usuarios (autenticación)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Configuración para encriptación de contraseñas de servicios
# IMPORTANTE: Cambia esta clave en producción o usa variable de entorno
ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY", "default_key_should_be_changed_in_production_")
fernet_key = base64.urlsafe_b64encode(ENCRYPTION_KEY.ljust(32)[:32].encode())
cipher_suite = Fernet(fernet_key)

# ============================================================================
# 🔐 FUNCIONES DE AUTENTICACIÓN
# ============================================================================

def hashear_password(password: str) -> str:
    """Hashea una contraseña usando bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verificar_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica si una contraseña coincide con su hash bcrypt"""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def obtener_usuario_por_username(db: Session, username: str):
    """Busca usuario por nombre de usuario"""
    return db.query(models.Usuario).filter(models.Usuario.username == username).first()

def obtener_usuario_por_email(db: Session, email: str):
    """Busca usuario por email"""
    return db.query(models.Usuario).filter(models.Usuario.email == email).first()

def obtener_usuario_por_id(db: Session, usuario_id: int):
    """Busca usuario por ID"""
    return db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()

def crear_usuario(db: Session, usuario: schemas.UsuarioCreate):
    """Crea un nuevo usuario con contraseña hasheada"""
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

# ============================================================================
# 🏷️ FUNCIONES DE CATEGORÍAS
# ============================================================================

def crear_categoria(db: Session, categoria: schemas.CategoriaCreate, usuario_id: int):
    """Crea una nueva categoría para un usuario"""
    db_categoria = models.Categoria(**categoria.model_dump(), usuario_id=usuario_id)
    db.add(db_categoria)
    db.commit()
    db.refresh(db_categoria)
    return db_categoria

def obtener_categorias(db: Session, usuario_id: int, tipo: Optional[str] = None):
    """Obtiene todas las categorías de un usuario, opcionalmente filtradas por tipo"""
    query = db.query(models.Categoria).filter(models.Categoria.usuario_id == usuario_id)
    if tipo:
        query = query.filter(models.Categoria.tipo == tipo)
    return query.all()

def obtener_categoria_por_nombre(db: Session, nombre: str, usuario_id: int):
    """Busca categoría por nombre para un usuario específico"""
    return db.query(models.Categoria).filter(
        and_(models.Categoria.nombre == nombre, models.Categoria.usuario_id == usuario_id)
    ).first()

def obtener_categoria_por_nombre_y_tipo(db: Session, nombre: str, tipo: str, usuario_id: int):
    """Busca categoría por nombre y tipo para un usuario específico"""
    return db.query(models.Categoria).filter(
        and_(
            models.Categoria.nombre == nombre,
            models.Categoria.tipo == tipo,
            models.Categoria.usuario_id == usuario_id
        )
    ).first()

# ============================================================================
# 💰 FUNCIONES DE INGRESOS
# ============================================================================

def crear_ingreso(db: Session, ingreso: schemas.IngresoCreate, usuario_id: int):
    """Crea un nuevo ingreso para un usuario"""
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
    """Obtiene un ingreso por ID con su categoría cargada"""
    return db.query(models.Ingreso).join(
        models.Categoria, models.Ingreso.categoria_id == models.Categoria.id
    ).filter(models.Ingreso.id == ingreso_id).first()

def actualizar_ingreso(db: Session, ingreso_id: int, ingreso: schemas.IngresoUpdate, usuario_id: int):
    """Actualiza un ingreso existente"""
    db_ingreso = obtener_ingreso(db, ingreso_id)
    if not db_ingreso or db_ingreso.usuario_id != usuario_id:
        return None
    for key, value in ingreso.model_dump(exclude_unset=True).items():
        setattr(db_ingreso, key, value)
    db.commit()
    db.refresh(db_ingreso)
    return db_ingreso

def eliminar_ingreso(db: Session, ingreso_id: int):
    """Elimina un ingreso"""
    db_ingreso = obtener_ingreso(db, ingreso_id)
    if db_ingreso:
        db.delete(db_ingreso)
        db.commit()
    return db_ingreso

def obtener_ingresos_paginados(db: Session, usuario_id: int, page: int = 1, 
                              tipo: Optional[str] = None, estado: Optional[str] = None, 
                              per_page: int = 10):
    """
    Obtiene ingresos paginados para un usuario específico
    
    Args:
        db: Sesión de base de datos
        usuario_id: ID del usuario
        page: Página actual
        tipo: Tipo de categoría para filtrar
        estado: Estado para filtrar ('recibido', 'pendiente', None = todos)
        per_page: Elementos por página
    
    Returns:
        Dict con ingresos y total de páginas
    """
    print(f"\n=== OBTENER INGRESOS PAGINADOS ===")
    print(f"Usuario ID: {usuario_id}")
    print(f"Filtros - tipo: '{tipo}', estado: '{estado}'")
    
    # Construir query base con join a categoría
    query = db.query(models.Ingreso).join(
        models.Categoria, models.Ingreso.categoria_id == models.Categoria.id
    ).filter(models.Ingreso.usuario_id == usuario_id)
    
    # Aplicar filtro por tipo (si se especifica)
    if tipo and tipo.strip():
        query = query.filter(models.Categoria.tipo == tipo.strip())
        print(f"✅ Aplicado filtro por tipo: '{tipo}'")
    
    # Aplicar filtro por estado (si se especifica)
    if estado in ['recibido', 'pendiente']:
        query = query.filter(models.Ingreso.estado == estado)
        print(f"✅ Aplicado filtro por estado: '{estado}'")
    
    # Contar total después de filtros
    total_filtrado = query.count()
    print(f"📊 Total después de filtros: {total_filtrado}")
    
    # Calcular offset y límite para paginación
    offset = (page - 1) * per_page
    
    # Obtener resultados paginados ordenados por fecha descendente
    ingresos = query.order_by(
        models.Ingreso.fecha.desc()
    ).offset(offset).limit(per_page).all()
    
    # Calcular total de páginas
    total_pages = 1
    if total_filtrado > 0:
        total_pages = (total_filtrado + per_page - 1) // per_page
    
    print(f"📖 Total de páginas: {total_pages}")
    
    return {
        "ingresos": ingresos,
        "total_pages": total_pages,
        "total_items": total_filtrado,
        "current_page": page,
        "per_page": per_page
    }

def obtener_ultimo_salario(db: Session, usuario_id: int):
    """Obtiene el último salario registrado por un usuario"""
    return db.query(models.Ingreso).filter(
        models.Ingreso.usuario_id == usuario_id,
    ).order_by(models.Ingreso.fecha.desc()).first()

def obtener_ingresos_mensuales(db: Session, usuario_id: int, year: int, month: int):
    """Obtiene la suma de ingresos de un usuario para un mes específico"""
    return db.query(func.coalesce(func.sum(models.Ingreso.valor), 0)).filter(
        models.Ingreso.usuario_id == usuario_id,
        extract('year', models.Ingreso.fecha) == year,
        extract('month', models.Ingreso.fecha) == month
    ).scalar()

def reparar_ingresos_corruptos(db: Session, usuario_id: int):
    """
    Encuentra y repara ingresos con categorías faltantes
    
    Args:
        db: Sesión de base de datos
        usuario_id: ID del usuario
    
    Returns:
        int: Número de ingresos reparados
    """
    print("=== REPARANDO INGRESOS CON CATEGORÍAS FALTANTES ===")
    
    # Encontrar ingresos con categoría_id que no existe
    todos_ingresos = db.query(models.Ingreso).filter(
        models.Ingreso.usuario_id == usuario_id
    ).all()
    
    problemas = []
    
    for ingreso in todos_ingresos:
        # Verificar si la categoría existe
        categoria = db.query(models.Categoria).filter(
            models.Categoria.id == ingreso.categoria_id
        ).first()
        
        if not categoria:
            problemas.append(ingreso)
            print(f"❌ Ingreso ID {ingreso.id} tiene categoría_id {ingreso.categoria_id} que NO EXISTE")
    
    # Reparar problemas
    if problemas:
        print(f"\nEncontrados {len(problemas)} ingresos con problemas")
        
        # Buscar o crear categoría por defecto
        categoria_default = db.query(models.Categoria).filter(
            models.Categoria.nombre == 'Sin Categoría',
            models.Categoria.usuario_id == usuario_id
        ).first()
        
        if not categoria_default:
            # Crear categoría por defecto
            categoria_default = models.Categoria(
                nombre='Sin Categoría',
                tipo='variable',
                usuario_id=usuario_id
            )
            db.add(categoria_default)
            db.commit()
            db.refresh(categoria_default)
            print(f"✅ Creada categoría por defecto ID: {categoria_default.id}")
        
        # Reparar ingresos
        for ingreso in problemas:
            print(f"Reparando ingreso ID {ingreso.id}: {ingreso.categoria_id} -> {categoria_default.id}")
            ingreso.categoria_id = categoria_default.id
        
        db.commit()
        print(f"✅ Reparados {len(problemas)} ingresos")
    else:
        print("✅ No se encontraron ingresos con problemas")
    
    return len(problemas)

# ============================================================================
# 💸 FUNCIONES DE GASTOS
# ============================================================================

def crear_gasto(db: Session, gasto: schemas.GastoCreate, usuario_id: int):
    """Crea un nuevo gasto para un usuario"""
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
    """Obtiene un gasto por ID"""
    return db.query(models.Gasto).filter(models.Gasto.id == gasto_id).first()

def actualizar_gasto(db: Session, gasto_id: int, gasto: schemas.GastoUpdate, usuario_id: int):
    """Actualiza un gasto existente"""
    db_gasto = obtener_gasto(db, gasto_id)
    if not db_gasto or db_gasto.usuario_id != usuario_id:
        return None
    for key, value in gasto.model_dump(exclude_unset=True).items():
        setattr(db_gasto, key, value)
    db.commit()
    db.refresh(db_gasto)
    return db_gasto

def eliminar_gasto(db: Session, gasto_id: int):
    """Elimina un gasto"""
    db_gasto = obtener_gasto(db, gasto_id)
    if db_gasto:
        db.delete(db_gasto)
        db.commit()
    return db_gasto

def obtener_gastos_paginados(db: Session, usuario_id: int, page: int = 1, 
                            page_size: int = 10, tipo: Optional[str] = None, 
                            pagado: Optional[bool] = None):
    """
    Obtiene gastos paginados para un usuario específico
    
    Args:
        db: Sesión de base de datos
        usuario_id: ID del usuario
        page: Página actual
        page_size: Elementos por página
        tipo: Tipo de categoría para filtrar
        pagado: Estado de pago para filtrar
    
    Returns:
        Dict con gastos, total de páginas y página actual
    """
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
    
    return {
        "gastos": gastos,
        "total_pages": total_pages,
        "current_page": page
    }

# ============================================================================
# 📊 FUNCIONES DE ESTADÍSTICAS
# ============================================================================

def calcular_variacion(anterior: float, actual: float) -> float:
    """
    Calcula la variación porcentual entre dos valores
    
    Args:
        anterior: Valor del periodo anterior
        actual: Valor del periodo actual
    
    Returns:
        float: Porcentaje de variación redondeado a 1 decimal
    """
    if anterior == 0:
        return 0.0
    
    variacion = ((actual - anterior) / anterior) * 100
    return round(variacion, 1)

def obtener_evolucion_mensual(db: Session, usuario_id: int, meses: int = 6) -> Dict[str, list]:
    """
    Obtiene la evolución histórica de ingresos y gastos por mes
    
    Args:
        db: Sesión de base de datos
        usuario_id: ID del usuario
        meses: Cantidad de meses históricos a incluir
    
    Returns:
        Dict con labels, ingresos y gastos por mes
    """
    hoy = datetime.now()
    resultado = {
        'labels': [],
        'ingresos': [],
        'gastos': []
    }
    
    # Recorrer los últimos N meses en orden cronológico
    for i in range(meses, 0, -1):
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
        
        # Formatear label (ej: "Ene 2023")
        nombre_mes = fecha_referencia.strftime('%b')
        resultado['labels'].append(f"{nombre_mes} {año}")
        resultado['ingresos'].append(float(ingresos))
        resultado['gastos'].append(float(gastos))
    
    return resultado

def obtener_estadisticas_dashboard(db: Session, usuario_id: int):
    """
    Obtiene todas las estadísticas para el dashboard
    
    Args:
        db: Sesión de base de datos
        usuario_id: ID del usuario
    
    Returns:
        DashboardStats: Objeto con todas las estadísticas
    """
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

# ============================================================================
# 📅 FUNCIONES DE PENDIENTES
# ============================================================================

def get_pendiente(db: Session, pendiente_id: int):
    """Obtiene un pendiente por ID"""
    return db.query(models.Pendiente).filter(models.Pendiente.id == pendiente_id).first()

def get_pendientes(db: Session, usuario_id: int, skip: int = 0, limit: int = 100):
    """Obtiene todos los pendientes de un usuario"""
    return db.query(models.Pendiente).filter(
        models.Pendiente.usuario_id == usuario_id
    ).offset(skip).limit(limit).all()

def get_pendientes_by_filters(db: Session, usuario_id: int, 
                             estado: Optional[str] = None, 
                             prioridad: Optional[str] = None):
    """Obtiene pendientes de un usuario con filtros opcionales"""
    query = db.query(models.Pendiente).filter(models.Pendiente.usuario_id == usuario_id)
    if estado:
        query = query.filter(models.Pendiente.estado == estado)
    if prioridad:
        query = query.filter(models.Pendiente.prioridad == prioridad)
    return query.all()

def create_pendiente(db: Session, pendiente: schemas.PendienteCreate, usuario_id: int):
    """Crea un nuevo pendiente"""
    db_pendiente = models.Pendiente(**pendiente.model_dump(), usuario_id=usuario_id)
    db.add(db_pendiente)
    db.commit()
    db.refresh(db_pendiente)
    return db_pendiente

def update_pendiente(db: Session, pendiente_id: int, pendiente: schemas.PendienteUpdate):
    """Actualiza un pendiente existente"""
    db_pendiente = get_pendiente(db, pendiente_id)
    if db_pendiente:
        for key, value in pendiente.model_dump(exclude_unset=True).items():
            setattr(db_pendiente, key, value)
        db.commit()
        db.refresh(db_pendiente)
    return db_pendiente

def delete_pendiente(db: Session, pendiente_id: int):
    """Elimina un pendiente"""
    db_pendiente = get_pendiente(db, pendiente_id)
    if db_pendiente:
        db.delete(db_pendiente)
        db.commit()
    return db_pendiente

def cambiar_estado_pendiente(db: Session, pendiente_id: int, estado: str):
    """Cambia el estado de un pendiente"""
    db_pendiente = get_pendiente(db, pendiente_id)
    if db_pendiente:
        db_pendiente.estado = estado
        db.commit()
        db.refresh(db_pendiente)
    return db_pendiente

def agregar_recordatorio(db: Session, pendiente_id: int, recordatorio: datetime):
    """Agrega o actualiza el recordatorio de un pendiente"""
    db_pendiente = get_pendiente(db, pendiente_id)
    if db_pendiente:
        db_pendiente.recordatorio = recordatorio
        db.commit()
        db.refresh(db_pendiente)
    return db_pendiente

# ============================================================================
# 🔐 FUNCIONES PARA CONTRASEÑAS ENCRIPTADAS
# ============================================================================

def encriptar_contrasena(contrasena: str) -> str:
    """Encripta una contraseña usando Fernet (encriptación simétrica)"""
    return cipher_suite.encrypt(contrasena.encode()).decode()

def desencriptar_contrasena(contrasena_encriptada: str) -> str:
    """Desencripta una contraseña usando Fernet"""
    return cipher_suite.decrypt(contrasena_encriptada.encode()).decode()

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
        contrasena_encriptada=contrasena_encriptada,
        url=contrasena.url,
        notas=contrasena.notas,
        usuario_id=usuario_id
    )
    db.add(db_contrasena)
    db.commit()
    db.refresh(db_contrasena)
    return db_contrasena

def actualizar_contrasena(db: Session, contrasena_id: int, 
                         contrasena: schemas.ContrasenaUpdate, usuario_id: int):
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

# ============================================================================
# 🎂 FUNCIONES DE CUMPLEAÑOS
# ============================================================================

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

def obtener_cumpleanos_paginados(db: Session, usuario_id: int, page: int = 1, 
                                per_page: int = 10, relacion: Optional[str] = None):
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

def actualizar_cumpleano(db: Session, cumpleano_id: int, 
                        cumpleano: schemas.CumpleanoUpdate, usuario_id: int):
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
    """Calcula la fecha del próximo cumpleaños"""
    hoy = date.today()
    proximo = date(hoy.year, fecha_nacimiento.month, fecha_nacimiento.day)

    if proximo < hoy:
        proximo = date(hoy.year + 1, fecha_nacimiento.month, fecha_nacimiento.day)

    return proximo



# ============================================================================
# 💳 FUNCIONES DE CRÉDITOS
# ============================================================================

def calcular_cuota_credito(monto: float, interes_mensual: float, plazo_meses: int, 
                          frecuencia: str = 'mensual') -> float:
    """
    Calcula la cuota de un crédito usando fórmula de amortización francesa
    
    Args:
        monto: Monto del crédito
        interes_mensual: Tasa de interés MENSUAL en porcentaje (ej: 1.4 para 1.4%)
        plazo_meses: Plazo en meses
        frecuencia: Frecuencia de pago ('mensual' principalmente)
    
    Returns:
        Cuota calculada (solo del crédito, sin seguro)
    
    Ejemplo:
        Crédito: $48,000,000
        Interés: 1.4% mensual
        Plazo: 72 meses
        Cuota esperada: $1,180,000
    """
    if interes_mensual == 0:
        # Sin interés, dividir el monto entre el plazo
        return round(monto / plazo_meses, 2)
    
    # Convertir interés de porcentaje a decimal
    i = interes_mensual / 100
    
    # Número de cuotas según frecuencia
    if frecuencia == 'quincenal':
        i = i / 2  # Interés quincenal
        n = plazo_meses * 2
    elif frecuencia == 'semanal':
        i = i / 4  # Interés semanal
        n = plazo_meses * 4
    elif frecuencia == 'diario':
        i = i / 30  # Interés diario
        n = plazo_meses * 30
    else:  # mensual (por defecto)
        n = plazo_meses
    
    # Fórmula de amortización francesa: 
    # Cuota = P * [i * (1 + i)^n] / [(1 + i)^n - 1]
    try:
        numerador = i * pow(1 + i, n)
        denominador = pow(1 + i, n) - 1
        cuota = monto * (numerador / denominador)
        
        # Redondear a 2 decimales
        return round(cuota, 2)
    except Exception as e:
        print(f"Error en cálculo de cuota: {e}")
        return 0.0

def crear_credito(db: Session, credito: schemas.CreditoCreate, usuario_id: int):
    """Crea un nuevo crédito para un usuario"""
    try:
        # ✅ DECISIÓN: ¿Usar cuota manual o calcular?
        if credito.cuota_manual and credito.cuota_manual > 0:
            # Usar la cuota manual proporcionada por el usuario
            cuota = credito.cuota_manual
            print(f"📌 USANDO CUOTA MANUAL: ${cuota:,.2f}")
        else:
            # Calcular cuota automáticamente
            cuota = calcular_cuota_credito(
                credito.monto,
                credito.interes,
                credito.plazo_meses,
                credito.frecuencia_pago
            )
            print(f"🧮 CUOTA CALCULADA: ${cuota:,.2f}")
        
        print(f"\n💳 CREANDO CRÉDITO:")
        print(f"   Monto: ${credito.monto:,.2f}")
        print(f"   Interés: {credito.interes}% mensual")
        print(f"   Plazo: {credito.plazo_meses} meses")
        print(f"   Cuota manual: ${credito.cuota_manual:,.2f}" if credito.cuota_manual else "   Cuota manual: No usada")
        print(f"   Cuota a usar: ${cuota:,.2f}")
        print(f"   Seguro: ${credito.seguro:,.2f}")
        print(f"   Cuota total: ${cuota + credito.seguro:,.2f}")
        
        # Calcular total a pagar (cuota + seguro) * número de cuotas
        if credito.frecuencia_pago == 'quincenal':
            total_cuotas = credito.plazo_meses * 2
        elif credito.frecuencia_pago == 'semanal':
            total_cuotas = credito.plazo_meses * 4
        elif credito.frecuencia_pago == 'diario':
            total_cuotas = credito.plazo_meses * 30
        else:  # mensual
            total_cuotas = credito.plazo_meses
        
        total_pagar = (cuota + credito.seguro) * total_cuotas
        
        # Crear crédito
        db_credito = models.Credito(
            nombre_credito=credito.nombre_credito,
            monto=credito.monto,
            interes=credito.interes,
            plazo_meses=credito.plazo_meses,
            frecuencia_pago=credito.frecuencia_pago,
            fecha_inicio=credito.fecha_inicio,
            cuota_manual=credito.cuota_manual,  # ✅ Guardamos el valor manual
            cuota=cuota,  # Esta es la cuota que realmente se usará (manual o calculada)
            seguro=credito.seguro,
            total_pagar=total_pagar,
            saldo_actual=credito.monto,
            estado='activo',
            observaciones=credito.observaciones,
            usuario_id=usuario_id
        )
        
        db.add(db_credito)
        db.commit()
        db.refresh(db_credito)
        
        print(f"✅ Crédito creado con ID: {db_credito.id}")
        
        return db_credito
        
    except Exception as e:
        print(f"❌ Error al crear crédito: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return None

def obtener_credito(db: Session, credito_id: int):
    """Obtiene un crédito por ID"""
    return db.query(models.Credito).filter(models.Credito.id == credito_id).first()

def obtener_creditos_paginados(db: Session, usuario_id: int, page: int = 1,
                               page_size: int = 10, estado: Optional[str] = None,
                               frecuencia: Optional[str] = None):
    """Obtiene créditos paginados con filtros"""
    query = db.query(models.Credito).filter(models.Credito.usuario_id == usuario_id)
    
    if estado:
        query = query.filter(models.Credito.estado == estado)
    
    if frecuencia:
        query = query.filter(models.Credito.frecuencia_pago == frecuencia)
    
    total_items = query.count()
    total_pages = (total_items + page_size - 1) // page_size if total_items > 0 else 1
    
    creditos = query.order_by(models.Credito.fecha_inicio.desc()) \
                    .offset((page - 1) * page_size) \
                    .limit(page_size) \
                    .all()
    
    return {
        "creditos": creditos,
        "total_pages": total_pages,
        "current_page": page
    }

def actualizar_credito(db: Session, credito_id: int, credito: schemas.CreditoUpdate, usuario_id: int):
    """Actualiza un crédito existente"""
    db_credito = obtener_credito(db, credito_id)
    if not db_credito or db_credito.usuario_id != usuario_id:
        return None
    
    # Recalcular cuota si cambiaron monto, interés, plazo o frecuencia
    recalcular = any([
        credito.monto is not None,
        credito.interes is not None,
        credito.plazo_meses is not None,
        credito.frecuencia_pago is not None
    ])
    
    if recalcular:
        monto = credito.monto if credito.monto is not None else db_credito.monto
        interes = credito.interes if credito.interes is not None else db_credito.interes
        plazo = credito.plazo_meses if credito.plazo_meses is not None else db_credito.plazo_meses
        frecuencia = credito.frecuencia_pago if credito.frecuencia_pago is not None else db_credito.frecuencia_pago
        
        nueva_cuota = calcular_cuota_credito(monto, interes, plazo, frecuencia)
        
        if frecuencia == 'quincenal':
            total_cuotas = plazo * 2
        elif frecuencia == 'semanal':
            total_cuotas = plazo * 4
        elif frecuencia == 'diario':
            total_cuotas = plazo * 30
        else:
            total_cuotas = plazo
        
        seguro = credito.seguro if credito.seguro is not None else db_credito.seguro
        
        db_credito.cuota = nueva_cuota
        db_credito.total_pagar = (nueva_cuota + seguro) * total_cuotas
    
    # Actualizar otros campos
    for key, value in credito.model_dump(exclude_unset=True).items():
        if key not in ['cuota', 'total_pagar']:  # Estos se calculan automáticamente
            setattr(db_credito, key, value)
    
    # Si solo cambió el seguro, recalcular total_pagar
    if credito.seguro is not None and not recalcular:
        if db_credito.frecuencia_pago == 'quincenal':
            total_cuotas = db_credito.plazo_meses * 2
        elif db_credito.frecuencia_pago == 'semanal':
            total_cuotas = db_credito.plazo_meses * 4
        elif db_credito.frecuencia_pago == 'diario':
            total_cuotas = db_credito.plazo_meses * 30
        else:
            total_cuotas = db_credito.plazo_meses
        
        db_credito.total_pagar = (db_credito.cuota + credito.seguro) * total_cuotas
    
    db.commit()
    db.refresh(db_credito)
    return db_credito


def actualizar_credito(db: Session, credito_id: int, credito: schemas.CreditoUpdate, usuario_id: int):
    """Actualiza un crédito existente - VERSIÓN CORREGIDA"""
    db_credito = obtener_credito(db, credito_id)
    if not db_credito or db_credito.usuario_id != usuario_id:
        return None
    
    # ✅ CORREGIDO: Inicializar variables
    recalcular_total = False
    cuota_a_usar = db_credito.cuota
    ha_cambiado_cuota_manual = False
    
    # 🔹 1. Si cambia la cuota manual
    if credito.cuota_manual is not None:
        db_credito.cuota_manual = credito.cuota_manual
        ha_cambiado_cuota_manual = True
        
        if credito.cuota_manual > 0:
            # MODO MANUAL: Usar valor del banco
            cuota_a_usar = credito.cuota_manual
            print(f"🏦 Actualizando a CUOTA MANUAL: ${cuota_a_usar:,.2f}")
        else:
            # MODO CÁLCULO: Volver a calcular
            cuota_a_usar = calcular_cuota_credito(
                db_credito.monto, db_credito.interes, 
                db_credito.plazo_meses, db_credito.frecuencia_pago
            )
            print(f"📐 Volviendo a CÁLCULO AUTOMÁTICO: ${cuota_a_usar:,.2f}")
        
        recalcular_total = True
        db_credito.cuota = cuota_a_usar
    
    # 🔹 2. Si cambian parámetros de cálculo (monto, interés, plazo, frecuencia)
    parametros_modificados = any([
        credito.monto is not None,
        credito.interes is not None,
        credito.plazo_meses is not None,
        credito.frecuencia_pago is not None
    ])
    
    if parametros_modificados and not ha_cambiado_cuota_manual:
        # Determinar valores nuevos o mantener actuales
        monto = credito.monto if credito.monto is not None else db_credito.monto
        interes = credito.interes if credito.interes is not None else db_credito.interes
        plazo = credito.plazo_meses if credito.plazo_meses is not None else db_credito.plazo_meses
        frecuencia = credito.frecuencia_pago if credito.frecuencia_pago is not None else db_credito.frecuencia_pago
        
        # ¿Usar cuota manual existente o recalcular?
        if db_credito.cuota_manual and db_credito.cuota_manual > 0:
            # Mantener cuota manual (no recalcular aunque cambien parámetros)
            cuota_a_usar = db_credito.cuota_manual
            print(f"📌 Manteniendo CUOTA MANUAL existente: ${cuota_a_usar:,.2f}")
        else:
            # Calcular nueva cuota
            cuota_a_usar = calcular_cuota_credito(monto, interes, plazo, frecuencia)
            print(f"🔄 Recalculando cuota: ${cuota_a_usar:,.2f}")
        
        recalcular_total = True
        db_credito.cuota = cuota_a_usar
    
    # 🔹 3. Recalcular total_pagar si es necesario
    if recalcular_total or credito.seguro is not None:
        # Determinar número de cuotas según frecuencia
        frecuencia_actual = credito.frecuencia_pago if credito.frecuencia_pago is not None else db_credito.frecuencia_pago
        plazo_actual = credito.plazo_meses if credito.plazo_meses is not None else db_credito.plazo_meses
        
        if frecuencia_actual == 'quincenal':
            total_cuotas = plazo_actual * 2
        elif frecuencia_actual == 'semanal':
            total_cuotas = plazo_actual * 4
        elif frecuencia_actual == 'diario':
            total_cuotas = plazo_actual * 30
        else:
            total_cuotas = plazo_actual
        
        # Determinar seguro actual
        seguro_actual = credito.seguro if credito.seguro is not None else db_credito.seguro
        
        # Calcular total a pagar
        db_credito.total_pagar = (cuota_a_usar + seguro_actual) * total_cuotas
    
    # 🔹 4. Actualizar otros campos
    for key, value in credito.model_dump(exclude_unset=True).items():
        if key not in ['cuota', 'total_pagar', 'cuota_manual']:  # Estos ya los manejamos
            setattr(db_credito, key, value)
    
    # 🔹 5. Recalcular cuota_calculada (siempre)
    db_credito.cuota_calculada = calcular_cuota_credito(
        db_credito.monto, db_credito.interes, 
        db_credito.plazo_meses, db_credito.frecuencia_pago
    )
    
    db.commit()
    db.refresh(db_credito)
    
    print(f"✅ Crédito actualizado")
    print(f"   Cuota real: ${db_credito.cuota:,.2f}")
    print(f"   Cuota calculada: ${db_credito.cuota_calculada:,.2f}")
    
    return db_credito


def eliminar_credito(db: Session, credito_id: int, usuario_id: int):
    """Elimina un crédito"""
    db_credito = obtener_credito(db, credito_id)
    if not db_credito or db_credito.usuario_id != usuario_id:
        return False
    
    db.delete(db_credito)
    db.commit()
    return True



# ============================================================================
# 📇 FUNCIONES DE CONTACTOS
# ============================================================================

def crear_contacto(db: Session, contacto: schemas.ContactoCreate, usuario_id: int):
    """Crea un nuevo contacto para un usuario"""
    db_contacto = models.Contacto(**contacto.model_dump(), usuario_id=usuario_id)
    db.add(db_contacto)
    db.commit()
    db.refresh(db_contacto)
    return db_contacto

def obtener_contacto(db: Session, contacto_id: int):
    """Obtiene un contacto por ID"""
    return db.query(models.Contacto).filter(models.Contacto.id == contacto_id).first()

def obtener_contactos_usuario(db: Session, usuario_id: int, skip: int = 0, limit: int = 100):
    """Obtiene todos los contactos de un usuario"""
    return db.query(models.Contacto).filter(
        models.Contacto.usuario_id == usuario_id
    ).order_by(models.Contacto.nombres).offset(skip).limit(limit).all()

def obtener_contactos_paginados(db: Session, usuario_id: int, page: int = 1, 
                               per_page: int = 10, categoria: Optional[str] = None):
    """
    Obtiene contactos paginados para un usuario específico
    
    Args:
        db: Sesión de base de datos
        usuario_id: ID del usuario
        page: Página actual
        per_page: Elementos por página
        categoria: Categoría para filtrar
    
    Returns:
        Dict con contactos, total de páginas y página actual
    """
    query = db.query(models.Contacto).filter(models.Contacto.usuario_id == usuario_id)
    
    if categoria and categoria != "":
        query = query.filter(models.Contacto.categoria == categoria)
    
    total_items = query.count()
    total_pages = (total_items + per_page - 1) // per_page if total_items > 0 else 1
    
    # Ajustar página
    if page < 1:
        page = 1
    elif page > total_pages and total_pages > 0:
        page = total_pages
    
    contactos = query.order_by(models.Contacto.nombres, models.Contacto.apellidos) \
                    .offset((page - 1) * per_page) \
                    .limit(per_page) \
                    .all()
    
    return {
        "contactos": contactos,
        "total_pages": total_pages,
        "current_page": page,
        "total_items": total_items
    }

def actualizar_contacto(db: Session, contacto_id: int, 
                       contacto: schemas.ContactoUpdate, usuario_id: int):
    """Actualiza un contacto existente"""
    db_contacto = obtener_contacto(db, contacto_id)
    if not db_contacto or db_contacto.usuario_id != usuario_id:
        return None
    
    for key, value in contacto.model_dump(exclude_unset=True).items():
        setattr(db_contacto, key, value)
    
    db.commit()
    db.refresh(db_contacto)
    return db_contacto

def eliminar_contacto(db: Session, contacto_id: int, usuario_id: int):
    """Elimina un contacto"""
    db_contacto = obtener_contacto(db, contacto_id)
    if not db_contacto or db_contacto.usuario_id != usuario_id:
        return False
    
    db.delete(db_contacto)
    db.commit()
    return True

def buscar_contactos(db: Session, usuario_id: int, busqueda: str):
    """Busca contactos por nombre, apellido, empresa o teléfono"""
    query = db.query(models.Contacto).filter(models.Contacto.usuario_id == usuario_id)
    
    # Búsqueda en múltiples campos
    busqueda_like = f"%{busqueda}%"
    resultados = query.filter(
        or_(
            models.Contacto.nombres.ilike(busqueda_like),
            models.Contacto.apellidos.ilike(busqueda_like),
            models.Contacto.empresa.ilike(busqueda_like),
            models.Contacto.telefono1.ilike(busqueda_like),
            models.Contacto.celular1.ilike(busqueda_like),
            models.Contacto.email.ilike(busqueda_like)
        )
    ).all()
    
    return resultados
