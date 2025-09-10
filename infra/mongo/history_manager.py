"""
Módulo de armazenamento de histórico OPC UA em MongoDB.

Este módulo implementa a interface HistoryStorageInterface do asyncua para
armazenar dados históricos e eventos de um servidor OPC UA em um banco de dados MongoDB.
Fornece funcionalidades completas de persistência para monitoramento industrial.

Classes:
    HistoryMongoDB: Interface de armazenamento histórico usando MongoDB

Dependencies:
    - pymongo: Driver assíncrono para MongoDB
    - asyncua: Biblioteca OPC UA para Python
    - infra.mongo.mappers: Conversores entre tipos OPC UA e MongoDB
    - utils.sanitize: Utilitários para sanitização de nomes de coleções

Environment Variables:
    MONGO_URI: String de conexão com MongoDB
    MONGO_DBNAME: Nome do banco de dados (padrão: motor50cv_teste)

"""

import os
import logging
from typing import List, Tuple, Union
from datetime import timedelta, datetime, timezone
from services.events.event_generator import generate_event_properly
from asyncua.common.events import Event
import pymongo
import asyncua.ua as ua
from asyncua.server import Server
from asyncua.server.history import HistoryStorageInterface
from asyncua.ua import NodeId, DataValue

from infra.mongo.mappers import (
    datavalue_to_dict,
    datavalue_from_dict,
    event_to_dict,
    event_from_dict,
)
from utils.sanitize import sanitize_collection  

logger = logging.getLogger(__name__)

