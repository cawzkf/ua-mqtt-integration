import json
import asyncio
from typing import Dict, Any
from utils.constants import MQTT_TO_OPCUA_MAP


class MQTTMessageHandler:

    def __init__(self, variable_mapper: Dict = None):
        self.variable_mapper = variable_mapper or MQTT_TO_OPCUA_MAP
        self.opcua_nodes = {}

    def set_opcua_nodes(self, nodes: Dict):
        self.opcua_nodes = nodes

    def on_connect(self, _client, _userdata, _flags, rc, _properties=None):
        if rc == 0:
            print("MQTT Handler Connected")

    def on_disconnect(self, _client, _userdata, rc, _properties=None):
        if rc != 0:
            print("MQTT Handler Disconnected")

    def on_subscribe(self, _client, _userdata, mid, granted_qos, _properties=None):
        pass

    def on_message(self, _client, _userdata, message):
        try:
            topic = message.topic
            payload = message.payload.decode('utf-8')
            data = json.loads(payload)
            
            print(f"Topic: {topic}")
            self._process_message_data(data)

        except (json.JSONDecodeError, UnicodeDecodeError):
            pass

    def _process_message_data(self, data: Dict[str, Any]):
        if not self.opcua_nodes:
            return

        for key_path, variable_name in self.variable_mapper.items():
            if variable_name in self.opcua_nodes:
                try:
                    value = self._extract_value_from_data(data, key_path)
                    if value is not None:
                        asyncio.create_task(
                            self.opcua_nodes[variable_name].set_value(value)
                        )
                        print(f"{variable_name} = {value}")

                except Exception:
                    pass

    def _extract_value_from_data(self, data: Dict[str, Any], key_path: tuple) -> Any:
        current = data
        for key in key_path:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        return current


def create_message_handler(variable_mapping: Dict = None) -> MQTTMessageHandler:
    return MQTTMessageHandler(variable_mapping)
