# services/opcua/node_manager.py

import logging
import asyncio
from asyncua import ua
from typing import Any, Awaitable, Callable, Dict, Optional, TYPE_CHECKING

logger = logging.getLogger(__name__)

NodeResolver = Callable[[str], Awaitable[Optional[Any]]]

class OPCUANodeManager:
    def __init__(self, node_resolver: Optional[NodeResolver] = None) -> None:
        self._nodes: Dict[str, Any] = {}
        self._node_resolver = node_resolver
        self._create_lock = asyncio.Lock()

    def set_nodes(self, nodes: Dict[str, Any]) -> None:
        self._nodes = nodes or {}
        logger.info("OPC UA nodes configured: %d", len(self._nodes))
        
    def __contains__(self, key: str) -> bool:
        return key in self._nodes

    def __getitem__(self, key: str):
        return self._nodes[key]

    def get(self, key: str, default=None):
        return self._nodes.get(key, default)

    def items(self):
        return self._nodes.items()

    def keys(self):
        return self._nodes.keys()

    def values(self):
        return self._nodes.values()

    async def _ensure_node(self, variable_name: str) -> Optional[Any]:
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
        node = self._nodes.get(variable_name) or await self._ensure_node(variable_name)
        if node is None:
            raise KeyError(f"OPC UA node not found: {variable_name}")
        return await node.read_value()

    async def read_float(self, variable_name: str) -> float:
        val = await self.read_value(variable_name)
        return float(val)
