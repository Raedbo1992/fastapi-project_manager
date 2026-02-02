import uvicorn
import os

if __name__ == "__main__":
    # Railway usa PORT variable, si no existe usa 8000
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    print(f"🚀 Iniciando servidor en {host}:{port}")
    print(f"📁 Directorio actual: {os.getcwd()}")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=False,  # IMPORTANTE: False en Railway
        log_level="info",
        access_log=True
    )