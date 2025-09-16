import os, pydoc, importlib, pathlib
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s]: %(message)s"
)

OUTPUT_DIR = pathlib.Path("docs")
PACKAGES = ["aas_api", "services", "infra", "utils"]  

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
# pydoc.writedoc grava no diretório atual
os.chdir(OUTPUT_DIR) 

for root_pkg in PACKAGES:
    try:
        pkg = importlib.import_module(root_pkg)
    except Exception as e:
        logger.info(f"[skip] {root_pkg}: {e}")
        continue

    # inclui o próprio pacote
    logger.info(f"[doc] {root_pkg}")
    pydoc.writedoc(root_pkg)

    modulo = [
        "infra",
        "aas_api",
        "services",
        "utils"
    ]

    # varre 
    for mod in modulo:
        try:
            importlib.import_module(modulo)
            logger.info(f"[doc] {modulo}")
            pydoc.writedoc(modulo)
        except Exception as e:
            logger.info(f"[erro] {modulo}: {e}")
