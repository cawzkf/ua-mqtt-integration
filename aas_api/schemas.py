from typing import Optional, List, Literal
from pydantic import BaseModel, Field

class AssetCreate(BaseModel):
    """
    Modelo para criar um novo ativo.

    Atributos:
        id_short: Identificador curto para o ativo
        category: Classificação opcional de categoria para o ativo
        description: Descrição textual opcional do ativo
    """
    id_short: str
    category: Optional[str] = None
    description: Optional[str] = None

class SubmodelElementsCreate(BaseModel):
    """
    Modelo base para elementos de submodelo com vários tipos e propriedades.

    Atributos:
        id_short: Identificador curto para o elemento do submodelo
        description: Descrição textual opcional do elemento
        type: Tipo do elemento, pode ser "Property", "File" ou "Blob"
        value: Valor string opcional associado ao elemento
        unit: Unidade de medida opcional para o valor
        meta: Dicionário opcional contendo metadados
    """
    id_short: str
    description: Optional[str] = None
    type: Literal["Property", "File", "Blob"] = "Property"
    value: Optional[str] = None
    unit: Optional[str] = None
    meta: Optional[dict] = None

class SubmodelCreate(BaseModel):
    """
    Modelo para criar um novo submodelo com elementos.

    Atributos:
        id_short: Identificador curto para o submodelo
        semantic_id: Identificador semântico opcional fornecendo significado/contexto
        elements: Lista de elementos do submodelo, padrão para lista vazia
    """
    id_short: str
    semantic_id: Optional[str] = None
    elements: List[SubmodelElementsCreate] = Field(default_factory=list)


class ShellCreate(BaseModel):
    """
    Modelo para criar um Asset Administration Shell (AAS).

    Atributos:
        id_short: Identificador curto para o shell
        asset_id: ID inteiro do ativo associado
        submodels: Lista de submodelos contidos neste shell, padrão para lista vazia
    """
    id_short: str
    asset_id: str
    submodels: List[SubmodelCreate] = Field(default_factory=list)
