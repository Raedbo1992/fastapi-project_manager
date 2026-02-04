from app.config.database import SessionLocal
from app.schema import models
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

db = SessionLocal()
try:
    # Buscar el usuario admin
    usuario = db.query(models.Usuario).filter(models.Usuario.username == "admin").first()
    
    if usuario:
        # Hashear la contraseña
        usuario.password = pwd_context.hash("admin123")
        db.commit()
        print("✅ Contraseña actualizada correctamente")
        print(f"Hash generado: {usuario.password[:50]}...")
    else:
        print("❌ Usuario 'admin' no encontrado")
finally:
    db.close()