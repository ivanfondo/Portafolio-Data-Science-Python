"""Pipeline de pricing (Dominick's): elasticidad, demanda y optimización de precio.

Módulos:
    config      constantes, rutas y registro de productos
    data        carga y limpieza de datos crudos
    features    reconstrucción de precio de referencia, descuento, calendario, rival
    elasticity  elasticidad propia y cruzada (regresión log-log con controles)
    cost        coste unitario desde PROFIT y anclas de la curva
    forecast    modelo de demanda LightGBM (entrenar / predecir escenario)
    optimize    regla de Lerner, curva de margen, banda y sensibilidad
    pipeline    orquestación: entrenar / optimizar / escalar

Uso típico desde código:
    from src import pipeline
    pipeline.entrenar("pepsi_2l", buscar_hparams=True)
    resultado = pipeline.optimizar("pepsi_2l")
"""

__all__ = [
    "config",
    "data",
    "features",
    "elasticity",
    "cost",
    "forecast",
    "optimize",
    "pipeline",
]
