"""
Módulo gerador de eventos OPC UA personalizados - SALVA DIRETO NO MONGODB

Este módulo fornece funcionalidades para gerar eventos OPC UA com salvamento direto no MongoDB.
"""

import uuid
import traceback
import logging
import os
import pymongo
from datetime import datetime, timezone
from asyncua import ua
from asyncua.common.events import Event

logger = logging.getLogger(__name__)

async def generate_event_properly(event_generator, event_type, message, severity, **extra_props):
    """
    Gera e dispara um evento OPC UA personalizado salvando diretamente no MongoDB.
    
    Args:
        event_generator: Objeto gerador de eventos OPC UA
        event_type (str): Tipo do evento para identificação
        message (str): Mensagem descritiva do evento
        severity (int): Nível de severidade (0-1000)
        **extra_props: Campos personalizados adicionais
    
    Returns:
        None
    """
    try:
        # Configurar campos obrigatórios do evento OPC UA
        event_id_bytes = uuid.uuid4().bytes
        current_time = datetime.now(timezone.utc)
        
        # EventId
        event_generator.event.EventId = ua.Variant(
            event_id_bytes, 
            ua.VariantType.ByteString
        )
        
        # Time
        event_generator.event.Time = ua.Variant(
            current_time, 
            ua.VariantType.DateTime
        )
        
        # ReceiveTime
        event_generator.event.ReceiveTime = ua.Variant(
            current_time, 
            ua.VariantType.DateTime
        )
        
        # Message
        event_generator.event.Message = ua.Variant(
            ua.LocalizedText(message or ""), 
            ua.VariantType.LocalizedText
        )
        
        # Severity
        event_generator.event.Severity = ua.Variant(
            severity, 
            ua.VariantType.UInt16
        )

        # Adicionar campos personalizados
        for name, val in extra_props.items():
            logger.info("Adicionando campo personalizado: %s = %s", name, val)
            
            if isinstance(val, str):
                v = ua.Variant(val, ua.VariantType.String)
            elif isinstance(val, bool):
                v = ua.Variant(val, ua.VariantType.Boolean)
            elif isinstance(val, int):
                v = ua.Variant(val, ua.VariantType.Int32)
            elif isinstance(val, float):
                v = ua.Variant(val, ua.VariantType.Float)
            else:
                v = ua.Variant(str(val), ua.VariantType.String)
            
            try:
                event_generator.event.add_property(name, v, None)
                logger.info("Campo %s adicionado via add_property", name)
            except Exception as e1:
                try:
                    setattr(event_generator.event, name, v)
                    logger.info("Campo %s adicionado via setattr", name)
                except Exception as e2:
                    logger.warning("Não foi possível adicionar campo %s: %s, %s", name, e1, e2)

        # CONSTRUIR O DICIONÁRIO out
        out = {
            "Time": {
                "VariantType": 13,  # DateTime
                "Value": current_time
            },
            "ReceiveTime": {
                "VariantType": 13,  # DateTime
                "Value": current_time
            },
            "Message": {
                "VariantType": 21,  # LocalizedText
                "Value": message or ""
            },
            "Severity": {
                "VariantType": 5,   # UInt16
                "Value": severity
            }
        }
                
        # Adicionar campos personalizados ao out
        for name, val in extra_props.items():
            logger.info("Adicionando %s ao out: %s", name, val)
            
            # Determinar tipo OPC UA
            if isinstance(val, str):
                vt = 12  # String
            elif isinstance(val, bool):
                vt = 1   # Boolean
            elif isinstance(val, int):
                vt = 6   # Int32
            elif isinstance(val, float):
                vt = 10  # Float
            else:
                vt = 12  # String (fallback)
                val = str(val)
            
            out[name] = {
                "VariantType": vt,
                "Value": val
            }

        # SALVAR DIRETO NO MONGODB
        logger.info("Salvando evento diretamente no MongoDB...")
        logger.info("Campos no out: %s", list(out.keys()))
        
        try:
            mongo_uri = os.getenv("MONGO_URI")
            mongo_client = pymongo.AsyncMongoClient(mongo_uri)
            database_name = os.getenv("MONGO_DBNAME", "motor50cv_teste")
            db = mongo_client[database_name]
            
            # Verificar campos personalizados ANTES de salvar no MongoDB
            standard_fields = {'EventId', 'Time', 'ReceiveTime', 'Message', 'Severity'}
            custom_fields_before_save = set(out.keys()) - standard_fields

            # Salvar no MongoDB
            result = await db["events"].insert_one(out)

            logger.info("Evento salvo no mongo: [%s]", result)

            # Mostrar campos personalizados usando os dados ANTES de salvar
            if custom_fields_before_save:
                for field in custom_fields_before_save:
                    try:
                        if isinstance(out[field], dict) and 'Value' in out[field]:
                            logger.info("  - %s: %s", field, out[field]['Value'])
                        else:
                            logger.info("  - %s: %s", field, out[field])
                    except Exception as e:
                        logger.warning("Erro ao exibir campo %s: %s", field, e)
            else:
                logger.warning("Nenhum campo personalizado encontrado")

            await mongo_client.close()
            
        except Exception as e:
            logger.exception("Erro ao salvar diretamente no MongoDB: %s", e)

        # Disparar o evento normalmente 
        await event_generator.trigger()
        logger.info("Evento '%s' disparado - eventos salvos no MongoDB", event_type)
        
    except Exception as e:
        logger.exception("Erro ao gerar evento '%s': %s", event_type, e)
        traceback.print_exc()