"""
Módulo de monitoramento de temperatura crítica para proteção de equipamentos.

Este módulo monitora continuamente a temperatura da carcaça do motor,
detectando condições críticas de superaquecimento e gerando eventos OPC UA.
"""

import logging
from services.events.event_generator import generate_event_properly
from services.opcua.node_manager import OPCUANodeManager
from utils.constants import CRITICAL_TEMPERATURE

logger = logging.getLogger(__name__)
logging.basicConfig(
    level = logging.INFO,
    format="%(asctime)s [%(levelname)s]: %(message)s"
)

async def _read_float(nodes_variables, name: str) -> float:
    """
    Lê um valor numérico de uma variável OPC UA com conversão para float.
    
    Args:
        nodes_variables (OPCUANodeManager | dict): Container de variáveis OPC UA
        name (str): Nome da variável a ser lida
        
    Returns:
        float: Valor numérico da variável convertido para float
    """
    if isinstance(nodes_variables, OPCUANodeManager):
        return await nodes_variables.read_float(name)
    
    node = nodes_variables.get(name)

    if node is None:
        raise KeyError(f"Node {name} not found")
    
    val = await node.read_value()

    return float(val)


async def check_temperature_events(nodes_variables: OPCUANodeManager, event_generator):
    """
    Monitora temperatura da carcaça e gera eventos para condições críticas.
    
    Realiza monitoramento contínuo da temperatura da carcaça do motor, comparando
    com o limite crítico. Gera eventos OPC UA de alta severidade quando a
    temperatura excede o limite seguro.
    
    Args:
        nodes_variables (OPCUANodeManager): Gerenciador contendo a variável CaseTemperature
        event_generator: Gerador de eventos OPC UA configurado
    """
    logger.info('Gerando evento de temperatura....')
    try:
        # Tentativa de leitura da temperatura da carcaça
        try:
            temp_carcaca = await _read_float(nodes_variables, "CaseTemperature")
        except KeyError:
            # Sensor de temperatura não disponível - retorna silenciosamente
            # Estratégia fail-safe: não gera alarmes falsos
            return

        # Verificação de condição crítica de temperatura
        if temp_carcaca > CRITICAL_TEMPERATURE:
            # Geração de evento crítico de temperatura
            await generate_event_properly(
                event_generator,
                event_type="CriticalTemperature",
                message="Case temperature critical",
                severity=900,  # Severidade crítica 
                CaseTemperature=temp_carcaca
            )
        else:
            # Temperatura dentro da faixa segura
            logger.info("Temperatura normal: %s °C ", temp_carcaca)

    except Exception as e:
        logger.info("Erro ao verificar temperatura: {%s}", e)
        # Erro é registrado mas não interrompe o sistema de monitoramento