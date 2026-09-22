"""Modelo de demanda con LightGBM (nb 04 y 05).

Predice la demanda semanal a partir del precio, el descuento, el precio del rival y
el calendario, sin imponer forma funcional. Aquí se concentra la separación
entrenamiento/inferencia:

    - entrenar_forecaster : ajusta el modelo (offline). Para producción se ajusta con
      TODOS los datos disponibles, no solo con train. La búsqueda de hiperparámetros,
      cuando se pide, se hace sobre train (para no elegir hiperparámetros mirando el
      test) y luego se reajusta el modelo final con esos hiperparámetros sobre todo.
    - predecir_escenario : inferencia (online). Dada una hipótesis de precio para las
      próximas semanas, devuelve la demanda esperada con su intervalo.

Corrección de diseño respecto al notebook: el notebook guardaba el forecaster
entrenado SOLO con train (útil para validar de forma reproducible). El modelo que se
despliega debe estar entrenado con todos los datos; eso es lo que hace este módulo.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from lightgbm import LGBMRegressor
from sklearn.metrics import mean_absolute_error, root_mean_squared_error
from skforecast.recursive import ForecasterRecursive
from skforecast.model_selection import (
    TimeSeriesFold,
    bayesian_search_forecaster,
)
from skforecast.utils import save_forecaster, load_forecaster

from . import config


# --------------------------------------------------------------------------- #
# Agregación panel → serie semanal (nb 04)
# --------------------------------------------------------------------------- #
def agregar_serie(df: pd.DataFrame) -> pd.DataFrame:
    """Colapsa el panel (tienda·semana) a una única serie semanal.

    Cada variable se agrega según su naturaleza: unidades y precios se promedian
    entre tiendas; el festivo se colapsa con el máximo (es característica de la
    semana, no de la tienda). Se pierde la variación entre tiendas que se explotó en
    la elasticidad, pero aquí el objetivo es predecir la demanda agregada, no estimar
    el efecto causal del precio.
    """
    agg = (
        df.groupby("start")
        .agg(
            UNIDADES=("MOVE", "mean"),
            PRECIO_REF=("PRECIO_REF", "mean"),
            DESCUENTO=("DESCUENTO", "mean"),
            PRECIO_REF_RIVAL=("PRECIO_REF_RIVAL", "mean"),
            FESTIVO=("FESTIVO", "max"),
            N_TIENDAS=("STORE", "nunique"),
        )
        .reset_index()
        .sort_values("start")
        .reset_index(drop=True)
    )
    agg["WEEK_YEAR"] = agg["start"].dt.isocalendar().week.astype(int)
    agg["MES"] = agg["start"].dt.month
    return agg


def _rellenar_huecos(serie: pd.DataFrame) -> pd.DataFrame:
    """Rellena los NaN que aparecen al forzar frecuencia semanal (nb 04).

    skforecast necesita un índice temporal continuo. Al hacer asfreq('7D') se crean
    filas vacías en las semanas ausentes. Se rellenan:
      - calendario: se recalcula desde la fecha.
      - festivo/descuento: 0 (sabemos el valor por defecto).
      - precios: interpolación temporal (conocemos el rango en que se mueven).
      - unidades: interpolación temporal (con cautela: es inventar demanda, pero
        skforecast exige la serie objetivo sin huecos).
    """
    serie = serie.copy()
    serie["WEEK_YEAR"] = serie.index.isocalendar().week.astype(int)
    serie["MES"] = serie.index.month
    serie["FESTIVO"] = serie["FESTIVO"].fillna(0).astype(int)
    serie["DESCUENTO"] = serie["DESCUENTO"].fillna(0)
    for col in ("PRECIO_REF", "PRECIO_REF_RIVAL", "UNIDADES"):
        # interpolación temporal para huecos interiores; ffill/bfill para los bordes
        # (la interpolación no extrapola, y la ventana centrada deja NaN en extremos).
        serie[col] = serie[col].interpolate(method="time").ffill().bfill()
    return serie


def preparar_serie_modelo(agg: pd.DataFrame) -> tuple[pd.Series, pd.DataFrame]:
    """Indexa por fecha, fija frecuencia semanal, rellena huecos y separa y / exog."""
    serie = agg.set_index("start").asfreq("7D").sort_index()
    serie = _rellenar_huecos(serie)
    y = serie["UNIDADES"]
    exog = serie[config.EXOGENAS]
    return y, exog


# --------------------------------------------------------------------------- #
# Construcción y entrenamiento del forecaster (nb 04)
# --------------------------------------------------------------------------- #
def construir_forecaster(hparams: dict | None = None) -> ForecasterRecursive:
    """Crea un ForecasterRecursive con LightGBM y `LAGS` retardos de demanda."""
    hparams = hparams or {}
    return ForecasterRecursive(
        estimator=LGBMRegressor(
            random_state=config.RANDOM_STATE, n_jobs=-1, verbose=-1, **hparams
        ),
        lags=config.LAGS,
    )


def _espacio_busqueda(trial):
    """Espacio de hiperparámetros adaptado a un modelo pequeño (nb 04)."""
    return {
        "n_estimators": trial.suggest_int("n_estimators", 100, 600, step=50),
        "max_depth": trial.suggest_int("max_depth", 2, 6),
        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
        "num_leaves": trial.suggest_int("num_leaves", 8, 40),
        "min_child_samples": trial.suggest_int("min_child_samples", 5, 30),
        "reg_lambda": trial.suggest_float("reg_lambda", 0, 2),
    }


def buscar_hiperparametros(y: pd.Series, exog: pd.DataFrame, n_train: int) -> dict:
    """Búsqueda bayesiana de hiperparámetros sobre el tramo de entrenamiento.

    Se hace sobre train (reservando el último año para no elegir mirando el test),
    con backtesting de origen deslizante y horizonte de 4 semanas.
    """
    forecaster = construir_forecaster()
    cv = TimeSeriesFold(
        steps=config.HORIZONTE,
        initial_train_size=n_train - 52,   # reserva un año dentro de train
        refit=True,
        fixed_train_size=False,
    )
    resultados, _ = bayesian_search_forecaster(
        forecaster=forecaster,
        y=y.iloc[:n_train],
        exog=exog.iloc[:n_train],
        search_space=_espacio_busqueda,
        cv=cv,
        metric=[mean_absolute_error, root_mean_squared_error],
        n_trials=config.N_TRIALS,
        random_state=config.RANDOM_STATE,
        return_best=False,
        n_jobs=-1,
    )
    return dict(resultados.iloc[0]["params"])


def entrenar_forecaster(
    agg: pd.DataFrame, buscar_hparams: bool = False
) -> tuple[ForecasterRecursive, dict, pd.Series, pd.DataFrame]:
    """Entrena el forecaster de producción.

    1. Prepara la serie completa (train + test).
    2. Si buscar_hparams=True, busca hiperparámetros sobre train; si no, usa los
       valores por defecto de config.
    3. Reajusta el modelo final sobre TODOS los datos con esos hiperparámetros y
       guarda los residuos in-sample (para poder dar intervalos en la inferencia).

    Devuelve (forecaster, hiperparámetros, y_full, exog_full).
    """
    y_full, exog_full = preparar_serie_modelo(agg)

    if buscar_hparams:
        n_train = int((y_full.index <= config.FIN_TRAIN).sum())
        hparams = buscar_hiperparametros(y_full, exog_full, n_train)
    else:
        hparams = dict(config.HPARAMS_DEFECTO)

    forecaster = construir_forecaster(hparams)
    forecaster.fit(y=y_full, exog=exog_full, store_in_sample_residuals=True)
    return forecaster, hparams, y_full, exog_full


def guardar(forecaster: ForecasterRecursive, ruta) -> None:
    config.asegurar_directorios()
    save_forecaster(forecaster, file_name=str(ruta), verbose=False)


def cargar(ruta) -> ForecasterRecursive:
    return load_forecaster(str(ruta), verbose=False)


# --------------------------------------------------------------------------- #
# Inferencia: predicción de demanda bajo un escenario de precio (nb 04, anexo)
# --------------------------------------------------------------------------- #
def _construir_futuro(y_full: pd.Series, escenario: dict, n: int) -> pd.DataFrame:
    """Genera las exógenas de las próximas n semanas a partir de un escenario.

    escenario admite escalares o listas de longitud n para: precio_ref, descuento,
    precio_ref_rival y festivo. El calendario (WEEK_YEAR, MES) se deriva de la fecha.
    Predecir a futuro OBLIGA a fijar un escenario de precio: no existe "la predicción
    a futuro" a secas, sino la demanda condicionada a un plan de precios.
    """
    ult_fecha = y_full.index.max()
    fechas = pd.date_range(start=ult_fecha + pd.Timedelta(weeks=1), periods=n, freq="7D")

    def _col(clave, defecto):
        v = escenario.get(clave, defecto)
        return np.full(n, v) if np.isscalar(v) else np.asarray(v)

    futuro = pd.DataFrame(index=fechas)
    futuro["PRECIO_REF"] = _col("precio_ref", 0.0)
    futuro["DESCUENTO"] = _col("descuento", 0.0)
    futuro["PRECIO_REF_RIVAL"] = _col("precio_ref_rival", np.nan)
    futuro["FESTIVO"] = _col("festivo", 0)
    futuro["WEEK_YEAR"] = futuro.index.isocalendar().week.astype(int)
    futuro["MES"] = futuro.index.month
    return futuro[config.EXOGENAS]


def predecir_escenario(
    forecaster: ForecasterRecursive,
    y_full: pd.Series,
    escenario: dict,
    n: int = config.HORIZONTE,
    con_intervalo: bool = True,
) -> pd.DataFrame:
    """Predice la demanda de las próximas n semanas bajo un escenario de precio.

    Devuelve un DataFrame indexado por fecha con la predicción puntual y, si se
    pide y la versión de skforecast lo soporta, el intervalo de predicción por
    bootstrap de residuos in-sample.
    """
    exog_futuro = _construir_futuro(y_full, escenario, n)
    pred = forecaster.predict(steps=n, exog=exog_futuro).rename("prediccion")
    salida = pred.to_frame()

    if con_intervalo:
        try:
            intervalo = forecaster.predict_interval(
                steps=n,
                exog=exog_futuro,
                interval=config.INTERVALO,
                n_boot=config.N_BOOT,
                use_in_sample_residuals=True,
            )
            # skforecast devuelve columnas tipo 'pred', 'lower_bound', 'upper_bound';
            # nos quedamos con las dos bandas sea cual sea su nombre exacto.
            cols = [c for c in intervalo.columns if c != "pred"]
            for c in cols:
                salida[c] = intervalo[c].values
        except Exception as e:  # noqa: BLE001 - el intervalo es opcional
            salida.attrs["aviso_intervalo"] = f"No se pudo calcular el intervalo: {e}"

    return salida


# --------------------------------------------------------------------------- #
# Elasticidad implícita del ML (nb 05) — para validación y sensibilidad
# --------------------------------------------------------------------------- #
def elasticidad_implicita(
    forecaster: ForecasterRecursive, y_full: pd.Series, exog_full: pd.DataFrame
) -> float:
    """Elasticidad que implica la curva de demanda del LightGBM (nb 05).

    Se fija una semana representativa (mediana de cada variable), se barre el precio
    a través del descuento dentro del rango observado, se predice la demanda en cada
    punto y se mide la pendiente en escala log-log (que es la elasticidad). Sirve
    para validar la elasticidad de la regresión con un método independiente y para
    el análisis de sensibilidad.
    """
    # Reconstruye la matriz de features tal como la ve el modelo (lags + exógenas)
    X, _ = forecaster.create_train_X_y(y=y_full, exog=exog_full)

    base = X.median().to_dict()
    base["FESTIVO"] = 0

    precio_reg = float(exog_full["PRECIO_REF"].median())
    dto_max = float(np.quantile(exog_full["DESCUENTO"], 0.99))
    rejilla = np.linspace(0.0, dto_max, 100)

    curva = pd.DataFrame([base] * len(rejilla))
    curva["PRECIO_REF"] = precio_reg
    curva["DESCUENTO"] = rejilla
    curva["PRECIO_EFECTIVO"] = precio_reg * np.exp(-curva["DESCUENTO"])
    curva["Q"] = forecaster.estimator.predict(curva[X.columns])

    ln_p = np.log(curva["PRECIO_EFECTIVO"].values)
    ln_q = np.log(curva["Q"].values)
    pendiente, _ = np.polyfit(ln_p, ln_q, 1)
    return float(pendiente)
