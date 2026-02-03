from sqlalchemy import create_engine, inspect, Column, Integer, String, Float, Boolean, Date, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

print("🚀 CONECTANDO A POSTGRESQL...")

# URL de conexión - usa la contraseña que configuraste al instalar
# Si no recuerdas la contraseña, prueba con estas comunes:
# admin2026, postgres, 123456, password
DATABASE_URL = "postgresql://postgres:admin2026@localhost:5432/project_manager"

try:
    # Primero probar conexión simple
    test_engine = create_engine("postgresql://postgres:admin2026@localhost:5432/postgres")
    with test_engine.connect() as conn:
        print("✅ PostgreSQL está corriendo y acepta conexiones")
        
        # Crear base de datos si no existe
        try:
            conn.execute("COMMIT")
            conn.execute("CREATE DATABASE IF NOT EXISTS project_manager")
            print("✅ Base de datos 'project_manager' verificada")
        except:
            print("ℹ️ La base de datos ya existe o hubo error")
            
except Exception as e:
    print(f"❌ Error de conexión: {e}")
    print("\n🔧 Posibles soluciones:")
    print("1. Verifica la contraseña (admin2026)")
    print("2. Prueba con 'postgres' como password")
    print("3. Abre pgAdmin 4 para ver la contraseña")
    print("4. O usa Docker con:")
    print("   docker run --name postgres-local -e POSTGRES_PASSWORD=admin2026 -p 5432:5432 -d postgres")
    exit()

# Ahora conectar a project_manager
try:
    engine = create_engine(DATABASE_URL)
    
    # Probar conexión específica
    with engine.connect() as conn:
        print("✅ Conectado a 'project_manager'")
    
except Exception as e:
    print(f"❌ Error conectando a project_manager: {e}")
    exit()

# Crear modelos
Base = declarative_base()

class Usuario(Base):
    __tablename__ = 'usuarios'
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    salario = Column(Float, default=0)
    activo = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Categoria(Base):
    __tablename__ = 'categorias'
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    tipo = Column(String(20), nullable=False)
    usuario_id = Column(Integer, ForeignKey('usuarios.id'), nullable=False)

class Gasto(Base):
    __tablename__ = 'gastos'
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey('usuarios.id'), nullable=False)
    categoria_id = Column(Integer, ForeignKey('categorias.id'), nullable=False)
    valor = Column(Float, nullable=False)
    fecha_limite = Column(Date, nullable=True)
    pagado = Column(Boolean, default=False)
    notas = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Ingreso(Base):
    __tablename__ = 'ingresos'
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey('usuarios.id'), nullable=False)
    valor = Column(Float, nullable=False)
    fecha = Column(Date, nullable=False)
    notas = Column(Text, nullable=True)

class Pendiente(Base):
    __tablename__ = 'pendientes'
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey('usuarios.id'), nullable=False)
    titulo = Column(String(200), nullable=False)
    descripcion = Column(Text, nullable=True)
    estado = Column(String(20), default='pendiente')
    prioridad = Column(String(20), default='media')
    fecha_limite = Column(DateTime, nullable=True)
    recordatorio = Column(DateTime, nullable=True)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)

class Contrasena(Base):
    __tablename__ = 'contrasenas'
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey('usuarios.id'), nullable=False)
    servicio = Column(String(100), nullable=False)
    usuario = Column(String(100), nullable=False)
    contrasena = Column(String(255), nullable=False)
    url = Column(String(255), nullable=True)
    notas = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Cumpleano(Base):
    __tablename__ = 'cumpleanos'
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey('usuarios.id'), nullable=False)
    nombre_persona = Column(String(100), nullable=False)
    fecha_nacimiento = Column(Date, nullable=False)
    telefono = Column(String(20), nullable=True)
    email = Column(String(100), nullable=True)
    relacion = Column(String(50), nullable=True)
    notas = Column(Text, nullable=True)
    notificar_dias_antes = Column(Integer, default=7)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Crear tablas
print("\n🔄 Creando tablas...")
try:
    Base.metadata.create_all(bind=engine)
    
    # Verificar
    inspector = inspect(engine)
    tablas = inspector.get_table_names()
    
    print(f"✅ {len(tablas)} tablas creadas:")
    for tabla in tablas:
        print(f"  • {tabla}")
        
    # Agregar usuario admin simple
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Verificar si ya existe
        from sqlalchemy import func
        count = session.query(func.count(Usuario.id)).scalar()
        
        if count == 0:
            admin = Usuario(
                nombre="Administrador",
                email="admin@example.com",
                username="admin",
                password_hash="admin123",  # En producción usa bcrypt
                salario=5000.0
            )
            session.add(admin)
            session.commit()
            print("👤 Usuario admin creado: admin@example.com / admin123")
        else:
            print(f"ℹ️ Ya hay {count} usuarios en la base de datos")
            
    except Exception as e:
        print(f"⚠️ Error creando usuario: {e}")
    finally:
        session.close()
        
except Exception as e:
    print(f"❌ Error: {e}")

print("\n🎉 ¡PROCESO COMPLETADO!")
print("🔗 URL: postgresql://postgres:admin2026@localhost:5432/project_manager")