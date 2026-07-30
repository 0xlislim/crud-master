-- Billing API database init
-- Creates the orders table used by the Billing API.
-- Safe to re-run: uses IF NOT EXISTS.

CREATE TABLE IF NOT EXISTS orders (
  id SERIAL PRIMARY KEY,
  user_id VARCHAR(255) NOT NULL,
  number_of_items INTEGER NOT NULL,
  total_amount NUMERIC NOT NULL
);