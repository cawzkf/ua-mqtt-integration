import os
import asyncio
import logging
from datetime import datetime, timezone
from asyncua import Client, Server
from dotenv import load_dotenv
from infra.mqtt.client import MQTTChannel
from services.opcua.node_manager import OPCUANodeManager
from utils.constants import MQTT_TO_OPCUA_MAP

load_dotenv()
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(processName)s %(name)s: %(message)s"
)


async def task_register_discovery(server: Server, registration_interval: float | None):
    lds_endpoint = os.getenv("LDS_ENDPOINT")
    if not lds_endpoint:
        logger.warning("LDS_ENDPOINT não configurado")
        return
 
    if registration_interval is None:
        try:
            registration_interval = float(os.getenv("LDS_REGISTER_INTERVAL", "10"))
        except Exception:
            registration_interval = 10.0

    while True:
        try:
            async with Client(lds_endpoint) as client:
                await client.register_server(server)
                logger.info("Registrado no LDS: %s", lds_endpoint)
        except Exception as e:
            logger.exception("Falha ao registrar no LDS: %s", e)
        await asyncio.sleep(registration_interval)


async def configure_server_info(server: Server):
    await server.set_build_info(
        product_uri=os.getenv("OPCUA_PRODUCT_URI", "http://examples.freeopcua.github.io"),
        manufacturer_name=os.getenv("OPCUA_MANUFACTURER", "Camila LTDA"),
        product_name=os.getenv("OPCUA_PRODUCT_NAME", "opcua-server"),
        software_version=os.getenv("OPCUA_SOFTWARE_VERSION", "1.0.0"),
        build_number=os.getenv("OPCUA_BUILD_NUMBER", "20250820"),
        build_date=datetime.now(timezone.utc),
    )
    app_uri = os.getenv("OPCUA_APPLICATION_URI", "urn:camila:opcua-server")
    await server.set_application_uri(app_uri)
    server.name = os.getenv("OPCUA_SERVER_NAME")


async def init_mqtt(node_manager: OPCUANodeManager) -> MQTTChannel:
    ch = MQTTChannel(node_manager=node_manager, variable_mapper=MQTT_TO_OPCUA_MAP)
    await ch.init()
    return ch

async def discovery():
    server = Server()
    await server.init()
    await configure_server_info(server)

    idx = await server.register_namespace(
        os.getenv("OPCUA_SERVER_PRODUCT_URI", "urn:camila.github.io:python:server")
    )

    motor50cv = await server.nodes.objects.add_folder(idx, "Motor50CV")
    electrical = await motor50cv.add_object(idx, "Electrical")
    environment = await motor50cv.add_object(idx, "Environment")
    vibration = await motor50cv.add_object(idx, "Vibration")

    electrical_variables = [
        "VoltageA", "VoltageB", "VoltageC",
        "CurrentA", "CurrentB", "CurrentC",
        "PowerActive", "PowerReactive", "PowerApparent",
        "EnergyActive", "EnergyReactive", "EnergyApparent",
        "PowerFactor", "Frequency",
    ]

    environment_variables = ["Temperature", "Humidity", "CaseTemperature"]
    vibration_variables   = ["Axial", "Radial"]

    nodes_variables: dict[str, object] = {}

    for parent, variables in (
        (electrical, electrical_variables),
        (environment, environment_variables),
        (vibration, vibration_variables),
    ):
        for var in variables:
            node_val = await parent.add_variable(idx, var, 0.0)
            await node_val.set_writable()
            nodes_variables[var] = node_val

    node_manager = OPCUANodeManager()
    node_manager.set_nodes(nodes_variables)

    _ch = await init_mqtt(node_manager)

    async with server:
        asyncio.create_task(task_register_discovery(server, None))
        await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(discovery())
