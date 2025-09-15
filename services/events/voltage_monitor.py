"""
Módulo de monitoramento de tensão elétrica para detecção de anomalias trifásicas.

Este módulo monitora continuamente as tensões elétricas trifásicas de um motor,
detectando condições de sobretensão e subtensão e gerando eventos OPC UA.
"""

import logging
from utils.constants import NOMINAL_VOLTAGE, TOLERANCE
from services.events.event_generator import generate_event_properly
from services.opcua.node_manager import OPCUANodeManager

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


async def check_voltage_events(nodes_variables: OPCUANodeManager, event_generator):
    """
    Monitora tensões trifásicas e gera eventos para condições anômalas.
    
    Realiza monitoramento contínuo das tensões elétricas nas três fases (A, B, C)
    do motor, comparando com a tensão nominal mais/menos tolerância. Detecta
    sobretensão e subtensão, gerando eventos OPC UA específicos.
    
    Args:
        nodes_variables (OPCUANodeManager): Gerenciador contendo as variáveis de tensão
        event_generator: Gerador de eventos OPC UA configurado
    """
    logger.info('Gerando evento de voltage....')
    
    # Monitoramento de cada fase independentemente
    for fase in ['A', 'B', 'C']:
        try:
            variavel_tensao = f"Voltage{fase}"
            
            # Verifica se a variável existe antes de tentar ler
            if variavel_tensao not in nodes_variables:
                continue

            # Leitura da tensão atual da fase
            tensao = await _read_float(nodes_variables, variavel_tensao)

            # Cálculo dos limites de operação
            limite_superior = NOMINAL_VOLTAGE * (1 + TOLERANCE)
            limite_inferior = NOMINAL_VOLTAGE * (1 - TOLERANCE)

            # Detecção de condição de sobretensão
            if tensao > limite_superior:
                await generate_event_properly(
                    event_generator,
                    event_type="Overvoltage",
                    message=f"Overvoltage detected: Voltage{fase}",
                    severity=700,  # Severidade alta
                    VoltagePhase=(f'{tensao}')
                )

            # Detecção de condição de subtensão
            elif tensao < limite_inferior:
                await generate_event_properly(
                    event_generator,
                    event_type="Undervoltage",
                    message=f"Undervoltage detected: Voltage{fase}",
                    severity=700,  # Severidade alta
                    VoltagePhase=(f'{tensao}')
                )
            else:
                # Tensão dentro da faixa normal
                logger.info("Tensão fase {%s} normal", fase)

        except Exception as e:
            logger.info("Erro ao verificar tensão fase {%s}: {%s}", fase, e)
            # Erro é registrado mas não interrompe verificação das outras fases
