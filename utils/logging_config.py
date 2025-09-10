import logging, sys

def setup_logging(level: str ="INFO")-> logging.Logger:
    """
    Configura o logging básico para saída no `stdout` e retorna um logger nomeado.

    Define:
      - `level`: nível de log (ex.: "CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET");
        valores inválidos caem em `logging.INFO`.
      - `format`: `%(asctime)s [%(levelname)s]: %(message)s`
      - `stream`: `sys.stdout`

    Args:
        level (str, optional): Nível mínimo das mensagens a registrar.
            Padrão: "INFO".

    Returns:
        logging.Logger: Instância de logger com o nome `"logger"`.
    """
    logging.basicConfig(
        level = getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s]: %(message)s",
        stream=sys.stdout,
    )
    return logging.getLogger("logger")
