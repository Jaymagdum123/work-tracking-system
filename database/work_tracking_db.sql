CREATE DATABASE IF NOT EXISTS work_tracking_db;
USE work_tracking_db;

CREATE TABLE IF NOT EXISTS users (
 id INT AUTO_INCREMENT PRIMARY KEY,
 full_name VARCHAR(100) NOT NULL,
 username VARCHAR(80) NOT NULL UNIQUE,
 email VARCHAR(120) NOT NULL UNIQUE,
 password_hash VARCHAR(255) NOT NULL,
 role VARCHAR(50) NOT NULL DEFAULT 'Administrator',
 phone VARCHAR(30), department VARCHAR(100), address VARCHAR(255),
 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS departments (
 id INT AUTO_INCREMENT PRIMARY KEY,
 name VARCHAR(100) NOT NULL UNIQUE,
 description VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS employees (
 id INT AUTO_INCREMENT PRIMARY KEY,
 employee_code VARCHAR(30) NOT NULL UNIQUE,
 full_name VARCHAR(100) NOT NULL,
 email VARCHAR(120),
 department VARCHAR(100) NOT NULL,
 role VARCHAR(100) NOT NULL,
 phone VARCHAR(30),
 status VARCHAR(30) DEFAULT 'Active',
 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS work_assignments (
 id INT AUTO_INCREMENT PRIMARY KEY,
 title VARCHAR(150) NOT NULL,
 description TEXT,
 employee_id INT NOT NULL,
 department VARCHAR(100),
 deadline DATETIME,
 priority VARCHAR(30) DEFAULT 'Medium',
 status VARCHAR(30) DEFAULT 'Pending',
 progress INT DEFAULT 0,
 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS attendance (
 id INT AUTO_INCREMENT PRIMARY KEY,
 attendance_date DATE NOT NULL,
 employee_id INT NOT NULL,
 check_in TIME,
 check_out TIME,
 status VARCHAR(30) NOT NULL DEFAULT 'Present',
 UNIQUE KEY unique_attendance(attendance_date, employee_id),
 FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS production (
 id INT AUTO_INCREMENT PRIMARY KEY,
 production_date DATE NOT NULL,
 product VARCHAR(120) NOT NULL,
 department VARCHAR(100),
 quantity INT NOT NULL,
 good_units INT NOT NULL DEFAULT 0,
 defective INT NOT NULL DEFAULT 0,
 status VARCHAR(30) DEFAULT 'Completed',
 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT IGNORE INTO departments(name,description) VALUES
('Production','Manufacturing and assembly operations'),
('Quality Control','Inspection and quality assurance'),
('Maintenance','Machine maintenance and repair'),
('Packaging','Product packing and dispatch'),
('Administration','Office and management operations');

INSERT IGNORE INTO employees(employee_code,full_name,email,department,role,phone,status) VALUES
('EMP-001','Rahul Patil','rahul@worktrack.com','Production','Operator','98765 43210','Active'),
('EMP-002','Neha Sharma','neha@worktrack.com','Quality Control','Inspector','98765 12345','Active'),
('EMP-003','Vikas More','vikas@worktrack.com','Maintenance','Technician','98220 45678','On Leave'),
('EMP-004','Anita Shah','anita@worktrack.com','Packaging','Supervisor','97654 98765','Active');

-- Default administrator is created automatically by Flask on first startup.
-- Login: admin@worktrack.com / admin123

INSERT INTO production(production_date,product,department,quantity,good_units,defective,status)
SELECT CURDATE(),'Component A','Production',800,776,24,'Completed' WHERE NOT EXISTS(SELECT 1 FROM production);
INSERT INTO production(production_date,product,department,quantity,good_units,defective,status)
SELECT CURDATE(),'Component B','Production',484,470,14,'In Progress' WHERE (SELECT COUNT(*) FROM production)=1;
