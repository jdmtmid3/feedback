-- Customer Feedback System database export
-- Import this file in phpMyAdmin or MySQL.

CREATE DATABASE IF NOT EXISTS feedback_system
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE feedback_system;

SET FOREIGN_KEY_CHECKS = 0;

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('superadmin', 'admin', 'user') DEFAULT 'admin',
    max_stores INT DEFAULT 0,
    license_key VARCHAR(255) NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS stores (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NULL,
    store_name VARCHAR(255) NOT NULL,
    address TEXT,
    city VARCHAR(100),
    province VARCHAR(100),
    postal_code VARCHAR(20),
    contact_number VARCHAR(20),
    email VARCHAR(255),
    store_manager_name VARCHAR(255),
    manager_contact VARCHAR(20),
    store_type VARCHAR(100),
    operating_hours VARCHAR(255),
    status ENUM('active', 'inactive', 'pending') DEFAULT 'active',
    logo_url VARCHAR(500),
    access_token VARCHAR(100) UNIQUE,
    subdomain VARCHAR(100) UNIQUE,
    google_review_url VARCHAR(1000) NULL,
    reward_type VARCHAR(255) DEFAULT 'Store Reward or Discount',
    google_review_mode ENUM('review_only', 'reward') DEFAULT 'reward',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_stores_user_id (user_id),
    CONSTRAINT fk_stores_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS staff (
    id INT AUTO_INCREMENT PRIMARY KEY,
    store_id INT NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(20),
    position VARCHAR(100),
    photo_url LONGTEXT,
    role ENUM('staff', 'manager', 'supervisor') DEFAULT 'staff',
    hire_date DATE,
    status ENUM('active', 'inactive') DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (store_id) REFERENCES stores(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS questionnaires (
    id INT AUTO_INCREMENT PRIMARY KEY,
    store_id INT NULL,
    title VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_template BOOLEAN DEFAULT FALSE,
    template_id INT NULL,
    version INT DEFAULT 1,
    logo_url LONGTEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_questionnaires_store_id (store_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS questions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    questionnaire_id INT NOT NULL,
    question_text TEXT NOT NULL,
    question_type ENUM('rating', 'text', 'multiple_choice') NOT NULL,
    target_scope ENUM('overall', 'staff', 'manager') DEFAULT 'overall',
    min_label VARCHAR(255) DEFAULT 'Poor',
    max_label VARCHAR(255) DEFAULT 'Excellent',
    allow_comment BOOLEAN DEFAULT FALSE,
    is_required BOOLEAN DEFAULT TRUE,
    question_order INT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    is_template BOOLEAN DEFAULT FALSE,
    template_id INT NULL,
    FOREIGN KEY (questionnaire_id) REFERENCES questionnaires(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS question_options (
    id INT AUTO_INCREMENT PRIMARY KEY,
    question_id INT NOT NULL,
    option_text VARCHAR(255) NOT NULL,
    is_template BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS responses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    questionnaire_id INT NOT NULL,
    store_id INT NOT NULL,
    user_email VARCHAR(255),
    receipt_number VARCHAR(100),
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status ENUM('unresolved', 'resolved') DEFAULT 'unresolved',
    is_read BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (questionnaire_id) REFERENCES questionnaires(id) ON DELETE CASCADE,
    FOREIGN KEY (store_id) REFERENCES stores(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS answers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    response_id INT NOT NULL,
    question_id INT NOT NULL,
    staff_id INT NULL,
    answer_text TEXT,
    rating_value DECIMAL(3,1),
    FOREIGN KEY (response_id) REFERENCES responses(id) ON DELETE CASCADE,
    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS staff_commendations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    response_id INT NOT NULL,
    staff_id INT NOT NULL,
    rating INT DEFAULT 5,
    commendation_type ENUM('excellent_service', 'friendly_attitude', 'professional', 'helpful', 'knowledgeable') DEFAULT 'excellent_service',
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (response_id) REFERENCES responses(id) ON DELETE CASCADE,
    FOREIGN KEY (staff_id) REFERENCES staff(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS system_notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    message TEXT NOT NULL,
    type VARCHAR(50) DEFAULT 'info',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_read BOOLEAN DEFAULT FALSE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS audit_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    entity_type VARCHAR(50) NOT NULL,
    entity_id INT NOT NULL,
    action VARCHAR(50) NOT NULL,
    old_values TEXT,
    new_values TEXT,
    user_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS client_conversations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    client_identifier VARCHAR(255) NOT NULL UNIQUE,
    company_name VARCHAR(255),
    license_key VARCHAR(255),
    contact_email VARCHAR(255),
    portal_conversation_id INT NULL,
    last_message_at TIMESTAMP NULL,
    last_message_preview TEXT NULL,
    unread_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_client_identifier (client_identifier),
    INDEX idx_last_message_at (last_message_at)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS client_messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    conversation_id INT NOT NULL,
    sender_type ENUM('client', 'admin') NOT NULL,
    sender_name VARCHAR(255),
    message TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES client_conversations(id) ON DELETE CASCADE,
    INDEX idx_conversation_created (conversation_id, created_at)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS license_config (
    id INT AUTO_INCREMENT PRIMARY KEY,
    license_key VARCHAR(255) NOT NULL,
    api_key VARCHAR(255) NOT NULL,
    licensing_portal_url VARCHAR(255) DEFAULT 'https://feedbacklicensing-production.up.railway.app',
    main_system_url VARCHAR(255) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

INSERT INTO users (username, email, password_hash, role)
SELECT 'dev', 'dev@tugon.com', '$2b$12$khe7ecdexbwivPmb8j5YEeRPkxoZGTgVfGuteoSDCdvYHTMYEIEr.', 'superadmin'
WHERE NOT EXISTS (SELECT 1 FROM users WHERE username = 'dev' OR email = 'dev@tugon.com');

INSERT INTO questionnaires (title, is_active, is_template)
SELECT 'Master Questionnaire', TRUE, TRUE
WHERE NOT EXISTS (SELECT 1 FROM questionnaires WHERE is_template = TRUE);

SET FOREIGN_KEY_CHECKS = 1;

-- Optional licensing portal database used by licensing_system/app.py
-- The portal's local default DB_NAME is licensing_db.
CREATE DATABASE IF NOT EXISTS licensing_db
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE licensing_db;

CREATE TABLE IF NOT EXISTS licenses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    license_key VARCHAR(255) NOT NULL UNIQUE,
    license_key_hash VARCHAR(255) NOT NULL UNIQUE,
    company_name VARCHAR(255) NOT NULL,
    contact_email VARCHAR(255),
    max_stores INT DEFAULT 0,
    max_questionnaires INT DEFAULT 0,
    features JSON NULL,
    expiry_date DATE NULL,
    is_active BOOLEAN DEFAULT TRUE,
    api_key VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS support_tickets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    license_id INT NULL,
    license_key VARCHAR(255) NULL,
    company_name VARCHAR(255) NOT NULL,
    contact_email VARCHAR(255) NOT NULL,
    subject VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    ticket_type ENUM('general', 'renewal', 'bug', 'feature') DEFAULT 'general',
    status ENUM('open', 'in_progress', 'resolved', 'closed') DEFAULT 'open',
    priority ENUM('low', 'medium', 'high') DEFAULT 'medium',
    admin_reply TEXT NULL,
    replied_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS client_conversations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    client_identifier VARCHAR(255) NOT NULL UNIQUE,
    company_name VARCHAR(255) NOT NULL,
    license_key VARCHAR(255) NULL,
    contact_email VARCHAR(255) NOT NULL,
    last_message_at TIMESTAMP NULL,
    last_message_preview TEXT NULL,
    unread_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_client_identifier (client_identifier),
    INDEX idx_last_message_at (last_message_at)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    conversation_id INT NOT NULL,
    sender_type ENUM('client', 'admin') NOT NULL,
    sender_name VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES client_conversations(id) ON DELETE CASCADE,
    INDEX idx_conversation_created (conversation_id, created_at)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS system_config (
    id INT AUTO_INCREMENT PRIMARY KEY,
    config_key VARCHAR(255) NOT NULL UNIQUE,
    config_value TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

INSERT INTO system_config (config_key, config_value)
SELECT 'main_system_url', NULL
WHERE NOT EXISTS (SELECT 1 FROM system_config WHERE config_key = 'main_system_url');

USE feedback_system;
