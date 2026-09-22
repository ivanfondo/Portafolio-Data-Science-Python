"""Fase ONLINE: carga los artefactos y calcula precio óptimo + demanda prevista.

Uso:
    python scripts/optimizar.py --producto pepsi_2l
    python scripts/optimizar.py --producto pepsi_2l --precio-ref 1.59 --descuento 0.20
    python scripts/optimizar.py --producto pepsi_2l --sin-forecast
    python scripts/optimizar.py --todos            # tabla consolidada (escalado)

Produce (salvo --todos): reports/<producto>_optimizacion.json
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import config, pipeline  # noqa: E402


def _imprimir(resultado: dict) -> None:
    opt = resultado["optimizacion"]
    print(f"\n=== {resultado['etiqueta']} ===")
    print(f"  Precio óptimo:      {opt['precio_optimo']:.3f} €")
    print(f"  Banda ({opt['banda']['umbral']:.0%}):        "
          f"[{opt['banda']['banda_min']:.2f}, {opt['banda']['banda_max']:.2f}] €")
    print(f"  Markup s/coste:     {opt['markup_sobre_coste']:.1%}")
    print(f"  Margen s/precio:    {opt['margen_sobre_precio']:.1%}")
    print(f"  ¿Dentro del rango?  {opt['dentro_del_rango']}")

    print("  Sensibilidad a la elasticidad:")
    for nombre, precio in opt["sensibilidad_elasticidad"].items():
        print(f"      {nombre:24s} → {precio:.3f} €")
    print("  Sensibilidad al coste:")
    for nombre, precio in opt["sensibilidad_coste"].items():
        print(f"      {nombre:24s} → {precio:.3f} €")

    if "demanda_prevista" in resultado:
        dp = resultado["demanda_prevista"]
        print("  Demanda prevista (escenario dado):")
        for i, fecha in enumerate(dp["fechas"]):
            print(f"      {fecha}: {dp['prediccion'][i]:.0f} uds/tienda")
    if "aviso_forecast" in resultado:
        print(f"  [aviso] {resultado['aviso_forecast']}")


def main() -> None:
    p = argparse.ArgumentParser(description="Optimización de precio del pipeline de pricing.")
    grupo = p.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--producto", help="Nombre del producto en el registro.")
    grupo.add_argument("--todos", action="store_true", help="Tabla consolidada de todos los productos (escalado).")
    p.add_argument("--umbral", type=float, default=config.UMBRAL_BANDA, help="Umbral de la banda (0-1).")
    p.add_argument("--sin-forecast", action="store_true", help="Solo precio óptimo, sin predicción de demanda.")
    # Escenario de precio para el forecast (opcional)
    p.add_argument("--precio-ref", type=float, help="Precio regular asumido en las próximas semanas.")
    p.add_argument("--descuento", type=float, help="Descuento (log-fracción) asumido, p.ej. 0.20.")
    p.add_argument("--precio-rival", type=float, help="Precio del rival asumido.")
    args = p.parse_args()

    if args.todos:
        tabla = pipeline.optimizar_varios(umbral=args.umbral)
        print(tabla.to_string(index=False))
        return

    # Escenario solo si el usuario pasó algún valor; si no, se usa el por defecto.
    escenario = None
    if any(v is not None for v in (args.precio_ref, args.descuento, args.precio_rival)):
        params = pipeline.cargar_params(args.producto)
        escenario = {
            "precio_ref": args.precio_ref if args.precio_ref is not None else params["precio_ref_mediano"],
            "descuento": args.descuento if args.descuento is not None else 0.0,
            "precio_ref_rival": args.precio_rival if args.precio_rival is not None else params["precio_ref_mediano"],
            "festivo": 0,
        }

    resultado = pipeline.optimizar(
        args.producto,
        escenario=escenario,
        umbral=args.umbral,
        con_forecast=not args.sin_forecast,
    )
    _imprimir(resultado)
    print(f"\n  Resultado guardado en: {config.REPORTS / (args.producto + '_optimizacion.json')}")


if __name__ == "__main__":
    main()
