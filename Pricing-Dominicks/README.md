# Pricing en retail: elasticidad y optimización de precio

Estimación de la **elasticidad precio-demanda** de un producto de refrescos a partir
de datos reales de scanner, y uso de esa elasticidad para **optimizar el precio**
(ingreso y margen). Es un proyecto de *pricing*, no solo de previsión de demanda:
el objetivo no es únicamente predecir cuánto se venderá, sino entender cómo responde
la demanda al precio y qué precio conviene poner.

## Datos

**Dominick's Finer Foods** — datos de scanner a nivel de tienda y semana recogidos por
una cadena de supermercados del área de Chicago entre 1989 y 1997. Es uno de los pocos
conjuntos públicos aptos para pricing con rigor: incluye precio, unidades vendidas,
margen del minorista y código de promoción, y en su origen contiene experimentos de
precio.

- **Categoría analizada:** refrescos (*soft drinks*).
- **Producto seleccionado:** Pepsi Cola 2 L (UPC 1200000230), elegido por combinar alto
  volumen, presencia en la mayoría de las tiendas y variación de precio suficiente para
  identificar la elasticidad. Coca-Cola y Diet Coke (mismo formato) quedan reservadas
  para una posible extensión a elasticidad cruzada entre marcas.

Los datos **no se incluyen en el repositorio** (pesan y no son redistribuibles). Para
reproducir el proyecto, descargar y colocar en `data/raw/`:

- `wsdr.csv` y `upcsdr.csv` — ficheros de movimiento y catálogo de la categoría de
  refrescos, desde el [Kilts Center](https://www.chicagobooth.edu/research/kilts/research-data/dominicks).
- `weeks.csv` — mapa de semana → fecha, desde el repositorio [eurostat/dff](https://github.com/eurostat/dff)
  (carpeta `CSV/`).

## Estructura del proyecto

```
Pricing-Dominicks/
├── data/                
│   ├── raw/              
│   ├── interim/          
│   └── processed/        
├── notebooks/
│   ├── 01_eda_limpieza.ipynb
│   ├── 02_grupo_reducido_stl.ipynb
│   ├── 03_demanda_elasticidad.ipynb
│   ├── 04_ml_features_opt.ipynb
│   ├── 05_comparacion_oos.ipynb
│   └── 06_optimizacion_precio.ipynb
├── src/                  
├── reports/figures/      
├── requirements.txt
├── .gitignore
└── README.md
```

## Enfoque

El proyecto avanza sobre un grupo reducido (un producto) y escala al final. Las fases:

1. EDA y limpieza.
2. Setup de evaluación y marco de pricing (target, horizonte, validación, métrica; y la
   pregunta de pricing: ingreso vs margen, control de confusores).
3. Descomposición STL para entender la serie.
4. Modelo de demanda con precio → elasticidad (regresión log-log con controles).
5. Modelo de ML (LightGBM) con features de precio + optimización de hiperparámetros.
6. Comparación fuera de muestra y validación de la curva de demanda.
7. Optimización de precio (maximizar ingreso o margen).
8. Escalado a más productos y cierre.

## Hallazgos del EDA (fase 1)

**La relación precio–cantidad existe y es clara.** En escala log-log la nube de puntos
(todas las combinaciones tienda·semana) desciende de forma limpia: a mayor precio, menor
cantidad. La pendiente de un ajuste ingenuo es de aproximadamente **−4,0**.

![Precio vs cantidad en escala log-log, con ajuste ingenuo](report/figures/01_precio_cantidad_loglog.png)

**Ese −4,0 está inflado y no es la elasticidad final.** El ajuste ingenuo no controla
nada y, sobre todo, confunde el efecto del precio con el de la promoción: los precios
bajos son casi siempre semanas de promoción, que venden más también por el cartel y el
expositor, no solo por el precio. Al colorear la nube según haya promoción se ve el
gradiente con claridad: la promoción se concentra a precios bajos (más ventas) y el
precio regular a precios altos (menos ventas). La estimación honesta de la elasticidad
se obtendrá en la fase 4, al introducir los controles, y se espera que atenúe respecto
a este valor.

![Precio vs cantidad, coloreado por promoción](report/figures/02_precio_cantidad_promo.png)

**La demanda tiene un suelo estacional suave dominado por picos promocionales
irregulares.** La serie semanal agregada está gobernada por picos agudos de una sola
semana que no siguen calendario (son promociones, no estación); la estacionalidad anual
(menos refrescos en invierno) aparece solo en el nivel base. Para pricing esto es
favorable: casi toda la variación de precio es de origen comercial, que es justo el
combustible para estimar elasticidad.

![Demanda semanal agregada y cobertura de tiendas](report/figures/03_demanda_semanal_agregada.png)

**El precio se agrupa en escalones discretos, y regular y promoción se solapan.**
Dominick's manejaba unos pocos precios de lista; las promociones empujan el precio por
debajo. Es importante que exista una franja de precios donde conviven semanas regulares
y promocionales: ese solape es lo que permitirá a la regresión separar el efecto del
precio del efecto de la promoción (sin él, ambos serían indistinguibles).

![Distribución del precio, regular vs promoción](report/figures/04_distribucion_precio.png)

**Limpieza aplicada:** se descartaron los registros marcados como poco fiables por el
proveedor (flag `OK`, ~1,4 %, casi todos con precio 0) y las observaciones con precio 0
(semanas sin venta del producto). Se conservan las variables de promoción (`SALE`),
festividad (`special`) y tienda como controles para la fase de modelado. Nota de
identificación pendiente para la fase 4: el flag `SALE` no está registrado de forma
consistente, por lo que el precio regular se reconstruirá sin depender solo de él.

## Reproducibilidad

```bash
python -m venv .venv
# Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Ejecutar los notebooks en orden numérico. El `01` produce
`data/processed/pepsi_2l.parquet`, que consumen los siguientes.

## Estado

Fase 1 (EDA y limpieza) completada. En curso: descomposición STL y modelado de la
elasticidad.

## Fuente de datos

Este trabajo utiliza datos de Dominick's Finer Foods facilitados por el **Kilts Center
for Marketing, University of Chicago Booth School of Business**. Datos para uso
académico. El mapa de semanas procede del repositorio eurostat/dff.