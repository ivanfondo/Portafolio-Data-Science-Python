## Decisiones metodológicas

Como ya se comprobó en la Etapa 1, no es posible usar la totalidad de los datos. Por eso se toman varias decisiones para la Etapa 2, en la que se mide el crecimiento de las categorías y los vendedores a lo largo del periodo de análisis disponible.

### 1. Qué se mide como ingreso

- Se usa únicamente el precio de venta (`price`).
- No se tienen en cuenta los cargos de flete (`freight_value`).

### 2. Cómo se agrupa el tiempo

- Los datos se agrupan en trimestres.
- Así se pueden diferenciar periodos más marcados y comparar su evolución.
- Se emplea la columna `order_delivered_customer_date` para separar por trimestres, porque el ingreso se cuenta cuando el pedido llega al cliente.
- Se eliminan los 8 registros `delivered` que tienen esa fecha nula (menos del 0,02 %).

### 3. Qué pedidos cuentan como venta

- Los pedidos están en distintos estados (ver `ficha_datos.md`).
- Solo se usan para la medición los pedidos entregados, es decir, con estado `delivered`.
- Motivo: es el único estado en el que el ingreso se ha realizado. Quedan fuera los pedidos cancelados, no disponibles y los que aún están en curso.

### 4. Cómo se mide el crecimiento

- Valor absoluto (diferencia entre trimestres).
- Porcentaje de variación entre trimestres consecutivos.
- Para julio y agosto, porcentaje de variación frente al mismo mes de 2017.

### 5. Manejo de nulos en categorías

- Se aplica un `COALESCE` para asignar el valor `Sin categoria` a los 610 productos sin categoría.

### 6. Periodo de análisis

- Se analiza del primer trimestre de 2017 al segundo de 2018.
- Se excluyen septiembre y octubre de 2018: solo tienen 56 y 3 pedidos entregados, frente a entre 5.800 y 8.300 en un mes normal. Los datos están cortados.
- `q4_2016` (267 pedidos) solo se muestra como contexto y no entra en ninguna comparación.

### 7. Julio y agosto de 2018

- No se agrupan como trimestre, porque el tercer trimestre está incompleto.
- Se comparan por separado con julio y agosto de 2017, para no perder la información más reciente.

### 8. Umbral mínimo de ingreso

- En la comparación por trimestres, solo se incluyen categorías con al menos 5.000 de ingreso en Q2 2018.
- En la comparación de julio y agosto no se aplica umbral.
- Motivo: sin umbral, las categorías pequeñas dan porcentajes enormes sin significado.
- Limitación: filtrar por Q2 2018 deja fuera categorías que cayeron por debajo del umbral, así que el número de las que bajan es un mínimo.

### 9. Referencia de la plataforma

- Los porcentajes de cada categoría se leen frente al crecimiento del ingreso total en el mismo periodo.
- Motivo: una categoría que crece menos que la plataforma pierde peso aunque crezca.

### 10. Estacionalidad

- Las subidas del cuarto trimestre de 2017 se consideran estacionales (noviembre) y no un cambio de tendencia.

### 11. Análisis de vendedores

- Como los datos están anonimizados y no se sabe quién es cada vendedor, se analizan en conjunto y no por nombre, con el porcentaje de ventas de Q2 de 2017 y 2018.
- Se usan esos trimestres concretamente para evitar la estacionalidad.
- Para medir la concentración, se cuenta cuántos vendedores hacen falta para llegar al 20 % del ingreso.
- El resultado se da en bruto y como porcentaje de vendedores activos, ya que el número de vendedores se más que duplica de un trimestre a otro (de 779 a 1.676).
