-- Etapa 5

-- ¡Cómo de eficiente es el servicio de entrega de la empresa?¿Los pedidos llegan con retraso o llegan antes de lo estimado?

-- ----------------
-- 5.1 Cálculo de porcentaje de pedidos que llegan con retraso y mediana global.


WITH filter_cte AS(
  SELECT
    order_delivered_customer_date::DATE AS delivered,  -- Fecha de entrega
    order_estimated_delivery_date::DATE AS estimated -- Fecha estimada de entrega
  FROM orders
  WHERE order_status = 'delivered' -- Solo pedidos entregados
  AND order_purchase_timestamp::DATE BETWEEN '2017-02-01' AND '2018-08-31' -- Rango de fechas
  AND order_delivered_customer_date IS NOT NULL
),
diff_cte AS (
  SELECT
    delivered - estimated AS diff_entrega -- Calculamos la diferencia de días
  FROM filter_cte
)
SELECT 
  COUNT(*) AS n_pedidos,
  COUNT(*) FILTER (WHERE diff_entrega > 0) AS con_retraso,
  ROUND(100.0 * COUNT(*) FILTER (WHERE diff_entrega > 0) / COUNT(*), 2) AS pct_retraso,
  PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY diff_entrega) AS mediana_diff,
  PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY diff_entrega) FILTER (WHERE diff_entrega > 0) AS mediana_retraso
FROM diff_cte;

-- Conclusión: para el conjunto de datos global, que abarca de febrero 2017 a agosto 2018, de un total de 95.453 pedidos, sólo llegan con
-- retraso un 6.82% de los pedidos, o dicho de otra manera, el 93% de los pedios llega a tiempo. Para saber con cuantos días de retraso 
-- llegan los pedidos, calculamos la mediana sobre los días de diferencia. Sobre el conjunto global, los pedidos llegan con 12 días de antelación
-- sobre sobre la fecha estimada. Por otro lado, si observamos la mediana de aquellos pedidos que llegan con retraso, estos tardan 7 días.
-- No podemos determinar que el servicio de mensajería sea bueno o malo, ya que la fecha estimada puede ser muy conservadora, marcando
-- de esta forma una gran diferencia.

-- -----------------------------
-- 5.2 Cálculo de porcentajes y mediana mensual.
-- A continuación vamos a realizar el cálculo de forma similar pero separando por meses.

WITH filter_cte AS(
  SELECT
    TO_CHAR(order_purchase_timestamp::DATE, 'YYYY-MM') AS fecha, -- Pasamos fecha de compra a formato YYYY-MM
    order_delivered_customer_date::DATE AS delivered,  -- Fecha de entrega
    order_estimated_delivery_date::DATE AS estimated -- Fecha estimada de entrega
  FROM orders
  WHERE order_status = 'delivered' -- Solo pedidos entregados
  AND order_purchase_timestamp::DATE BETWEEN '2017-02-01' AND '2018-08-31' -- Rango de fechas
  AND order_delivered_customer_date IS NOT NULL
),
diff_cte AS (
  SELECT
    fecha,
    (delivered - estimated) AS diff_entrega -- Calculamos la diferencia de días
  FROM filter_cte
)
SELECT
  fecha,
  COUNT(*) AS n_pedidos,
  COUNT(*) FILTER (WHERE diff_entrega > 0) AS con_retraso,
  ROUND(100.0 * COUNT(*) FILTER (WHERE diff_entrega > 0) / COUNT(*), 2) AS pct_retraso,
  PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY diff_entrega) AS mediana_diff,
  PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY diff_entrega) FILTER (WHERE diff_entrega > 0) AS mediana_retraso
FROM diff_cte
GROUP BY fecha
ORDER BY fecha ASC;

-- Conclusión: salvando 3 meses que muestran más de un 10% de retraso, el resto de meses mantienen un porcentaje de retraso bastante bajo,
-- generalmente inferior al global de 6.82%. Importante destacar esos 3 meses con porcentajes de retraso elevado, llegando a rozar casi el 20%
-- algún mes. Con estos datos no podemos determinar que causa el retraso de entrega.
-- Si observamos la mediana de la diferencia, esta es negativa todos los meses, es decir, el pedido mediano llega antes de 
-- lo estimado. Si por el contrario filtramos, la mediana de los días con retraso se encuentra habitualmente entre 5 y 8 días.