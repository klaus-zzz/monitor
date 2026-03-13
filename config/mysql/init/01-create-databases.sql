-- ============================================================
-- MySQL 初始化脚本：自动创建额外业务数据库
-- 此脚本仅在 MySQL 首次初始化时执行（data 目录为空时）
-- MYSQL_DATABASE 环境变量已自动创建 monitor 库，此处创建其他库
-- ============================================================

-- Uptime Kuma 数据库（独立库，避免与 Grafana 表名冲突）
CREATE DATABASE IF NOT EXISTS `kuma` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
