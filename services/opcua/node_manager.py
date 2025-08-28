import logging
import asyncio
from typing import Dict, Any

logger = logging.getLogger(__name__)

class OPCUANodeManager:
    def __init__(self, nodes: Dict[str, Any] | None = None):
        self.nodes = nodes or {}

    def set_nodes(self, nodes: Dict[str, Any]):
        self.nodes = nodes or {}
        logger.info("OPC UA nodes configured: %d", len(self.nodes))

    async def set_value(self, variable_name: str, value: Any):
        node = self.nodes.get(variable_name)
        if node is None:
            logger.warning("OPC UA node not found: %s", variable_name)
            return
        try:
            await node.set_value(value)
            logger.info("%s <- %r", variable_name, value)
        except Exception:
            logger.exception("Failed to set value on %s", variable_name)


