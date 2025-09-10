"""
Módulo de monitoramento de tensão elétrica para detecção de anomalias trifásicas.

Este módulo implementa o sistema de monitoramento contínuo das tensões elétricas
trifásicas de um motor, detectando condições de sobretensão e subtensão que podem
causar danos ao equipamento ou operação inadequada.

Funcionalidades principais:
- Monitoramento de tensão em tempo real para as três fases (A, B, C)
- Detecção de sobretensão e subtensão baseada em tensão nominal + tolerância
- Geração automática de eventos OPC UA para condições anômalas
- Tratamento independente de cada fase elétrica
- Tratamento robusto de erros para garantir continuidade do monitoramento

Voltage Monitoring:
    - VoltageA, VoltageB, VoltageC: Tensões das fases em volts RMS
    - Comparação com faixas: NOMINAL_VOLTAGE ± (TOLERANCE × NOMINAL_VOLTAGE)
    - Detecção de sobretensão e subtensão com severidade alta

Constants Required:
    NOMINAL_VOLTAGE: Tensão nominal do sistema em volts RMS (ex: 220.0, 380.0, 440.0)
    TOLERANCE: Percentual de tolerância para variações (ex: 0.1 = 10%)

Dependencies:
    - utils.constants: Constantes do sistema (tensão nominal e tolerância)
    - services.events.event_generator: Gerador de eventos OPC UA
    - services.opcua.node_manager: Gerenciador de nós OPC UA
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
    
    Função utilitária que abstrai a leitura de valores numéricos de nós OPC UA,
    oferecendo compatibilidade com diferentes tipos de containers de variáveis
    e garantindo conversão segura para tipo float.
    
    Args:
        nodes_variables (OPCUANodeManager | dict): Container de variáveis OPC UA.
                                                  Pode ser um OPCUANodeManager 
                                                  ou dicionário de nós
        name (str): Nome da variável a ser lida (ex: 'VoltageA', 'VoltageB')
        
    Returns:
        float: Valor numérico da variável convertido para float
        
    Raises:
        KeyError: Se a variável especificada não for encontrada no container
        ValueError: Se o valor lido não puder ser convertido para float
        Exception: Erros de comunicação OPC UA, problemas de rede ou sensor
        
    Example:
        >>> tensao_a = await _read_float(node_manager, 'VoltageA')
        >>> logger(f"Tensão fase A: {tensao_a:.1f} V")
        
    Note:
        Esta função serve como camada de abstração que permite flexibilidade
        no tipo de container usado, facilitando testes unitários e diferentes
        implementações de armazenamento de variáveis.
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
    
    Esta função realiza o monitoramento contínuo das tensões elétricas nas
    três fases (A, B, C) do motor, comparando os valores lidos com a tensão
    nominal mais/menos tolerância. Detecta tanto sobretensão quanto subtensão,
    gerando eventos OPC UA específicos para cada condição anômala.
    
    Args:
        nodes_variables (OPCUANodeManager): Gerenciador contendo as variáveis
                                          de tensão (VoltageA, VoltageB, VoltageC)
        event_generator: Gerador de eventos OPC UA configurado para o tipo
                        Motor50CVMonitoringEvent
                        
    Monitored Variables:
        - VoltageA: Tensão da fase A em volts RMS
        - VoltageB: Tensão da fase B em volts RMS  
        - VoltageC: Tensão da fase C em volts RMS
        
    Event Generation:
        Sobretensão:
        - Tipo: "Overvoltage"
        - Severidade: 700 (Alta - requer ação)
        - Mensagem: "Overvoltage detected: {valor:.2f}"
        - Campo personalizado: VoltagePhase (identifica a fase problemática)
        
        Subtensão:
        - Tipo: "Undervoltage"  
        - Severidade: 700 (Alta - requer ação)
        - Mensagem: "Undervoltage detected: {valor:.2f}"
        - Campo personalizado: VoltagePhase (identifica a fase problemática)
        
    Detection Logic:
        Sobretensão detectada quando:
        tensão > NOMINAL_VOLTAGE × (1 + TOLERANCE)
        
        Subtensão detectada quando:
        tensão < NOMINAL_VOLTAGE × (1 - TOLERANCE)
        
        Exemplo com NOMINAL_VOLTAGE=220V e TOLERANCE=0.1:
        - Sobretensão: tensão > 242V (220V + 10%)
        - Subtensão: tensão < 198V (220V - 10%)
        - Faixa normal: 198V a 242V
        
    Error Handling:
        - Variáveis inexistentes são ignoradas (não interrompem o processo)
        - Erros de leitura são registrados mas não param o monitoramento
        - Cada fase é verificada independentemente
        - Sistema continua operando mesmo com falhas em fases individuais
        
    Example:
        >>> # Configuração típica para sistema 220V
        >>> NOMINAL_VOLTAGE = 220.0  # 220 volts RMS
        >>> TOLERANCE = 0.10         # 10% de tolerância
        >>> 
        >>> # Monitoramento detectará:
        >>> # - Sobretensão se qualquer fase > 242V
        >>> # - Subtensão se qualquer fase < 198V
        >>> await check_voltage_events(node_manager, event_gen)
        
        >>> # Configuração para sistema industrial 380V
        >>> NOMINAL_VOLTAGE = 380.0  # 380 volts RMS
        >>> TOLERANCE = 0.05         # 5% de tolerância (mais restritiva)
        >>> # Faixa operacional: 361V a 399V
        
    Note:
        Esta função deve ser chamada periodicamente (recomendado: a cada 5s)
        para garantir detecção rápida de variações de tensão. O monitoramento
        é não-bloqueante e permite que o sistema continue operando mesmo
        com falhas em fases individuais.
        
    Electrical Safety Considerations:
        Sobretensão (> limite superior):
        - Risco de danos aos enrolamentos do motor
        - Degradação acelerada do isolamento elétrico
        - Possível falha de componentes eletrônicos
        - Aquecimento excessivo dos condutores
        
        Subtensão (< limite inferior):
        - Redução significativa do torque disponível
        - Aumento da corrente para manter potência
        - Aquecimento excessivo dos enrolamentos
        - Dificuldade de partida ou impossibilidade de partir
        - Operação instável em baixas rotações
        
    """
    logger.info('gerado eventooooooo de voltageeeeee')
    
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
                logger.info("SOBRETENSÃO DETECTADA - Fase {%s}: %s V > %s V", fase, tensao, limite_superior)
                
                await generate_event_properly(
                    event_generator,
                    event_type="Overvoltage",
                    message=f"Overvoltage detected",
                    severity=700,  # Severidade alta (requer ação)
                    VoltagePhase=fase
                )

            # Detecção de condição de subtensão
            elif tensao < limite_inferior:
                logger.info("SUBTENSÃO DETECTADA - Fase {%s}: %sV < %sV", fase, tensao, limite_inferior)
                
                await generate_event_properly(
                    event_generator,
                    event_type="Undervoltage", 
                    message=f"Undervoltage detected",
                    severity=700,  # Severidade alta 
                    VoltagePhase=fase
                )
            else:
                # Tensão dentro da faixa normal
                logger.info("Tensão fase {%s} normal: %sV (faixa: %sV - %sV)", fase, tensao, limite_inferior, limite_superior)
                
        except Exception as e:
            logger.info("Erro ao verificar tensão fase {%s}: {%s}", fase, e)
            # Erro é registrado mas não interrompe verificação das outras fases