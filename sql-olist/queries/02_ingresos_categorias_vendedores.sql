-- ETAPA 2
-- ¿Qué categorías y vendedores generan más ingresos a lo largo del período?

-- --------------------------
-- 2.1 Cómo evolucionan las categorías a lo largo del período
-- Realizamos una consulta inicial para ver el número de pedidos por mes y evaluar la consistencia.

SELECT
  TO_CHAR(a1.order_delivered_customer_date::DATE, 'YYYY-MM') AS mes,
  COUNT(DISTINCT a1.order_id) AS pedidos,
  ROUND(SUM(a2.price)) AS ingreso,
  COUNT(DISTINCT a1.order_delivered_customer_date::DATE) AS dias_con_entregas
FROM orders AS a1
INNER JOIN order_items AS a2
  ON a1.order_id = a2.order_id
WHERE a1.order_status = 'delivered'
  AND a1.order_delivered_customer_date IS NOT NULL
GROUP BY 1
ORDER BY 1;

-- La consulta devuelve que Septiembre 2018 tiene datos cortados, con solo 56 pedidos ese mes, rompiendo la tendencia de los meses anteriores.
-- Esta situación nos lleva a eliminar Q3 2018 del análisis siguiente. Los meses de Julio y Agosto 2018 se van a comparar por separado
-- con los del año 2017.

WITH join_cte AS (
  SELECT -- Seleccionamos las columnas que necesitamos
    a1.order_id,
    a1.order_delivered_customer_date::DATE,
    a2.price,
    COALESCE(a3.product_category_name, 'Sin categoria') AS product_category_name -- Cambiamos resultados NULL a valor Sin categoria
  FROM orders AS a1
  INNER JOIN order_items AS a2 -- Unimos orders con order_items
  ON a1.order_id = a2.order_id
  INNER JOIN products AS a3 -- Unimos order_items con products
  ON a2.product_id = a3.product_id
  WHERE a1.order_status = 'delivered' -- Filtramos por delivered
  AND a1.order_delivered_customer_date IS NOT NULL) -- Eliminamos las 8 filas nulas dentro de delivered

-- Una vez filtrados los datos mediante CTE se procede a realizar las agregaciones mediante el uso de CASE para separar los datos trimestralmente

SELECT
  product_category_name AS product,
  SUM(CASE WHEN order_delivered_customer_date BETWEEN '2017-01-01' AND '2017-03-31' THEN price ELSE 0 END) AS q1_2017,
  SUM(CASE WHEN order_delivered_customer_date BETWEEN '2017-04-01' AND '2017-06-30' THEN price ELSE 0 END) AS q2_2017,
  SUM(CASE WHEN order_delivered_customer_date BETWEEN '2017-07-01' AND '2017-09-30' THEN price ELSE 0 END) AS q3_2017,
  SUM(CASE WHEN order_delivered_customer_date BETWEEN '2017-10-01' AND '2017-12-31' THEN price ELSE 0 END) AS q4_2017,
  SUM(CASE WHEN order_delivered_customer_date BETWEEN '2018-01-01' AND '2018-03-31' THEN price ELSE 0 END) AS q1_2018,
  SUM(CASE WHEN order_delivered_customer_date BETWEEN '2018-04-01' AND '2018-06-30' THEN price ELSE 0 END) AS q2_2018
FROM join_cte
GROUP BY 1
ORDER BY 8 DESC;

-- Las cifras en valor absoluto muestran en general que las ventas crecen trimestre a trimestre. La mejor forma de consumir este resultado
-- es mediante un gráfico de líneas. A continuación vamos a obtener el mismo resultado en porcentaje, que será más fácil de ver el comportamiento
-- dentro de SQL.

-- A continuación hacemos la comparación en porcentajes.

WITH join_cte AS (
  SELECT -- Seleccionamos las columnas que necesitamos
    a1.order_id,
    a1.order_delivered_customer_date::DATE,
    a2.price,
    COALESCE(a3.product_category_name, 'Sin categoria') AS product_category_name -- Cambiamos resultados NULL a valor Sin categoria
  FROM orders AS a1
  INNER JOIN order_items AS a2 -- Unimos orders con order_items
  ON a1.order_id = a2.order_id
  INNER JOIN products AS a3 -- Unimos order_items con products
  ON a2.product_id = a3.product_id
  WHERE a1.order_status = 'delivered' -- Filtramos por delivered
  AND a1.order_delivered_customer_date IS NOT NULL -- Eliminamos las 8 filas nulas dentro de delivered
  ), 
