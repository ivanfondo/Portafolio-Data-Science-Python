"""Configuración central del pipeline de pricing.

Aquí viven las rutas, las constantes y el registro de productos. La idea es que
ningún otro módulo tenga números "mágicos" ni rutas escritas a mano: todo lo que
podría cambiar (la ventana del precio de referencia, el cuantil, el horizonte,
qué producto se analiza) se decide en un único sitio.

Las constantes reproducen exactamente las decisiones tomadas en los notebooks
(VENTANA=13, CUANTIL=0.90, horizonte=4, corte en 1991, FIN_TRAIN=1996-05-01...),
de modo que el código productivizado dé los mismos resultados que la exploración.
"""

from pathlib import Path

# --------------------------------------------------------------------------- #
# Rutas del proyecto
# --------------------------------------------------------------------------- #
# config.py vive en <raíz>/src/, así que la raíz es el directorio padre de src.
RAIZ = Path(__file__).resolve().parents[1]

DATA = RAIZ / "data"
RAW = DATA / "raw"              # ficheros originales (wsdr.csv, upcsdr.csv, weeks.csv)
INTERIM = DATA / "interim"      # categoría enriquecida (todos los refrescos)
PROCESSED = DATA / "processed"  # producto ya filtrado y con features
MODELS = RAIZ / "models"        # forecaster.joblib + params.json por producto
REPORTS = RAIZ / "reports"      # resultados de optimización (json)

# Nombres de los ficheros crudos (por si en tu descarga difieren, se cambian aquí)
FICHERO_MOVIMIENTO = "wsdr.csv"
FICHERO_CATALOGO = "upcsdr.csv"
FICHERO_SEMANAS = "weeks.csv"

# Fichero intermedio con toda la categoría de refrescos (lo necesita el rival)
NOMBRE_CATEGORIA = "soft_drinks_enriched.parquet"


def asegurar_directorios() -> None:
    """Crea las carpetas de salida si no existen. Idempotente."""
    for d in (INTERIM, PROCESSED, MODELS, REPORTS):
        d.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------------------------------- #
# Constantes de negocio / modelado (idénticas a los notebooks)
# --------------------------------------------------------------------------- #
INICIO_SERIE = "1991-01-01"   # corte donde el nº de tiendas se estabiliza (nb 01/02)
FIN_TRAIN = "1996-05-01"      # frontera train/test (nb 04); el test es el último año

VENTANA = 13                  # ventana móvil del precio de referencia (≈ trimestre)
CUANTIL = 0.90                # percentil alto = precio regular (nb 03)
MIN_PERIODOS = 5              # min_periods de la ventana móvil

HORIZONTE = 4                 # semanas a predecir (avalado por el backtesting)
LAGS = 4                      # lags de demanda en el forecaster (un mes)
RANDOM_STATE = 123            # semilla, para reproducibilidad

# Optimización de precio
UMBRAL_BANDA = 0.95           # % del margen máximo que define la banda de precios
N_PUNTOS_CURVA = 300          # resolución de la rejilla de precios

# Búsqueda de hiperparámetros
N_TRIALS = 30                 # nº de pruebas de la búsqueda bayesiana

# Intervalos de predicción (bootstrap de residuos)
INTERVALO = [10, 90]          # percentiles del intervalo de predicción
N_BOOT = 1000

# Orden CANÓNICO de las variables exógenas del forecaster.
# Fijarlo aquí garantiza que train e inferencia usen las mismas columnas en el
# mismo orden (skforecast es sensible a esto).
EXOGENAS = [
    "PRECIO_REF",
    "DESCUENTO",
    "PRECIO_REF_RIVAL",
    "FESTIVO",
    "WEEK_YEAR",
    "MES",
]

# Hiperparámetros por defecto (punto medio del espacio de búsqueda del nb 04).
# Sirven para entrenar rápido sin lanzar la búsqueda bayesiana; para el modelo
# "bueno" se usa entrenar(..., buscar_hparams=True).
HPARAMS_DEFECTO = {
    "n_estimators": 300,
    "max_depth": 4,
    "learning_rate": 0.05,
    "num_leaves": 20,
    "min_child_samples": 15,
    "reg_lambda": 1.0,
}

# --------------------------------------------------------------------------- #
# Registro de productos
# --------------------------------------------------------------------------- #
# Cada producto se identifica por su UPC y, opcionalmente, por el UPC de su rival
# directo (para la elasticidad cruzada y el precio del sustituto en el modelo).
# Escalar a N productos = añadir entradas aquí y recorrer el diccionario.
PRODUCTOS = {
    "pepsi_2l": {
        "upc": 1200000230,
        "rival_upc": 4900000639,   # Coca-Cola 2 L
        "etiqueta": "Pepsi Cola 2 L",
    },
    # Reservados para el escalado (mismo formato 2 L). Descomentar al escalar:
    # "coca_2l": {"upc": 4900000639, "rival_upc": 1200000230, "etiqueta": "Coca-Cola 2 L"},
    # "diet_coke_2l": {"upc": 4900000663, "rival_upc": 1200000230, "etiqueta": "Diet Coke 2 L"},
}


def get_producto(nombre: str) -> dict:
    """Devuelve la ficha de un producto del registro o lanza un error claro."""
    if nombre not in PRODUCTOS:
        disponibles = ", ".join(PRODUCTOS)
        raise KeyError(
            f"Producto '{nombre}' no está en el registro. Disponibles: {disponibles}. "
            f"Añádelo en config.PRODUCTOS con su UPC."
        )
    return PRODUCTOS[nombre]


def ruta_forecaster(nombre: str) -> Path:
    return MODELS / f"{nombre}_forecaster.joblib"


def ruta_params(nombre: str) -> Path:
    return MODELS / f"{nombre}_params.json"


def ruta_model_ready(nombre: str) -> Path:
    """Serie agregada (y + exógenas) que consumió el forecaster.

    Se guarda para poder reconstruir la curva de demanda del ML (validación y
    elasticidad implícita) sin recalcular desde los datos crudos.
    """
    return PROCESSED / f"{nombre}_model_ready.parquet"


def ruta_procesado(nombre: str) -> Path:
    return PROCESSED / f"{nombre}.parquet"


def ruta_features(nombre: str) -> Path:
    return PROCESSED / f"{nombre}_features.parquet"
