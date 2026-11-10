-- ETAPA 4 

-- ¿Los clientes vuelven?

-- ----------------
-- 4.1 Cálculo porcentaje de clientes que vuelven

WITH join_cte AS (
  SELECT
    a1.order_id,
    a1.order_purchase_timestamp::DATE AS purchase, -- Selecionamos fecha de compra
    a3.customer_unique_id AS customer,
    a2.price
  FROM orders AS a1 -- Unimos las tablas
  INNER JOIN order_items AS a2
  ON a1.order_id = a2.order_id
  INNER JOIN customers AS a3
  ON a1.customer_id = a3.customer_id
  WHERE a1.order_status = 'delivered' -- Aplicamos filtros
  AND a1.order_purchase_timestamp IS NOT NULL
  AND a1.order_purchase_timestamp::DATE BETWEEN '2018-03-01' AND '2018-08-31' -- Filtro de fecha 
),
grupos_cte AS (
  SELECT
    customer,
    MAX(CASE WHEN purchase BETWEEN '2018-03-01' AND '2018-05-31' THEN 1 ELSE 0 END) AS base, -- Seleccionamos valor máximo de cada cliente en período marcado.
    MAX(CASE WHEN purchase BETWEEN '2018-06-01' AND '2018-08-31' THEN 1 ELSE 0 END) AS vuelve -- Si 1, vuelve a comprar.
  FROM join_cte
  GROUP BY customer -- Agrupamos por cliente
)
SELECT
  SUM(base) AS clientes_base,
  SUM(base * vuelve) AS clientes_que_vuelven, -- Solo los que tienen las dos marcas
  ROUND(100.0 * SUM(base * vuelve) / NULLIF(SUM(base), 0), 2) AS pct_vuelve
FROM grupos_cte;

-- Conclusión: de los 20.254 clientes que compraron en marzo - mayo 2018, solo 157 (0,78 %) vuelven a comprar
-- en junio - agosto, es decir, casi nadie repite en los tres meses siguientes. Esto muestra que el negocio
-- depende sobre todo de clientes nuevos y no de clientes que vuelven a comprar.
-- Con una ventana comparativa de 3 meses no se puede extrapolar estos datos, por tanto hay que ser cautelosos.
-- Antes de decidir entre captar clientes nuevos o fomentar la recompra, haría falta tener una muestra de datos más grande.