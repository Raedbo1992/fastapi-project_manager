import bcrypt

password = "raul2025"
hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
print(hashed.decode())  # Esto lo insertas en la columna password
