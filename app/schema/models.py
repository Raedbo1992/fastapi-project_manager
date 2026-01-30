from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import relationship
from app.config.database import Base
import datetime

class Usuario(Base):
    __tablename__ = "usuarios"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    username = Column(String(255), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    rol = Column(String(50), default="user")  # ← AGREGAR esto
    fecha_registro = Column(DateTime, default=datetime.utcnow)  # ← AGREGAR esto
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relaciones (ya las tienes)
    categorias = relationship("Categoria", back_populates="usuario", cascade="all, delete-orphan")
    gastos = relationship("Gasto", back_populates="usuario", cascade="all, delete-orphan")
    ingresos = relationship("Ingreso", back_populates="usuario", cascade="all, delete-orphan")
    contrasenas = relationship("Contrasena", back_populates="usuario_rel", cascade="all, delete-orphan")
    cumpleanos = relationship("Cumpleano", back_populates="usuario", cascade="all, delete-orphan")

class Gasto(Base):
    __tablename__ = "gastos"
    
    id = Column(Integer, primary_key=True, index=True)
    descripcion = Column(String(200), nullable=False)
    monto = Column(Float, nullable=False)
    categoria = Column(String(100))
    fecha = Column(Date, nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))

class Ingreso(Base):
    __tablename__ = "ingresos"
    
    id = Column(Integer, primary_key=True, index=True)
    descripcion = Column(String(200), nullable=False)
    monto = Column(Float, nullable=False)
    fuente = Column(String(100))
    fecha = Column(Date, nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))

class Pendiente(Base):
    __tablename__ = "pendientes"
    
    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String(200), nullable=False)
    descripcion = Column(Text)  # Text no necesita longitud
    estado = Column(String(50), default="pendiente")
    prioridad = Column(String(50))
    fecha_creacion = Column(DateTime, default=datetime.datetime.utcnow)
    fecha_vencimiento = Column(Date)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))

class Cumpleanos(Base):
    __tablename__ = "cumpleanos"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    fecha = Column(Date, nullable=False)
    relacion = Column(String(100))
    notas = Column(Text)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))

class Contrasena(Base):
    __tablename__ = "contrasenas"
    
    id = Column(Integer, primary_key=True, index=True)
    servicio = Column(String(100), index=True)  # ← AGREGAR longitud
    usuario = Column(String(100))  # ← AGREGAR longitud
    contrasena_encriptada = Column(String(500))  # ← AGREGAR longitud (mayor porque está encriptada)
    url = Column(String(500), nullable=True)  # ← AGREGAR longitud
    notas = Column(Text, nullable=True)  # Text no necesita longitud
    created_at = Column(DateTime, default=datetime.utcnow)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    
    # Relación
    usuario_rel = relationship("Usuario", back_populates="contrasenas")