from typing import Optional
from pydantic import BaseModel, Field


class SiesaProduct(BaseModel):
    f_codigo: str
    f_nombre: str
    f_codigo_externo: Optional[str] = None
    f_referencia: Optional[str] = None
    f_ean: Optional[str] = None

    class Config:
        extra = 'allow'


class CanonicalProduct(BaseModel):
    id: str = Field(..., min_length=1, max_length=100)
    external_id: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=500)
    sku: str = Field(..., min_length=1, max_length=100)
    ean: Optional[str] = Field(None, pattern=r'^\d{13}$')
    stock_quantity: Optional[int] = Field(0, ge=0)

    class Config:
        extra = 'allow'
