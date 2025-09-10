import logging
import asyncio
from asyncua import ua
from typing import Any, Awaitable, Callable, Dict, Optional, TYPE_CHECKING

logger = logging.getLogger(__name__)

NodeResolver = Callable[[str], Awaitable[Optional[Any]]]

class OPCUANodeManager:
    """
    Gerencia nós OPC UA de forma assíncrona, permitindo resolução,
    cache e leitura/escrita de valores em variáveis do servidor.
    """

    def __init__(self, node_resolver: Optional[NodeResolver] = None) -> None:
        """
        Inicializa o gerenciador de nós OPC UA.

        :param node_resolver: Função assíncrona opcional para resolver nós dinamicamente.
        """
        self._nodes: Dict[str, Any] = {}
        self._node_resolver = node_resolver
        self._create_lock = asyncio.Lock()

    def set_nodes(self, nodes: Dict[str, Any]) -> None:
        """
        Define o conjunto inicial de nós OPC UA.

        :param nodes: Dicionário mapeando nomes de variáveis para objetos de nós.
        """
        self._nodes = nodes or {}
        logger.info("OPC UA nodes configured: %d", len(self._nodes))
        
    def __contains__(self, key: str) -> bool:
        """
        Verifica se um nó existe no gerenciador.

        :param key: Nome da variável.
        :return: True se o nó existe, False caso contrário.
        """
        return key in self._nodes

    def __getitem__(self, key: str):
        """
        Obtém um nó pelo nome da variável.

        :param key: Nome da variável.
        :return: Objeto do nó correspondente.
        """
        return self._nodes[key]

    def get(self, key: str, default=None):
        """
        Retorna um nó se existir, caso contrário retorna o valor padrão.

        :param key: Nome da variável.
        :param default: Valor de fallback se o nó não existir.
        :return: Nó OPC UA ou valor padrão.
        """
        return self._nodes.get(key, default)

    def items(self):
        """
        Retorna os itens (pares chave-valor) dos nós registrados.
        """
        return self._nodes.items()

    def keys(self):
        """
        Retorna as chaves (nomes das variáveis) dos nós registrados.
        """
        return self._nodes.keys()

    def values(self):
        """
        Retorna os valores (objetos de nós) registrados.
        """
        return self._nodes.values()

    async def _ensure_node(self, variable_name: str) -> Optional[Any]:
        """
        Garante que um nó esteja disponível. Se não existir em cache,
        tenta resolver dinamicamente com o node_resolver.

        :param variable_name: Nome da variável a ser verificada.
        :return: Nó OPC UA ou None se não encontrado.
        """
        node = self._nodes.get(variable_name)
        if node is not None:
            return node
        if self._node_resolver is None:
            return None
        async with self._create_lock:
            node = self._nodes.get(variable_name)
            if node is not None:
                return node
            try:
                node = await self._node_resolver(variable_name)
            except Exception as e:
                logger.exception("Node resolver failed for %s: %s", variable_name, e)
                return None
            if node is None:
                return None
            self._nodes[variable_name] = node
            logger.info("OPC UA node resolved/created: %s", variable_name)
            return node

    async def set_value(self, variable_name: str, value: Any) -> None:
        """
        Define um valor para um nó OPC UA.

        :param variable_name: Nome da variável a ser escrita.
        :param value: Valor a ser atribuído ao nó.
        """
        node = self._nodes.get(variable_name) or await self._ensure_node(variable_name)
        if node is None:
            logger.warning("OPC UA node not found: %s", variable_name)
            return
        try:
            await node.write_value(value)
            logger.info("%s <- %r", variable_name, value)
        except Exception as e:
            logger.exception("Failed to set value on %s: %s", variable_name, e)

    async def read_value(self, variable_name: str) -> Any:
        """
        Lê o valor atual de um nó OPC UA.

        :param variable_name: Nome da variável a ser lida.
        :return: Valor do nó.
        :raises KeyError: Se o nó não for encontrado.
        """
        node = self._nodes.get(variable_name) or await self._ensure_node(variable_name)
        if node is None:
            raise KeyError(f"OPC UA node not found: {variable_name}")
        return await node.read_value()

    async def read_float(self, variable_name: str) -> float:
        """
        Lê o valor de um nó e converte para float.

        :param variable_name: Nome da variável a ser lida.
        :return: Valor convertido para float.
        """
        val = await self.read_value(variable_name)
        return float(val)
