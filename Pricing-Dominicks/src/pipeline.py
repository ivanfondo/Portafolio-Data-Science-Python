"""Orquestación del pipeline por producto.

Dos operaciones, coherentes con la separación entrenamiento/inferencia:

    entrenar(producto)  → estima elasticidad y coste, entrena el forecaster y
                          guarda los artefactos (forecaster.joblib + params.json).
                          Fase OFFLINE, ocasional (cuando llegan datos nuevos).

    optimizar(producto) → carga los artefactos y calcula el precio óptimo, la banda
                          y, si se pide, la predicción de demanda a 4 semanas bajo un
                          escenario de precio. Fase ONLINE, lo que se automatiza.

El escalado a N productos es un bucle sobre estas funciones, con un filtro de calidad
que marca los productos cuya estimación no es de fiar (poca variación de precio, etc.).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pandas as pd

from . import config, data, features, elasticity, cost, forecast, optimize


# --------------------------------------------------------------------------- #
# ENTRENAR (offline)
# --------------------------------------------------------------------------- #
def entrenar(producto: str, buscar_hparams: bool = False, forzar_datos: bool = False) -> dict:
    """Ejecuta la fase de entrenamiento completa para un producto y guarda artefactos.

    Devuelve el diccionario de parámetros que se ha escrito en params.json.
    """
    ficha = config.get_producto(producto)

    # 1. Datos: slice limpio del producto (+ categoría enriquecida para el rival)
    df = data.preparar_producto(producto, forzar=forzar_datos)

    # 2. Features de precio + precio del rival
    feats = features.construir_features(df)
    feats = features.añadir_precio_rival(feats, data.cargar_rival(producto))
    features.guardar_features(feats, producto)

    # 3. Elasticidad (regresión log-log con controles)
    elas = elasticity.estimar_elasticidad(feats)

    # 4. Coste de referencia y anclas de la curva
    cst = cost.estimar_coste(feats)

    # 5. Forecaster (entrenado con TODOS los datos)
    agg = forecast.agregar_serie(feats)
    fc, hparams, y_full, exog_full = forecast.entrenar_forecaster(
        agg, buscar_hparams=buscar_hparams
    )
    forecast.guardar(fc, config.ruta_forecaster(producto))
    # Serie que consumió el modelo, para validación / elasticidad implícita
    pd.concat([y_full, exog_full], axis=1).sort_index().to_parquet(
        config.ruta_model_ready(producto)
    )

    # 6. Elasticidad implícita del ML (valida la de la regresión; alimenta sensibilidad)
    try:
        elas_ml = forecast.elasticidad_implicita(fc, y_full, exog_full)
    except Exception:  # noqa: BLE001 - no debe tumbar el entrenamiento
        elas_ml = None

    # 7. Constante A de la curva de demanda
    A = optimize.constante_demanda(
        cst["demanda_reg_media"], cst["precio_ref_mediano"], elas["elasticidad"]
    )

    # 8. Empaquetar y guardar params.json (todo lo que la optimización necesita)
    params = {
        "producto": producto,
        "etiqueta": ficha["etiqueta"],
        "upc": ficha["upc"],
        "fecha_entrenamiento": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        # Elasticidades
        "elasticidad": elas["elasticidad"],
        "elasticidad_con_rival": elas["elasticidad_con_rival"],
        "elasticidad_sin_rival": elas["elasticidad_sin_rival"],
        "elasticidad_cruzada": elas["elasticidad_cruzada"],
        "elasticidad_ml": elas_ml,
        "efecto_descuento": elas["efecto_descuento"],
        "r2_elasticidad": elas["r2"],
        "n_obs_elasticidad": elas["n_obs"],
        # Coste y anclas
        "coste_ref": cst["coste_ref"],
        "coste_q1": cst["coste_q1"],
        "coste_q3": cst["coste_q3"],
        "n_regular": cst["n_regular"],
        "precio_min": cst["precio_min"],
        "precio_max": cst["precio_max"],
        "precio_ref_mediano": cst["precio_ref_mediano"],
        "demanda_reg_media": cst["demanda_reg_media"],
        "cv_precio": cst["cv_precio"],
        "A": A,
        # Forecaster
        "hiperparametros": hparams,
        "horizonte": config.HORIZONTE,
    }

    config.asegurar_directorios()
    with open(config.ruta_params(producto), "w", encoding="utf-8") as f:
        json.dump(params, f, ensure_ascii=False, indent=2)

    return params


# --------------------------------------------------------------------------- #
# OPTIMIZAR (online)
# --------------------------------------------------------------------------- #
def cargar_params(producto: str) -> dict:
    ruta = config.ruta_params(producto)
    if not ruta.exists():
        raise FileNotFoundError(
            f"No hay params.json para '{producto}'. Ejecuta antes el entrenamiento."
        )
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def optimizar(
    producto: str,
    escenario: dict | None = None,
    umbral: float = config.UMBRAL_BANDA,
    con_forecast: bool = True,
    guardar_resultado: bool = True,
) -> dict:
    """Calcula el precio óptimo (+ banda, sensibilidad) y, opcionalmente, la demanda
    prevista a 4 semanas bajo un escenario de precio.

    El óptimo sale solo del params.json. El forecast, si se pide, usa el forecaster
    y el escenario: son dos salidas distintas que se entregan juntas.
    """
    params = cargar_params(producto)

    # --- Precio óptimo (no necesita el forecaster) ---
    resultado = {
        "producto": producto,
        "etiqueta": params.get("etiqueta", producto),
        "optimizacion": optimize.optimizar(params, umbral),
    }

    # --- Predicción de demanda a futuro (sí necesita forecaster + escenario) ---
    if con_forecast:
        # Escenario por defecto: precio óptimo sin descuento, rival en su nivel habitual
        if escenario is None:
            escenario = {
                "precio_ref": resultado["optimizacion"]["precio_optimo"],
                "descuento": 0.0,
                "precio_ref_rival": params["precio_ref_mediano"],
                "festivo": 0,
            }
        try:
            fc = forecast.cargar(config.ruta_forecaster(producto))
            modelo = pd.read_parquet(config.ruta_model_ready(producto))
            y_full = modelo["UNIDADES"]
            pred = forecast.predecir_escenario(fc, y_full, escenario, n=params["horizonte"])
            resultado["escenario"] = escenario
            resultado["demanda_prevista"] = {
                "fechas": [d.date().isoformat() for d in pred.index],
                "prediccion": [round(float(v), 1) for v in pred["prediccion"]],
            }
            # Bandas del intervalo si están disponibles
            for c in pred.columns:
                if c != "prediccion":
                    resultado["demanda_prevista"][c] = [round(float(v), 1) for v in pred[c]]
        except Exception as e:  # noqa: BLE001 - el forecast es opcional frente al óptimo
            resultado["aviso_forecast"] = f"No se pudo predecir la demanda: {e}"

    if guardar_resultado:
        config.asegurar_directorios()
        ruta = config.REPORTS / f"{producto}_optimizacion.json"
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(resultado, f, ensure_ascii=False, indent=2)

    return resultado


# --------------------------------------------------------------------------- #
# ESCALADO a N productos (bucle + filtro de calidad)
# --------------------------------------------------------------------------- #
def evaluar_calidad(params: dict) -> list[str]:
    """Marca señales de que la estimación de un producto no es de fiar.

    Automatizar no exime de vigilar la calidad: un producto con poca variación de
    precio da una elasticidad poco fiable (el caso de Dom Cola). Se devuelven los
    avisos encontrados; lista vacía = estimación fiable.
    """
    avisos = []
    if params.get("cv_precio", 1.0) < 0.05:
        avisos.append("variación de precio muy baja (CV < 5%): elasticidad poco fiable")
    eps = abs(params.get("elasticidad", 0.0))
    if eps < 1.0:
        avisos.append(f"elasticidad implausible para este método (|ε|={eps:.2f} < 1)")
    if eps > 10.0:
        avisos.append(f"elasticidad explosiva (|ε|={eps:.2f} > 10): revisar")
    if params.get("n_regular", 0) < 30:
        avisos.append(f"pocas semanas regulares ({params.get('n_regular')}): coste poco fiable")
    if params.get("r2_elasticidad", 1.0) < 0.3:
        avisos.append(f"R² de la elasticidad bajo ({params.get('r2_elasticidad'):.2f})")
    if not (params["precio_min"] <= params["coste_ref"] * params["elasticidad"] / (1 + params["elasticidad"]) <= params["precio_max"]):
        avisos.append("el precio óptimo cae fuera del rango histórico (extrapola)")
    return avisos


def optimizar_varios(
    productos: list[str] | None = None,
    umbral: float = config.UMBRAL_BANDA,
    guardar_csv: bool = True,
) -> pd.DataFrame:
    """Recorre varios productos y devuelve una tabla consolidada con filtro de calidad.

    Cada producto debe estar ya entrenado (tener su params.json). El resultado es el
    entregable final de la automatización: una fila por producto con su precio óptimo,
    banda, y un marcador de fiabilidad. Por defecto lo guarda también en
    reports/optimizacion_consolidada.csv (una fila por producto, formato ideal para
    abrir en Excel o Power BI).
    """
    productos = productos or list(config.PRODUCTOS)
    filas = []
    for prod in productos:
        try:
            params = cargar_params(prod)
        except FileNotFoundError:
            filas.append({"producto": prod, "estado": "sin entrenar"})
            continue
        opt = optimize.optimizar(params, umbral)
        avisos = evaluar_calidad(params)
        filas.append(
            {
                "producto": prod,
                "etiqueta": params.get("etiqueta", prod),
                "precio_optimo": round(opt["precio_optimo"], 3),
                "banda_min": round(opt["banda"]["banda_min"], 3),
                "banda_max": round(opt["banda"]["banda_max"], 3),
                "elasticidad": round(params["elasticidad"], 2),
                "coste_ref": round(params["coste_ref"], 3),
                "fiable": len(avisos) == 0,
                "avisos": "; ".join(avisos) if avisos else "",
            }
        )

    tabla = pd.DataFrame(filas)

    if guardar_csv:
        config.asegurar_directorios()
        ruta = config.REPORTS / "optimizacion_consolidada.csv"
        # Formato español para que Excel en Windows lo abra bien al doble clic:
        #   sep=";"       separador de columnas (en España la coma es el decimal)
        #   decimal=","   separador decimal
        #   utf-8-sig     acentos y símbolo € correctos
        # (pandas entrecomilla solo las celdas que contengan ";", p.ej. varios avisos)
        tabla.to_csv(ruta, index=False, sep=";", decimal=",", encoding="utf-8-sig")

    return tabla
