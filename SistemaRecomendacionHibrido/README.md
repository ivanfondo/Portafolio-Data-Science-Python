## SISTEMA DE RECOMENDACIÓN HÍBRIDO Y ALGORITMO APRIORI PARA INTELIGENCIA DE NEGOCIO

Uno de los principales problemas que se puede encontrar un negocio en el sector retail es buscar aumentar la fidelización de los clientes y por consiguiente las ventas. Este problema, puede ser abordado desde diferentes perspectivas, pero en esta ocasión, el planteamiento es realizar recomendaciones personalizadas a los clientes.

El sistema analiza el historial de compra de cada cliente para identificar sus patrones de consumo y, a partir de ellos, generar un listado de productos afines a sus preferencias. Estas recomendaciones se envían mediante correo electrónico con el objetivo de incentivar un mayor consumo.. La frecuencia y relevancia de las recomendaciones son clave: un exceso de comunicaciones o sugerencias poco acertadas puede resultar contraproducente y generar rechazo hacia la marca.

Hacer recomendaciones personalizadas es importante, pero tal vez no todos los clientes hagan uso de su correo electrónico. Para ello, se enfoca el problema desde otra perspectiva, la inteligencia de negocio, es decir, conocer la relación de compra entre los productos nos permite tomar decisiones estratégicas a la hora de realizar promociones o colocar productos en las tiendas, buscando crear un efecto gancho, en donde se busca generar una necesidad al cliente para que compre productos complementarios, logrando de esta manera aumentar el ticket medio.


### CONTEXTO
El problema se ha planteado para una superficie comercial, en donde el objetivo es realizar recomendaciones entre visitas. Los datos empleados han sido generados de forma sintética, por tanto nos enfrentamos a situaciones que no se dan en la realidad. Entre estas situaciones nos encontramos con datos totalmente limpios, algo que en la realidad nunca se va a dar. Los datos reales presentarían patrones menos diferenciados y más ruidosos, mientras que en este dataset sintético los perfiles de cliente están deliberadamente bien diferenciados para facilitar el aprendizaje de los modelos.

Estas situaciones se tienen muy presentes en el desarrollo de todo el ejercicio.

### DESARROLLO SISTEMA RECOMENDACIÓN 
El sistema de recomendación se plantea con dos perspectivas, que van de menor a mayor complejidad. El sistema menos complejo se basa en recomendaciones no personalizadas, en donde se desarrolla un modelo de recomendación sobre popularidad de productos. Este primer modelo nos sirve como punto de inicio y resuelve un problema, el cold start. Este problema se da cuando hay nuevos clientes que no cuentan con historial y por tanto no se pueden realizar recomendaciones personalizadas.

Para desarrollar este sistema se aplica un filtro en donde se busca hacer recomendaciones nuevas, es decir, que las recomendaciones generadas no sean productos que el cliente ya ha comprado, por tanto nos enfocamos en hacer descubrimiento de productos a los clientes.

Una vez terminado el sistema basado en popularidad, se procede a desarrollar un sistema ALS (Alternating Least Squares), que se trata de un sistema personalizado. Este algoritmo se enfoca en descubrir gustos ocultos. 
La idea central es la factorización de matrices, en donde se parte de una matriz cliente-producto, una tabla, que en entornos reales, suele estar prácticamente vacía. Esto se debe principalmente al número de productos, en donde no todos los clientes van a comprar todos los productos, sino que cada uno se va a enfocar en una serie de productos. En la matriz de este ejercicio, como el número de productos es menor, la matriz tendrá una mayor densidad. ALS se encarga de descomponer esta matriz en dos matrices más pequeñas, una de clientes y otra de productos, descritas por factores latentes. Un factor latente es una característica oculta que el modelo inventa para explicar los datos.

Para medir los resultados de los modelos, se usan como referencia las métricas Precision@K y Recall@K, siendo la precision la métrica de referencia.
- Precision@K nos indica de los K productos recomendados, que proporción de ellos ha comprado el cliente. Mide la puntería de las recomendaciones.
- Recall@K: de todo lo que compró el cliente, que proporción cubrieron las recomendaciones. Mide la cobertura.

El principal problema que presenta el Recall aquí, es que está limitado. Si trabajamos con 10 recomendaciones y el cliente ha comprado muchos más productos, el recall nunca podrá alcanzar el 100%, ya que es imposible cubrir todas sus compras con solo 10 recomendaciones. Por ello, se interpreta como métrica comparativa entre modelos más que por su valor absoluto.
Con estas métricas, se puede hacer una comparación de resultados en modelos. En este caso, el modelo ALS optimizado mediante Optuna alcanza una Precision@10 de 0.24, prácticamente el doble que el baseline de popularidad (0.12), lo que confirma que la personalización aporta valor cuando existe diferenciación entre clientes.
Partiendo del modelo basado en popularidad como base, si ALS no consigue mejorar los resultados, habría que replantearse si realmente tiene sentido hacer una implementación de ese modelo.

![Comparación de métricas entre modelo popularidad y ALS](images/comparacion_metricas.png)

Una vez se han comparado los modelos, se crea un sistema en cascada. Este sistema en cascada es lo que hace que cada modelo se active en el momento necesario, es decir, si estamos ante un cliente con historial, el modelo aplica una recomendación personalizada basada en ALS, en caso contrario, estamos ante un cliente sin historial, la recomendación se hace mediante popularidad.

Para consumir los resultados, se genera un archivo CSV, que sería cargado en el CRM que use la empresa.


### APRIORI PARA INTELIGENCIA DE NEGOCIO
El algoritmo Apriori se puede emplear como sistema recomendador, pero en el contexto en el que se sitúa este ejercicio, el enfoque se centra en entender como se relacionan los productos y buscar definir una estrategia de colocación o promoción dentro de las tiendas. El algoritmo se centra en el análisis de las cestas de compra para crear perfiles.

Para este algoritmo, no hay una métrica objetivo que sea optimizable como en ALS, al contrario, como se basa en reglas, el criterio con el que se aplican las mismas dependerá de las decisiones que la persona encargada del negocio considere mejor.
Tres métricas que se pueden observar y actúan como reglas son:
- Support: frecuencia de aparición de la combinación en las cestas. En este ejercicio se aplica un mínimo del 3%.
- Confidence: indica la confianza con la que se compran los productos. Es importante ser cauteloso con este valor, ya que una confianza del 90% no indica que los productos resulten complementarios. Alguien que compra agua puede comprar un snack con una confianza del 80% por ejemplo, pero pueden mostrar un lift de 1.05, siendo una compra meramente casual. Se indica un valor mínimo del 50%
- Lift: métrica estrella. Mide la fuerza de asociación entre productos. Lo ideal es que este valor sea superior a 1, cuanto más grande sea, más fuerte es la asocación entre productos. Si el valor es igual a 1 los productos presentan independencia total entre ellos, la relación es aleatoria. Si el valor es inferior a 1, en vez de actuar como productos complementarios, actúan como productos sustitituvos.