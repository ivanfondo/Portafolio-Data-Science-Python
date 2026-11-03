-- Consulta para crear relaciones entre las tablas

-- Claves primarias
ALTER TABLE customers ADD CONSTRAINT pk_customers PRIMARY KEY (customer_id);
ALTER TABLE sellers ADD CONSTRAINT pk_sellers PRIMARY KEY (seller_id);
ALTER TABLE products ADD CONSTRAINT pk_products PRIMARY KEY (product_id);
ALTER TABLE product_category_name_translation ADD CONSTRAINT pk_category_translation PRIMARY KEY (product_category_name);
ALTER TABLE orders ADD CONSTRAINT pk_orders PRIMARY KEY (order_id);
ALTER TABLE order_items ADD CONSTRAINT pk_order_items PRIMARY KEY (order_id, order_item_id);
ALTER TABLE order_payments ADD CONSTRAINT pk_order_payments PRIMARY KEY (order_id, payment_sequential);
-- review_id solo NO es único (se repite entre pedidos): la clave es compuesta.
ALTER TABLE order_reviews ADD CONSTRAINT pk_order_reviews PRIMARY KEY (review_id, order_id);

-- Claves foráneas
ALTER TABLE orders ADD CONSTRAINT fk_orders_customer FOREIGN KEY (customer_id) REFERENCES customers (customer_id);
ALTER TABLE order_items ADD CONSTRAINT fk_order_items_order FOREIGN KEY (order_id) REFERENCES orders (order_id);
ALTER TABLE order_items ADD CONSTRAINT fk_order_items_product FOREIGN KEY (product_id) REFERENCES products (product_id);
ALTER TABLE order_items ADD CONSTRAINT fk_order_items_seller FOREIGN KEY (seller_id) REFERENCES sellers (seller_id);
ALTER TABLE order_payments ADD CONSTRAINT fk_order_payments_order FOREIGN KEY (order_id) REFERENCES orders (order_id);
ALTER TABLE order_reviews ADD CONSTRAINT fk_order_reviews_order FOREIGN KEY (order_id) REFERENCES orders (order_id);
