import os, uuid, asyncio, logging, json
from dotenv import load_dotenv
from gmqtt import Client as MQTTClient
from services.mqtt.message_handler import MQTTMessageHandler
from services.opcua.node_manager import OPCUANodeManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

class MQTTChannel:
    def __init__(self, client_id=None):
        load_dotenv()
        self.host = "lse.dev.br"
        self.port = 1883
        
        cid = client_id or f"ua-mqtt-{uuid.uuid4().hex[:6]}"
        self.client = MQTTClient(cid)


        node_manager = OPCUANodeManager({})
        self.handler = MQTTMessageHandler(node_manager=node_manager)

        self.client.on_message = self.handler.on_message
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect


    async def init(self):
        logger.info("Connecting to %s:%s", self.host, self.port)
        await self.client.connect(self.host, self.port)
        logger.info("Connected to %s:%s", self.host, self.port)


    def on_connect(self, _client, _flags, rc, _properties=None):
        if rc == 0:
            logger.info("MQTT connected")
        else:
            logger.error("MQTT connect failed rc=%s", rc)

    def on_disconnect(self, _client, _packet, exc=None):
        if exc:
            logger.warning("MQTT disconnected: %s", exc)
        else:
            logger.info("MQTT disconnected")

async def main():
    try:
        ch = MQTTChannel()
        await ch.init()
        ch.client.subscribe('scgdi/motor/electrical')
        ch.client.subscribe('scgdi/motor/vibration')
        ch.client.subscribe('scgdi/motor/environment')
        logger.info("Listening...")
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        logger.warning("Stopped")

if __name__ == "__main__":
    asyncio.run(main())