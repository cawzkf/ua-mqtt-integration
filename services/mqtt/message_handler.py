"""
Manipulador de mensagens MQTT para atualização de variáveis OPC UA.

Este módulo define `MQTTMessageHandler`, responsável por:
- decodificar payloads MQTT (JSON),
- extrair valores por caminhos de chave (`key_path`),
- mapear para nomes de variáveis OPC UA via `variable_mapper`,
- e escrever assíncronamente os valores no `OPCUANodeManager`.

Variáveis de ambiente de controle:
- MQTT_LOG_PAYLOAD: "1" para logar payloads completos.
- MQTT_LOG_MAPPING: "1" para logar mapeamentos (key_path -> variável).
- MQTT_DRY_RUN: "1" para não escrever no OPC UA (somente log).
- MQTT_LOG_KEYS: lista separada por vírgula de caminhos (ex: "sensor.voltageA,sensor.voltageB") para filtrar logs de mapeamento.
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
"""
Conjunto de caminhos de chaves a logar quando LOG_MAPPING estiver ativo.
Formato do caminho: "a.b.c" representando o tuple ("a", "b", "c").
"""

class MQTTMessageHandler:
    """
    Manipula mensagens MQTT e atualiza variáveis OPC UA conforme um mapeamento.

    A classe recebe um `OPCUANodeManager` e um dicionário `variable_mapper`
    onde a chave é um tuple de strings representando o caminho até o valor no JSON
    (ex.: `("sensor", "voltageA")`) e o valor é o nome da variável OPC UA
    (ex.: `"VoltageA"`). Quando uma mensagem chega, o handler extrai os valores
    conforme os caminhos e agenda a escrita assíncrona no OPC UA.
    """

    def __init__(self, node_manager: OPCUANodeManager, variable_mapper: Dict[Tuple[str, ...], str]):
        """
        Inicializa o manipulador de mensagens MQTT.

        Args:
            node_manager: Instância de `OPCUANodeManager` usada para escrever valores.
            variable_mapper: Mapeamento `{ key_path_tuple: "NomeVariavelOPCUA" }`.
        """
        self.variable_mapper = variable_mapper
        self.node_manager = node_manager

    def on_message(self, _client, topic, payload, qos, properties):
        """
        Callback de recebimento de mensagem MQTT.

        Decodifica o payload em UTF-8, faz o parse de JSON e delega para `_process_message_data`.
        Em caso de payload inválido, registra aviso.

        Args:
            _client: Cliente MQTT (não utilizado).
            topic (str): Tópico da mensagem.
            payload (bytes): Conteúdo bruto da mensagem.
            qos (int): QoS da publicação.
            properties: Propriedades do protocolo (MQTT v5).
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
        Indica se um determinado caminho de chave deve ser logado no modo de mapeamento.

        Se `FOCUS_KEYS` estiver vazio, loga todos. Caso contrário, somente loga
        quando o caminho (flattened com '.') estiver presente em `FOCUS_KEYS`.

        Args:
            key_path: Tupla representando o caminho no JSON (ex.: ("sensor","voltageA")).

        Returns:
            bool: True para logar, False caso contrário.
        """
        if not FOCUS_KEYS:
            return True
        flat = ".".join(key_path)
        return flat in FOCUS_KEYS

    def _process_message_data(self, data: Dict[str, Any], topic: str):
        """
        Processa o dicionário JSON da mensagem e aplica o mapeamento para OPC UA.

        Para cada `key_path` definido em `variable_mapper`:
          - extrai o valor do `data`,
          - converte numéricos para `float` quando aplicável,
          - loga o mapeamento (condicional),
          - escreve no OPC UA (ou faz DRY_RUN).

        Args:
            data: Dicionário resultante do payload JSON.
            topic: Tópico MQTT da mensagem (usado para logs).
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
        Extrai um valor aninhado de `data` seguindo um caminho de chaves.

        Percorre o dicionário conforme as chaves do tuple; se em algum ponto
        a chave não existir, retorna `None`.

        Args:
            data: Dicionário JSON.
            key_path: Tupla de chaves (ex.: ("sensor","phase","A")).

        Returns:
            Any | None: Valor encontrado ou `None` se o caminho não existir.
        """
        curr: Any = data
        for key in key_path:
            if isinstance(curr, dict) and key in curr:
                curr = curr[key]
            else:
                return None
        return curr
