-- Consulta inicial para crear las diferentes tablas que componen el ejercicio
-- En esta fase solo se crean tablas y se visualiza la relación entre ellas para crear las PK y FK

create table product_category_name_translation (
  product_category_name text,
  product_category_name_english text
);

create table customers (
  customer_id text,
  customer_unique_id text,
  customer_zip_code_prefix text,
  customer_city text,
  customer_state text
);

create table sellers (
  seller_id text,
  seller_zip_code_prefix text,
  seller_city text,
  seller_state text
);

create table products (
  product_id text,
  product_category_name text,
  product_name_lenght int,
  product_description_lenght int,
  product_photos_qty int,
  product_weight_g int,
  product_length_cm int,
  product_height_cm int,
  product_width_cm int
);

create table orders (
  order_id text,
  customer_id text,
  order_status text,
  order_purchase_timestamp timestamp,
  order_approved_at timestamp,
  order_delivered_carrier_date timestamp,
  order_delivered_customer_date timestamp,
  order_estimated_delivery_date timestamp
);

create table order_items (
  order_id text,
  order_item_id int,
  product_id text,
  seller_id text,
  shipping_limit_date timestamp,
  price numeric(10,2),
  freight_value numeric(10,2)
);

create table order_payments (
  order_id text,
  payment_sequential int,
  payment_type text,
  payment_installments int,
  payment_value numeric(10,2)
);

create table order_reviews (
  review_id text,
  order_id text,
  review_score int,
  review_comment_title text,
  review_comment_message text,
  review_creation_date timestamp,
  review_answer_timestamp timestamp
);