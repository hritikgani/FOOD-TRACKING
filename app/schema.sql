CREATE TABLE IF NOT EXISTS restaurants (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    normalized_name TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    updated_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS cuisines (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    order_date TEXT NOT NULL,
    order_time TEXT,
    platform TEXT NOT NULL CHECK (platform IN ('zomato', 'swiggy')),
    restaurant_id INTEGER NOT NULL REFERENCES restaurants(id),
    cuisine_id INTEGER REFERENCES cuisines(id),
    subtotal REAL,
    discount REAL,
    delivery_fee REAL,
    platform_fee REAL,
    tax REAL,
    total_amount REAL NOT NULL,
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    updated_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    item_name TEXT NOT NULL,
    normalized_item_name TEXT NOT NULL,
    quantity INTEGER DEFAULT 1,
    unit_price REAL,
    total_price REAL
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);

-- CSV/XLSX import is a multi-request flow (upload -> map -> preview ->
-- confirm). On serverless (Vercel) each request can land on a different,
-- disposable container, so the in-progress session can't live on local
-- disk -- it has to be in the database like everything else.
CREATE TABLE IF NOT EXISTS import_sessions (
    id TEXT PRIMARY KEY,
    payload JSONB NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_orders_date ON orders(order_date);
CREATE INDEX IF NOT EXISTS idx_orders_restaurant ON orders(restaurant_id);
CREATE INDEX IF NOT EXISTS idx_orders_cuisine ON orders(cuisine_id);
CREATE INDEX IF NOT EXISTS idx_orders_platform ON orders(platform);
CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_norm_name ON order_items(normalized_item_name);
