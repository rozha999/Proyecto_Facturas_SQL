
-- =========================================
-- PROYECTO: SUPERMERCADO
-- CREACION DE BASE DE DATOS Y TABLAS
-- =========================================

CREATE DATABASE IF NOT EXISTS supermercado
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE supermercado;

-- =========================================
-- 1. TABLA SUCURSAL
-- =========================================

CREATE TABLE IF NOT EXISTS sucursal (
    id_sucursal INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(150) NOT NULL,
    cif VARCHAR(20) NOT NULL UNIQUE,
    direccion VARCHAR(200)
) ENGINE=InnoDB;

-- =========================================
-- 2. TABLA EMPLEADO
-- =========================================

CREATE TABLE IF NOT EXISTS empleado (
    id_empleado INT AUTO_INCREMENT PRIMARY KEY,
    codigo VARCHAR(20) NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    id_sucursal INT NOT NULL,

    UNIQUE (codigo, id_sucursal),

    CONSTRAINT fk_empleado_sucursal
        FOREIGN KEY (id_sucursal)
        REFERENCES sucursal(id_sucursal)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
) ENGINE=InnoDB;

-- =========================================
-- 3. TABLA PRODUCTO
-- =========================================

CREATE TABLE IF NOT EXISTS producto (
    id_producto INT AUTO_INCREMENT PRIMARY KEY,
    descripcion VARCHAR(200) NOT NULL UNIQUE
) ENGINE=InnoDB;

-- =========================================
-- 4. TABLA TICKET
-- =========================================

CREATE TABLE IF NOT EXISTS ticket (
    id_ticket INT AUTO_INCREMENT PRIMARY KEY,
    numero_ticket VARCHAR(30) NOT NULL,
    fecha DATE NOT NULL,
    hora TIME NOT NULL,
    subtotal DECIMAL(10,2) NOT NULL,
    iva DECIMAL(10,2) NOT NULL,
    total DECIMAL(10,2) NOT NULL,
    id_sucursal INT NOT NULL,
    id_empleado INT NOT NULL,

    UNIQUE (numero_ticket, id_sucursal),

    CONSTRAINT fk_ticket_sucursal
        FOREIGN KEY (id_sucursal)
        REFERENCES sucursal(id_sucursal)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    CONSTRAINT fk_ticket_empleado
        FOREIGN KEY (id_empleado)
        REFERENCES empleado(id_empleado)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
) ENGINE=InnoDB;

-- =========================================
-- 5. TABLA TICKET_LINEA
-- =========================================

CREATE TABLE IF NOT EXISTS ticket_linea (
    id_linea INT AUTO_INCREMENT PRIMARY KEY,
    id_ticket INT NOT NULL,
    id_producto INT NOT NULL,
    cantidad DECIMAL(10,3) NOT NULL,
    precio_unitario DECIMAL(10,2) NOT NULL,
    importe DECIMAL(10,2) NOT NULL,

    CONSTRAINT fk_linea_ticket
        FOREIGN KEY (id_ticket)
        REFERENCES ticket(id_ticket)
        ON UPDATE CASCADE
        ON DELETE CASCADE,

    CONSTRAINT fk_linea_producto
        FOREIGN KEY (id_producto)
        REFERENCES producto(id_producto)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
) ENGINE=InnoDB;

-- =========================================
-- 6. TABLA PAGO
-- =========================================

CREATE TABLE IF NOT EXISTS pago (
    id_pago INT AUTO_INCREMENT PRIMARY KEY,
    id_ticket INT NOT NULL UNIQUE,
    metodo_pago VARCHAR(50) NOT NULL,
    importe DECIMAL(10,2) NOT NULL,

    CONSTRAINT fk_pago_ticket
        FOREIGN KEY (id_ticket)
        REFERENCES ticket(id_ticket)
        ON UPDATE CASCADE
        ON DELETE CASCADE
) ENGINE=InnoDB;

-- =========================================
-- FIN DEL SCRIPT
-- =========================================

