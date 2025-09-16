from fastapi import APIRouter, HTTPException
from ..schemas import AssetCreate, ShellCreate
from bson import ObjectId
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
    Note:
        - O id_short deve ser único em todo o sistema
        - O asset deve ser criado antes de poder ser referenciado em shells
        - Campos opcionais podem ser omitidos na requisição
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

@router.post("/shells")
async def create_shell(payload: ShellCreate):
    """
    Cria um Asset Administration Shell (AAS) completo.

    Este endpoint cria um shell que conecta um asset existente com seus
    submodelos e elementos associados, formando a estrutura principal do AAS.
    O shell atua como contêiner que organiza todas as informações relacionadas
    a um asset específico.

    Args:
        payload (ShellCreate): Dados para criação do shell contendo:
            - id_short (str): Identificador único do shell
            - asset_id (str): ID MongoDB do asset a ser vinculado
            - submodels (List[SubmodelCreate]): Lista de submodelos com elementos

    Returns:
        dict: Resposta com informações do shell criado
            - id (str): ID único gerado pelo MongoDB
            - id_short (str): Identificador fornecido na criação

    Raises:
        HTTPException:
            - 500: Quando não há conexão com o banco de dados
            - 400: Quando o asset_id fornecido é inválido
            - 409: Quando o asset referenciado não existe no banco

    Note:
        - O asset referenciado deve existir previamente no banco
        - Submodelos são armazenados como documentos aninhados no shell
        - Elementos dos submodelos são validados automaticamente
        - O asset_id deve ser um ObjectId MongoDB válido (24 caracteres hex)

    Process Flow:
        1. Valida conexão com banco de dados
        2. Verifica se asset_id é um ObjectId válido
        3. Confirma existência do asset referenciado
        4. Cria shell com submodelos aninhados
        5. Retorna confirmação com IDs gerados
    """
    db = get_db()
    if db is None:
        raise HTTPException(status_code=500, detail="Database not connected")

    # Verifica se o asset_id é um ObjectId válido e se o asset existe
    try:
        asset = await db.assets.find_one({"_id": ObjectId(payload.asset_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Asset ID inválido")

    if not asset:
        raise HTTPException(status_code=409, detail="Asset não encontrado")

    # Converte o payload para dicionário e insere no banco
    shell_data = payload.dict()
    result = await db.shells.insert_one(shell_data)

    return {"id": str(result.inserted_id), "id_short": payload.id_short}
