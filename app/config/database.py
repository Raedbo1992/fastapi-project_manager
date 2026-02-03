from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

load_dotenv()

def get_database_url():
    """Obtiene la URL de la base de datos para cualquier entorno"""
    # 1. DATABASE_URL de variables de entorno
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        # 2. Si no hay DATABASE_URL, usar SQLite local
        print("⚠️ DATABASE_URL no encontrada. Usando SQLite para desarrollo local.")
        return "sqlite:///./project_manager.db"
    
    # 3. Corregir postgres:// a postgresql:// para SQLAlchemy
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    
    print(f"🔗 Database URL configurada: {database_url[:50]}...")  # Mostrar solo parte por seguridad
    return database_url

SQLALCHEMY_DATABASE_URL = get_database_url()

# Configurar parámetros específicos para SQLite
connect_args = {}
if "sqlite" in SQLALCHEMY_DATABASE_URL:
    connect_args = {"check_same_thread": False}

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True if "postgresql" in SQLALCHEMY_DATABASE_URL else False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()