# Pipeline de pricing — guía de uso (`src/`)

Convierte los notebooks del proyecto en un paquete reutilizable con dos comandos.
Este documento es la guía práctica: **qué se ejecuta, con qué opciones, qué produce
y cómo se configura**. Para el porqué de la arquitectura, mira la sección final.

---

## 1. Antes de empezar

Tres condiciones para que nada falle:

1. **Los datos crudos** tienen que estar en `data/raw/`: `wsdr.csv` (movimiento),
   `upcsdr.csv` (catálogo) y `weeks.csv` (calendario). No se versionan en el repo
   (no son redistribuibles); los pones tú.
2. **Las dependencias** instaladas en tu entorno virtual: `pandas`, `numpy`,
   `scikit-learn`, `scipy`, `joblib`, `statsmodels`, `lightgbm`, `skforecast`
   (ver `requirements_src.txt`).
3. **Ejecutas desde la raíz del proyecto**, no desde dentro de `scripts/`. Los
   scripts resuelven las rutas (`data/`, `models/`, `reports/`) relativas a esa
   carpeta. Si entras en `scripts/` y ejecutas desde ahí, no encontrará los datos.

> Nota: en los ejemplos escribo `python scripts/entrenar.py`. Si tú tienes los
> scripts en otra carpeta (p. ej. `src/`), ajusta la ruta: `python src/entrenar.py`.
> El comportamiento es idéntico; solo cambia dónde está el archivo.

---

## 2. Solo hay dos comandos

Todo lo que está en `src/` son piezas internas que **no** ejecutas directamente
(no lanzas `features.py` ni `elasticity.py` por separado). Los únicos dos ejecutables
son:

| Comando | Fase | Qué hace | Cuándo |
|---|---|---|---|
| `entrenar.py` | offline | Lee datos crudos, estima elasticidad y coste, entrena el modelo y **escribe** los artefactos | Pocas veces: al inicio y cuando lleguen datos nuevos |
| `optimizar.py` | online | **Lee** esos artefactos y calcula precio óptimo + demanda prevista | A menudo / automatizable |

**El orden importa: primero `entrenar.py`, después `optimizar.py`.** Optimizar no
toca los datos crudos ni reentrena nada; solo consume lo que entrenar dejó en
`models/`. Si optimizas sin haber entrenado, te avisa con un error claro
(`No hay params.json… Ejecuta antes el entrenamiento`).

> **Importante:** estos scripts **no funcionan con el botón ▶ de VS Code.** Ese botón
> ejecuta el archivo sin argumentos, y ambos exigen que le digas el producto. Si lo
> pulsas verás `error: one of the arguments --producto --todos is required`. No es un
> fallo: es el script pidiéndote que uses la terminal con sus opciones.

---

## 3. `entrenar.py` — la fase de entrenamiento

### Forma básica

```bash
python scripts/entrenar.py --producto pepsi_2l
```

Esto recorre todo el pipeline para Pepsi y deja cuatro archivos:

```
models/pepsi_2l_forecaster.joblib           # el modelo de demanda entrenado
models/pepsi_2l_params.json                 # elasticidad, coste, curva… (lo lee optimizar)
data/processed/pepsi_2l_features.parquet    # el panel con las variables de precio
data/processed/pepsi_2l_model_ready.parquet # la serie que consumió el modelo
```

Por pantalla te resume la elasticidad, el coste y el rango de precios.

### Opciones

| Flag | Qué hace | Cuándo usarlo |
|---|---|---|
| `--producto <nombre>` | Entrena **un** producto del registro | Uso normal |
| `--todos` | Entrena **todos** los productos de `config.PRODUCTOS` en bucle | Cuando tengas varios productos |
| `--buscar-hparams` | Lanza la búsqueda bayesiana de hiperparámetros del modelo (más lento, mejor modelo). Sin este flag usa los valores por defecto de `config.py` | Para el modelo "bueno" final |
| `--forzar-datos` | Reconstruye la categoría enriquecida desde los CSV crudos, ignorando la caché de `data/interim/` | Si cambiaste los datos crudos y quieres releerlos |

