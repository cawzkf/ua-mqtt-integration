"""
Módulo cliente MQTT para comunicação com sistemas externos.

Este módulo implementa um cliente MQTT que permite comunicação bidirecional
entre o servidor OPC UA e sistemas externos via protocolo MQTT.
"""

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
    format="%(asctime)s [%(levelname)s]: %(message)s"
)
logger = logging.getLogger(__name__)

logging.getLogger("gmqtt").setLevel(logging.WARNING)

class MQTTChannel:
    """
    Cliente MQTT para integração com sistemas externos.
    
    Esta classe gerencia a conexão MQTT e o mapeamento de mensagens
    recebidas para variáveis OPC UA correspondentes.
    """
    
    def __init__(self, node_manager: OPCUANodeManager, variable_mapper: Dict[Tuple[str, ...], str]):
        """
        Inicializa o canal MQTT.
        
        Args:
            node_manager (OPCUANodeManager): Gerenciador de nós OPC UA
            variable_mapper (Dict): Mapeamento entre tópicos MQTT e variáveis OPC UA
        """
        load_dotenv()
        self.username = os.getenv("MQTT_USERNAME") or None
        self.password = os.getenv("MQTT_PASSWORD") or None
        self.host = os.getenv("MQTT_BROKER_HOST", "lse.dev.br")
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
        """
        Estabelece conexão com o broker MQTT.
        """
        logger.info("Connecting to %s:%s", self.host, self.port)
        if self.username and self.password:
            self.client.set_auth_credentials(self.username, self.password)
        await self.client.connect(self.host, self.port)
        logger.info("Connected to %s:%s", self.host, self.port)

    def on_connect(self, _client, _flags, rc, _properties=None):
        """
        Callback executado quando conecta ao broker MQTT.
        
        Args:
            _client: Cliente MQTT
            _flags: Flags de conexão
            rc: Código de retorno da conexão
            _properties: Propriedades da conexão
        """
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
        """
        Callback executado quando desconecta do broker MQTT.
        
        Args:
            _client: Cliente MQTT
            _packet: Pacote de desconexão
            exc: Exceção que causou a desconexão, se houver
        """
        if exc:
            logger.warning("MQTT disconnected: %s", exc)
        else:
            logger.info("MQTT disconnected")
    
    async def close(self):
        """
        Encerra a conexão MQTT de forma limpa.
        """
        try:
            await self.client.disconnect()
        except Exception:
            pass

async def main():
    """
    Função principal para execução standalone do cliente MQTT.
    """
    node_manager = OPCUANodeManager()
    ch = MQTTChannel(node_manager=node_manager, variable_mapper=MQTT_TO_OPCUA_MAP)
    await ch.init()
    logger.info("Ouvindo...")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())