trimestres_cte AS ( -- Segunda CTE para generar absolutos de trimestres
  SELECT
    product_category_name AS product,
    SUM(CASE WHEN order_delivered_customer_date BETWEEN '2017-01-01' AND '2017-03-31' THEN price ELSE 0 END) AS q1_2017,
    SUM(CASE WHEN order_delivered_customer_date BETWEEN '2017-04-01' AND '2017-06-30' THEN price ELSE 0 END) AS q2_2017,
    SUM(CASE WHEN order_delivered_customer_date BETWEEN '2017-07-01' AND '2017-09-30' THEN price ELSE 0 END) AS q3_2017,
    SUM(CASE WHEN order_delivered_customer_date BETWEEN '2017-10-01' AND '2017-12-31' THEN price ELSE 0 END) AS q4_2017,
    SUM(CASE WHEN order_delivered_customer_date BETWEEN '2018-01-01' AND '2018-03-31' THEN price ELSE 0 END) AS q1_2018,
    SUM(CASE WHEN order_delivered_customer_date BETWEEN '2018-04-01' AND '2018-06-30' THEN price ELSE 0 END) AS q2_2018
  FROM join_cte
  GROUP BY 1)
  
SELECT
  product, 
  ROUND(100.0 * (q2_2017 - q1_2017)/ NULLIF(q1_2017, 0), 1) AS pct_q1_q2_17, -- Para evitar errores aplicamos NULLIF si el denominador es 0
  ROUND(100.0 * (q3_2017 - q2_2017)/ NULLIF(q2_2017, 0), 1) AS pct_q2_q3_17,
  ROUND(100.0 * (q4_2017 - q3_2017)/ NULLIF(q3_2017, 0), 1) AS pct_q3_q4_17,
  ROUND(100.0 * (q1_2018 - q4_2017)/ NULLIF(q4_2017, 0), 1) AS pct_q4_q1_17_18,
  ROUND(100.0 * (q2_2018 - q1_2018)/NULLIF(q1_2018, 0), 1) AS pct_q1_q2_18
FROM trimestres_cte
WHERE q2_2018 >= 5000 -- linea opcional para eliminar valores pequeños
ORDER BY q2_2018 DESC NULLS LAST; -- Ordenamos por valor de ventas absolutas en Q2_2018

-- Conclusión (filtro: categorías con al menos 5.000 de ingreso en Q2 2018; son 47 de las 74):
-- 10 categorías reducen su ingreso en Q2 2018 respecto a Q1, entre un -1,6 % y un -63 %. Entre las de más volumen
-- están informatica_acessorios (-23,2 %) y esporte_lazer (-10,3 %).
-- Al filtrar por Q2 2018 quedan fuera categorías que cayeron por debajo de 5.000, así que el número de las que bajan es un mínimo.

-- --------------
-- 2.2 Comparación Julio y Agosto 2017-2018

WITH join_cte AS (
  SELECT -- Seleccionamos las columnas que necesitamos
    a1.order_id,
    a1.order_delivered_customer_date::DATE,
    a2.price,
    COALESCE(a3.product_category_name, 'Sin categoria') AS product_category_name -- Cambiamos resultados NULL a valor Sin categoria
  FROM orders AS a1
  INNER JOIN order_items AS a2 -- Unimos orders con order_items
  ON a1.order_id = a2.order_id
  INNER JOIN products AS a3 -- Unimos order_items con products
  ON a2.product_id = a3.product_id
  WHERE a1.order_status = 'delivered' -- Filtramos por delivered
  AND a1.order_delivered_customer_date IS NOT NULL -- Eliminamos las 8 filas nulas dentro de delivered
  ),

meses_cte AS (
  SELECT
    product_category_name,
    SUM(CASE WHEN order_delivered_customer_date BETWEEN '2017-07-01' AND '2017-07-31' THEN price ELSE 0 END) AS jul_17,
    SUM(CASE WHEN order_delivered_customer_date BETWEEN '2017-08-01' AND '2017-08-31' THEN price ELSE 0 END) AS aug_17,
    SUM(CASE WHEN order_delivered_customer_date BETWEEN '2018-07-01' AND '2018-07-31' THEN price ELSE 0 END) AS jul_18,
    SUM(CASE WHEN order_delivered_customer_date BETWEEN '2018-08-01' AND '2018-08-31' THEN price ELSE 0 END) AS aug_18
  FROM join_cte
  GROUP BY 1
)

