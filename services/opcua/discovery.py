import os
import asyncio
from asyncua import Client, Server
from dotenv import load_dotenv

load_dotenv()

async def task_register_discovery(server: Server, registration_interval = 5):
    lds_endpoint = os.getenv('LDS_ENDPOINT')
    if not lds_endpoint:
        print("LDS_ENDPOINT não configurado")
        return
    while True:
        try:
            async with Client(lds_endpoint) as client:
                await client.register_server(server)
                print("Servidor registrado no LDS")
        except ValueError as e:
            print(f"Erro no registro de discovery: {e}")
        except OSError:
            await asyncio.sleep(registration_interval)

