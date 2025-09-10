"""
Constantes e mapeamentos do sistema (MQTT ↔ OPC UA).

Atributos
NOMINAL_VOLTAGE : float
    Tensão nominal de fase em volts (V). Usada como referência para
    detecção de sobretensão/subtensão.

TOLERANCE : float
    Tolerância relativa (ex.: 0.1 = ±10%). Exemplo de uso:
    - Overvoltage:   valor > NOMINAL_VOLTAGE * (1 + TOLERANCE)
    - Undervoltage:  valor < NOMINAL_VOLTAGE * (1 - TOLERANCE)

NOMINAL_CURRENT : float
    Corrente nominal de fase em amperes (A). Usada para detecção de
    sobrecorrente.

CRITICAL_TEMPERATURE : float
    Temperatura crítica de carcaça em °C. Acima deste valor dispara
    evento de "CriticalTemperature".

MQTT_TOPICS : dict[str, str]
    Tópicos MQTT de entrada, agrupados por domínio lógico:
    - "ELECTRICAL": medições elétricas (tensão, corrente, potência, energia, etc.)
    - "VIBRATION" : medições de vibração
    - "ENVIRONMENT": condições ambientais (temperatura, umidade)

MQTT_TO_OPCUA_MAP : dict[tuple[str, ...], str]
    Mapeia caminhos (tuplas de chaves) encontrados no payload JSON recebido
    via MQTT para os nomes de variáveis no servidor OPC UA. As chaves do
    caminho são *case-sensitive* e tipicamente minúsculas, por exemplo:
      - ('voltage', 'a')    → 'VoltageA'
      - ('power', 'active') → 'PowerActive'
      - ('powerFactor',)    → 'PowerFactor'
      - ('caseTemperature',)→ 'CaseTemperature'

Notas
- Os nomes das variáveis OPC UA (lado direito do mapeamento) devem existir
  no servidor e ser graváveis.
- As unidades esperadas, salvo especificação contrária, são:
  V (tensão), A (corrente), Hz (frequência), °C (temperaturas), p.u. para
  fator de potência, e grandezas de energia/potência em unidades usuais.
- Para adicionar novos campos do payload, inclua a tupla de chaves no
  `MQTT_TO_OPCUA_MAP` apontando para o nome OPC UA correspondente.

Exemplo de payload MQTT (JSON)
{
  "voltage":  { "a": 228.7, "b": 229.1, "c": 227.9 },
  "current":  { "a": 10.2,  "b": 10.7,  "c": 10.4  },
  "power":    { "active": 3.1, "reactive": 0.6, "apparent": 3.2 },
  "energy":   { "active": 12034.5, "reactive": 321.7, "apparent": 12456.0 },
  "powerFactor": 0.96,
  "frequency": 60.0,
  "temperature": 35.2,
  "humidity": 48.0,
  "caseTemperature": 61.3,
  "axial": 0.12,
  "radial": 0.08
}
"""

NOMINAL_VOLTAGE = 220.0
TOLERANCE = 0.1
NOMINAL_CURRENT = 10.5
CRITICAL_TEMPERATURE = 60.0

MQTT_TOPICS = {
    "ELECTRICAL": "scgdi/motor/electrical",
    "VIBRATION": "scgdi/motor/vibration", 
    "ENVIRONMENT": "scgdi/motor/environment"
}

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