class HistoryMongoDB(HistoryStorageInterface):
    """
    Implementação da interface de armazenamento histórico usando MongoDB.
    
    Esta classe implementa a interface HistoryStorageInterface do asyncua para
    persistir dados históricos e eventos em um banco MongoDB. Oferece funcionalidades
    completas de CRUD para dados temporais de um servidor OPC UA.
    
    Funcionalidades:
    - Armazenamento de valores históricos de variáveis OPC UA
    - Persistência de eventos personalizados
    - Consulta temporal de dados com filtros de data
    - Indexação automática para otimização de performance
    - Sanitização automática de nomes de coleções
    
    Attributes:
        connection (pymongo.AsyncMongoClient): Cliente assíncrono MongoDB
        database_name (str): Nome do banco de dados MongoDB
        server (Server): Instância do servidor OPC UA
        
    Note:
        Cada variável OPC UA é armazenada em uma coleção separada, nomeada
        como 'ParentNode_VariableName' (sanitizada). Eventos são armazenados
        na coleção 'events'.
    """
  
    def __init__(self, server: Server, max_history_data_response_size: int = 10000):
        """
        Inicializa o armazenamento histórico MongoDB.
        
        Args:
            server (Server): Instância do servidor OPC UA para acesso aos nós
            max_history_data_response_size (int, optional): Tamanho máximo de
                                                          resposta para consultas
                                                          históricas. Padrão: 10000
        
        Environment Variables:
            MONGO_URI: String de conexão MongoDB (obrigatória)
            MONGO_DBNAME: Nome do banco de dados (padrão: motor50cv_teste)
            
        Note:
            A conexão MongoDB é estabelecida de forma assíncrona e deve ser
            inicializada com o método init() antes do uso.
        """
        mongo_uri = os.getenv("MONGO_URI")
        self.connection = pymongo.AsyncMongoClient(mongo_uri)
        self.database_name = os.getenv("MONGO_DBNAME", "motor50cv_teste")
        self.server = server
        super().__init__(max_history_data_response_size)

    async def get_parent_name(self, node_id: NodeId) -> str:
        """
        Obtém o nome sanitizado para a coleção baseado na hierarquia do nó.
        
        Constrói o nome da coleção MongoDB combinando o nome do nó pai
        com o nome do nó atual, aplicando sanitização para garantir
        compatibilidade com MongoDB.
        
        Args:
            node_id (NodeId): Identificador do nó OPC UA
            
        Returns:
            str: Nome sanitizado da coleção no formato 'ParentName_NodeName'
            
        Example:
            Para um nó 'Temperature' filho de 'Environment':
            Retorna: 'Environment_Temperature'
            
        Note:
            A sanitização remove caracteres especiais e espaços para
            garantir nomes válidos de coleção MongoDB.
        """
        node = self.server.get_node(node_id)
        node_name = (await node.read_browse_name()).Name
        parent = await node.get_parent()
        parent_name = (await parent.read_browse_name()).Name
        return sanitize_collection(f"{parent_name}_{node_name}")

    async def init(self):
        """
        Inicializa o banco de dados e cria índices necessários.
        
        Configura a estrutura inicial do banco MongoDB, criando índices
        otimizados para consultas temporais na coleção de eventos.
        
        Indexes Created:
            - events_time_idx: Índice no campo 'Time.Value' da coleção 'events'
              para otimizar consultas temporais de eventos
              
        Note:
            Este método deve ser chamado antes de qualquer operação de
            armazenamento histórico. É idempotente e pode ser chamado
            múltiplas vezes sem efeitos colaterais.
        """
        db = self.connection[self.database_name]
        await db["events"].create_index("Time.Value", name="events_time_idx")

    async def stop(self):
        """
        Encerra a conexão com MongoDB de forma limpa.
        
        Fecha a conexão assíncrona com o banco de dados, liberando
        recursos de rede e conexões do pool.
        
        Note:
            Este método deve ser chamado durante o shutdown da aplicação
            para garantir que todas as conexões sejam encerradas adequadamente.
        """
        if self.connection:
            await self.connection.close()

    async def historize_data_change(self, node, period: timedelta, count: int = 0):
        """
        Habilita o armazenamento histórico para mudanças de dados de um nó.
        
        Configura um nó OPC UA para ter suas mudanças de valor automaticamente
        armazenadas no MongoDB com base no período especificado.
        
        Args:
            node: Nó OPC UA para historização
            period (timedelta): Período de coleta de dados
            count (int, optional): Limite de registros históricos. Padrão: 0 (ilimitado)
            
        Note:
            Em caso de erro durante a configuração, registra a exceção no log
            mas não interrompe a execução. O nó pode continuar funcionando
            sem histórico.
        """
        try:
            await self.new_historized_node(node.nodeid, period, count)
            logger.info("Histórico habilitado para: %s", node.nodeid)
        except Exception as e:
            logger.exception("Erro ao habilitar histórico para %s: %s", node.nodeid, e)

    async def new_historized_node(self, node_id: NodeId, period: timedelta, count: int = 0):
        """
        Cria estrutura de armazenamento para um novo nó historizado.
        
        Prepara a infraestrutura MongoDB necessária para armazenar dados
        históricos de um nó específico, incluindo criação de índices otimizados.
        
        Args:
            node_id (NodeId): Identificador do nó OPC UA
            period (timedelta): Período de coleta (não utilizado atualmente)
            count (int, optional): Limite de registros. Padrão: 0 (ilimitado)
            
        Database Structure:
            - Cria coleção com nome baseado na hierarquia do nó
            - Adiciona índice 'server_timestamp_index' para consultas temporais
            
        Note:
            O índice criado melhora significativamente a performance de
            consultas históricas ordenadas por tempo.
        """
        try:
            collection = await self.get_parent_name(node_id)
            db = self.connection[self.database_name]
            await db[collection].create_index("server_timestamp", unique=False, name="server_timestamp_index")
        except Exception as e:
            logger.exception("Erro em new_historized_node: %s", e)

    async def save_node_value(self, node_id: NodeId, datavalue: DataValue):
        """
        Salva um valor de nó no histórico MongoDB.
        
        Persiste um DataValue OPC UA no banco de dados, convertendo-o para
        formato MongoDB e armazenando na coleção apropriada.
        
        Args:
            node_id (NodeId): Identificador do nó OPC UA
            datavalue (DataValue): Valor e metadados a serem salvos
            
        Document Structure:
            O documento salvo contém:
            - Valor da variável
            - Timestamp do servidor
            - Timestamp da fonte
            - Status code
            - Metadados de qualidade
            
        Note:
            Utiliza mapeadores personalizados para converter tipos OPC UA
            para tipos compatíveis com MongoDB. Em caso de erro, registra
            a exceção mas não interrompe a operação.
        """
        try:
            collection = await self.get_parent_name(node_id)
            db = self.connection[self.database_name]

            document = datavalue_to_dict(datavalue)

            await db[collection].insert_one(document)
            v = datavalue.Value.Value if datavalue.Value else None
            logger.info("SALVO: %s = %r", collection, v)
        except Exception as e:
            logger.exception("ERRO save_node_value: %s", e)

    async def read_node_history(
        self,
        node_id: NodeId,
        start: datetime,
        end: datetime,
        nb_values: int,
    ) -> Tuple[List[DataValue], Union[datetime, None]]:
        """
        Lê dados históricos de um nó dentro de um período específico.
        
        Consulta o histórico de um nó OPC UA no MongoDB, retornando os valores
        armazenados dentro do intervalo temporal especificado.
        
        Args:
            node_id (NodeId): Identificador do nó OPC UA
            start (datetime): Data/hora de início da consulta
            end (datetime): Data/hora de fim da consulta
            nb_values (int): Número máximo de valores a retornar
            
        Returns:
            Tuple[List[DataValue], Union[datetime, None]]: 
                - Lista de DataValues encontrados (ordenados por timestamp)
                - Timestamp de continuação se houver mais dados, None caso contrário
                
        Query Details:
            - Usa índice 'server_timestamp' para performance otimizada
            - Ordena resultados em ordem cronológica ascendente
            - Aplica limite conforme nb_values
            
        Note:
            Retorna lista vazia em caso de erro ou ausência de dados.
            O timestamp de continuação permite implementar paginação
            para grandes volumes de dados históricos.
        """
        try:
            db = self.connection[self.database_name]
            collection = await self.get_parent_name(node_id)

            query = {"server_timestamp": {"$gte": start, "$lte": end}}
            count = await db[collection].count_documents(query)
            if count == 0:
                return [], None

            cursor = db[collection].find(query).sort("server_timestamp", pymongo.ASCENDING).limit(nb_values)
            result: List[DataValue] = []

            async for doc in cursor:
                try:
                    dv = datavalue_from_dict(doc)
                    result.append(dv)
                except Exception:
                    logger.exception("Erro ao converter documento para DataValue")

            continuation = result[-1].ServerTimestamp if count > nb_values and result else None
            return result, continuation
        except Exception as e:
            logger.exception("ERRO read_node_history: %s", e)
            return [], None

    async def historize_event(self, source, period: timedelta, count: int = 0):
        """
        Habilita o armazenamento histórico de eventos para um nó fonte.
        
        Configura um nó OPC UA para ter seus eventos automaticamente
        persistidos no MongoDB quando emitidos.
        
        Args:
            source: Nó fonte dos eventos (objeto que emite eventos)
            period (timedelta): Período de retenção (não utilizado atualmente)
            count (int, optional): Limite de eventos históricos. Padrão: 0 (ilimitado)
            
        Note:
            Eventos são armazenados na coleção 'events' com indexação temporal.
            Em caso de erro, registra a exceção mas permite que o sistema
            continue funcionando sem histórico de eventos.
        """
        try:
            await self.new_historized_event(source.nodeid, None, period, count)
            logger.info("Histórico de eventos habilitado para: %s", source.nodeid)
        except Exception as e:
            logger.exception("Erro ao habilitar histórico de eventos para %s: %s", source.nodeid, e)

    async def new_historized_event(self, source_id, evtypes, period: timedelta, count: int = 0):
        """
        Cria configuração para historização de eventos de uma fonte específica.
        
        Método de configuração inicial para preparar o armazenamento de eventos
        de um nó emissor específico.
        
        Args:
            source_id: Identificador do nó fonte dos eventos
            evtypes: Tipos de eventos a historizar (não utilizado atualmente)
            period (timedelta): Período de retenção
            count (int, optional): Limite de eventos. Padrão: 0 (ilimitado)
            
        Note:
            Atualmente apenas registra a configuração no log. A implementação
            completa pode incluir configurações específicas por tipo de evento.
        """
        logger.info("new_historized_event: %s, %s, %s, %s", source_id, evtypes, period, count)

    async def save_event(self, event: generate_event_properly ):
        """
        Salva um evento OPC UA no histórico MongoDB.
        """
        logger.info("save ent chamadooooooooooooooooooooooooooooooooooo")
        try:
            event_dict = event_to_dict(event)
            basic_fields = {'EventId', 'Time', 'ReceiveTime', 'Message', 'Severity'}
            if set(event_dict.keys()) == basic_fields and event_dict['Severity']['Value'] ==  700 or event_dict["Severity"]['Value'] == 900:
                logger.info("Evento detectado")
                
            logger.info("EVENT_DICT: %s", event_dict)
            
            logger.info("Database name: [%s]", self.database_name)
            logger.info("Connection: [%s]", self.connection)
            
            db = self.connection[self.database_name]
            logger.info("DB object: [%s]", db)
            
            result = await db["events"].insert_one(event_dict)
            logger.info("INSERT RESULT: [%s]", result)
            logger.info("INSERTED ID: [%s]", result.inserted_id)
            
            count = await db["events"].count_documents({})
            logger.info("TOTAL EVENTS IN DB: {%s}", count)
            
        except Exception as e:
            logger.info("ERRO COMPLETO: {%s}", e)
            import traceback
            traceback.logger_exc()
            logger.exception("ERRO save_event: %s", e)

    async def read_event_history(
        self,
        source_id: NodeId,
        start: datetime,
        end: datetime,
        nb_events: int,
        select_clauses,
    ) -> Tuple[List[Event], Union[datetime, None]]:
        """
        Lê histórico de eventos dentro de um período específico.
        
        Consulta eventos armazenados no MongoDB dentro do intervalo temporal
        especificado, retornando objetos Event reconstituídos.
        
        Args:
            source_id (NodeId): Identificador do nó fonte (não utilizado atualmente)
            start (datetime): Data/hora de início da consulta
            end (datetime): Data/hora de fim da consulta  
            nb_events (int): Número máximo de eventos a retornar
            select_clauses: Cláusulas de seleção (não utilizadas atualmente)
            
        Returns:
            Tuple[List[Event], Union[datetime, None]]:
                - Lista de objetos Event encontrados (ordenados cronologicamente)
                - Timestamp de continuação se houver mais eventos, None caso contrário
                
        Query Details:
            - Usa índice 'events_time_idx' para performance otimizada
            - Consulta campo 'Time.Value' para filtro temporal
            - Ordena resultados em ordem cronológica ascendente
            - Aplica limite conforme nb_events
            
        Note:
            Utiliza mapeadores personalizados para reconstituir objetos Event
            a partir de documentos MongoDB. Em caso de erro na conversão de
            um evento específico, registra o erro mas continua processando
            os demais eventos.
        """
        try:
            db = self.connection[self.database_name]
            query = {"$and": [{"Time.Value": {"$gte": start}}, {"Time.Value": {"$lte": end}}]}
            count = await db["events"].count_documents(query)
            cursor = db["events"].find(query).sort("Time.Value", pymongo.ASCENDING).limit(nb_events)

            events: List[Event] = []
            async for document in cursor:
                logger.info("Documento: [%s]", document)
                try:
                    events.append(event_from_dict(document))
                except Exception:
                    logger.exception("Erro ao converter evento")

            continuation = events[-1].Time.Value if count > nb_events and events else None
            return events, continuation
        except Exception as e:
            logger.exception("ERRO read_event_history: %s", e)
            return [], None