from typing import Optional, Literal, List
from pydantic import BaseModel, Field

class SubmodelElement(BaseModel):
    """
    Representa um elemento de submodelo.
    """
    id_short: str
    description: Optional[str] = None
    type: Literal["Property", "File", "Blob"] = "Property"
    value: Optional[str] = None
    unit: Optional[str] = None
    meta: Optional[str] = None

class Submodel(BaseModel):
    """
    Representa um submodelo.
    """
    id_short: str
    semantic_id: Optional[str] = None
    elements: List[SubmodelElement] = Field(default_factory=list)

class Asset(BaseModel):
    """
    Modelo de Asset.
    """
    id_short: str
    category: Optional[str] = None
    description: Optional[str] = None

class Shell(BaseModel):
    """
    Modelo de Shell.
    """
    id_short: str
    asset_id: str  # ID do asset referenciado
    submodels: List[Submodel] = Field(default_factory=list)