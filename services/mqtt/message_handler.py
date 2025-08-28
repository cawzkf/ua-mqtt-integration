import json
import asyncio
import logging
from typing import Dict, Any, Tuple
from utils.constants import MQTT_TO_OPCUA_MAP
from services.opcua.node_manager import OPCUANodeManager

logger = logging.getLogger(__name__)

class MQTTMessageHandler:
    def __init__(self, node_manager: OPCUANodeManager, variable_mapper: Dict[Tuple[str, ...], str] = None):
        self.variable_mapper = variable_mapper or MQTT_TO_OPCUA_MAP
        self.node_manager = node_manager

    def on_message(self, _client, topic, payload, qos, properties):
        try:
            text = payload.decode("utf-8")
            data = json.loads(text)
            logger.debug("MQTT topic=%s payload=%s", topic, text)
            self._process_message_data(data)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.warning("Invalid payload on %s: %s", topic, e)
        except Exception:
            logger.exception("Unexpected error in on_message")

    def _process_message_data(self, data: Dict[str, Any]):
        for key_path, variable_name in self.variable_mapper.items():
            try:
                value = self._extract_value_from_data(data, key_path)
                if value is None:
                    logger.warning("[JSON:%s] -> [OPCUA:%s] missing value", key_path, variable_name)
                    continue
                if isinstance(value, (float, str)):
                    logger.info("[JSON:%s] -> [OPCUA:%s] type: %r", key_path, variable_name, value)
                    asyncio.create_task(self.node_manager.set_value(variable_name, value))
                else: 
                    logger.info("[JSON:%s] -> [OPCUA:%s] invalid type: %r", key_path, variable_name, value)              
                    continue
            except Exception:
                logger.exception("Failed processing %s (path=%s)", variable_name, key_path)

    @staticmethod
    def _extract_value_from_data(data: Dict[str, Any], key_path: tuple) -> Any:
        current: Any = data
        for key in key_path:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        return current
    
