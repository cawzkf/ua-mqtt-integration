"""
Constantes e mapeamentos do sistema (MQTT ↔ OPC UA).

Este módulo define as constantes operacionais do motor e os mapeamentos
entre tópicos MQTT e variáveis OPC UA para comunicação de dados.
"""

# Constantes operacionais do motor
NOMINAL_VOLTAGE = 220.0        # Tensão nominal de fase em volts (V)
TOLERANCE = 0.1                # Tolerância relativa (±10%)
NOMINAL_CURRENT = 10.5         # Corrente nominal de fase em amperes (A)
CRITICAL_TEMPERATURE = 60.0    # Temperatura crítica de carcaça em °C

# Tópicos MQTT de entrada
MQTT_TOPICS = {
    "ELECTRICAL": "scgdi/motor/electrical",
    "VIBRATION": "scgdi/motor/vibration", 
    "ENVIRONMENT": "scgdi/motor/environment"
}

# Mapeamento de caminhos JSON para variáveis OPC UA
MQTT_TO_OPCUA_MAP = {
    ('voltage', 'a'): 'VoltageA',
    ('voltage', 'b'): 'VoltageB', 
    ('voltage', 'c'): 'VoltageC',
    ('current', 'a'): 'CurrentA',
    ('current', 'b'): 'CurrentB',
    ('current', 'c'): 'CurrentC',
    ('power', 'active'): 'PowerActive',
    ('power', 'reactive'): 'PowerReactive',
    ('power', 'apparent'): 'PowerApparent',
    ('energy', 'active'): 'EnergyActive',
    ('energy', 'reactive'): 'EnergyReactive',
    ('energy', 'apparent'): 'EnergyApparent',
    ('powerFactor',): 'PowerFactor',
    ('frequency',): 'Frequency',
    ('temperature',): 'Temperature',
    ('humidity',): 'Humidity',
    ('caseTemperature',): 'CaseTemperature',
    ('axial',): 'Axial',
    ('radial',): 'Radial'
}