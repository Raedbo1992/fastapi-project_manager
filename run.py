import uvicorn
import os

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    print(f"🚀 Iniciando servidor en {host}:{port}")
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=False,  # Desactivar reload en producción
        workers=1
    )