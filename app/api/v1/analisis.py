from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.ml.reposicion import ordenar_por_urgencia, recomendar

from app.bd.session import get_db
from app.core.seguridad import requiere_rol
from app.esquemas.analitica import (
    AnomaliaDetectada,
    AnomaliasResponse,
    DemandaSemanalResponse,
    ResumenSuficiencia,
    SemanaDemanda,
    SuficienciaProducto,
    SuficienciaResponse,
    PronosticoProducto, 
    PronosticoResponse, 
    PronosticoSemana,
    ReposicionProducto,
    ReposicionResponse
)
from app.ml.pronostico import HORIZONTE
from app.ml.servicio import obtener_pronosticos
from app.ml.consultas import movimientos_recientes, ventas_semanales
from app.ml.suficiencia import (
    TIPOS_VENTA,
    evaluar,
    hoy_lima,
    listos_para_pronosticar,
    mensaje_resumen,
)
from app.servicios.dashboard_consultas import leer_productos_stock

from datetime import datetime, timedelta

from app.ml.anomalias import HISTORIAL_MOVIMIENTOS_SEMANAS, ULTIMAS_SEMANAS, detectar
from app.servicios.dashboard_calculos import ZONA

# Solo el admin ve la analítica (igual que el dashboard del front).
router = APIRouter(
    prefix="/analitica",
    tags=["analitica"],
    dependencies=[Depends(requiere_rol("ADMIN"))],
)


@router.get("/demanda/semanal", response_model=DemandaSemanalResponse)
async def demanda_semanal(product_id: int | None = None, db: AsyncSession = Depends(get_db)):
    """Unidades vendidas por semana. Con ?product_id= filtra un producto."""
    filas = await ventas_semanales(db, product_id)
    return DemandaSemanalResponse(
        tiposVenta=list(TIPOS_VENTA),
        productId=product_id,
        semanas=[
    SemanaDemanda(productId=f.product_id, semana=f.semana, unidades=f.unidades, lineas=f.lineas)
    for f in filas
],
    )


@router.get("/demanda/suficiencia", response_model=SuficienciaResponse)
async def suficiencia_datos(db: AsyncSession = Depends(get_db)):
    """Dice, por producto, si hay historial suficiente para pronosticar su demanda."""
    filas = await ventas_semanales(db)
    evaluaciones = evaluar(filas, hoy_lima())
    return SuficienciaResponse(
        tiposVenta=list(TIPOS_VENTA),
        resumen=ResumenSuficiencia(
            productosConVentas=len(evaluaciones),
            productosListos=len(listos_para_pronosticar(evaluaciones)),
            mensaje=mensaje_resumen(evaluaciones),
        ),
        productos=[
            SuficienciaProducto(
                productId=e.product_id,
                unidadesTotales=e.unidades_totales,
                semanasConVentas=e.semanas_con_ventas,
                semanasHistorial=e.semanas_historial,
                primeraSemana=e.primera_semana,
                ultimaSemana=e.ultima_semana,
                nivel=e.nivel,
                intermitente=e.intermitente,
            )
            for e in evaluaciones
        ],
    )

