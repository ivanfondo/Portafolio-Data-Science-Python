"""Optimización de precio (nb 06).

Traduce la curva de demanda en una decisión de negocio: ¿qué precio conviene fijar?

Se maximiza el MARGEN de contribución, no el ingreso. Con una demanda tan elástica,
maximizar ingreso llevaría a bajar el precio hasta el mínimo (solución de esquina que
además ignora el coste). El margen sí tiene un óptimo interior y accionable.

    Demanda de elasticidad constante:   Q(P) = A · P^ε
    Margen:                             π(P) = (P - c) · Q(P)
    Óptimo (regla de Lerner):           P* = c · ε/(1+ε)

IMPORTANTE (corrección de diseño): este módulo NO usa el forecaster. El precio
óptimo depende solo de la elasticidad, el coste y el rango de precios. La predicción
de demanda a futuro es una salida distinta e independiente (ver forecast.py). Aquí
todo se calcula a partir del params.json, sin tocar los datos crudos ni el modelo.
"""

from __future__ import annotations

import numpy as np

from . import config


def precio_optimo_lerner(elasticidad: float, coste: float) -> dict:
    """Óptimo analítico por la regla de Lerner (fórmula cerrada)."""
    factor = elasticidad / (1 + elasticidad)          # multiplicador sobre el coste
    p_optimo = coste * factor
    markup = factor - 1                                # (P*-c)/c
    margen_relativo = -1 / elasticidad                 # (P*-c)/P*, índice de Lerner
    return {
        "precio_optimo": float(p_optimo),
        "factor_markup": float(factor),
        "markup_sobre_coste": float(markup),
        "margen_sobre_precio": float(margen_relativo),
    }


def constante_demanda(demanda_reg_media: float, precio_ref_mediano: float, elasticidad: float) -> float:
    """Constante A de la curva Q = A·P^ε.

    A no afecta al precio óptimo, pero sí a la altura de la curva de margen. Se
    recupera anclando la curva a un punto real: la demanda media a precio regular
    evaluada al precio regular mediano.
    """
    return float(demanda_reg_media / (precio_ref_mediano ** elasticidad))


def curva_margen(
    elasticidad: float,
    coste: float,
    precio_min: float,
    precio_max: float,
    A: float,
    n: int = config.N_PUNTOS_CURVA,
) -> dict:
    """Rejilla de precios con su demanda y margen. Base de la banda y del gráfico."""
    precios = np.linspace(precio_min, precio_max, n)
    demanda = A * precios ** elasticidad
    margen = (precios - coste) * demanda
    i_max = int(np.argmax(margen))
    return {
        "precios": precios,
        "demanda": demanda,
        "margen": margen,
        "precio_optimo_numerico": float(precios[i_max]),
        "margen_maximo": float(margen[i_max]),
    }


def banda_precios(precios: np.ndarray, margen: np.ndarray, umbral: float = config.UMBRAL_BANDA) -> dict:
    """Banda de precios que conserva al menos `umbral` (p.ej. 95%) del margen máximo.

    Cerca del óptimo la curva es plana, así que precios ligeramente distintos rinden
    casi lo mismo; la banda da margen de maniobra sin apenas sacrificar beneficio.
    """
    margen_max = float(margen.max())
    dentro = precios[margen >= umbral * margen_max]
    return {
        "umbral": float(umbral),
        "banda_min": float(dentro.min()),
        "banda_max": float(dentro.max()),
    }


def sensibilidad_elasticidad(coste: float, elasticidades: dict[str, float]) -> dict[str, float]:
    """Precio óptimo bajo distintas elasticidades. Suele ser robusto."""
    return {
        nombre: float(coste * eps / (1 + eps))
        for nombre, eps in elasticidades.items()
        if eps is not None
    }


def sensibilidad_coste(factor: float, costes: dict[str, float]) -> dict[str, float]:
    """Precio óptimo bajo distintos costes. El coste multiplica en la fórmula, así
    que aquí el precio SÍ es sensible: conocer bien el coste importa más que afinar
    la elasticidad."""
    return {nombre: float(c * factor) for nombre, c in costes.items()}


def optimizar(params: dict, umbral: float = config.UMBRAL_BANDA) -> dict:
    """Orquesta la optimización completa a partir del params.json de un producto.

    No necesita datos crudos ni forecaster. Devuelve el óptimo, la banda y los dos
    análisis de sensibilidad, listos para informar o guardar.
    """
    eps = params["elasticidad"]
    coste = params["coste_ref"]

    lerner = precio_optimo_lerner(eps, coste)

    A = params.get("A") or constante_demanda(
        params["demanda_reg_media"], params["precio_ref_mediano"], eps
    )
    curva = curva_margen(eps, coste, params["precio_min"], params["precio_max"], A)
    banda = banda_precios(curva["precios"], curva["margen"], umbral)

    dentro_rango = params["precio_min"] <= lerner["precio_optimo"] <= params["precio_max"]

    # Sensibilidad a la elasticidad: todas las estimaciones disponibles
    elasticidades = {
        "log-log (con rival)": params.get("elasticidad_con_rival"),
        "LightGBM (implícita)": params.get("elasticidad_ml"),
        "log-log (sin rival)": params.get("elasticidad_sin_rival"),
    }
    sens_eps = sensibilidad_elasticidad(coste, elasticidades)

    # Sensibilidad al coste: Q1 / mediana / Q3
    costes = {
        "bajo (Q1)": params.get("coste_q1", coste),
        "central (mediana)": coste,
        "alto (Q3)": params.get("coste_q3", coste),
    }
    sens_coste = sensibilidad_coste(lerner["factor_markup"], costes)

    return {
        "precio_optimo": lerner["precio_optimo"],
        "precio_optimo_numerico": curva["precio_optimo_numerico"],
        "markup_sobre_coste": lerner["markup_sobre_coste"],
        "margen_sobre_precio": lerner["margen_sobre_precio"],
        "dentro_del_rango": bool(dentro_rango),
        "banda": banda,
        "elasticidad_usada": eps,
        "coste_usado": coste,
        "sensibilidad_elasticidad": sens_eps,
        "sensibilidad_coste": sens_coste,
    }
