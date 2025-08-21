"""
Constants used throughout the MQTT-OPCUA integration system.
"""

# === MOTOR SPECIFICATIONS ===
NOMINAL_VOLTAGE = 220.0
VOLTAGE_TOLERANCE = 0.1
NOMINAL_CURRENT = 10.5
CRITICAL_TEMPERATURE = 60.0

# === MQTT TOPICS ===
MQTT_TOPICS = {
    "ELECTRICAL": "scgdi/motor/electrical",
    "VIBRATION": "scgdi/motor/vibration", 
    "ENVIRONMENT": "scgdi/motor/environment"
}

# === MQTT TO OPCUA VARIABLE MAPPING ===
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
