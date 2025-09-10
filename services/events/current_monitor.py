"""
Módulo de monitoramento de corrente elétrica para detecção de sobrecarga.

Este módulo implementa o sistema de monitoramento contínuo das correntes elétricas
trifásicas de um motor, detectando condições de sobrecarga e gerando eventos OPC UA
automáticos quando os limites operacionais são excedidos.

Funcionalidades principais:
- Monitoramento de corrente em tempo real para as três fases (A, B, C)
- Detecção de sobrecarga baseada em corrente nominal + tolerância
- Geração automática de eventos OPC UA para condições anômalas
- Tratamento robusto de erros para garantir continuidade do monitoramento

Constants Required:
    NOMINAL_CURRENT: Corrente nominal do motor em amperes
    TOLERANCE: Percentual de tolerância para sobrecarga (ex: 0.1 = 10%)

Dependencies:
    - services.opcua.node_manager: Gerenciador de nós OPC UA
    - services.events.event_generator: Gerador de eventos personalizado
    - utils.constants: Constantes do sistema (corrente nominal e tolerância)

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
    
    Função utilitária que abstrai a leitura de valores numéricos de nós OPC UA,
    oferecendo compatibilidade com diferentes tipos de containers de variáveis
    (OPCUANodeManager ou dicionários simples).
    
    Args:
        nodes_variables (OPCUANodeManager | dict): Container de variáveis OPC UA.
                                                  Pode ser um OPCUANodeManager 
                                                  ou dicionário de nós
        name (str): Nome da variável a ser lida (ex: 'CurrentA', 'CurrentB')
        
    Returns:
        float: Valor numérico da variável convertido para float
        
    Raises:
        KeyError: Se a variável especificada não for encontrada
        ValueError: Se o valor não puder ser convertido para float
        Exception: Erros de comunicação OPC UA ou problemas de rede
        
    Example:
        >>> corrente_a = await _read_float(node_manager, 'CurrentA')
        >>> logger(f"Corrente fase A: {corrente_a:.2f} A")
        
    Note:
        Esta função serve como uma camada de abstração que permite
        flexibilidade no tipo de container usado para as variáveis,
        facilitando testes e diferentes implementações.
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
    
    Esta função realiza o monitoramento contínuo das correntes elétricas nas
    três fases (A, B, C) do motor, comparando os valores lidos com a corrente
    nominal mais tolerância. Quando detectada sobrecarga em qualquer fase,
    gera automaticamente um evento OPC UA com severidade alta.
    
    Args:
        nodes_variables (OPCUANodeManager): Gerenciador contendo as variáveis
                                          de corrente (CurrentA, CurrentB, CurrentC)
        event_generator: Gerador de eventos OPC UA configurado para o tipo
                        Motor50CVMonitoringEvent
                        
    Monitored Variables:
        - CurrentA: Corrente da fase A em amperes
        - CurrentB: Corrente da fase B em amperes  
        - CurrentC: Corrente da fase C em amperes
        
    Event Generation:
        Tipo: "Overcurrent"
        Severidade: 700 (Alta - indica condição perigosa)
        Mensagem: "Overcurrent detected"
        Campo personalizado: CurrentPhase (identifica a fase problemática)
        
    Detection Logic:
        Sobrecarga detectada quando:
        corrente > NOMINAL_CURRENT × (1 + TOLERANCE)
        
        Exemplo com NOMINAL_CURRENT=10A e TOLERANCE=0.1:
        Alarme disparado se corrente > 11A
        
    Error Handling:
        - Variáveis inexistentes são ignoradas (não interrompem o processo)
        - Erros de leitura são registrados mas não param o monitoramento
        - Cada fase é verificada independentemente
        
    Example:
        >>> # Configuração típica
        >>> NOMINAL_CURRENT = 10.0  # 10 amperes
        >>> TOLERANCE = 0.15        # 15% de tolerância
        >>> 
        >>> # Monitoramento detectará sobrecarga se qualquer corrente > 11.5A
        >>> await check_current_events(node_manager, event_gen)
        
    Note:
        Esta função deve ser chamada periodicamente (recomendado: a cada 5s)
        para garantir detecção rápida de condições anômalas. O monitoramento
        é não-bloqueante e permite que o sistema continue operando mesmo
        com falhas em fases individuais.
        
    Safety Considerations:
        - Sobrecarga pode indicar problemas mecânicos ou elétricos sérios
        - Eventos gerados devem acionar alarmes ou sistemas de proteção
        - Correntes muito altas podem danificar equipamentos permanentemente
    """
    logger.info("evento de corrent gerandooooooo")
    
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
                logger("SOBRECARGA DETECTADA - Fase {%s}: %sA > %sA", fase, corrente, limite_sobrecarga)
                
                # Geração de evento OPC UA para sobrecarga
                await generate_event_properly(
                    event_generator,
                    event_type="Overcurrent",
                    message=f"Overcurrent detected",
                    severity=700,  # Severidade alta (0-1000, onde 1000 é crítico)
                    CurrentPhase=fase
                )
                
        except Exception as e:
            logger.info("Erro ao verificar corrente fase {%s}: {%s}", fase, e)
            # Erro é registrado mas não interrompe verificação das outras fases