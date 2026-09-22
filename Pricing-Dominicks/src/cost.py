"""Recuperación del coste unitario y de las anclas de la curva (nb 06).

El coste no viene dado; se despeja del margen bruto del minorista (PROFIT):

    coste = precio_unitario · (1 - PROFIT/100)

Como coste de referencia se toma la MEDIANA en las semanas a precio regular (sin
descuento). Se excluyen las promociones a propósito: en ellas el margen está
comprimido y calcular el coste ahí lo distorsionaría. El coste de un producto no
cambia porque esté de oferta; lo que cambia es el margen.

De paso se calculan las "anclas" que la curva de demanda necesita (el precio
regular mediano y la demanda media a precio regular) y el rango de precios
histórico. Todo esto va al params.json para que la optimización no tenga que
volver a tocar los datos crudos.
"""

from __future__ import annotations

import pandas as pd


def estimar_coste(df: pd.DataFrame, umbral_regular: float = 0.01) -> dict:
    """Estima el coste de referencia y las magnitudes derivadas del precio.

    Requiere un panel con UNIT_PRICE, PROFIT, DESCUENTO y MOVE (ya con features).

    Devuelve:
        coste_ref          : mediana del coste en semanas regulares (para Lerner)
        coste_q1, coste_q3 : cuartiles del coste (sensibilidad al coste)
        n_regular          : nº de semanas regulares usadas
        precio_min/max     : rango histórico de precios (donde la curva es fiable)
        precio_ref_mediano : precio regular mediano (ancla A de la curva)
        demanda_reg_media  : demanda media a precio regular (ancla A de la curva)
        cv_precio          : coef. de variación del precio (control de calidad)
    """
    df = df.copy()
    df["COSTE"] = df["UNIT_PRICE"] * (1 - df["PROFIT"] / 100)

    # Semanas a precio regular = sin descuento apreciable
    regular = df[df["DESCUENTO"] < umbral_regular]
    if regular.empty:
        raise ValueError("No hay semanas a precio regular para estimar el coste.")

    coste_ref = float(regular["COSTE"].median())

    return {
        "coste_ref": coste_ref,
        "coste_q1": float(regular["COSTE"].quantile(0.25)),
        "coste_q3": float(regular["COSTE"].quantile(0.75)),
        "n_regular": int(len(regular)),
        "precio_min": float(df["UNIT_PRICE"].min()),
        "precio_max": float(df["UNIT_PRICE"].max()),
        "precio_ref_mediano": float(regular["UNIT_PRICE"].median()),
        "demanda_reg_media": float(regular["MOVE"].mean()),
        "cv_precio": float(df["UNIT_PRICE"].std() / df["UNIT_PRICE"].mean()),
    }
