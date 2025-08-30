import os
import uuid
import asyncio
import logging
from typing import Dict, Tuple
from dotenv import load_dotenv
from gmqtt import Client as MQTTClient
from services.mqtt.message_handler import MQTTMessageHandler
from services.opcua.node_manager import OPCUANodeManager
from utils.constants import MQTT_TO_OPCUA_MAP

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

class MQTTChannel:
    def __init__(self, node_manager: OPCUANodeManager, variable_mapper: Dict[Tuple[str, ...], str]):
        load_dotenv()
        self.username = os.getenv("MQTT_USERNAME") or None
        self.password = os.getenv("MQTT_PASSWORD") or None
        self.host = os.getenv("MQTT_BROKER_HOST", "localhost")
        self.port = int(os.getenv("MQTT_BROKER_PORT", "1883"))

        self.client = MQTTClient(uuid.uuid4().hex)

        self.handler = MQTTMessageHandler(
            node_manager=node_manager,
            variable_mapper=variable_mapper
        )

        self.client.on_message = self.handler.on_message
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect

    async def init(self):
        logger.info("Connecting to %s:%s", self.host, self.port)
        if self.username and self.password:
            self.client.set_auth_credentials(self.username, self.password)
        await self.client.connect(self.host, self.port)
        logger.info("Connected to %s:%s", self.host, self.port)

    def on_connect(self, _client, _flags, rc, _properties=None):
        if rc == 0:
            topics = [
                "scgdi/motor/electrical",
                "scgdi/motor/vibration",
                "scgdi/motor/environment",
            ]
            for t in topics:
                self.client.subscribe(t)
            logger.info("MQTT connected; subscribed to: %s", ", ".join(topics))
        else:
            logger.error("MQTT connect failed rc=%s", rc)

    def on_disconnect(self, _client, _packet, exc=None):
        if exc:
            logger.warning("MQTT disconnected: %s", exc)
        else:
            logger.info("MQTT disconnected")
    
    async def close(self):
        try:
            await self.client.disconnect()
        except Exception:
            pass

async def main():
    node_manager = OPCUANodeManager()
    ch = MQTTChannel(node_manager=node_manager, variable_mapper=MQTT_TO_OPCUA_MAP)
    await ch.init()
    logger.info("Listening...")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
