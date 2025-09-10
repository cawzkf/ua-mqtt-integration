"""
Módulo de monitoramento de temperatura crítica para proteção de equipamentos.

Este módulo implementa o sistema de monitoramento contínuo da temperatura da carcaça
do motor, detectando condições críticas de superaquecimento que podem causar danos
permanentes ao equipamento ou riscos de segurança.

Funcionalidades principais:
- Monitoramento em tempo real da temperatura da carcaça do motor
- Detecção de condições críticas de superaquecimento
- Geração automática de eventos OPC UA de alta severidade
- Proteção contra falhas de leitura de sensores
- Tratamento robusto de erros para continuidade operacional

Temperature Monitoring:
    - CaseTemperature: Temperatura da carcaça em graus Celsius
    - Comparação com limite CRITICAL_TEMPERATURE
    - Eventos gerados apenas para condições verdadeiramente críticas

Constants Required:
    CRITICAL_TEMPERATURE: Temperatura crítica da carcaça em °C (ex: 80.0)

Dependencies:
    - services.events.event_generator: Gerador de eventos OPC UA
    - services.opcua.node_manager: Gerenciador de nós OPC UA
    - utils.constants: Constantes do sistema (temperatura crítica)

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
    
    Função utilitária que abstrai a leitura de valores numéricos de nós OPC UA,
    oferecendo compatibilidade com diferentes tipos de containers de variáveis
    e garantindo conversão segura para tipo float.
    
    Args:
        nodes_variables (OPCUANodeManager | dict): Container de variáveis OPC UA.
                                                  Pode ser um OPCUANodeManager 
                                                  ou dicionário de nós
        name (str): Nome da variável a ser lida (ex: 'CaseTemperature')
        
    Returns:
        float: Valor numérico da variável convertido para float
        
    Raises:
        KeyError: Se a variável especificada não for encontrada no container
        ValueError: Se o valor lido não puder ser convertido para float
        Exception: Erros de comunicação OPC UA, problemas de rede ou sensor
        
    Example:
        >>> temperatura = await _read_float(node_manager, 'CaseTemperature')
        >>> logger(f"Temperatura da carcaça: {temperatura:.1f} °C")
        
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


async def check_temperature_events(nodes_variables: OPCUANodeManager, event_generator):
    """
    Monitora temperatura da carcaça e gera eventos para condições críticas.
    
    Esta função realiza o monitoramento contínuo da temperatura da carcaça do motor,
    comparando com o limite crítico estabelecido. Quando a temperatura excede o
    limite seguro, gera automaticamente um evento OPC UA de alta severidade para
    alertar sobre possível falha iminente ou risco de segurança.
    
    Args:
        nodes_variables (OPCUANodeManager): Gerenciador contendo a variável
                                          CaseTemperature
        event_generator: Gerador de eventos OPC UA configurado para o tipo
                        Motor50CVMonitoringEvent
                        
    Monitored Variable:
        - CaseTemperature: Temperatura da carcaça do motor em graus Celsius
        
    Event Generation:
        Tipo: "CriticalTemperature"
        Severidade: 900 (Crítica - requer ação imediata)
        Mensagem: "Case temperature critical: {valor:.2f} °C"
        Campo personalizado: CaseTemperature (valor numérico da temperatura)
        
    Detection Logic:
        Condição crítica detectada quando:
        CaseTemperature > CRITICAL_TEMPERATURE
        
        Exemplo com CRITICAL_TEMPERATURE=80°C:
        Alarme disparado se temperatura > 80°C
        
    Error Handling:
        - Se CaseTemperature não existir, retorna silenciosamente (fail-safe)
        - Erros de leitura são registrados mas não interrompem monitoramento
        - Sistema continua operando mesmo com falhas do sensor
        - Não gera eventos falsos em caso de erro de comunicação
        
    Example:
        >>> # Configuração típica
        >>> CRITICAL_TEMPERATURE = 80.0  # 80 graus Celsius
        >>> 
        >>> # Monitoramento detectará condição crítica se temp > 80°C
        >>> await check_temperature_events(node_manager, event_gen)
        >>> # Resultado: evento gerado se temperatura = 85°C
        
    Note:
        Esta função deve ser chamada periodicamente (recomendado: a cada 5s)
        para detectar rapidamente condições de superaquecimento. O monitoramento
        é fail-safe: prefere não gerar evento a gerar falso positivo.
        
    Safety Considerations:
        - Temperatura crítica pode indicar falha iminente de componentes
        - Superaquecimento pode causar deformação de peças metálicas
        - Risco de incêndio em casos extremos de superaquecimento
        - Degradação acelerada de lubrificantes e isolamentos
        - Necessidade de parada de emergência em casos críticos
        
    Operational Context:
        - Temperaturas normais de operação: 40-60°C
        - Faixa de atenção: 60-80°C
        - Faixa crítica: > 80°C (conforme CRITICAL_TEMPERATURE)
        - Temperatura de desligamento de emergência: definida pela aplicação
        
    Sensor Requirements:
        - Sensor de temperatura RTD ou termopar na carcaça
        - Precisão mínima: ±2°C
        - Tempo de resposta: < 10 segundos
        - Faixa operacional: -20°C a +150°C
    """
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
            logger.info("TEMPERATURA CRÍTICA DETECTADA: : %s°C > %s°C", temp_carcaca, CRITICAL_TEMPERATURE)
            
            # Geração de evento crítico de temperatura
            await generate_event_properly(
                event_generator,
                event_type="CriticalTemperature",
                message="Case temperature critical",
                severity=900,  # Severidade crítica (requer ação imediata)
                CaseTemperature=temp_carcaca
            )
        else:
            # Temperatura dentro da faixa segura - log opcional para debug
            logger.info("Temperatura normal: %s °C (limite: %s°C)", temp_carcaca, CRITICAL_TEMPERATURE)

    except Exception as e:
        logger("Erro ao verificar temperatura: {%s}", e)
        # Erro é registrado mas não interrompe o sistema de monitoramento