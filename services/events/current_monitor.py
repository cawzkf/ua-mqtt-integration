from services.opcua.node_manager import OPCUANodeManager
from services.events.event_generator import generate_event_properly
from utils.constants import NOMINAL_CURRENT, TOLERANCE

async def _read_float(nodes_variables, name: str) -> float:
    if isinstance(nodes_variables, OPCUANodeManager):
        return await nodes_variables.read_float(name)
    node = nodes_variables.get(name)
    if node is None:
        raise KeyError(f"Node {name} not found")
    val = await node.read_value()
    return float(val)

async def check_current_events(nodes_variables: OPCUANodeManager, event_generator):
    
    
    for fase in ['A', 'B', 'C']:
        try:
            variavel_corrente = f"Current{fase}"
            if variavel_corrente not in nodes_variables:
                continue
                
            corrente  = await _read_float(nodes_variables, variavel_corrente)
            
            if corrente > NOMINAL_CURRENT * (1 + TOLERANCE):
                await generate_event_properly(
                    event_generator,
                    event_type="Overcurrent",
                    message=f"Overcurrent detected: {corrente:.2f}",
                    severity=700,
                    CurrentPhase=fase
                )
                
        except Exception as e:
            print(f"Erro ao verificar corrente fase {fase}: {e}")