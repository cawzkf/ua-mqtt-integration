from fastapi import HTTPException, APIRouter
from ..models import Asset
from ..schemas import AssetCreate

router = APIRouter(prefix="/submodels", tags=["submodels"])

from ..database import get_database

def get_db():
    return get_database()

@router.post("/assets")
async def create_asset(payload: AssetCreate):
    """
    Cria um novo asset no sistema AAS (Asset Administration Shell).
    
    Este endpoint permite criar um ativo que posteriormente pode ser associado
    a shells e submodelos, formando a estrutura base de um Asset Administration Shell.
    
    Args:
        payload (AssetCreate): Dados para criação do asset contendo:
            - id_short (str): Identificador único do asset
            - category (str, optional): Categoria de classificação do asset
            - description (str, optional): Descrição detalhada do asset
    
    Returns:
        dict: Resposta com informações do asset criado
            - id (str): ID único gerado pelo MongoDB
            - id_short (str): Identificador fornecido na criação
    
    Raises:
        HTTPException:
            - 500: Quando não há conexão com o banco de dados
            - 409: Quando já existe um asset com o mesmo id_short
    """
    db = get_db()
    if db is None:
        raise HTTPException(status_code=500, detail="Database not connected")

    # Verifica se já existe um asset com o mesmo id_short
    existing = await db.assets.find_one({"id_short": payload.id_short})
    if existing:
        raise HTTPException(status_code=409, detail="id_short já existe")

    # Converte o payload para dicionário e insere no banco
    asset_data = payload.dict()
    result = await db.assets.insert_one(asset_data)

    return {"id": str(result.inserted_id), "id_short": payload.id_short}
