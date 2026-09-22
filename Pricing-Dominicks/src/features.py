"""Feature engineering (nb 03).

El corazón del proyecto: reconstruir la señal de precio a partir del propio precio,
porque la bandera de promoción original (SALE) no es fiable.

    precio_ref  = percentil 90 del precio en una ventana móvil de 13 semanas, por tienda
    descuento   = cuánto cae el precio de esta semana respecto a su precio regular
                  (diferencia de logaritmos ≈ % de bajada), acotado a >= 0

Estas dos variables separan dos efectos que antes se confundían: el nivel de precio
regular y la intensidad de la promoción.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config


def precio_referencia(df: pd.DataFrame, col_precio: str = "UNIT_PRICE") -> pd.Series:
    """Precio regular por tienda: cuantil alto en ventana móvil centrada.

    La lógica: como las promociones bajan el precio y son frecuentes, el precio
    regular vive en la parte alta de la distribución local. Un cuantil alto lo
    captura mejor que la mediana (que se contaminaría con las semanas de oferta).
    La ventana móvil deja que la referencia se adapte a los cambios de precio a lo
    largo de los 6 años en vez de fijar un único precio.

    Requiere que df venga ordenado por (STORE, start).
    """
    return (
        df.groupby("STORE", observed=True)[col_precio]
        .transform(
            lambda x: x.rolling(
                config.VENTANA, min_periods=config.MIN_PERIODOS, center=True
            ).quantile(config.CUANTIL)
        )
    )


def _festivo(serie_special: pd.Series) -> pd.Series:
    """1 si la semana tiene festividad señalada, 0 en caso contrario.

    Robusto ante NaN y cadenas vacías (evita el fallo del accesor .str sobre NaN).
    """
    return (
        serie_special.fillna("").astype(str).str.strip().ne("").astype(int)
    )


def construir_features(df: pd.DataFrame) -> pd.DataFrame:
    """Añade al panel de un producto todas las variables de precio y control.

    Devuelve el DataFrame ordenado por (STORE, start) con:
    UNIT_PRICE, ln_q, ln_p, PRECIO_REF, DESCUENTO, FESTIVO, ln_precio_ref, STORE(cat).
    """
    df = df.sort_values(["STORE", "start"]).reset_index(drop=True).copy()

    # Precio unitario y logaritmos (la elasticidad es una pendiente en log-log)
    df["UNIT_PRICE"] = df["PRICE"] / df["QTY"]
    df["ln_q"] = np.log(df["MOVE"])
    df["ln_p"] = np.log(df["UNIT_PRICE"])

    # Festivo como control de calendario
    df["FESTIVO"] = _festivo(df["special"])

    # Precio de referencia y descuento
    df["PRECIO_REF"] = precio_referencia(df, "UNIT_PRICE")
    df["DESCUENTO"] = np.log(df["PRECIO_REF"]) - df["ln_p"]
    # Descuentos negativos (la referencia aún no capturó un cambio de escalón) → 0
    df["DESCUENTO"] = df["DESCUENTO"].clip(lower=0)

    # Log del precio de referencia, precomputado para la regresión (evita depender
    # de que patsy evalúe np.log dentro de la fórmula).
    df["ln_precio_ref"] = np.log(df["PRECIO_REF"])

    # Tienda como categórica (para efectos fijos sin que el nº se lea como magnitud)
    df["STORE"] = df["STORE"].astype("category")

    return df


def añadir_precio_rival(df: pd.DataFrame, rival: pd.DataFrame | None) -> pd.DataFrame:
    """Reconstruye el precio de referencia del rival y lo une al panel por (STORE, start).

    Si no hay rival, crea la columna a NaN para mantener el esquema estable (el
    modelo y la regresión la ignoran cuando está vacía).
    """
    if rival is None:
        df = df.copy()
        df["PRECIO_REF_RIVAL"] = np.nan
        df["ln_precio_ref_rival"] = np.nan
        return df

    rival = rival.sort_values(["STORE", "start"]).reset_index(drop=True).copy()
    rival["UNIT_PRICE"] = rival["PRICE"] / rival["QTY"]
    rival["PRECIO_REF_RIVAL"] = precio_referencia(rival, "UNIT_PRICE")

    rival_precio = rival[["STORE", "start", "PRECIO_REF_RIVAL"]].copy()

    df = df.merge(rival_precio, on=["STORE", "start"], how="left")
    df["ln_precio_ref_rival"] = np.log(df["PRECIO_REF_RIVAL"])
    return df


def guardar_features(df: pd.DataFrame, nombre: str) -> None:
    config.asegurar_directorios()
    df.to_parquet(config.ruta_features(nombre))
