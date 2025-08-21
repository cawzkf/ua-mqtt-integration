import os
import asyncio
from datetime import datetime, timezone
from asyncua import Server
from dotenv import load_dotenv

load_dotenv()

async def configure_server_info(server: Server):
    await server.set_build_info(
        product_uri=os.getenv('OPCUA_PRODUCT_URI', 'http://examples.freeopcua.github.io'),
        manufacturer_name=os.getenv('OPCUA_MANUFACTURER', 'Camila LTDA'),
        product_name=os.getenv('OPCUA_PRODUCT_NAME', 'opcua-server'),
        software_version=os.getenv('OPCUA_SOFTWARE_VERSION', '1.0.0'),
        build_number=os.getenv('OPCUA_BUILD_NUMBER', '20250820'),
        build_date=datetime.now(timezone.utc)
    )

    uri = os.getenv('OPCUA_APPLICATION_URI', 'urn:motor50cv:digitaltwin')
    await server.set_application_uri(uri)
    server.name = os.getenv('OPCUA_SERVER_NAME', 'Motor50cv' )
    server.product_uri = os.getenv('OPCUA_SERVER_PRODUCT_URI', 'urn:motor50cv:product')

async def main():
    print('teste....')
    server = Server()
    await server.init()
    await configure_server_info(server)
    print('ok')

if __name__ == "__main__":
    asyncio.run(main())
