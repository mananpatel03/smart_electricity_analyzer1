-- ========================================================
-- Smart Electricity Bill & Energy Waste Analyzer (VoltWise)
-- Standard SQL Database Schema (Compatible with PostgreSQL / MySQL / SQLite)
-- ========================================================

-- 1. Users Table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(150) UNIQUE,
    password_hash VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Tariffs Table
CREATE TABLE IF NOT EXISTS tariffs (
    id SERIAL PRIMARY KEY,
    user_id INT DEFAULT 1,
    name VARCHAR(100) NOT NULL,
    rate_type VARCHAR(20) DEFAULT 'slab',
    flat_rate NUMERIC(8,2) DEFAULT 7.00,
    fixed_charge NUMERIC(8,2) DEFAULT 60.00,
    tax_percent NUMERIC(5,2) DEFAULT 6.00,
    slab_json TEXT,
    is_default INT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Appliances Table
CREATE TABLE IF NOT EXISTS appliances (
    id SERIAL PRIMARY KEY,
    user_id INT DEFAULT 1,
    name VARCHAR(150) NOT NULL,
    category VARCHAR(50) DEFAULT 'General',
    power_watts NUMERIC(8,2) NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    hours_per_day NUMERIC(5,2) NOT NULL,
    days_per_month INT NOT NULL DEFAULT 30,
    standby_watts NUMERIC(6,2) DEFAULT 0.00,
    standby_hours NUMERIC(5,2) DEFAULT 0.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Bill Records Table (History)
CREATE TABLE IF NOT EXISTS bill_records (
    id SERIAL PRIMARY KEY,
    user_id INT DEFAULT 1,
    billing_period VARCHAR(50) NOT NULL,
    prev_reading NUMERIC(10,2) DEFAULT 0.00,
    curr_reading NUMERIC(10,2) DEFAULT 0.00,
    units_consumed NUMERIC(10,2) NOT NULL,
    tariff_rate NUMERIC(8,2) NOT NULL,
    fixed_charge NUMERIC(8,2) DEFAULT 0.00,
    tax_amount NUMERIC(8,2) DEFAULT 0.00,
    estimated_amount NUMERIC(10,2) NOT NULL,
    actual_amount NUMERIC(10,2),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. Saving Scenarios Table
CREATE TABLE IF NOT EXISTS saving_scenarios (
    id SERIAL PRIMARY KEY,
    user_id INT DEFAULT 1,
    scenario_name VARCHAR(150) NOT NULL,
    details_json TEXT,
    monthly_saved_kwh NUMERIC(8,2) NOT NULL,
    monthly_saved_cost NUMERIC(10,2) NOT NULL,
    yearly_saved_cost NUMERIC(10,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ========================================================
-- Seed Initial Demo Data
-- ========================================================

-- Seed User
INSERT INTO users (username, email, password_hash)
VALUES ('demo_user', 'demo@energyanalyzer.local', 'demo_hash')
ON CONFLICT (username) DO NOTHING;

-- Seed Default Tariff (Progressive Tiered Slabs)
INSERT INTO tariffs (user_id, name, rate_type, flat_rate, fixed_charge, tax_percent, slab_json, is_default)
VALUES (
    1,
    'Standard Domestic (Tiered Slabs)',
    'slab',
    7.00,
    60.00,
    6.00,
    '[{"from": 0, "to": 100, "rate": 3.75}, {"from": 101, "to": 300, "rate": 6.50}, {"from": 301, "to": 500, "rate": 8.75}, {"from": 501, "to": 999999, "rate": 11.20}]',
    1
);

-- Seed Realistic Household Appliances
INSERT INTO appliances (user_id, name, category, power_watts, quantity, hours_per_day, days_per_month, standby_watts, standby_hours) VALUES
(1, 'Inverter Air Conditioner 1.5T', 'Cooling', 1200.0, 1, 6.0, 30, 2.0, 18.0),
(1, 'Ceiling Fan', 'Cooling', 75.0, 3, 10.0, 30, 0.0, 0.0),
(1, 'Double-Door Refrigerator', 'Kitchen', 180.0, 1, 24.0, 30, 0.0, 0.0),
(1, 'LED Room Bulbs', 'Lighting', 9.0, 6, 6.0, 30, 0.0, 0.0),
(1, 'Desktop PC / Monitor', 'Computing', 220.0, 1, 5.0, 30, 5.0, 19.0),
(1, 'Smart LED TV 43"', 'Entertainment', 80.0, 1, 4.0, 30, 3.0, 20.0),
(1, 'Water Geyser / Heater', 'Heating', 2000.0, 1, 0.75, 30, 0.0, 0.0),
(1, 'Washing Machine', 'Laundry', 500.0, 1, 0.8, 20, 1.0, 23.0);

-- Seed Past Historical Bill Records
INSERT INTO bill_records (user_id, billing_period, prev_reading, curr_reading, units_consumed, tariff_rate, fixed_charge, tax_amount, estimated_amount, actual_amount, notes) VALUES
(1, 'May 2026', 1420.0, 1780.0, 360.0, 7.0, 60.0, 151.2, 2731.2, 2810.0, 'Hot summer month, high AC use'),
(1, 'Jun 2026', 1780.0, 2195.0, 415.0, 7.0, 60.0, 174.3, 3139.3, 3190.0, 'Peak summer billing'),
(1, 'Jul 2026', 2195.0, 2520.0, 325.0, 7.0, 60.0, 136.5, 2471.5, 2450.0, 'Monsoon cooling'),
(1, 'Aug 2026', 2520.0, 2815.0, 295.0, 7.0, 60.0, 123.9, 2248.9, 2290.0, 'Moderate usage'),
(1, 'Sep 2026', 2815.0, 3090.0, 275.0, 7.0, 60.0, 115.5, 2100.5, 2080.0, 'Optimized fan and AC hours'),
(1, 'Oct 2026', 3090.0, 3350.0, 260.0, 7.0, 60.0, 109.2, 1989.2, 1970.0, 'Mild weather, consistent savings');
