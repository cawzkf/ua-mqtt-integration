import asyncio
from services.opcua.discovery import discovery

async def init():
    await discovery()

if __name__=="__main__":
     asyncio.run(init())