"""
Manipulador de mensagens MQTT para atualização de variáveis OPC UA.

Este módulo define MQTTMessageHandler, responsável por decodificar payloads MQTT,
extrair valores por caminhos de chave e mapear para variáveis OPC UA.
"""

import os
import json
import asyncio
import logging
from typing import Dict, Any, Tuple
from services.opcua.node_manager import OPCUANodeManager

logger = logging.getLogger(__name__)

LOG_PAYLOAD   = os.getenv("MQTT_LOG_PAYLOAD", "0") == "1"  # Log detalhado do payload
LOG_MAPPING   = os.getenv("MQTT_LOG_MAPPING", "1") == "1"  # Log dos mapeamentos aplicados
DRY_RUN       = os.getenv("MQTT_DRY_RUN", "0") == "1"      # Não escrever no OPC UA, apenas logar
FOCUS_KEYS    = {k.strip() for k in os.getenv("MQTT_LOG_KEYS", "").split(",") if k.strip()} 

class MQTTMessageHandler:
    """
    Manipula mensagens MQTT e atualiza variáveis OPC UA conforme um mapeamento.

    A classe recebe um OPCUANodeManager e um dicionário variable_mapper onde
    a chave é um tuple representando o caminho até o valor no JSON e o valor
    é o nome da variável OPC UA.
    """

    def __init__(self, node_manager: OPCUANodeManager, variable_mapper: Dict[Tuple[str, ...], str]):
        """
        Inicializa o manipulador de mensagens MQTT.

        Args:
            node_manager (OPCUANodeManager): Instância para escrever valores
            variable_mapper (Dict): Mapeamento key_path_tuple -> nome_variavel_OPCUA
        """
        self.variable_mapper = variable_mapper
        self.node_manager = node_manager

    def on_message(self, _client, topic, payload, qos, properties):
        """
        Callback de recebimento de mensagem MQTT.

        Decodifica o payload UTF-8, faz parse JSON e processa os dados.

        Args:
            _client: Cliente MQTT (não utilizado)
            topic (str): Tópico da mensagem
            payload (bytes): Conteúdo bruto da mensagem
            qos (int): QoS da publicação
            properties: Propriedades do protocolo MQTT v5
        """
        try:
            text = payload.decode("utf-8", errors="replace")
            data = json.loads(text)

            if LOG_PAYLOAD:
                try:
                    logger.info("MQTT <- topic=%s qos=%s\n%s", topic, qos, json.dumps(data, indent=2, ensure_ascii=False))
                except Exception:
                    logger.info("MQTT <- topic=%s qos=%s %s", topic, qos, text[:500])

            self._process_message_data(data, topic)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.warning("Invalid payload on %s: %s", topic, e)
        except Exception:
            logger.exception("Unexpected error in on_message")

    def _want_log_key(self, key_path: Tuple[str, ...]) -> bool:
        """
        Indica se um caminho de chave deve ser logado no modo de mapeamento.

        Args:
            key_path (Tuple): Tupla representando o caminho no JSON

        Returns:
            bool: True para logar, False caso contrário
        """
        if not FOCUS_KEYS:
            return True
        flat = ".".join(key_path)
        return flat in FOCUS_KEYS

    def _process_message_data(self, data: Dict[str, Any], topic: str):
        """
        Processa o dicionário JSON da mensagem e aplica o mapeamento para OPC UA.

        Args:
            data (Dict): Dicionário resultante do payload JSON
            topic (str): Tópico MQTT da mensagem
        """
        for key_path, variable_name in self.variable_mapper.items():
            try:
                value = self._extract_value_from_data(data, key_path)
                if value is None:
                    continue
                if isinstance(value, (int, float)):
                    value = float(value)

                if LOG_MAPPING and self._want_log_key(key_path):
                    logger.info("MAP %s -> %s  (topic=%s)", ".".join(key_path), variable_name, topic)

                if DRY_RUN:
                    logger.info("DRY_RUN %s <- %r", variable_name, value)
                else:
                    asyncio.create_task(self.node_manager.set_value(variable_name, value))

            except Exception:
                logger.exception("Failed processing %s (path=%s)", variable_name, key_path)

    @staticmethod
    def _extract_value_from_data(data: Dict[str, Any], key_path: tuple):
        """
        Extrai um valor aninhado de data seguindo um caminho de chaves.

        Args:
            data (Dict): Dicionário JSON
            key_path (tuple): Tupla de chaves

        Returns:
            Any | None: Valor encontrado ou None se o caminho não existir
        """
        curr: Any = data
        for key in key_path:
            if isinstance(curr, dict) and key in curr:
                curr = curr[key]
            else:
                return None
        return curr