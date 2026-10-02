-- Sample database for local testing only. The app itself does NOT depend on it.
CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    city VARCHAR(80),
    created_at DATE NOT NULL DEFAULT CURRENT_DATE
);

CREATE TABLE employees (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    department VARCHAR(60) NOT NULL,
    salary NUMERIC(10,2) NOT NULL,
    hired_at DATE NOT NULL,
    manager_id INTEGER REFERENCES employees(id)
);

CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    category VARCHAR(60) NOT NULL,
    price NUMERIC(10,2) NOT NULL,
    stock INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    employee_id INTEGER REFERENCES employees(id),
    order_date DATE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending'
);

CREATE TABLE order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(id),
    product_id INTEGER NOT NULL REFERENCES products(id),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(10,2) NOT NULL
);

CREATE INDEX idx_orders_customer ON orders(customer_id);
CREATE INDEX idx_orders_date ON orders(order_date);
CREATE INDEX idx_items_order ON order_items(order_id);

INSERT INTO employees (name, department, salary, hired_at, manager_id) VALUES
 ('Asha Verma','Sales',92000,'2019-03-11',NULL),
 ('Rohan Mehta','Sales',64000,'2021-07-01',1),
 ('Priya Nair','Support',52000,'2022-01-15',1),
 ('Karan Singh','Engineering',118000,'2018-09-20',NULL),
 ('Meera Iyer','Engineering',99000,'2020-11-02',4);

INSERT INTO customers (name, email, city, created_at)
SELECT 'Customer ' || g, 'customer' || g || '@example.com',
       (ARRAY['Chandigarh','Delhi','Mumbai','Pune','Bengaluru','Chennai'])[1 + g % 6],
       CURRENT_DATE - (g * 9 % 400)
FROM generate_series(1, 60) g;

INSERT INTO products (name, category, price, stock) VALUES
 ('Laptop Pro 14','Electronics',1299.00,40),('Wireless Mouse','Electronics',25.50,300),
 ('Mechanical Keyboard','Electronics',89.99,120),('Standing Desk','Furniture',420.00,25),
 ('Ergonomic Chair','Furniture',310.00,30),('Notebook Pack','Stationery',12.75,500),
 ('Gel Pens (10)','Stationery',8.99,800),('Monitor 27"','Electronics',349.00,60);

INSERT INTO orders (customer_id, employee_id, order_date, status)
SELECT 1 + g % 60, 1 + g % 3, CURRENT_DATE - (g * 3 % 120),
       (ARRAY['completed','completed','pending','shipped','cancelled'])[1 + g % 5]
FROM generate_series(1, 200) g;

INSERT INTO order_items (order_id, product_id, quantity, unit_price)
SELECT o.id, 1 + (o.id * k) % 8, 1 + (o.id + k) % 4,
       (SELECT price FROM products WHERE id = 1 + (o.id * k) % 8)
FROM orders o, generate_series(1, 3) k;
