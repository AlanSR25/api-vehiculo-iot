from typing import Optional

from pydantic import BaseModel, Field


class VehiculoCrear(BaseModel):
    nombre: str = Field(min_length=1, max_length=80)
    modelo: Optional[str] = Field(None, max_length=80)
    descripcion: Optional[str] = Field(None, max_length=255)
    microcontrolador: Optional[str] = Field(None, max_length=50)


class VehiculoActualizar(VehiculoCrear):
    activo: bool


class ComandoCrear(BaseModel):
    id_vehiculo: int = Field(gt=0)
    nombre: str = Field(min_length=1, max_length=60)
    codigo: int
    descripcion: Optional[str] = Field(None, max_length=255)


class ComandoActualizar(BaseModel):
    nombre: str = Field(min_length=1, max_length=60)
    codigo: int
    descripcion: Optional[str] = Field(None, max_length=255)
    activo: bool


class MovimientoIndividual(BaseModel):
    id_comando: int = Field(gt=0)
    origen: str = Field(default="API-MANUAL", min_length=1, max_length=30)


class EstadoActualizar(BaseModel):
    id_comando: Optional[int] = Field(None, gt=0)
    conectado: bool


class DemoCrear(BaseModel):
    id_vehiculo: int = Field(gt=0)
    nombre: str = Field(min_length=1, max_length=80)
    descripcion: Optional[str] = Field(None, max_length=255)


class DemoActualizar(BaseModel):
    nombre: str = Field(min_length=1, max_length=80)
    descripcion: Optional[str] = Field(None, max_length=255)
    activo: bool


class DemoMovimientoCrear(BaseModel):
    id_comando: int = Field(gt=0)
    orden: int = Field(gt=0)
    duracion_ms: int = Field(gt=0, le=300_000)
    pausa_ms: int = Field(default=0, ge=0, le=300_000)


class DemoMovimientoActualizar(DemoMovimientoCrear):
    pass

