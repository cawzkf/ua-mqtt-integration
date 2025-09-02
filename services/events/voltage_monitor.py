from utils.constants import NOMINAL_VOLTAGE, TOLERANCE
from services.events.event_generator import generate_event_properly
from services.opcua.node_manager import OPCUANodeManager

async def _read_float(nodes_variables, name: str) -> float:
    if isinstance(nodes_variables, OPCUANodeManager):
        return await nodes_variables.read_float(name)
    node = nodes_variables.get(name)
    if node is None:
        raise KeyError(f"Node {name} not found")
    val = await node.read_value()
    return float(val)

async def check_voltage_events(nodes_variables: OPCUANodeManager, event_generator):
    
    
    for fase in ['A', 'B', 'C']:
        try:
            variavel_tensao = f"Voltage{fase}"
            if variavel_tensao not in nodes_variables:
                continue
                
            tensao = await _read_float(nodes_variables, variavel_tensao)
            
            if tensao > NOMINAL_VOLTAGE * (1 + TOLERANCE):
                await generate_event_properly(
                    event_generator,
                    event_type="Overvoltage",
                    message=f"Overvoltage detected: {tensao:.2f}",
                    severity=700,
                    VoltagePhase=fase
                )
            
            elif tensao < NOMINAL_VOLTAGE * (1 - TOLERANCE):
                await generate_event_properly(
                    event_generator,
                    event_type="Undervoltage", 
                    message=f"Undervoltage detected: {tensao:.2f}",
                    severity=700,
                    VoltagePhase=fase
                )
                
        except Exception as e:
            print(f"Erro ao verificar tensão fase {fase}: {e}")