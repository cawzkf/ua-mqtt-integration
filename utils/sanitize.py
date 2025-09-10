def sanitize_collection(name: str) -> str:
    """
    Sanitiza um nome para uso como coleção no MongoDB.
    Substitui caracteres problemáticos por sublinhado:
    Args:
        name (str): Nome original.

    Returns:
        str: Nome sanitizado, seguro para ser usado como nome de coleção.
    """
    return str(name).replace(".", "_").replace("$", "_").replace(" ", "_")