`--producto` y `--todos` son **excluyentes**: pones uno u otro, no los dos.

### Ejemplos

```bash
# Entrenamiento rápido de Pepsi (hiperparámetros por defecto)
python scripts/entrenar.py --producto pepsi_2l

# Entrenamiento con búsqueda de hiperparámetros (lento, para el modelo definitivo)
python scripts/entrenar.py --producto pepsi_2l --buscar-hparams

# Reentrenar todos los productos tras actualizar los datos crudos
python scripts/entrenar.py --todos --forzar-datos
```

---

## 4. `optimizar.py` — la fase de optimización

### Forma básica

```bash
python scripts/optimizar.py --producto pepsi_2l
```

Lee los artefactos de Pepsi y te da **dos cosas independientes**:

- **El precio óptimo** (regla de Lerner), su banda, el markup y dos análisis de
  sensibilidad. Esto sale solo de `params.json`, sin tocar el modelo.
- **La demanda prevista** a 4 semanas bajo un escenario de precio. Esto sí usa el
  forecaster.

Guarda el detalle en `reports/pepsi_2l_optimizacion.json`.

### Opciones

| Flag | Qué hace | Por defecto |
|---|---|---|
| `--producto <nombre>` | Optimiza **un** producto | — |
| `--todos` | Tabla consolidada de todos los productos + la guarda en CSV (ver §5) | — |
| `--umbral <0-1>` | Umbral de la banda de precios (% del margen máximo que se conserva) | `0.95` |
| `--sin-forecast` | Calcula **solo** el precio óptimo, se salta la predicción de demanda | forecast activado |
| `--precio-ref <€>` | Precio regular asumido para el escenario de demanda | mediana histórica |
| `--descuento <log>` | Descuento asumido para el escenario (ver recuadro abajo) | `0.0` (sin oferta) |
| `--precio-rival <€>` | Precio del rival asumido para el escenario | ver aviso abajo |

### El escenario de descuento (esto es lo que no conocías)

Cuando pasas `--precio-ref`, `--descuento` o `--precio-rival`, le estás preguntando
al modelo: *"si el mes que viene el precio regular es X, con un descuento Y, y el
rival está a Z, ¿cuánta demanda tendré?"*. Es un **what-if**.

```bash
# ¿Cuánta demanda si mantengo precio regular 1.59 y hago una promoción?
python scripts/optimizar.py --producto pepsi_2l --precio-ref 1.59 --descuento 0.20
```

**Qué significa el número del descuento.** No es un porcentaje directo: es una
*log-fracción* (así se definió `DESCUENTO` en el proyecto, como
`log(precio_regular / precio_efectivo)`). La conversión a descuento real:

| `--descuento` | Descuento real aprox. |
|---|---|
| `0.05` | ~5 % |
| `0.10` | ~9.5 % |
| `0.20` | ~18 % |
| `0.30` | ~26 % |
| `0.40` | ~33 % |

Para descuentos pequeños el número casi coincide con el porcentaje; a partir de ~0.15
empieza a separarse. Un `--descuento 0.20` es una promo de ~18 %, no del 20 %.

Fíjate en que **precio regular y descuento son dos variables separadas**: `--precio-ref`
fija el nivel permanente, `--descuento` la oferta puntual encima de ese nivel. El
precio que el cliente ve esa semana es `precio_ref × e^(-descuento)`. Por eso puedes
combinarlos: "precio regular 1.59, con 18 % de oferta" → precio efectivo ≈ 1.30.

> **Aviso de honestidad sobre `--precio-rival`:** si no lo pasas, el escenario usa
> ahora mismo la mediana del **propio** producto como aproximación del precio del
> rival, que no es lo ideal. Hasta que lo corrija, para escenarios donde importe el
> rival **pásalo explícitamente** con `--precio-rival`. (Dímelo y lo arreglo.)

### Más ejemplos

