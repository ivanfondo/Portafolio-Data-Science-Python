## Ficha de datos

En esta ficha se recoge la información de la primera etapa, en donde identificamos cada tabla, cómo se relacionan entre ellas y se comprueba la calidad del dato.

| Tabla | Qué registra | Filas | Relación | Grano | Clave |
|---|---|---|---|---|---|
| `orders` | Registra los pedidos: qué cliente lo ha realizado, su estado y la fecha de cada hito del proceso. | 99.441 | `customers`, `order_items`, `order_reviews` y `order_payments` | Cada fila es un pedido; sus fechas recogen la evolución del mismo | `order_id` |
| `customers` | Registra el cliente asociado a cada pedido (ciudad y región). `customer_id` se genera por pedido: la persona real es `customer_unique_id`. | 99.441 | `orders` | Cada fila es un cliente dentro de un pedido: un `customer_id` por pedido (hay 96.096 personas distintas) | `customer_id` (para contar personas, `customer_unique_id`) |
| `order_items` | Registra cada producto vendido dentro de un pedido: producto, vendedor, precio y flete. No hay columna de cantidad: sale de contar filas. | 112.650 | `orders`, `products` y `sellers` | Cada fila es una línea de un pedido (un producto dentro del mismo pedido) | `order_id` + `order_item_id` |
| `order_payments` | Registra cada pago de un pedido: medio de pago e importe. Un pedido puede tener varios pagos; el total sale de sumarlos. | 103.886 | `orders` | Cada fila es un pago de un pedido | `order_id` + `payment_sequential` |
| `order_reviews` | Registra la reseña de un pedido: puntuación, comentario y fechas. No tiene producto: cuelga del pedido completo. | 99.224 | `orders` | Cada fila es una reseña de un pedido (un pedido puede tener varias) | `review_id` + `order_id` |
| `product_category_name_translation` | Registra la traducción al inglés de cada categoría de producto. | 71 | `products` | Cada fila es una categoría y su traducción | `product_category_name` |
| `products` | Registra el tipo de producto y sus características. | 32.951 | `order_items` y `product_category_name_translation` (lógica) | Cada fila es un producto | `product_id` |
| `sellers` | Registra los datos de cada vendedor. | 3.095 | `order_items` | Cada fila es un vendedor | `seller_id` |

## Calidad del dato

Resumen de lo comprobado en `queries/01_calidad_datos.sql`.

| Hallazgo | Cifra | Qué implica |
|---|---|---|
| Periodo de los pedidos | 2016-09-04 a 2018-10-17 | Es el periodo bruto: no garantiza un volumen uniforme a lo largo del tiempo |
| Pedidos sin ninguna línea (`order_items`) | 775 | No generan ingresos si estos se calculan desde `order_items` |
| Pedidos sin ningún pago (`order_payments`) | 1 | Caso aislado, a tener en cuenta al sumar pagos |
| Pedidos `delivered` con fechas nulas | 14 sin aprobación, 2 sin transportista y 8 sin fecha de entrega (menos del 0,02 %) | Para plazos de entrega, excluir los 8 sin fecha de entrega |
| Pedidos `canceled` con fecha de entrega | 6 | Caso a revisar: no se puede saber si es un error o una cancelación posterior a la entrega |
| Productos sin categoría | 610 (1,9 %) | Los análisis por categoría tendrán un grupo sin categoría |
| `customer_id` frente a personas | 99.441 frente a 96.096 | Para contar clientes hay que usar `customer_unique_id` |

## Preguntas de negocio que se pueden responder

- Categoría de producto más vendida
- Tiempo entre pedido y envío, comparado con el tiempo estimado
- Valor del ticket medio
- Concentración geográfica de customers y sellers
- Monto de ventas y medias móviles