SELECT
  product_category_name,
  ROUND(100.0 * (jul_18 - jul_17)/ NULLIF(jul_17, 0), 1) AS pct_jul_17_18,
  ROUND(100.0 * (aug_18 - aug_17)/ NULLIF(aug_17, 0), 1) AS pct_aug_17_18
FROM meses_cte
ORDER BY jul_17 DESC;

-- 2.3 Crecimiento de la plataforma (todas las categorías, sin filtro de umbral)
-- Mismas columnas que las consultas de categorías de 2.1 y 2.2, para compararlas directamente

WITH join_cte AS (
  SELECT
    a1.order_delivered_customer_date::DATE AS order_delivered_customer_date,
    a2.price
  FROM orders AS a1
  INNER JOIN order_items AS a2
    ON a1.order_id = a2.order_id
  WHERE a1.order_status = 'delivered'
    AND a1.order_delivered_customer_date IS NOT NULL
),
plataforma_cte AS (
  SELECT
    SUM(CASE WHEN order_delivered_customer_date BETWEEN '2017-01-01' AND '2017-03-31' THEN price ELSE 0 END) AS q1_2017,
    SUM(CASE WHEN order_delivered_customer_date BETWEEN '2017-04-01' AND '2017-06-30' THEN price ELSE 0 END) AS q2_2017,
    SUM(CASE WHEN order_delivered_customer_date BETWEEN '2017-07-01' AND '2017-09-30' THEN price ELSE 0 END) AS q3_2017,
    SUM(CASE WHEN order_delivered_customer_date BETWEEN '2017-10-01' AND '2017-12-31' THEN price ELSE 0 END) AS q4_2017,
    SUM(CASE WHEN order_delivered_customer_date BETWEEN '2018-01-01' AND '2018-03-31' THEN price ELSE 0 END) AS q1_2018,
    SUM(CASE WHEN order_delivered_customer_date BETWEEN '2018-04-01' AND '2018-06-30' THEN price ELSE 0 END) AS q2_2018,
    SUM(CASE WHEN order_delivered_customer_date BETWEEN '2017-07-01' AND '2017-07-31' THEN price ELSE 0 END) AS jul_17,
    SUM(CASE WHEN order_delivered_customer_date BETWEEN '2017-08-01' AND '2017-08-31' THEN price ELSE 0 END) AS aug_17,
    SUM(CASE WHEN order_delivered_customer_date BETWEEN '2018-07-01' AND '2018-07-31' THEN price ELSE 0 END) AS jul_18,
    SUM(CASE WHEN order_delivered_customer_date BETWEEN '2018-08-01' AND '2018-08-31' THEN price ELSE 0 END) AS aug_18
  FROM join_cte
)
SELECT
  ROUND(100.0 * (q2_2017 - q1_2017) / NULLIF(q1_2017, 0), 1) AS pct_q1_q2_17,
  ROUND(100.0 * (q3_2017 - q2_2017) / NULLIF(q2_2017, 0), 1) AS pct_q2_q3_17,
  ROUND(100.0 * (q4_2017 - q3_2017) / NULLIF(q3_2017, 0), 1) AS pct_q3_q4_17,
  ROUND(100.0 * (q1_2018 - q4_2017) / NULLIF(q4_2017, 0), 1) AS pct_q4_q1_17_18,
  ROUND(100.0 * (q2_2018 - q1_2018) / NULLIF(q1_2018, 0), 1) AS pct_q1_q2_18,
  ROUND(100.0 * (jul_18 - jul_17) / NULLIF(jul_17, 0), 1) AS pct_jul_17_18,
  ROUND(100.0 * (aug_18 - aug_17) / NULLIF(aug_17, 0), 1) AS pct_aug_17_18
FROM plataforma_cte;

-- Conclusión: la plataforma crece a lo largo del tiempo, pero a medida que pasa el tiempo crece menos a nivel general. Por el contrario
-- si comparamos los meses de julio y agosto, los que quedan sueltos, de un año a otro crecen. En la consulta previa se puede ver el crecimiento
-- por categoría.

