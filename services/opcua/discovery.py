"""
Servidor OPC UA para monitoramento de Motor 50CV.

Este módulo implementa um servidor OPC UA completo para monitoramento de um motor de 50CV,
incluindo variáveis elétricas, ambientais e de vibração com histórico e eventos.
"""

import os
import asyncio
import logging
import types
from asyncua import ua
from asyncua.server.history import HistoryStorageInterface
from datetime import datetime, timezone, timedelta
from asyncua import Client, Server
from asyncua.ua import ObjectIds, VariantType
from dotenv import load_dotenv
from asyncua import ua
from infra.mqtt.client import MQTTChannel
from services.opcua.node_manager import OPCUANodeManager
from utils.constants import MQTT_TO_OPCUA_MAP
from infra.mongo.history_manager import HistoryMongoDB
from services.events.current_monitor import check_current_events
from services.events.voltage_monitor import check_voltage_events
from services.events.temperature_monitor import check_temperature_events

load_dotenv()
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s]: %(message)s"
)
    
def patch_monitored_item_service():
    """Patch para desabilitar WhereClause no MonitoredItemService."""
    try:
        from asyncua.server.monitored_item_service import MonitoredItemService
        
        # Salva o método original
        original_trigger_event = MonitoredItemService.trigger_event
        
        # Cria novo método que preserva o evento original
        async def new_trigger_event(self, original_event):
            # Para cada monitored item de eventos
            for mid, mdata in self._monitored_items.items():
                try:
                    # Verifica se é um EventFilter
                    if hasattr(mdata, 'filter') and mdata.filter:
                        # PRESERVAR O EVENTO ORIGINAL ao invés de criar novo
                        fieldlist = ua.EventFieldList()
                        fieldlist.ClientHandle = mdata.client_handle
                        
                        # Usar o evento original diretamente
                        if hasattr(mdata.filter, 'Body') and hasattr(mdata.filter.Body, 'SelectClauses'):
                            select_clauses = mdata.filter.Body.SelectClauses
                        elif hasattr(mdata.filter, 'SelectClauses'):
                            select_clauses = mdata.filter.SelectClauses
                        else:
                            continue
                            
                        # USAR O EVENTO ORIGINAL para preservar campos personalizados
                        fieldlist.EventFields = original_event.to_event_fields(select_clauses)
                        await self.isub.enqueue_event(mid, fieldlist, mdata.queue_size)
                        
                        logger.info(f"Evento preservado para monitored item {mid}")
                        
                except Exception as e:
                    logger.warning(f"Erro ao processar monitored item {mid}: {e}")
        
        # Aplica o patch
        MonitoredItemService.trigger_event = new_trigger_event
        logger.info("Patch aplicado - eventos originais serão preservados")
        
    except Exception as e:
        logger.warning(f"Erro ao aplicar patch: {e}")
        
async def task_register_discovery(server: Server, registration_interval: float | None):
    """
    Registra o servidor OPC UA no Local Discovery Server (LDS) periodicamente.
    
    Args:
        server (Server): Instância do servidor OPC UA
        registration_interval (float | None): Intervalo em segundos entre registros
    """
    lds_endpoint = os.getenv("LDS_ENDPOINT")
    if not lds_endpoint:
        logger.warning("LDS_ENDPOINT não configurado")
        return
 
    if registration_interval is None:
        try:
            registration_interval = float(os.getenv("LDS_REGISTER_INTERVAL", "15"))
        except Exception:
            registration_interval = 15.0

    while True:
        try:
            async with Client(lds_endpoint) as client:
                await client.register_server(server)
                logger.info("Registrado no LDS: %s", lds_endpoint)
        except Exception as e:
            logger.exception("Falha ao registrar no LDS: %s", e)
        await asyncio.sleep(registration_interval)

async def configure_server_info(server: Server):
    """
    Configura as informações básicas do servidor OPC UA.
    
    Args:
        server (Server): Instância do servidor OPC UA a ser configurado
    """
    await server.set_build_info(
        product_uri=os.getenv("OPCUA_PRODUCT_URI", "http://examples.freeopcua.github.io"),
        manufacturer_name=os.getenv("OPCUA_MANUFACTURER", "Camila LTDA"),
        product_name=os.getenv("OPCUA_PRODUCT_NAME", "opcua-server"),
        software_version=os.getenv("OPCUA_SOFTWARE_VERSION", "1.0.0"),
        build_number=os.getenv("OPCUA_BUILD_NUMBER", "20250820"),
        build_date=datetime.now(timezone.utc),
    )
    app_uri = os.getenv("OPCUA_APPLICATION_URI", "urn:camila:opcua-server")
    await server.set_application_uri(app_uri)
    server.set_server_name(os.getenv("OPCUA_SERVER_NAME", "Camila OPC UA Server"))

async def check_events(event_generator, nodes_variables):
    """
    Monitora continuamente as variáveis do motor e gera eventos quando necessário.
    
    Args:
        event_generator: Gerador de eventos OPC UA personalizado
        nodes_variables: Gerenciador de nós contendo as variáveis do motor
    """
    await asyncio.sleep(0.5)
    while True:
        try:
            if event_generator:
                await check_temperature_events(nodes_variables, event_generator)
                await check_voltage_events(nodes_variables, event_generator)
                await check_current_events(nodes_variables, event_generator)
        except Exception:
            logger.exception("Falha ao checar eventos")
        await asyncio.sleep(5) 
    
