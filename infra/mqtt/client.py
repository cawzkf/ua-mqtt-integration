import uuid
import asyncio
import os
from dotenv import load_dotenv
from gmqtt import Client as MQTTClient
from utils.constants import MQTT_TOPICS


class MQTTChannel:

    def __init__(self, client_id=None):
        load_dotenv()
        self.host = os.getenv('MQTT_BROKER_HOST', 'localhost')
        self.port = int(os.getenv('MQTT_BROKER_PORT', '1883'))
        
        client_id = client_id or f"ua-mqtt-{uuid.uuid4().hex[:6]}"
        self.client = MQTTClient(client_id)
        
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.is_connected = False

    async def init(self):
        print(f"Connecting to {self.host}:{self.port}...")
        await self.client.connect(self.host, self.port)

    def subscribe_default_topics(self):
        topics = [
            MQTT_TOPICS.get("ELECTRICAL", "scgdi/motor/electrical"),
            MQTT_TOPICS.get("VIBRATION", "scgdi/motor/vibration"),
            MQTT_TOPICS.get("ENVIRONMENT", "scgdi/motor/environment")
        ]
        
        for topic in topics:
            self.client.subscribe(topic)
            print(f"Subscribed: {topic}")

    def on_connect(self, _client, _flags, rc, _properties=None):
        if rc == 0:
            self.is_connected = True
            print("Connected")
        else:
            print(f"Failed (code: {rc})")

    def on_message(self, _client, topic, payload, _qos, _properties=None):
        try:
            message = payload.decode('utf-8')[:100]  # Só primeiros 100 chars
            print(f"[{topic}]: {message}...")
        except:
            pass


async def main():
    try:
        client = MQTTChannel()
        await client.init()
        client.subscribe_default_topics()
        
        print("Listening...")
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        print("Stopped.")


if __name__ == '__main__':
    asyncio.run(main())
