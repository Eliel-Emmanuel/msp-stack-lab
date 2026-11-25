#!/bin/bash
set -euo pipefail
mariadb --protocol=socket -uroot -p"${MARIADB_ROOT_PASSWORD}" <<SQL
CREATE DATABASE IF NOT EXISTS osticket CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'osticket'@'%' IDENTIFIED BY '${OSTICKET_DB_PASSWORD}';
GRANT ALL PRIVILEGES ON osticket.* TO 'osticket'@'%';
CREATE DATABASE IF NOT EXISTS bookstack CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'bookstack'@'%' IDENTIFIED BY '${BOOKSTACK_DB_PASSWORD}';
GRANT ALL PRIVILEGES ON bookstack.* TO 'bookstack'@'%';
FLUSH PRIVILEGES;
SQL
