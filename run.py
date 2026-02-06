# run.py
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "main:app",  # <-- apuntar a main.py en el root
        host="127.0.0.1",
        port=8000,
        reload=True
    )
