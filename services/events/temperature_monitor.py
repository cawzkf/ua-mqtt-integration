from services.events.event_generator import generate_event_properly
from services.opcua.node_manager import OPCUANodeManager
from utils.constants import CRITICAL_TEMPERATURE
async def _read_float(nodes_variables, name: str) -> float:

    if isinstance(nodes_variables, OPCUANodeManager):
        return await nodes_variables.read_float(name)
    
    node = nodes_variables.get(name)

    if node is None:
        raise KeyError(f"Node {name} not found")
    val = await node.read_value()
    
    return float(val)

async def check_temperature_events(nodes_variables: OPCUANodeManager, event_generator):

    try:
        try:
            temp_carcaca = await _read_float(nodes_variables, "CaseTemperature")
        except KeyError:
            return

        if temp_carcaca > CRITICAL_TEMPERATURE:
            await generate_event_properly(
                event_generator,
                event_type="CriticalTemperature",
                message=f"Case temperature critical: {temp_carcaca:.2f} °C",
                severity=900,
                CaseTemperature=temp_carcaca
            )

    except Exception as e:
        print(f"Erro ao verificar temperatura: {e}")
