"""Carga, limpieza y validación de datos.

Reproduce el notebook 01 (EDA y limpieza) como funciones reutilizables:

    crudos → limpieza → unión con catálogo y calendario → categoría enriquecida
                                                         → slice de un producto

La "categoría enriquecida" (todos los refrescos) se guarda en interim/ porque la
necesita el rival: para calcular la elasticidad cruzada de Pepsi hay que leer los
precios de Coca-Cola de ese mismo fichero.

Novedad frente al notebook: validación de entrada. Un script automático no puede
"mirar" los datos como hacías tú en las celdas; tiene que comprobar por código que
no llegan sorpresas (columnas que faltan, precios a cero, claves duplicadas).
"""

from __future__ import annotations

import pandas as pd

from . import config


# --------------------------------------------------------------------------- #
# Validación de entrada
# --------------------------------------------------------------------------- #
_COLUMNAS_MOVIMIENTO = {"STORE", "UPC", "WEEK", "MOVE", "QTY", "PRICE", "SALE", "PROFIT", "OK"}


def validar_movimiento(mov: pd.DataFrame) -> None:
    """Comprueba que el fichero de movimiento trae lo mínimo imprescindible.

    Lanza ValueError con un mensaje concreto si algo falla, en lugar de dejar que
    el error aparezca más adelante disfrazado.
    """
    faltan = _COLUMNAS_MOVIMIENTO - set(mov.columns)
    if faltan:
        raise ValueError(f"Al fichero de movimiento le faltan columnas: {sorted(faltan)}")
    if mov.empty:
        raise ValueError("El fichero de movimiento está vacío.")


def validar_producto(df: pd.DataFrame, nombre: str) -> None:
    """Chequeos de sanidad sobre el slice de un producto antes de modelar."""
    if df.empty:
        raise ValueError(f"El producto '{nombre}' no tiene filas tras la limpieza.")
    n_precio_cero = int((df["PRICE"] <= 0).sum())
    if n_precio_cero:
        raise ValueError(f"'{nombre}' tiene {n_precio_cero} filas con precio <= 0 (deberían haberse limpiado).")
    dups = int(df.duplicated(subset=["STORE", "WEEK"]).sum())
    if dups:
        raise ValueError(f"'{nombre}' tiene {dups} claves (STORE, WEEK) duplicadas.")


# --------------------------------------------------------------------------- #
# Carga y limpieza (nb 01)
# --------------------------------------------------------------------------- #
def cargar_crudos() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Lee los tres ficheros originales desde data/raw/."""
    mov = pd.read_csv(config.RAW / config.FICHERO_MOVIMIENTO)

    # El catálogo trae acentos → latin-1. Normalizamos cabeceras a mayúsculas
    # para no depender de si vienen 'upc' o 'UPC'.
    cat = pd.read_csv(config.RAW / config.FICHERO_CATALOGO, encoding="latin-1")
    cat.columns = cat.columns.str.upper()

    # weeks.csv no tiene cabecera; las fechas están en formato americano MM/DD/YY.
    weeks = pd.read_csv(
        config.RAW / config.FICHERO_SEMANAS,
        header=None,
        names=["WEEK", "start", "end", "special"],
    )
    weeks["start"] = pd.to_datetime(weeks["start"], format="%m/%d/%y")
    weeks["end"] = pd.to_datetime(weeks["end"], format="%m/%d/%y")

    return mov, cat, weeks


def limpiar_movimiento(mov: pd.DataFrame) -> pd.DataFrame:
    """Limpieza del nb 01: descarta hex, filas no fiables (OK=0) y precios a 0.

    - PRICE_HEX / PROFIT_HEX: no se usan.
    - OK == 0: registros marcados como poco fiables (casi todos con precio 0).
    - PRICE == 0: semanas sin venta del producto.
    """
    mov = mov.drop(columns=["PRICE_HEX", "PROFIT_HEX"], errors="ignore")
    mov = mov[mov["OK"] == 1].copy()
    mov = mov[mov["PRICE"] > 0].copy()
    return mov


def construir_categoria(guardar: bool = True) -> pd.DataFrame:
    """Une movimiento + catálogo + calendario → categoría enriquecida (nb 01).

    Devuelve el DataFrame y, por defecto, lo guarda en interim/ para reutilizarlo
    (lo consumen tanto el producto como su rival).
    """
    mov, cat, weeks = cargar_crudos()
    validar_movimiento(mov)
    mov = limpiar_movimiento(mov)

    # Unión con el catálogo (marca, formato, código de commodity)
    mov = mov.merge(
        cat[["UPC", "DESCRIP", "SIZE", "COM_CODE"]],
        on="UPC",
        how="left",
    )
    # Unión con el calendario (fecha de inicio de semana y festividad)
    mov = mov.merge(
        weeks[["WEEK", "start", "end", "special"]],
        on="WEEK",
        how="left",
    )
    mov = mov.drop(columns=["OK"], errors="ignore")

    if mov["start"].isna().any():
        raise ValueError("Hay semanas sin fecha tras unir con el calendario (weeks.csv incompleto).")

    if guardar:
        config.asegurar_directorios()
        mov.to_parquet(config.INTERIM / config.NOMBRE_CATEGORIA)
    return mov


def cargar_categoria(forzar: bool = False) -> pd.DataFrame:
    """Carga la categoría enriquecida; la construye si no existe o si forzar=True."""
    ruta = config.INTERIM / config.NOMBRE_CATEGORIA
    if ruta.exists() and not forzar:
        return pd.read_parquet(ruta)
    return construir_categoria(guardar=True)


# --------------------------------------------------------------------------- #
# Slice por producto
# --------------------------------------------------------------------------- #
def slice_upc(cat: pd.DataFrame, upc: int) -> pd.DataFrame:
    """Extrae un producto (por UPC) y recorta el arranque inestable de la serie."""
    df = cat[cat["UPC"] == upc].copy()
    df = df[df["start"] > config.INICIO_SERIE].copy()
    return df.reset_index(drop=True)


def preparar_producto(nombre: str, forzar: bool = False) -> pd.DataFrame:
    """Devuelve el slice limpio de un producto del registro, listo para features.

    Asegura de paso que la categoría enriquecida existe (la necesita el rival).
    """
    ficha = config.get_producto(nombre)
    cat = cargar_categoria(forzar=forzar)
    df = slice_upc(cat, ficha["upc"])
    validar_producto(df, nombre)

    config.asegurar_directorios()
    df.to_parquet(config.ruta_procesado(nombre))
    return df


def cargar_rival(nombre: str) -> pd.DataFrame | None:
    """Devuelve el slice del rival del producto, o None si no tiene rival definido."""
    ficha = config.get_producto(nombre)
    rival_upc = ficha.get("rival_upc")
    if rival_upc is None:
        return None
    cat = cargar_categoria()
    return slice_upc(cat, rival_upc)
