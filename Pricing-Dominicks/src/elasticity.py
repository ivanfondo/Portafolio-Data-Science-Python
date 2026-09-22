"""Estimación de la elasticidad precio-demanda (nb 03).

Regresión log-log con controles. El coeficiente del log del precio regular es
directamente la elasticidad (en cuánto % cae la demanda si el precio sube un 1%).

Se estiman dos especificaciones:

    sin rival:  ln_q ~ ln(precio_ref) + descuento + festivo + tienda      → ε ≈ -3.78
    con rival:  ln_q ~ ln(precio_ref) + ln(precio_ref_rival) + descuento
                       + festivo + tienda                                 → ε ≈ -4.62 (propia)
                                                                            +0.91 (cruzada)

Ambas se guardan: la de con-rival es la que usa la optimización (índice de Lerner);
las dos alimentan el análisis de sensibilidad.
"""

from __future__ import annotations

import statsmodels.formula.api as smf

from . import config


# Columnas mínimas para cada especificación (para dropna explícito y n_obs claro)
_COLS_BASE = ["ln_q", "ln_precio_ref", "DESCUENTO", "FESTIVO", "STORE"]
_COLS_RIVAL = _COLS_BASE + ["ln_precio_ref_rival"]

_FORMULA_SIN_RIVAL = "ln_q ~ ln_precio_ref + DESCUENTO + FESTIVO + C(STORE)"
_FORMULA_CON_RIVAL = (
    "ln_q ~ ln_precio_ref + ln_precio_ref_rival + DESCUENTO + FESTIVO + C(STORE)"
)


def _ajustar(df, formula, cols):
    datos = df.dropna(subset=cols)
    modelo = smf.ols(formula, data=datos).fit()
    return modelo, len(datos)


def estimar_elasticidad(df) -> dict:
    """Estima la elasticidad del producto y, si hay rival, la cruzada.

    Devuelve un diccionario con todo lo necesario para optimización y sensibilidad:

        elasticidad          : la que usa el óptimo (con rival si está disponible)
        elasticidad_con_rival: ε propia controlando por el rival (-4.62)
        elasticidad_sin_rival: ε propia sin controlar por el rival (-3.78)
        elasticidad_cruzada  : respuesta al precio del rival (+0.91) o None
        efecto_descuento     : coeficiente del descuento
        r2                   : R² del modelo elegido
        n_obs                : nº de observaciones usadas
    """
    hay_rival = df["ln_precio_ref_rival"].notna().any()

    # Modelo sin rival (siempre se puede estimar)
    m_sin, n_sin = _ajustar(df, _FORMULA_SIN_RIVAL, _COLS_BASE)
    eps_sin = float(m_sin.params["ln_precio_ref"])

    resultado = {
        "elasticidad_sin_rival": eps_sin,
        "elasticidad_con_rival": None,
        "elasticidad_cruzada": None,
        "efecto_descuento": float(m_sin.params["DESCUENTO"]),
        "r2": float(m_sin.rsquared),
        "n_obs": n_sin,
    }

    if hay_rival:
        m_con, n_con = _ajustar(df, _FORMULA_CON_RIVAL, _COLS_RIVAL)
        eps_con = float(m_con.params["ln_precio_ref"])
        resultado.update(
            {
                "elasticidad_con_rival": eps_con,
                "elasticidad_cruzada": float(m_con.params["ln_precio_ref_rival"]),
                "efecto_descuento": float(m_con.params["DESCUENTO"]),
                "r2": float(m_con.rsquared),
                "n_obs": n_con,
            }
        )

    # La elasticidad "oficial" para optimizar: con rival si existe, si no, sin rival.
    resultado["elasticidad"] = (
        resultado["elasticidad_con_rival"]
        if resultado["elasticidad_con_rival"] is not None
        else resultado["elasticidad_sin_rival"]
    )
    return resultado
