"""
Módulo gerador de eventos OPC UA personalizados.

Este módulo fornece funcionalidades para criar e disparar eventos OPC UA
estruturados e padronizados para sistemas de monitoramento industrial.
Oferece conversão automática de tipos Python para tipos OPC UA Variant
e tratamento robusto de erros.

Funcionalidades principais:
- Geração de eventos OPC UA com metadados completos
- Conversão automática de tipos Python para OPC UA Variant
- Suporte a propriedades personalizadas dinâmicas
- Tratamento robusto de erros com logging detalhado
- Geração automática de IDs únicos para rastreamento

Supported Data Types:
    - str: Convertido para VariantType.String
    - bool: Convertido para VariantType.Boolean  
    - int: Convertido para VariantType.Int32
    - float: Convertido para VariantType.Float
    - outros: Convertidos para String via str()

Dependencies:
    - uuid: Geração de identificadores únicos
    - datetime: Timestamps UTC
    - asyncua.ua: Tipos OPC UA Variant e LocalizedText

"""

import uuid
import traceback
import logging
from datetime import datetime, timezone
from asyncua import ua
from asyncua.common.events import Event
logger = logging.getLogger(__name__)
logging.basicConfig(
    level = logging.INFO,
    format="%(asctime)s [%(levelname)s]: %(message)s"
)


