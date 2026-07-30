-- Inventory API database init
-- Creates the movies table used by the Inventory API.
-- Safe to re-run: uses IF NOT EXISTS.

CREATE TABLE IF NOT EXISTS movies (
  id SERIAL PRIMARY KEY,
  title VARCHAR(255) NOT NULL,
  description TEXT
);