async def init_mqtt(node_manager: OPCUANodeManager) -> MQTTChannel:
    """
    Inicializa o canal de comunicação MQTT.
    
    Args:
        node_manager (OPCUANodeManager): Gerenciador de nós OPC UA
    
    Returns:
        MQTTChannel: Canal MQTT inicializado
    """
    ch = MQTTChannel(node_manager=node_manager, variable_mapper=MQTT_TO_OPCUA_MAP)
    await ch.init()
    return ch

async def discovery():
    """
    Função principal que inicializa e executa o servidor OPC UA.
    
    Coordena toda a inicialização do servidor incluindo configuração de nós,
    histórico, eventos, MQTT e registro no LDS.
    """
    patch_monitored_item_service()
    
    server = Server()
    await server.init()

    storage = HistoryMongoDB(server)
    await storage.init()
    server.iserver.history_manager.set_storage(storage)
    await configure_server_info(server)

    # Registro do namespace personalizado
    idx = await server.register_namespace(
        os.getenv("OPCUA_SERVER_PRODUCT_URI", "urn:camila.github.io:python:server")
    )

    # Criação da estrutura hierárquica de nós
    motor50cv = await server.nodes.objects.add_folder(idx, "Motor50CV")
    electrical = await motor50cv.add_object(idx, "Electrical")
    environment = await motor50cv.add_object(idx, "Environment")
    vibration = await motor50cv.add_object(idx, "Vibration")

    # Definição das variáveis por categoria
    electrical_variables = [
        "VoltageA", "VoltageB", "VoltageC",          # Tensões por fase
        "CurrentA", "CurrentB", "CurrentC",          # Correntes por fase
        "PowerActive", "PowerReactive", "PowerApparent",  # Potências
        "EnergyActive", "EnergyReactive", "EnergyApparent",  # Energias
        "PowerFactor", "Frequency",                  # Fator de potência e frequência
    ]

    environment_variables = ["Temperature", "Humidity", "CaseTemperature"]
    vibration_variables   = ["Axial", "Radial"]

    # Criação e configuração das variáveis OPC UA
    nodes_variables = {}
    for parent, variables in (
        (electrical, electrical_variables),
        (environment, environment_variables),
        (vibration, vibration_variables),
    ): 
        for var in variables:
            node_val = await parent.add_variable(idx, var, 0.0)
            await node_val.set_writable()
            nodes_variables[var] = node_val
            
    # Configuração do gerenciador de nós e integração MQTT
    node_manager = OPCUANodeManager()
    node_manager.set_nodes(nodes_variables)
    _ch = await init_mqtt(node_manager)

    # Configuração do sistema de histórico
    variables_for_history = list(nodes_variables.keys())
    for nome_variavel in variables_for_history:
        try:
            node = nodes_variables[nome_variavel]
            await server.iserver.enable_history_data_change(
                node, 
                period=timedelta(seconds=5),  # Coleta a cada 5 segundos
                count=10000)                  # Máximo 10.000 registros
            
            await node.write_attribute(
                    ua.AttributeIds.Historizing,
                    ua.DataValue(ua.Variant(True, ua.VariantType.Boolean))
                )
            logger.info("History habilitado -> [%s]", nome_variavel)
        except:
            logger.exception("Error -> history")
    
    # Configuração de eventos personalizados
    try:
        # Criação do tipo de evento personalizado
        etype = await server.create_custom_event_type(
            idx, "Motor50CVMonitoringEvent", ObjectIds.BaseEventType, [
                ("CaseTemperature", VariantType.Float),   # Temperatura do case
                ("VoltagePhase", VariantType.String),     # Fase com problema de tensão
                ("CurrentPhase", VariantType.String)      # Fase com problema de corrente
            ],
        )

        # Configuração do nó como emissor de eventos
        try:
            await motor50cv.write_attribute(
                ua.AttributeIds.EventNotifier,
                ua.DataValue(ua.Variant(1, ua.VariantType.Byte))  
            )
        except AttributeError:
            await server.set_attribute_value(
                motor50cv.nodeid,
                ua.AttributeIds.EventNotifier,
                ua.DataValue(ua.Variant(1, ua.VariantType.Byte))
            )
        
        # Habilitação do histórico de eventos
        await server.iserver.enable_history_event(
            motor50cv, period=None, count=10000
        )

        # Criação do gerador de eventos
        event_generator = await server.get_event_generator(etype, motor50cv)
        try:
            event_generator.emitting_node = motor50cv
            logger("Event generator configurado com sucesso")
        except Exception:
            event_generator.emitting_node = motor50cv.nodeid

    except Exception as e:
        logger.exception("Erro ao configurar eventos: {%s}", e)
        event_generator = None

    # Execução do servidor com tarefas assíncronas
    async with server:
        asyncio.create_task(task_register_discovery(server, registration_interval=10))
        asyncio.create_task(check_events(event_generator, node_manager))
        await asyncio.Future()  # Mantém o servidor executando indefinidamente

if __name__ == "__main__":
    """
    Ponto de entrada da aplicação.
    
    Executa o servidor OPC UA em modo assíncrono utilizando asyncio.
    """
    asyncio.run(discovery())