@router.get("/demanda/pronostico", response_model=PronosticoResponse)
async def pronostico_demanda(
    product_id: int | None = None,
    actualizar: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """Pronóstico semanal por producto. ?actualizar=true ignora la caché."""
    datos = await obtener_pronosticos(db, forzar=actualizar)
    if product_id is not None:
        datos = [p for p in datos if p.product_id == product_id]

    # Nombre, SKU y unidad se leen al responder (no van en la caché del pronóstico).
    fichas = {p.product_id: p for p in await leer_productos_stock(db)}

    def ficha(pid: int) -> tuple[str, str, str]:
        f = fichas.get(pid)
        return (f.nombre, f.sku, f.unit_type) if f else (f"Producto {pid}", "", "UNIDAD")

    return PronosticoResponse(
        horizonteSemanas=HORIZONTE,
        productos=[
            PronosticoProducto(
                productId=p.product_id,
                nombre=ficha(p.product_id)[0],
                sku=ficha(p.product_id)[1],
                unitType=ficha(p.product_id)[2],
                metodo=p.metodo,
                wape=p.wape,
                confiable=p.confiable,
                semanasHistorial=p.semanas_historial,
                semanas=[PronosticoSemana(semana=f, unidades=u) for f, u in p.semanas],
            )
            for p in datos
        ],
    )

@router.get("/reposicion", response_model=ReposicionResponse)
async def reposicion_stock(
    actualizar: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """Cuánto dura el stock según el pronóstico y cuánto conviene pedir."""
    pronosticos = await obtener_pronosticos(db, forzar=actualizar)
    productos = {p.product_id: p for p in await leer_productos_stock(db)}
    hoy = hoy_lima()

    recomendaciones = []
    for pron in pronosticos:
        prod = productos.get(pron.product_id)
        if prod is None or not prod.is_active:
            continue
        recomendaciones.append(
            recomendar(
                product_id=prod.product_id,
                unit_type=prod.unit_type,
                stock=prod.current_stock,
                stock_minimo=prod.min_stock_alert,
                semanas=pron.semanas,
                confiable=pron.confiable,
                hoy=hoy,
            )
        )

    return ReposicionResponse(
        horizonteSemanas=HORIZONTE,
        productos=[
            ReposicionProducto(
                productId=r.product_id,
                nombre=productos[r.product_id].nombre,
                sku=productos[r.product_id].sku,
                unitType=productos[r.product_id].unit_type,
                stockActual=r.stock_actual,
                stockMinimo=r.stock_minimo,
                demandaHorizonte=r.demanda_horizonte,
                semanasCobertura=r.semanas_cobertura,
                semanaAgotamiento=r.semana_agotamiento,
                cantidadSugerida=r.cantidad_sugerida,
                fechaLimitePedido=r.fecha_limite_pedido,
                plazoSemanas=r.plazo_semanas,
                estado=r.estado,
                confiable=r.confiable,
            )
            for r in ordenar_por_urgencia(recomendaciones)
        ],
    )

@router.get("/anomalias", response_model=AnomaliasResponse)
async def anomalias_detectadas(db: AsyncSession = Depends(get_db)):
    """Ventas, mermas y stocks fuera de lo habitual en las últimas semanas."""
    ahora = datetime.now(ZONA)
    filas = await ventas_semanales(db)
    movimientos = await movimientos_recientes(
        db, ahora - timedelta(weeks=HISTORIAL_MOVIMIENTOS_SEMANAS)
    )
    productos = await leer_productos_stock(db)
    fichas = {p.product_id: p for p in productos}

    encontradas = detectar(
        filas,
        movimientos,
        productos,
        ahora.date(),
        desde=ahora - timedelta(weeks=ULTIMAS_SEMANAS),
    )
    return AnomaliasResponse(
        semanasRevisadas=ULTIMAS_SEMANAS,
        total=len(encontradas),
        altas=sum(1 for a in encontradas if a.severidad == "alta"),
        medias=sum(1 for a in encontradas if a.severidad == "media"),
        anomalias=[
            AnomaliaDetectada(
                tipo=a.tipo,
                severidad=a.severidad,
                productId=a.product_id,
                nombre=fichas[a.product_id].nombre if a.product_id in fichas else f"Producto {a.product_id}",
                sku=fichas[a.product_id].sku if a.product_id in fichas else "",
                unitType=fichas[a.product_id].unit_type if a.product_id in fichas else "UNIDAD",
                fecha=a.fecha,
                valor=a.valor,
                esperado=a.esperado,
                puntaje=a.puntaje,
                mensaje=a.mensaje,
            )
            for a in encontradas
        ],
    )