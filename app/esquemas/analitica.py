from datetime import date
from typing import Literal

from pydantic import BaseModel


class SemanaDemanda(BaseModel):
    productId: int
    semana: date          # lunes de esa semana (hora de Lima)
    unidades: float
    lineas: int           # filas de venta que componen esa semana         # filas de venta que componen esa semana


class DemandaSemanalResponse(BaseModel):
    tiposVenta: list[str]
    productId: int | None
    semanas: list[SemanaDemanda]


class SuficienciaProducto(BaseModel):
    productId: int
    unidadesTotales: float
    semanasConVentas: int
    semanasHistorial: int
    primeraSemana: date
    ultimaSemana: date
    nivel: str            # insuficiente | basico | estacional
    intermitente: bool


class ResumenSuficiencia(BaseModel):
    productosConVentas: int
    productosListos: int
    mensaje: str


class SuficienciaResponse(BaseModel):
    tiposVenta: list[str]
    resumen: ResumenSuficiencia
    productos: list[SuficienciaProducto]

class PronosticoSemana(BaseModel):
    semana: date
    unidades: float


class PronosticoProducto(BaseModel):
    productId: int
    nombre: str
    sku: str
    unitType: str                # UNIDAD | KILOGRAMO
    metodo: str               # promedio_movil | croston_sba | suavizado_exponencial | estacional_ingenuo | holt_winters
    wape: float | None           # error del backtest; None si no hubo datos para medirlo
    semanasHistorial: int        # semanas completas usadas (sin la semana actual)
    semanas: list[PronosticoSemana]
    confiable: bool              # False si el error del backtest es alto o no se pudo medir


class PronosticoResponse(BaseModel):
    horizonteSemanas: int
    productos: list[PronosticoProducto]

class ReposicionProducto(BaseModel):
    productId: int
    nombre: str
    sku: str
    unitType: str                        # UNIDAD | KILOGRAMO
    stockActual: float
    stockMinimo: float
    demandaHorizonte: float              # unidades esperadas en el pronóstico
    semanasCobertura: float | None       # None = el stock dura más que el pronóstico
    semanaAgotamiento: date | None
    cantidadSugerida: float
    fechaLimitePedido: date | None       # si ya pasó, es la semana actual
    plazoSemanas: int
    estado: Literal["pedir_ya", "pedir_pronto", "suficiente", "sin_demanda"]
    confiable: bool


class ReposicionResponse(BaseModel):
    horizonteSemanas: int
    productos: list[ReposicionProducto]

class AnomaliaDetectada(BaseModel):
    tipo: Literal["semana_atipica", "movimiento_atipico", "stock_negativo"]
    severidad: Literal["alta", "media"]
    productId: int
    nombre: str
    sku: str
    unitType: str                  # UNIDAD | KILOGRAMO
    fecha: date | None             # lunes de la semana, o día del movimiento; None en stock
    valor: float | None
    esperado: float | None
    puntaje: float | None          # desviaciones robustas; None si no aplica
    mensaje: str


class AnomaliasResponse(BaseModel):
    semanasRevisadas: int
    total: int
    altas: int
    medias: int
    anomalias: list[AnomaliaDetectada]