```bash
# Solo el precio óptimo, sin predicción de demanda (rápido)
python scripts/optimizar.py --producto pepsi_2l --sin-forecast

# Banda más estricta: precios que conservan el 99 % del margen máximo
python scripts/optimizar.py --producto pepsi_2l --umbral 0.99

# Escenario completo: precio regular, descuento y rival explícitos
python scripts/optimizar.py --producto pepsi_2l --precio-ref 1.59 --descuento 0.20 --precio-rival 1.49
```

---

## 5. `--todos` y el CSV consolidado (escalado)

Cuando tengas varios productos entrenados:

```bash
python scripts/optimizar.py --todos
```

Recorre todos los productos del registro, imprime una tabla (una fila por producto:
precio óptimo, banda, elasticidad, coste, y un marcador `fiable`) y la guarda en:

```
reports/optimizacion_consolidada.csv
```

Ese CSV está en **formato español** (separador `;`, decimal `,`, codificación
`utf-8-sig`) para que se abra bien con doble clic en Excel en Windows sin perder los
decimales. Si algún día lo relees con pandas, tienes que decírselo:
`pd.read_csv("...", sep=";", decimal=",")`.

La columna `fiable` viene del filtro de calidad (`evaluar_calidad`): marca los
productos cuya estimación no es de fiar (poca variación de precio, elasticidad
implausible, pocas semanas regulares, óptimo fuera de rango…). Un producto como
"Dom Cola", con precio casi constante, saldría `fiable = False`.

---

## 6. `config.py` — configuración

Es el único sitio donde tocas constantes, rutas y **qué productos existen**.

### Añadir un producto (el registro `PRODUCTOS`)

Cada producto es una entrada con tres campos:

```python
PRODUCTOS = {
    "pepsi_2l": {
        "upc": 1200000230,            # UPC del propio producto
        "rival_upc": 4900000639,      # UPC del competidor directo → Coca-Cola 2 L
        "etiqueta": "Pepsi Cola 2 L", # nombre legible para informes
    },
}
```

Para añadir otro producto, agregas otra entrada con su UPC. El resto del pipeline lo
recorre solo (`--todos`). El registro es **solo la lista de productos que existen**;
la maquinaria de escalado ya está activa en `pipeline.optimizar_varios()`.

### `rival_upc`: qué es y cómo usar `None`

`rival_upc` apunta al competidor directo. El pipeline lo usa para dos cosas:
la **elasticidad cruzada** (cuánto sube tu demanda cuando el rival sube de precio) y
como **variable del modelo de demanda** (el forecaster ve el precio del rival).

Si un producto **no tiene rival** que quieras modelar, pon `None`:

```python
"agua_1l": {
    "upc": 3800000123,
    "rival_upc": None,            # ← sin rival
    "etiqueta": "Agua mineral 1 L",
},
```

Con `rival_upc: None` el pipeline **sigue funcionando** sin problema: simplemente no
calcula la elasticidad cruzada y no mete el precio del rival en el modelo (la columna
queda vacía). Es exactamente lo que quieres cuando el producto no tiene un competidor
claro o no te interesa modelarlo. (Omitir el campo por completo tiene el mismo efecto
que ponerlo a `None`.)

> **Verifica siempre los UPC** en tu `upcsdr.csv` antes de añadir un producto. Un UPC
> equivocado filtra un producto que no existe (o el que no es) y el pipeline entrenaría
> sobre datos vacíos o erróneos. Los UPC de ejemplo comentados en `config.py` son
> ilustrativos: confírmalos antes de descomentarlos.

### Constantes que puedes ajustar

Las principales, todas en `config.py`:

- `VENTANA` (13) y `CUANTIL` (0.90): cómo se calcula el precio de referencia.
- `INICIO_SERIE` / `FIN_TRAIN`: dónde empieza la serie y la frontera train/test.
- `HORIZONTE` (4): cuántas semanas predice el modelo.
- `UMBRAL_BANDA` (0.95): umbral por defecto de la banda (el que sobreescribe `--umbral`).
- `HPARAMS_DEFECTO`: hiperparámetros del modelo para el modo rápido (sin `--buscar-hparams`).

Cambiar cualquiera aquí afecta a todo el pipeline de forma coherente, sin tocar el
resto de módulos.

---

