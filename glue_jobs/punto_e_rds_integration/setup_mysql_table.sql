-- MySQL Setup Script for News Database
-- Run this script in your RDS MySQL instance before deploying the Glue jobs

-- Create database if it doesn't exist
CREATE DATABASE IF NOT EXISTS news;
USE news;

-- Create the noticias table with proper schema
CREATE TABLE IF NOT EXISTS noticias (
    id INT AUTO_INCREMENT PRIMARY KEY,
    fecha DATE NOT NULL,
    categoria VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
    titular TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
    enlace TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
    periodico VARCHAR(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- Indexes for better query performance
    INDEX idx_fecha (fecha),
    INDEX idx_periodico (periodico),
    INDEX idx_categoria (categoria),
    INDEX idx_fecha_periodico (fecha, periodico),
    
    -- Unique constraint to prevent duplicates
    UNIQUE KEY unique_news (fecha, titular(500), periodico)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Create a view for easier querying
CREATE OR REPLACE VIEW news_summary AS
SELECT 
    DATE(fecha) as date,
    periodico as newspaper,
    categoria as category,
    COUNT(*) as total_articles,
    MIN(created_at) as first_added,
    MAX(created_at) as last_added
FROM noticias 
GROUP BY DATE(fecha), periodico, categoria
ORDER BY fecha DESC, periodico, categoria;

-- Create a view for recent news
CREATE OR REPLACE VIEW recent_news AS
SELECT 
    id,
    fecha,
    categoria,
    LEFT(titular, 100) as titulo_corto,
    periodico,
    created_at
FROM noticias 
WHERE fecha >= DATE_SUB(CURDATE(), INTERVAL 7 DAYS)
ORDER BY fecha DESC, created_at DESC;

-- Show table structure
DESCRIBE noticias;

-- Show sample queries
SELECT 'Table created successfully. Sample queries:' as status;

-- Count articles by newspaper
SELECT 
    periodico,
    COUNT(*) as total_articles 
FROM noticias 
GROUP BY periodico;

-- Articles by date (last 7 days)
SELECT 
    fecha,
    COUNT(*) as total_articles 
FROM noticias 
WHERE fecha >= DATE_SUB(CURDATE(), INTERVAL 7 DAYS)
GROUP BY fecha 
ORDER BY fecha DESC;

-- Top categories
SELECT 
    categoria,
    COUNT(*) as total_articles 
FROM noticias 
GROUP BY categoria 
ORDER BY total_articles DESC 
LIMIT 10; 