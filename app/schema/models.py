from datetime import date, datetime
from typing import Optional, Dict, List
from sqlalchemy import Column, Float, Integer, String, Text, Enum, ForeignKey, Boolean, Date, DateTime, DECIMAL, UniqueConstraint
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
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relaciones
    categorias = relationship("Categoria", back_populates="usuario", cascade="all, delete-orphan")
    gastos = relationship("Gasto", back_populates="usuario", cascade="all, delete-orphan")
    ingresos = relationship("Ingreso", back_populates="usuario", cascade="all, delete-orphan") 
    contrasenas = relationship("Contrasena", back_populates="usuario_rel", cascade="all, delete-orphan")
    cumpleanos = relationship("Cumpleano", back_populates="usuario", cascade="all, delete-orphan")
    creditos = relationship("Credito", back_populates="usuario", cascade="all, delete-orphan")
    contactos = relationship("Contacto", back_populates="usuario", cascade="all, delete-orphan")



# ============================================================================
# MODELO CRÉDITO (DEBE IR DESPUÉS DE USUARIO)
# ============================================================================
class Credito(Base):
    __tablename__ = "creditos"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre_credito = Column(String(200))
    monto = Column(Float)
    interes = Column(Float)
    plazo_meses = Column(Integer)
    frecuencia_pago = Column(String(20), default='mensual')
    fecha_inicio = Column(Date)
    
    # ✅ DOS MODOS DE CUOTA
    cuota_manual = Column(Float, default=0.0)      # Lo que ingresa el usuario
    cuota = Column(Float)                          # Lo que REALMENTE se paga
    cuota_calculada = Column(Float, nullable=True) # Lo que dice la fórmula
    
    seguro = Column(Float, default=0.0)
    total_pagar = Column(Float)
    saldo_actual = Column(Float)
    estado = Column(String(20), default='activo')
    observaciones = Column(Text, nullable=True)
    usuario_id = Column(Integer, ForeignKey('usuarios.id'))
    
    # ✅ RELACIÓN CORREGIDA
    usuario = relationship("Usuario", back_populates="creditos")
    pagos = relationship("Pago", back_populates="credito", cascade="all, delete-orphan")
    
    # Propiedades calculadas
    @property
    def cuota_total(self):
        """Cuota total a pagar (crédito + seguro)"""
        return float(self.cuota) + float(self.seguro)
    
    @property
    def modo_calculo(self):
        """Indica el modo de cálculo actual"""
        if self.cuota_manual and self.cuota_manual > 0:
            return "🏦 MODO BANCO (manual)"
        return "📐 MODO CÁLCULO (automático)"
    
    @property
    def diferencia(self):
        """Diferencia entre cuota real y calculada"""
        if self.cuota_calculada:
            diferencia = self.cuota - self.cuota_calculada
            return diferencia
        return 0.0


# ============================================================================
# 💰 MODELO PAGO - AGREGAR EN models.py
# ============================================================================
class Pago(Base):
    """Modelo para pagos de créditos"""
    __tablename__ = "pagos"
    
    id = Column(Integer, primary_key=True, index=True)
    credito_id = Column(Integer, ForeignKey("creditos.id", ondelete="CASCADE"), nullable=False)
    monto = Column(DECIMAL(12, 2), nullable=False)  # Usa DECIMAL para montos grandes
    fecha_pago = Column(Date, nullable=False)
    comprobante = Column(String(100), nullable=False)
    notas = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relación con Crédito (AGREGA ESTO EN LA CLASE Credito también)
    credito = relationship("Credito", back_populates="pagos")
    
    def __repr__(self):
        return f"<Pago {self.id} - ${self.monto:,.2f} - {self.fecha_pago}>"


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
    ingresos = relationship("Ingreso", back_populates="categoria", cascade="all, delete-orphan")  # ✅ Se agregó para que funcione Ingreso

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
    estado = Column(Enum('pendiente', 'recibido', name='estado_ingreso_enum'), nullable=False, default='pendiente')  # ✅ VERIFICAR QUE EXISTA
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


from typing import Union  # Añade esto al inicio de tus imports

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
    categoria_mayor: Dict[str, Union[str, float]] = {  # Cambiado para aceptar string o float
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
    servicio = Column(String, index=True)
    usuario = Column(String)
    contrasena_encriptada = Column(String)  # Este campo debe llamarse así
    url = Column(String, nullable=True)
    notas = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    
    # Relación
    usuario_rel = relationship("Usuario", back_populates="contrasenas")
    
# Agrega esta relación al modelo Usuario
# En la clase Usuario, añade:
contrasenas = relationship("Contrasena", back_populates="usuario_rel", cascade="all, delete-orphan")


# 🎂 AGREGAR ESTA CLASE AL FINAL
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
# 📌 Modelo Contacto
# ----------------------------------------
# En models.py, modifica la clase Contacto:
class Contacto(Base):
    __tablename__ = "contactos"
    
    id = Column(Integer, primary_key=True, index=True)
    nombres = Column(String(100), nullable=False)
    apellidos = Column(String(100), nullable=False)
    categoria = Column(Enum('familia', 'amigos', 'trabajo', 'servicios', 'educacion', 'otro', name='categoria_contacto_enum'), nullable=False, default='otro')
    direccion = Column(String(200), nullable=True)
    celular1 = Column(String(20), nullable=False)  # Obligatorio
    celular2 = Column(String(20), nullable=True)   # Opcional
    email = Column(String(100), nullable=True)
    notas = Column(Text, nullable=True)
    usuario_id = Column(Integer, ForeignKey('usuarios.id'), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relación
    usuario = relationship("Usuario", back_populates="contactos")
# ----------------------------------------
# 📌 Configuración explícita de mapeadores
# ----------------------------------------
configure_mappers()
