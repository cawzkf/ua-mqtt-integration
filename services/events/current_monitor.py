"""
Módulo de monitoramento de corrente elétrica para detecção de sobrecarga.

Este módulo monitora continuamente as correntes elétricas trifásicas de um motor,
detectando condições de sobrecarga e gerando eventos OPC UA automáticos.
"""

import logging
from services.opcua.node_manager import OPCUANodeManager
from services.events.event_generator import generate_event_properly
from utils.constants import NOMINAL_CURRENT, TOLERANCE

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

async def check_current_events(nodes_variables: OPCUANodeManager, event_generator):
    """
    Monitora correntes trifásicas e gera eventos para condições de sobrecarga.
    
    Realiza monitoramento contínuo das correntes elétricas nas três fases (A, B, C)
    do motor, comparando com a corrente nominal mais tolerância. Gera eventos OPC UA
    automáticos quando detectada sobrecarga.
    
    Args:
        nodes_variables (OPCUANodeManager): Gerenciador contendo as variáveis de corrente
        event_generator: Gerador de eventos OPC UA configurado
    """
    logger.info("Gerando evento de corrente....")

    # Monitoramento de cada fase independentemente
    for fase in ['A', 'B', 'C']:
        try:
            variavel_corrente = f"Current{fase}"

            # Verifica se a variável existe antes de tentar ler
            if variavel_corrente not in nodes_variables:
                continue

            # Leitura da corrente atual da fase
            corrente = await _read_float(nodes_variables, variavel_corrente)

            # Cálculo do limite de sobrecarga
            limite_sobrecarga = NOMINAL_CURRENT * (1 + TOLERANCE)

            # Detecção de condição de sobrecarga
            if corrente > limite_sobrecarga:
                # Geração de evento OPC UA para sobrecarga
                await generate_event_properly(
                    event_generator,
                    event_type="Overcurrent",
                    message=f"Overcurrent detected: Current{fase}",
                    severity=700,  # Severidade alta
                    CurrentPhase=(f'{corrente}')
                )
        except Exception as e:
            logger.info("Erro ao verificar corrente fase {%s}: {%s}", fase, e)
            # Erro é registrado mas não interrompe verificação das outras fases
