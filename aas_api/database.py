import os
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

# Carrega variáveis de ambiente
load_dotenv()
MONGODB_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/aas_database")

# Variável global para o banco de dados
database = None

async def init_database():
    """
    Inicializa a conexão com MongoDB.
    """
    global database
    try:
        # Estabelece conexão assíncrona com MongoDB
        client = AsyncIOMotorClient(MONGODB_URI)

        # Obtém a base de dados
        database = client.get_default_database()

        # Testa a conexão
        await client.admin.command('ismaster')
        print("Conectado ao MongoDB com sucesso!")

    except Exception as e:
        print(f"Erro ao conectar ao MongoDB: {e}")
        print("Aplicação iniciará sem banco de dados.")
        
def get_database():
    """
    Retorna a instância do banco de dados.
    """
    return database
