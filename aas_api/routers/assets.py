from fastapi import HTTPException, APIRouter
from ..models import Asset
from ..schemas import AssetCreate
from ..database import get_database

router = APIRouter(prefix="/submodels", tags=["submodels"])

def get_db():
    """
    Obtém a instância do banco de dados MongoDB.
    
    Returns:
        Database: Instância do banco de dados MongoDB ou None se não conectado
        
    Note:
        Esta função atua como wrapper para acessar a conexão global do banco
        de dados estabelecida durante o startup da aplicação.
    """
    return get_database()

@router.post("/assets")
async def create_asset(payload: AssetCreate):
    """
    Cria um novo asset no sistema AAS (Asset Administration Shell).
    
    Este endpoint permite criar um ativo que posteriormente pode ser associado
    a shells e submodelos, formando a estrutura base de um Asset Administration Shell.
    Um asset representa um objeto físico ou lógico do mundo real que possui valor
    para uma organização.
    
    Args:
        payload (AssetCreate): Dados para criação do asset contendo:
            - id_short (str): Identificador único e legível do asset
            - category (str, optional): Categoria de classificação do asset
            - description (str, optional): Descrição detalhada do asset
    
    Returns:
        dict: Resposta com informações do asset criado
            - id (str): ID único gerado pelo MongoDB (ObjectId como string)
            - id_short (str): Identificador fornecido na criação
    
    Raises:
        HTTPException:
            - 500: Quando não há conexão com o banco de dados MongoDB
            - 409: Quando já existe um asset com o mesmo id_short (conflito)

    Business Rules:
        - O id_short deve ser único em todo o sistema
        - Campos opcionais (category, description) podem ser omitidos
        - O asset criado pode ser referenciado posteriormente em shells

    Technical Details:
        - Utiliza MongoDB para persistência
        - Validação de unicidade antes da inserção
        - Retorna ObjectId convertido para string

    Note:
        Este é o primeiro passo na criação de uma estrutura AAS completa.
        Após criar o asset, você pode associá-lo a shells que contêm
        submodelos com propriedades e características específicas.
    """
    db = get_db()
    if db is None:
        raise HTTPException(status_code=500, detail="Database not connected")

    # Verifica se já existe um asset com o mesmo id_short
    existing = await db.assets.find_one({"id_short": payload.id_short})
    if existing:
        raise HTTPException(status_code=409, detail="id_short já existe")

    # Converte o payload para dicionário e insere no MongoDB
    asset_data = payload.dict()
    result = await db.assets.insert_one(asset_data)

    return {"id": str(result.inserted_id), "id_short": payload.id_short}
