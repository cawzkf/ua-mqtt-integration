# Sistema de Monitoramento Motor 50CV

Sistema completo de monitoramento industrial baseado em OPC UA para motor de 50CV, com integração MQTT e armazenamento histórico em MongoDB.

## Funcionalidades

- **Servidor OPC UA** com estrutura hierárquica de variáveis
- **Monitoramento em tempo real** de variáveis elétricas, ambientais e de vibração
- **Sistema de eventos** automático para condições anômalas
- **Histórico de dados** armazenado em MongoDB
- **Integração MQTT** para comunicação com sistemas externos
- **Registro automático** em Local Discovery Server (LDS)

## Estrutura do Sistema

### Variáveis Monitoradas

**Elétricas:**
- Tensões por fase (VoltageA, VoltageB, VoltageC)
- Correntes por fase (CurrentA, CurrentB, CurrentC)
- Potências (PowerActive, PowerReactive, PowerApparent)
- Energias (EnergyActive, EnergyReactive, EnergyApparent)
- Fator de potência (PowerFactor)
- Frequência (Frequency)

**Ambientais:**
- Temperatura ambiente (Temperature)
- Umidade (Humidity)
- Temperatura da carcaça (CaseTemperature)

**Vibração:**
- Vibração axial (Axial)
- Vibração radial (Radial)

### Eventos Automáticos

- **Sobretensão/Subtensão** - Severidade 700
- **Sobrecorrente** - Severidade 700
- **Temperatura crítica** - Severidade 900

## Configuração

### Variáveis de Ambiente

Crie um arquivo `.env` com as seguintes configurações:

```env
# MongoDB
MONGO_URI=mongodb://localhost:27017
MONGO_DBNAME=motor50cv

# OPC UA Server
OPCUA_SERVER_PRODUCT_URI=urn:x.github.io:python:server
OPCUA_MANUFACTURER=X LTDA
OPCUA_PRODUCT_NAME=opcua-server
OPCUA_SOFTWARE_VERSION=1.0.0
OPCUA_APPLICATION_URI=urn:x:opcua-server
OPCUA_SERVER_NAME=X OPC UA Server

# Local Discovery Server
LDS_ENDPOINT=opc.tcp://localhost:4840
LDS_REGISTER_INTERVAL=15

# MQTT
MQTT_BROKER_HOST=lse.dev.br
MQTT_BROKER_PORT=1883
MQTT_USERNAME=seu_usuario
MQTT_PASSWORD=sua_senha

# Logs MQTT (opcional)
MQTT_LOG_PAYLOAD=0
MQTT_LOG_MAPPING=1
MQTT_DRY_RUN=0
```

### Constantes Operacionais

Ajuste os valores no arquivo `utils/constants.py`:

```python
NOMINAL_VOLTAGE = 220.0      # Tensão nominal (V)
TOLERANCE = 0.1              # Tolerância ±10%
NOMINAL_CURRENT = 10.5       # Corrente nominal (A)
CRITICAL_TEMPERATURE = 60.0  # Temperatura crítica (°C)
```

## Instalação

### Dependências

```bash
pip install asyncua pymongo python-dotenv gmqtt motor
```

### Execução

**Servidor OPC UA principal:**
```bash
python server.py
```

**Cliente MQTT standalone:**
```bash
python infra/mqtt/client.py
```

## Estrutura de Diretórios

```
projeto/
├── services/
│   ├── events/
│   │   ├── event_generator.py     # Geração de eventos OPC UA
│   │   ├── current_monitor.py     # Monitoramento de corrente
│   │   ├── voltage_monitor.py     # Monitoramento de tensão
│   │   └── temperature_monitor.py # Monitoramento de temperatura
│   ├── opcua/
│   │   └── node_manager.py        # Gerenciador de nós OPC UA
│   └── mqtt/
│       └── message_handler.py     # Processamento de mensagens MQTT
├── infra/
│   ├── mongo/
│   │   ├── history_manager.py     # Armazenamento histórico
│   │   └── mappers.py             # Conversores OPC UA ↔ MongoDB
│   └── mqtt/
│       └── client.py              # Cliente MQTT
├── utils/
│   ├── constants.py               # Constantes e mapeamentos
│   └── sanitize.py                # Utilitários de sanitização
├── server.py                      # Servidor principal
└── .env                           # Configurações
```

## Protocolo MQTT

### Tópicos Subscritos

- `scgdi/motor/electrical` - Dados elétricos
- `scgdi/motor/vibration` - Dados de vibração
- `scgdi/motor/environment` - Dados ambientais

### Formato de Payload

```json
{
  "voltage": { "a": 228.7, "b": 229.1, "c": 227.9 },
  "current": { "a": 10.2, "b": 10.7, "c": 10.4 },
  "power": { "active": 3.1, "reactive": 0.6, "apparent": 3.2 },
  "powerFactor": 0.96,
  "frequency": 60.0,
  "temperature": 35.2,
  "humidity": 48.0,
  "caseTemperature": 61.3,
  "axial": 0.12,
  "radial": 0.08
}
```

## MongoDB

### Collections

- **events** - Histórico de eventos
- **[Parent]_[Variable]** - Histórico de cada variável (ex: `Electrical_VoltageA`)

### Índices Criados

- `events.Time.Value` - Consultas temporais de eventos
- `[collection].server_timestamp` - Consultas históricas por timestamp

## Logs

O sistema gera logs detalhados para:
- Conexões OPC UA e MQTT
- Eventos de monitoramento
- Operações de banco de dados
- Mapeamentos de variáveis
- Erros e exceções

## Desenvolvimento

### Documentação

Gere documentação das APIs:
```bash
python -m pydoc -w gen_pydoc_all
```

## Requisitos do Sistema

- Python 3.8+
- MongoDB 4.0+
- Broker MQTT (Mosquitto, etc.)
- Rede acessível para OPC UA (porta 4840 padrão)

## Monitoramento

O sistema monitora automaticamente:
- Sobretensão: > NOMINAL_VOLTAGE × (1 + TOLERANCE)
- Subtensão: < NOMINAL_VOLTAGE × (1 - TOLERANCE)  
- Sobrecorrente: > NOMINAL_CURRENT × (1 + TOLERANCE)
- Temperatura crítica: > CRITICAL_TEMPERATURE

Eventos são armazenados no MongoDB e podem ser consultados via clientes OPC UA.