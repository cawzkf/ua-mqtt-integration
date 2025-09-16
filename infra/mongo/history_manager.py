"""
Módulo de armazenamento de histórico OPC UA em MongoDB.

Este módulo implementa a interface HistoryStorageInterface do asyncua para
armazenar dados históricos e eventos de um servidor OPC UA em MongoDB.
"""

import os
import asyncua.ua as ua
import logging
import pymongo
from typing import List, Tuple, Union
from datetime import timedelta, datetime, timezone
from asyncua.common.events import Event
from motor.motor_asyncio import AsyncIOMotorClient
from asyncua.server import Server
from asyncua.server.history import HistoryStorageInterface
from asyncua.ua import NodeId, DataValue

from infra.mongo.mappers import (
    datavalue_to_dict,
    datavalue_from_dict,
    event_from_dict,
)
from utils.sanitize import sanitize_collection  

logger = logging.getLogger(__name__)

class HistoryMongoDB(HistoryStorageInterface):
    """
    Implementação da interface de armazenamento histórico usando MongoDB.
    
    Esta classe persiste dados históricos e eventos OPC UA em um banco MongoDB,
    oferecendo funcionalidades completas de CRUD para dados temporais.
    """
  
    def __init__(self, server: Server, max_history_data_response_size: int = 10000):
        """
        Inicializa o armazenamento histórico MongoDB.
        
        Args:
            server (Server): Instância do servidor OPC UA
            max_history_data_response_size (int): Tamanho máximo de resposta. Padrão: 10000
        """
        mongo_uri = os.getenv("MONGO_URI")
        self.connection = AsyncIOMotorClient(mongo_uri)
        self.database_name = os.getenv("MONGO_DBNAME", "motor50cv")
        self.server = server
        super().__init__(max_history_data_response_size)

    async def get_parent_name(self, node_id: NodeId) -> str:
        """
        Obtém o nome sanitizado para a coleção baseado na hierarquia do nó.
        
        Args:
            node_id (NodeId): Identificador do nó OPC UA
            
        Returns:
            str: Nome sanitizado da coleção no formato 'ParentName_NodeName'
        """
        node = self.server.get_node(node_id)
        node_name = (await node.read_browse_name()).Name
        parent = await node.get_parent()
        parent_name = (await parent.read_browse_name()).Name
        return sanitize_collection(f"{parent_name}_{node_name}")

    async def init(self):
        """
        Inicializa o banco de dados e cria índices necessários.
        """
        db = self.connection[self.database_name]
        await db["events"].create_index("Time.Value", name="events_time_idx")

    async def stop(self):
        """
        Encerra a conexão com MongoDB de forma limpa.
        """
        if self.connection:
            await self.connection.close()

    async def historize_data_change(self, node, period: timedelta, count: int = 0):
        """
        Habilita o armazenamento histórico para mudanças de dados de um nó.
        
        Args:
            node: Nó OPC UA para historização
            period (timedelta): Período de coleta de dados
            count (int): Limite de registros históricos. Padrão: 0 (ilimitado)
        """
        try:
            await self.new_historized_node(node.nodeid, period, count)
            logger.info("Histórico habilitado para: %s", node.nodeid)
        except Exception as e:
            logger.exception("Erro ao habilitar histórico para %s: %s", node.nodeid, e)

    async def new_historized_node(self, node_id: NodeId, period: timedelta, count: int = 0):
        """
        Cria estrutura de armazenamento para um novo nó historizado.
        
        Args:
            node_id (NodeId): Identificador do nó OPC UA
            period (timedelta): Período de coleta
            count (int): Limite de registros. Padrão: 0 (ilimitado)
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
        
        Args:
            node_id (NodeId): Identificador do nó OPC UA
            datavalue (DataValue): Valor e metadados a serem salvos
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
        
        Args:
            node_id (NodeId): Identificador do nó OPC UA
            start (datetime): Data/hora de início da consulta
            end (datetime): Data/hora de fim da consulta
            nb_values (int): Número máximo de valores a retornar
            
        Returns:
            Tuple[List[DataValue], Union[datetime, None]]: Lista de valores e timestamp de continuação
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
        
        Args:
            source: Nó fonte dos eventos
            period (timedelta): Período de retenção
            count (int): Limite de eventos históricos. Padrão: 0 (ilimitado)
        """
        try:
            await self.new_historized_event(source.nodeid, None, period, count)
            logger.info("Histórico de eventos habilitado para: %s", source.nodeid)
        except Exception as e:
            logger.exception("Erro ao habilitar histórico de eventos para %s: %s", source.nodeid, e)

    async def new_historized_event(self, source_id, evtypes, period: timedelta, count: int = 0):
        """
        Cria configuração para historização de eventos de uma fonte específica.
        
        Args:
            source_id: Identificador do nó fonte dos eventos
            evtypes: Tipos de eventos a historizar
            period (timedelta): Período de retenção
            count (int): Limite de eventos. Padrão: 0 (ilimitado)
        """
        logger.info("new_historized_event: %s, %s, %s, %s", source_id, evtypes, period, count)

    async def save_event(self, event):
        """
        Não faz nada - eventos já são salvos diretamente no MongoDB.
        
        Args:
            event: Evento OPC UA que seria salvo no histórico padrão
        """
        pass

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
        
        Args:
            source_id (NodeId): Identificador do nó fonte
            start (datetime): Data/hora de início da consulta
            end (datetime): Data/hora de fim da consulta  
            nb_events (int): Número máximo de eventos a retornar
            select_clauses: Cláusulas de seleção
            
        Returns:
            Tuple[List[Event], Union[datetime, None]]: Lista de eventos e timestamp de continuação
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