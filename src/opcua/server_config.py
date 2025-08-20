import os
from datetime import datetime, timezone
from asyncua import Server
from dotenv import load_dotenv

load_dotenv()


async def configure_server_info(server : Server):
    alt_host = os.getenv('OPCUA_SERVER_HOST')
    alt_port = os.getenv('OPCUA_SERVER_PORT')

    alt_endpoint = f"opc.tcp://{alt_host}:{alt_port}"
    print(f'endpoint: {alt_endpoint}')

    await server.set_build_info(
        product_uri=os.getenv('OPCUA_PRODUCT_URI'),
        manufacturer_name=os.getenv('OPCUA_MANUFACTURER'),
        product_name=os.getenv('OPCUA_PRODUCT_NAME'),
        build_date=datetime.now(timezone.utc)
    )


    uri = os.getenv("OPCUA_PRODUCT_URI")
    await server.set_application_uri(uri)

    server.name = os.getenv('OPCUA_SERVER_NAME',' ')
    server.product_uri = os.getenv("OPCUA_PRODUCT_URI")

    print(f'Servidor: {server.name}')
