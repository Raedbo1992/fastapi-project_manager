from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# OBTENER VARIABLES DE ENTORNO DE RAILWAY
DB_HOST = os.getenv("MYSQLHOST", "mysql.railway.internal")  # ← CRÍTICO
DB_PORT = os.getenv("MYSQLPORT", "3306")
DB_USER = os.getenv("MYSQLUSER", "root")
DB_PASSWORD = os.getenv("MYSQLPASSWORD", "")
DB_NAME = os.getenv("MYSQLDATABASE", "project_manager")

# CONSTRUIR URL DE CONEXIÓN
SQLALCHEMY_DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

print("=" * 50)
print("🔧 CONFIGURACIÓN DE BASE DE DATOS:")
print(f"   Host: {DB_HOST}")
print(f"   Puerto: {DB_PORT}")
print(f"   Usuario: {DB_USER}")
print(f"   Base de datos: {DB_NAME}")
print(f"   URL: mysql+pymysql://{DB_USER}:****@{DB_HOST}:{DB_PORT}/{DB_NAME}")
print("=" * 50)

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=True  # ← ACTIVAR PARA DEBUG
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()