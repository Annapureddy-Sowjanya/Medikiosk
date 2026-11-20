CREATE DATABASE IF NOT EXISTS medikiosk CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'medikiosk'@'localhost' IDENTIFIED BY 'ChangeThisPassword';
CREATE USER IF NOT EXISTS 'medikiosk'@'127.0.0.1' IDENTIFIED BY 'ChangeThisPassword';
GRANT ALL PRIVILEGES ON medikiosk.* TO 'medikiosk'@'localhost';
GRANT ALL PRIVILEGES ON medikiosk.* TO 'medikiosk'@'127.0.0.1';
FLUSH PRIVILEGES;
