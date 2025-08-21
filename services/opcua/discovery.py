"""
OPCUA Discovery Service - Handles server registration and discovery.
"""
import asyncio
import os
from asyncua import Client

class DiscoveryService:
    """Service for OPCUA server discovery and registration."""
    
    def __init__(self, server=None):
        self.server = server
        self.lds_endpoint = os.getenv('LDS_ENDPOINT')
        
    async def register_server_loop(self, registration_interval=5):
        """Register server with LDS periodically."""
        if not self.lds_endpoint:
            print("LDS_ENDPOINT não configurado")
            return
            
        while True:
            try:
                async with Client(self.lds_endpoint) as client:
                    await client.register_server(self.server)
                    print("Servidor registrado no LDS")
            except Exception as e:
                print(f"Erro no registro de discovery: {e}")
            finally:
                await asyncio.sleep(registration_interval)