async def generate_event_properly(event_generator, event_type, message, severity, **extra_props):
    """
    Gera e dispara um evento OPC UA personalizado com metadados completos.
    
    Esta função cria um evento OPC UA estruturado com todos os campos obrigatórios
    preenchidos e permite adicionar propriedades personalizadas dinamicamente.
    Realiza conversão automática de tipos Python para tipos OPC UA Variant
    apropriados.
    
    Args:
        event_generator: Instância do gerador de eventos OPC UA configurado.
                        Deve ter um atributo 'event' e método 'trigger()'
        event_type (str): Tipo/categoria do evento (ex: "Overcurrent", "Overvoltage").
                         Usado para classificação e filtragem
        message (str): Mensagem descritiva do evento em linguagem natural.
                      Se None ou vazia, será convertida para string vazia
        severity (int): Nível de severidade do evento (0-1000).
                       0=Baixa, 500=Média, 1000=Crítica
        **extra_props: Propriedades personalizadas adicionais como argumentos nomeados.
                      Serão convertidas automaticamente para tipos OPC UA
                      
    Event Fields Populated:
        - EventId: UUID único em bytes para identificação do evento
        - Time: Timestamp UTC de quando o evento foi gerado  
        - ReceiveTime: Timestamp UTC de quando o evento foi recebido
        - Message: Texto localizado com a mensagem do evento
        - Severity: Nível de severidade como UInt16
        - Propriedades personalizadas: Conforme **extra_props
        
    Type Conversion Rules:
        - str → VariantType.String
        - bool → VariantType.Boolean
        - int → VariantType.Int32  
        - float → VariantType.Float
        - outros → VariantType.String (via str())
        
    Severity Levels (OPC UA Standard):
        - 0-250: Baixa
        - 251-500: Média
        - 501-750: Alta
        - 751-1000: Crítica
        
    Example:
        >>> # Evento básico de sobrecorrente
        >>> await generate_event_properly(
        ...     event_gen,
        ...     event_type="Overcurrent", 
        ...     message="Corrente fase A excedeu limite",
        ...     severity=700,
        ...     CurrentPhase="A",
        ...     CurrentValue=12.5,
        ...     Threshold=10.0,
        ...     ActionRequired=True
        ... )
        
        >>> # Evento de temperatura com dados ambientais
        >>> await generate_event_properly(
        ...     event_gen,
        ...     event_type="OverTemperature",
        ...     message="Motor superaquecido", 
        ...     severity=800,
        ...     CaseTemperature=85.2,
        ...     MaxAllowed=75.0,
        ...     Location="Motor50CV"
        ... )
        
    Error Handling:
        - Propriedades inexistentes no event_generator são ignoradas silenciosamente
        - Erros de conversão de tipo são capturados e registrados
        - Falhas na geração não interrompem o sistema, apenas registram o erro
        - Stack trace completo é exibido para debugging
        
    Note:
        Esta função é assíncrona e deve ser aguardada. O evento é disparado
        imediatamente após a configuração bem-sucedida. Em caso de erro,
        o sistema continua operando normalmente, mas o evento pode não ser
        persistido ou distribuído.
        
    Technical Details:
        - EventId usa UUID4 para garantir unicidade global
        - Timestamps são sempre em UTC para consistência temporal
        - Message usa LocalizedText para suporte internacional
        - Severity segue padrão OPC UA UA-Part 5
        
    Performance Considerations:
        - Conversão de tipos é otimizada para tipos Python comuns
        - Geração de UUID tem overhead mínimo
        - Função é thread-safe para uso concorrente
    """
    logger.info('gerandooooooooo eventooooooooooooo')
    
    try:
        # Configuração de campos obrigatórios do evento OPC UA
        
        # EventId: Identificador único global para rastreamento
        event_generator.event.EventId = ua.Variant(
            uuid.uuid4().bytes, 
            ua.VariantType.ByteString
        )
        
        # Time: Timestamp de quando o evento foi gerado
        current_time = datetime.now(timezone.utc)
        event_generator.event.Time = ua.Variant(
            current_time, 
            ua.VariantType.DateTime
        )
        
        # ReceiveTime: Timestamp de quando o evento foi recebido pelo servidor
        event_generator.event.ReceiveTime = ua.Variant(
            current_time, 
            ua.VariantType.DateTime
        )
        
        # Message: Texto localizado com descrição do evento
        event_generator.event.Message = ua.Variant(
            ua.LocalizedText(message or ""), 
            ua.VariantType.LocalizedText
        )
        
        # Severity: Nível de severidade conforme padrão OPC UA
        event_generator.event.Severity = ua.Variant(
            severity, 
            ua.VariantType.UInt16
        )

        logger.info("=== DEBUG SEVERITY ===")
        logger.info("Severity input: %s (type: %s)", severity, type(severity))
        logger.info("event.Severity após definir: %s", event_generator.event.Severity)
        logger.info("event.Severity.Value: %s", getattr(event_generator.event.Severity, 'Value', 'NO VALUE ATTR'))
        logger.info("event.Severity.VariantType: %s", getattr(event_generator.event.Severity, 'VariantType', 'NO TYPE ATTR'))
        logger.info("=== END DEBUG ===")

        # Processamento de propriedades personalizadas
        for name, val in extra_props.items():
            # Verifica se a propriedade existe no tipo de evento
            if hasattr(event_generator.event, name):
                # Conversão automática de tipos Python para OPC UA Variant
                if isinstance(val, str):
                    v = ua.Variant(val, ua.VariantType.String)
                elif isinstance(val, bool):
                    v = ua.Variant(val, ua.VariantType.Boolean)
                elif isinstance(val, int):
                    v = ua.Variant(val, ua.VariantType.Int32)
                elif isinstance(val, float):
                    v = ua.Variant(val, ua.VariantType.Float)
                else:
                    # Fallback: converte qualquer outro tipo para string
                    v = ua.Variant(str(val), ua.VariantType.String)
                
                # Atribui a propriedade ao evento
                setattr(event_generator.event, name, v)

        # Disparo do evento para distribuição
        await event_generator.trigger()
        logger.info("Evento '{%s}' disparado com sucesso - Severity: {%s}", event_type, severity)
        
    except Exception as e:
        logger.exception("Erro ao gerar evento '{%s}': {%s}", event_type, e)
        traceback.logger_exc()
        # Não relança a exceção para não interromper o sistema