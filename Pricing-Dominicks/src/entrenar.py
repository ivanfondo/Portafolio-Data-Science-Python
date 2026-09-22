"""Fase OFFLINE: entrena y guarda los artefactos de un producto.

Uso:
    python scripts/entrenar.py --producto pepsi_2l
    python scripts/entrenar.py --producto pepsi_2l --buscar-hparams
    python scripts/entrenar.py --todos --buscar-hparams

Produce, por producto:
    models/<producto>_forecaster.joblib
    models/<producto>_params.json
    data/processed/<producto>_features.parquet
    data/processed/<producto>_model_ready.parquet
"""

import argparse
import sys
from pathlib import Path

# Permite ejecutar el script desde la raíz del proyecto sin instalar el paquete
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import config, pipeline  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description="Entrenamiento del pipeline de pricing.")
    grupo = p.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--producto", help="Nombre del producto en el registro (config.PRODUCTOS).")
    grupo.add_argument("--todos", action="store_true", help="Entrena todos los productos del registro.")
    p.add_argument(
        "--buscar-hparams",
        action="store_true",
        help="Lanza la búsqueda bayesiana de hiperparámetros (lento). Si no, usa los por defecto.",
    )
    p.add_argument(
        "--forzar-datos",
        action="store_true",
        help="Reconstruye la categoría enriquecida desde los datos crudos.",
    )
    args = p.parse_args()

    productos = list(config.PRODUCTOS) if args.todos else [args.producto]

    for prod in productos:
        print(f"\n=== Entrenando: {prod} ===")
        params = pipeline.entrenar(
            prod, buscar_hparams=args.buscar_hparams, forzar_datos=args.forzar_datos
        )
        print(f"  Elasticidad:        {params['elasticidad']:.2f}")
        if params.get("elasticidad_ml") is not None:
            print(f"  Elasticidad ML:     {params['elasticidad_ml']:.2f} (validación)")
        print(f"  Coste de referencia:{params['coste_ref']:.3f} €")
        print(f"  Rango de precios:   [{params['precio_min']:.2f}, {params['precio_max']:.2f}] €")
        print(f"  Artefactos en:      {config.MODELS}")


if __name__ == "__main__":
    main()
