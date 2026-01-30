from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.config.database import Base
import datetime

class Usuario(Base):
    __tablename__ = "usuarios"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    rol = Column(String(50), default="user")
    fecha_registro = Column(DateTime, default=datetime.datetime.utcnow)

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
    servicio = Column(String(100), nullable=False)
    usuario = Column(String(100))
    password = Column(String(255), nullable=False)
    email = Column(String(100))
    notas = Column(Text)
    fecha_creacion = Column(DateTime, default=datetime.datetime.utcnow)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))