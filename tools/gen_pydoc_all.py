import os, pydoc, pkgutil, importlib, pathlib
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s]: %(message)s"
)

OUTPUT_DIR = pathlib.Path("docs/api")
PACKAGES = ["services", "infra", "utils"]  

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

    # varre submódulos/subpacotes
    for mod in pkgutil.walk_packages(pkg.__path__, prefix=root_pkg + "."):
        name = mod.name
        try:
            logger(f"[doc] {name}")
            # garante import
            importlib.import_module(name)  
            pydoc.writedoc(name)
        except Exception as e:
            logger.info(f"[erro] {name}: {e}")
