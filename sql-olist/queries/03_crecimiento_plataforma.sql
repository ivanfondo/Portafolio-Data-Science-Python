-- ETAPA 3

-- ¿Cómo evolucionan las ventas y cómo esto afecta al crecimiento de la plataforma?

-- -------------------
-- 3.1 Calculo de variación mensual absoluta

WITH join_cte AS (
  SELECT -- Seleccionamos las columnas que necesitamos
    a1.order_id,
    a1.order_delivered_customer_date::DATE AS fecha,
    a2.price
  FROM orders AS a1
  INNER JOIN order_items AS a2 -- Unimos orders con order_items
  ON a1.order_id = a2.order_id
  WHERE a1.order_status = 'delivered' -- Filtramos por delivered
  AND a1.order_delivered_customer_date IS NOT NULL -- Eliminamos las 8 filas nulas dentro de delivered
  AND a1.order_delivered_customer_date::DATE BETWEEN '2017-02-01' AND '2018-08-31'
),
fecha_cte AS (
  SELECT
    TO_CHAR(fecha, 'YYYY-MM') AS mes, -- Pasamos fecha a formato AÑO-MES
    SUM(price) AS ingreso
  FROM join_cte
  GROUP BY 1
),
lag_cte AS (
  SELECT
    mes,
    ingreso,
    LAG(ingreso) OVER(ORDER BY mes ASC) AS prev_month -- Aplicamos función de ventana LAG para desplazar ingresos un mes
  FROM fecha_cte
)
SELECT
  mes,
  ingreso,
  prev_month,
  ingreso - prev_month AS var_absoluto, -- Calculamos variación absoluta
  ROUND(100.0 * (ingreso - prev_month) / NULLIF(prev_month, 0), 2) AS var_percent -- Calculamos variación porcentual
FROM lag_cte
ORDER BY mes ASC;

-- Conclusión: el rango de variación va de un -20% a un 93% en todo el período evaluado. Esto nos da una idea del ruido que hay
-- entre meses, abriendo la opción a una media móvil para suavizar el ruído. El crecimiento es alto al principio y se va
-- suavizando con el paso del tiempo. Hay que ser cauteloso con la cifra de marzo 2017, ya que los datos de febrero es el
-- primer mes que alimenta la variación.

-- 3.2 Crecimiento media móvil 3 meses.
-- La media móvil nos permite analizar la variación eliminando el ruido mensual que vemos en la consulta anterior.

WITH join_cte AS (
  SELECT -- Seleccionamos las columnas que necesitamos
    a1.order_id,
    a1.order_delivered_customer_date::DATE AS fecha,
    a2.price
  FROM orders AS a1
  INNER JOIN order_items AS a2 -- Unimos orders con order_items
  ON a1.order_id = a2.order_id
  WHERE a1.order_status = 'delivered' -- Filtramos por delivered
  AND a1.order_delivered_customer_date IS NOT NULL -- Eliminamos las 8 filas nulas dentro de delivered
  AND a1.order_delivered_customer_date::DATE BETWEEN '2017-02-01' AND '2018-08-31'
),
fecha_cte AS (
  SELECT
    TO_CHAR(fecha, 'YYYY-MM') AS mes, -- Pasamos fecha a formato AÑO-MES
    SUM(price) AS ingreso
  FROM join_cte
  GROUP BY 1
),
movil_cte AS (
  SELECT
    mes,
    ingreso,
    ROW_NUMBER() OVER (ORDER BY mes) AS n_mes, -- Obtenemos el número de mes
    AVG(ingreso) OVER (ORDER BY mes ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) AS media_movil_3m -- Calculamos media móvil
  FROM fecha_cte
),
lag_cte AS (
  SELECT
    mes,
    n_mes,
    ingreso,
    media_movil_3m,
    LAG(media_movil_3m) OVER(ORDER BY mes ASC) AS prev_movil -- Función ventana para un mes
  FROM movil_cte
)
SELECT
  mes,
  ingreso,
  media_movil_3m,
  ROUND(100.0 * (media_movil_3m - prev_movil)/ NULLIF(prev_movil, 0), 2) AS var_pct_movil -- Calculamos variación porcentual
FROM lag_cte
WHERE n_mes >= 4 -- Filtramos a partir de la primera fecha que obtiene 3 meses para la media móvil.
ORDER BY mes ASC;

-- Conclusión: ahora la variación reduce su rango pasando a -10% - 40%. La redución de rango muestra como se elimina el ruido.
-- Por otro lado, solo dos medias móviles devuelven valores negativos, por tanto la variación es positiva y la tendencia
-- de crecimiento sigue al alza, pero creciendo a un dígito, por tanto se relantiza el crecimiento . 
-- Al igual que en la consulta anterior, hay que ser cauteloso, ya que se empiezan a seleccionar los datos a partir del mes de mayo.


-- 3.3 Top 10 categorías y evolución entre Q2 2017 y Q2 2018.

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
trimestre_cte AS (
  SELECT
    product_category_name AS category,
    SUM(CASE WHEN order_delivered_customer_date BETWEEN '2017-04-01' AND '2017-06-30' THEN price ELSE 0 END) AS q2_2017,
    SUM(CASE WHEN order_delivered_customer_date BETWEEN '2018-04-01' AND '2018-06-30' THEN price ELSE 0 END) AS q2_2018
  FROM join_cte
  GROUP BY 1
),
rank_cte AS (
  SELECT
    category,
    q2_2017,
    DENSE_RANK() OVER(ORDER BY q2_2017 DESC) AS rank_2017, -- Posición en Q2 2017
    q2_2018,
    DENSE_RANK() OVER(ORDER BY q2_2018 DESC) AS rank_2018 -- Posición en Q2 2018
  FROM trimestre_cte
)
SELECT
  category,
  q2_2017,
  rank_2017,
  q2_2018,
  rank_2018,
  CASE WHEN q2_2017 > 0 THEN rank_2017 - rank_2018 END AS cambio_posicion, -- Resultado positivo implica cambio de posición
  q2_2018 - q2_2017 AS diff_ingreso -- Calculamos diferencia de ingreso entre trimestres
FROM rank_cte
ORDER BY rank_2018 ASC
LIMIT 10; -- Mostramos 10 primeros valores

-- Conclusión: el top 10 es bastante estable, 8 de las 10 categorías ya estaban en el top en Q2 2017 y solo
-- dos entran (bebes, desde la 19ª, y automotivo, desde la 12ª). Dentro del grupo hay movimiento (bebes sube
-- 10 puestos, informatica_acessorios baja 4), pero ninguna de las que bajan pierde ingreso: simplemente crecen
-- menos que las demás. Cómo solo hay 2 trimestres realizando la comparación, no se puede hablar de una tendencia.
