-- Etapa 1

-- Pregunta: ¿Qué podemos y qué no podemos responder con los datos presentes?

-- 1.1 Número de filas por tabla

SELECT
    COUNT(*) AS n_filas
FROM customers;
-- Resultado: 99.441 filas

SELECT
    COUNT(*) AS n_filas
FROM order_items;
-- Resultado: 112.650 filas

SELECT
    COUNT(*) AS n_filas
FROM order_payments;
-- Resultado: 103.886 filas

SELECT
    COUNT(*) AS n_filas
FROM order_reviews;
-- Resultado: 99.224 filas

SELECT
    COUNT(*) AS n_filas
FROM orders;
-- Resultado: 99.441 filas

SELECT
    COUNT(*) AS n_filas
FROM product_category_name_translation;
-- Resultado: 71 filas

SELECT
    COUNT(*) AS n_filas
FROM products;
-- Resultado: 32.951 filas

SELECT
    COUNT(*) AS n_filas
FROM sellers;
-- Resultado: 3.095 filas

-- --------------------------------
-- 1.2 Unicidad de claves ¿es order_id un valor único dentro de orders?
-- ¿Y las claves dentro de las tablas relacionadas con orders?

SELECT
  COUNT(*) AS n_filas,
  COUNT(DISTINCT order_id) AS order_id_unico
FROM orders;
-- Resultado: 99.441 filas y 99.441 order_id distinto
-- Conclusión: una fila = un pedido

SELECT
  COUNT(*) AS n_filas,
  COUNT(DISTINCT order_id) AS order_id_unico,
  COUNT(DISTINCT product_id) AS producto_unico, 
  COUNT(DISTINCT seller_id) AS vendedor_unico 
FROM order_items;
-- Resultado: 112.650 filas, 98.666 order_id distinto, 32.951 product_id distinto y 3.095 seller_id distinto
-- Conclusión: un pedido puede estar compuesto de varias filas
-- Hay 775 pedidos de orders (99.441 - 98.666) sin ninguna línea
-- Todos los productos y vendedores aparecen en alguna línea

SELECT
  COUNT(*) AS n_filas,
  COUNT(DISTINCT order_id) AS order_id_unico
FROM order_payments;
-- Resultado: 103.886 filas y 99.440 order_id distinto
-- Conclusión: un pedido puede tener varios pagos
-- Hay 1 pedido de orders (99.441 - 99.440) sin ningún pago.

SELECT
  COUNT(*) AS n_filas,
  COUNT(DISTINCT order_id) AS order_id_unico,
  COUNT(DISTINCT review_id) AS review_id_unico
FROM order_reviews;
-- Resultado: 99.224 filas, 98.673 order_id distinto y 98.410 review_id distinto
-- Conclusión: ni order_id ni review_id son únicos, un pedido puede tener varias reseñas.
-- Hay 768 pedidos de orders (99.441 - 98.673) sin ninguna reseña.

-- -----------------------------
-- 1.3 Rango de fechas. También se comprueba los nulos por cada columna de fecha

SELECT
  MIN(order_purchase_timestamp ::DATE) AS fecha_min, -- Extraemos solo fecha
  MAX(order_purchase_timestamp ::DATE) AS fecha_max
FROM orders;
-- Resultado: 2016-09-04 - 2018-10-17

SELECT
  order_status,  
  COUNT(*) AS n_filas,
  COUNT(order_purchase_timestamp) AS purchase,
  COUNT(order_approved_at) AS approved,
  COUNT(order_delivered_carrier_date) AS delivered_carrier,
  COUNT(order_delivered_customer_date) AS delivered_customer,
  COUNT(order_estimated_delivery_date) AS estimated
FROM orders
GROUP BY order_status;
-- Resultado: 99.441 filas; 99.441 purchase; 99.281 approved; 97.658 delivered_carrier; 
-- 96.476 delivered_customer; 99.441 estimated
-- Las categorías created, approved, invoiced, processing, unavailable y shipped tienen las fechas de las etapas que han alcanzado,
-- no hay incoherencias.
-- La categoría delivered (96.478) cuenta con 14 pedidos sin aprobación, 2 sin transportista y 8 sin fecha de entrega
-- Para calcular si los plazos de entrega se cumplen, solo usaremos el estado delivered

-- La siguiente consulta evita calcular los datos a mano.
SELECT
  COUNT(CASE WHEN order_status = 'delivered' AND order_approved_at IS NULL THEN 1 END) AS delivered_sin_aprobacion,
  COUNT(CASE WHEN order_status = 'delivered' AND order_delivered_carrier_date IS NULL THEN 1 END) AS delivered_sin_transportista,
  COUNT(CASE WHEN order_status = 'delivered' AND order_delivered_customer_date IS NULL THEN 1 END) AS delivered_sin_entrega,
  COUNT(CASE WHEN order_status = 'canceled' AND order_delivered_customer_date IS NOT NULL THEN 1 END) AS canceled_con_entrega
FROM orders;

-- --------------------------------
-- 1.4 Comprobación de nulos en tabla products y customers
SELECT
  COUNT(*) AS n_productos,
  COUNT(CASE WHEN product_category_name IS NULL THEN 1 END) AS sin_categoria
FROM products;
-- Resultado: 32.951 productos y 610 productos sin categoría

SELECT
  COUNT(*) AS n_filas,
  COUNT(DISTINCT customer_id) AS n_customer_id,
  COUNT(DISTINCT customer_unique_id) AS n_customer_unique_id
FROM customers;
-- Resultado: 99.441 filas, 99.441 customer_id distintos y 96.096 customer_unique_id distintos
-- Conclusión: customer_id se genera por pedido; la persona real es customer_unique_id,
-- así que hay 96.096 clientes distintos. Para contar clientes hay que usar customer_unique_id.