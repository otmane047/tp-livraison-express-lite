CREATE TABLE IF NOT EXISTS orders (
    order_id TEXT PRIMARY KEY,
    order_date DATE,
    hour INTEGER NOT NULL,
    day_of_week INTEGER NOT NULL,
    weekend INTEGER,
    distance_km DOUBLE PRECISION NOT NULL,
    order_value_eur DOUBLE PRECISION NOT NULL,
    weight_kg DOUBLE PRECISION NOT NULL,
    stock_available INTEGER NOT NULL,
    preparation_time_min DOUBLE PRECISION,
    carrier_capacity DOUBLE PRECISION NOT NULL,
    weather TEXT NOT NULL,
    delivery_zone TEXT NOT NULL,
    customer_type TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_orders_order_date ON orders (order_date);

