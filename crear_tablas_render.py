from sqlalchemy import create_engine
from app.schema.models import Base, Usuario  # Ajusta la ruta si tu models.py está en otro lugar
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# URL de tu base de datos en Render
DATABASE_URL = "postgresql://project_manager_db_zd2q_user:UeTPp8TJM92n3mKkU8DzIimblSeCYsur@dpg-d60ijm78bdcs73f4dlt0-a.oregon-postgres.render.com:5432/project_manager_db_zd2q"

# Conectar
engine = create_engine(DATABASE_URL)

# Crear todas las tablas
Base.metadata.create_all(bind=engine)
print("✅ Tablas creadas en Render")

# Crear usuario admin (opcional)
Session = sessionmaker(bind=engine)
session = Session()
try:
    from sqlalchemy import func
    count = session.query(func.count(Usuario.id)).scalar()
    if count == 0:
        admin = Usuario(
            nombre="Administrador",
            email="admin@example.com",
            username="admin",
            password_hash=("$2b$12$WSRk3GBAr6jlCw5haw2MRuakqVgqCj.af56xy/xI/KR2.gn5hsBSa")
        )

        session.add(admin)
        session.commit()
        print("👤 Usuario admin creado: admin@example.com / admin123")
    else:
        print(f"ℹ️ Ya hay {count} usuarios")
finally:
    session.close()
