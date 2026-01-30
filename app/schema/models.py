from datetime import date, datetime
from typing import Optional, Dict, List, Union
from sqlalchemy import Column, Integer, String, Text, Enum, ForeignKey, Boolean, Date, DateTime, DECIMAL, UniqueConstraint
from sqlalchemy.orm import relationship
from app.config.database import Base
from sqlalchemy.sql import func
from sqlalchemy.orm import configure_mappers
from pydantic import BaseModel, ConfigDict

# ----------------------------------------
# 📌 Esquema para crear Gasto (Pydantic)
# ----------------------------------------
class GastoCreate(BaseModel):
    categoria_id: int
    valor: float
    fecha_limite: Optional[date] = None
    pagado: bool = False
    notas: Optional[str] = None

# ----------------------------------------
# 📌 Modelo Usuario
# ----------------------------------------
class Usuario(Base):
    __tablename__ = "usuarios"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    username = Column(String(255), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    rol = Column(String(50), default="user")  # ← AGREGADO
    fecha_registro = Column(DateTime, default=datetime.utcnow)  # ← AGREGADO
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relaciones
    categorias = relationship("Categoria", back_populates="usuario", cascade="all, delete-orphan")
    gastos = relationship("Gasto", back_populates="usuario", cascade="all, delete-orphan")
    ingresos = relationship("Ingreso", back_populates="usuario", cascade="all, delete-orphan")
    contrasenas = relationship("Contrasena", back_populates="usuario_rel", cascade="all, delete-orphan")
    cumpleanos = relationship("Cumpleano", back_populates="usuario", cascade="all, delete-orphan")

# ----------------------------------------
# 📌 Modelo Categoria
# ----------------------------------------
class Categoria(Base):
    __tablename__ = "categorias"
    __table_args__ = (
        UniqueConstraint('nombre', 'usuario_id', name='uk_categoria_usuario'),
    )

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    tipo = Column(Enum('fijo', 'variable', 'opcional', name='tipo_categoria_enum'), nullable=False)
    usuario_id = Column(Integer, ForeignKey('usuarios.id'), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relaciones
    usuario = relationship("Usuario", back_populates="categorias")
    gastos = relationship("Gasto", back_populates="categoria", cascade="all, delete-orphan")
    ingresos = relationship("Ingreso", back_populates="categoria", cascade="all, delete-orphan")

# ----------------------------------------
# 📌 Modelo Gasto
# ----------------------------------------
class Gasto(Base):
    __tablename__ = "gastos"

    id = Column(Integer, primary_key=True, index=True)
    categoria_id = Column(Integer, ForeignKey('categorias.id'), nullable=False)
    usuario_id = Column(Integer, ForeignKey('usuarios.id'), nullable=False)
    valor = Column(DECIMAL(12, 2), nullable=False)
    fecha_limite = Column(Date)
    pagado = Column(Boolean, default=False)
    notas = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relaciones
    categoria = relationship("Categoria", back_populates="gastos")
    usuario = relationship("Usuario", back_populates="gastos")

# ----------------------------------------
# 📌 Modelo Ingreso
# ----------------------------------------
class Ingreso(Base):
    __tablename__ = "ingresos"

    id = Column(Integer, primary_key=True, index=True)
    categoria_id = Column(Integer, ForeignKey('categorias.id'), nullable=False)
    usuario_id = Column(Integer, ForeignKey('usuarios.id'), nullable=False)
    valor = Column(DECIMAL(12, 2), nullable=False)
    fecha = Column(Date, nullable=False)
    es_salario = Column(Boolean, default=False)
    recurrente = Column(Boolean, default=False)
    notas = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relaciones
    usuario = relationship("Usuario", back_populates="ingresos")
    categoria = relationship("Categoria", back_populates="ingresos")

# ----------------------------------------
# 📌 Esquemas Pydantic para Ingreso
# ----------------------------------------
class IngresoCreate(BaseModel):
    valor: float
    fecha: date
    notas: Optional[str] = None

class IngresoUpdate(IngresoCreate):
    pass

# ----------------------------------------
# 📌 Modelo Pendiente
# ----------------------------------------
class Pendiente(Base):
    __tablename__ = 'pendientes'
    
    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String(255), nullable=False)
    descripcion = Column(Text)
    estado = Column(Enum('pendiente', 'en_progreso', 'completado', 'cancelado', name='estado_pendiente'), nullable=False, default='pendiente')
    prioridad = Column(Enum('baja', 'media', 'alta', 'urgente', name='prioridad_pendiente'), nullable=False, default='media')
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())
    fecha_limite = Column(DateTime(timezone=True))
    recordatorio = Column(DateTime(timezone=True))
    usuario_id = Column(Integer, ForeignKey('usuarios.id'), nullable=False)

# ----------------------------------------
# 📌 Dashboard Stats (Pydantic)
# ----------------------------------------
class DashboardStats(BaseModel):
    salario_actual: float
    total_gastos: float
    total_ingresos: float
    saldo_disponible: float
    gastos_por_categoria: Dict[str, float]
    gastos_por_tipo: Dict[str, float]
    variacion_ingresos: float = 0.0
    variacion_gastos: float = 0.0
    porcentaje_ahorro: float = 0.0
    categoria_mayor: Dict[str, Union[str, float]] = {
        'nombre': 'Ninguna',
        'valor': 0.0,
        'porcentaje': 0.0
    }
    evolucion_mensual: Dict[str, List] = {
        'labels': [],
        'ingresos': [],
        'gastos': []
    }
    promedio_mensual: float = 0.0
    porcentaje_fijos: float = 0.0
    porcentaje_variables: float = 0.0

    model_config = ConfigDict(from_attributes=True)

# ----------------------------------------
# 📌 Modelo Contraseña
# ----------------------------------------
class Contrasena(Base):
    __tablename__ = "contrasenas"
    
    id = Column(Integer, primary_key=True, index=True)
    servicio = Column(String(100), index=True)  # ← CORREGIDO: agregada longitud
    usuario = Column(String(100))  # ← CORREGIDO: agregada longitud
    contrasena_encriptada = Column(String(500))  # ← CORREGIDO: agregada longitud
    url = Column(String(500), nullable=True)  # ← CORREGIDO: agregada longitud
    notas = Column(Text, nullable=True)  # ← CORREGIDO: Text en lugar de String
    created_at = Column(DateTime, default=datetime.utcnow)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    
    # Relación
    usuario_rel = relationship("Usuario", back_populates="contrasenas")

# ----------------------------------------
# 📌 Modelo Cumpleaño
# ----------------------------------------
class Cumpleano(Base):
    __tablename__ = "cumpleanos"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre_persona = Column(String(100), nullable=False)
    fecha_nacimiento = Column(Date, nullable=False)
    telefono = Column(String(20), nullable=True)
    email = Column(String(100), nullable=True)
    relacion = Column(String(50), nullable=True)
    notas = Column(Text, nullable=True)
    notificar_dias_antes = Column(Integer, default=7)
    usuario_id = Column(Integer, ForeignKey('usuarios.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relación
    usuario = relationship("Usuario", back_populates="cumpleanos")

# ----------------------------------------
# 📌 Configuración explícita de mapeadores
# ----------------------------------------
configure_mappers()