## 7. Qué produce cada cosa, y para quién

| Archivo | Formato | Para quién |
|---|---|---|
| `models/<p>_params.json` | JSON | La máquina (lo lee `optimizar.py`) |
| `models/<p>_forecaster.joblib` | binario | La máquina (el modelo entrenado) |
| `reports/<p>_optimizacion.json` | JSON anidado | La máquina / consulta técnica detallada |
| `reports/optimizacion_consolidada.csv` | CSV español | Hoja de cálculo / persona no técnica |

Regla mental: **JSON para el pipeline, CSV para la hoja de cálculo, informe
(Power BI / PDF) para la persona no técnica.** A un decisor no le pasas el JSON; le
pasas el CSV en Excel o, mejor, un informe de Power BI construido sobre él.

---

## 8. Cómo leer los resultados

- **Precio óptimo:** el precio que maximiza el margen de contribución (Lerner).
- **Banda:** rango de precios que conserva al menos el umbral (95 %) del margen
  máximo. Cerca del óptimo la curva es plana, así que tienes margen de maniobra.
- **¿Dentro del rango?** Si es `False`, el óptimo teórico cae **fuera** de los precios
  que se observaron históricamente: sería *extrapolar*. En ese caso el precio numérico
  se queda en el borde del rango con datos, y la acción sensata es **probar** un precio
  algo más alto y medir, no fijar el número a ciegas.
- **`fiable` (en `--todos`):** `False` = la estimación tiene señales de poca fiabilidad;
  revisa los `avisos` de esa fila.
- **Sensibilidad:** cómo cambia el precio óptimo si la elasticidad o el coste fueran
  distintos. El óptimo suele ser robusto a la elasticidad y más sensible al coste
  (conviene tener bien medido el coste).

---

## 9. Errores frecuentes

| Síntoma | Causa | Solución |
|---|---|---|
| `error: one of the arguments --producto --todos is required` | Ejecutaste sin argumentos (o con ▶) | Usa la terminal con `--producto <nombre>` |
| `No hay params.json… Ejecuta antes el entrenamiento` | Optimizaste antes de entrenar | Corre `entrenar.py` primero |
| `FileNotFoundError` en `data/raw/...` | Faltan los CSV crudos | Colócalos en `data/raw/` |
| No encuentra `data/` o `models/` | Ejecutaste desde dentro de `scripts/` | Ejecuta desde la raíz del proyecto |
| Excel pierde los decimales del CSV | Formato regional | Ya resuelto: el CSV se guarda en formato español (`;` y `,`) |
| `KeyError: producto '...' no está en el registro` | El nombre no está en `PRODUCTOS` | Añádelo en `config.py` o revisa el nombre |

---

## 10. Estado de validación (honestidad)

- **Cadena econométrica** (`data → features → elasticity → cost → optimize`): probada
  de principio a fin con datos sintéticos de elasticidad conocida. Recupera los valores
  inyectados; la banda y el flag `dentro_del_rango` funcionan.
- **`forecast.py`** (LightGBM + skforecast): validado por sintaxis y revisión,
  replicando la API de los notebooks, pero **no ejecutado aquí** (requiere los datos
  crudos y las librerías pesadas). Lo ejecutas tú en local con `entrenar.py`. El
  cálculo del intervalo va envuelto en `try/except` por si tu versión de skforecast
  cambia la firma de `predict_interval`.

---

## 11. Por qué está partido así (arquitectura, en breve)

Cada módulo de `src/` hace una sola cosa; `pipeline.py` es el único que los encadena y
`config.py` el único con constantes y rutas. La frontera real no es "un módulo por
notebook" sino **entrenar (offline, caro, ocasional) vs. optimizar (online, barato,
automatizable)**. El puente entre ambas fases son los artefactos en disco: por eso el
precio óptimo se reconstruye entero desde `params.json` sin volver a leer los datos
crudos ni cargar el modelo. Las cuatro decisiones de diseño concretas (óptimo separado
del forecaster, modelo entrenado con todos los datos, `params.json` con la curva
completa, umbral de banda parametrizado) están comentadas en el código de cada módulo.
