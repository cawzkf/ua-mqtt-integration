from fastapi import FastAPI
from .database import init_database, get_database
from .routers import submodels

# Inicializa a aplicação FastAPI
app = FastAPI(title="teste")

@app.on_event("startup")
async def start():
    """
    Inicializa a conexão com MongoDB usando Motor puro.
    """
    await init_database()

@app.get("/health")
async def status():
    """
    Endpoint de verificação de saúde da aplicação.
    """
    database = get_database()
    return {"status": "ok", "database": "connected" if database is not None else "disconnected"}

app.include_router(submodels.router)
