-- WhatsApp Forensic Analyzer - Sistema Licenze
-- Schema Database MySQL
-- © 2025 Luca Mercatanti

-- Crea database (se non esiste)
CREATE DATABASE IF NOT EXISTS licenze_afra CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE licenze_afra;

-- ============================================
-- Tabella: licenze
-- Memorizza tutte le licenze generate
-- ============================================
CREATE TABLE IF NOT EXISTS licenze (
    id INT AUTO_INCREMENT PRIMARY KEY,
    license_key VARCHAR(255) NOT NULL UNIQUE,
    nome VARCHAR(100) DEFAULT NULL,
    cognome VARCHAR(100) DEFAULT NULL,
    email VARCHAR(255) DEFAULT NULL,
    note TEXT DEFAULT NULL,
    attiva TINYINT(1) DEFAULT 1,
    data_creazione DATETIME DEFAULT CURRENT_TIMESTAMP,
    data_scadenza DATETIME DEFAULT NULL,
    ultimo_utilizzo DATETIME DEFAULT NULL,
    INDEX idx_license_key (license_key),
    INDEX idx_attiva (attiva),
    INDEX idx_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- Tabella: attivazioni_hardware
-- Memorizza i PC su cui ogni licenza è attiva
-- ============================================
CREATE TABLE IF NOT EXISTS attivazioni_hardware (
    id INT AUTO_INCREMENT PRIMARY KEY,
    licenza_id INT NOT NULL,
    hardware_id VARCHAR(64) NOT NULL,
    hostname VARCHAR(255) DEFAULT NULL,
    os_info VARCHAR(255) DEFAULT NULL,
    prima_attivazione DATETIME DEFAULT CURRENT_TIMESTAMP,
    ultimo_ping DATETIME DEFAULT CURRENT_TIMESTAMP,
    conteggio_ping INT DEFAULT 1,
    UNIQUE KEY unique_licenza_hardware (licenza_id, hardware_id),
    FOREIGN KEY (licenza_id) REFERENCES licenze(id) ON DELETE CASCADE,
    INDEX idx_hardware_id (hardware_id),
    INDEX idx_ultimo_ping (ultimo_ping)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- Tabella: log_utilizzo
-- Log dettagliato di ogni avvio dell'applicazione
-- ============================================
CREATE TABLE IF NOT EXISTS log_utilizzo (
    id INT AUTO_INCREMENT PRIMARY KEY,
    licenza_id INT NOT NULL,
    hardware_id VARCHAR(64) NOT NULL,
    hostname VARCHAR(255) DEFAULT NULL,
    os_info VARCHAR(255) DEFAULT NULL,
    app_version VARCHAR(50) DEFAULT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(45) DEFAULT NULL,
    FOREIGN KEY (licenza_id) REFERENCES licenze(id) ON DELETE CASCADE,
    INDEX idx_licenza_id (licenza_id),
    INDEX idx_timestamp (timestamp),
    INDEX idx_hardware_id (hardware_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- Tabella: log_accessi_senza_licenza
-- Traccia aperture del programma senza licenza valida
-- Utile per vedere quante persone provano il software
-- ma non procedono con la richiesta
-- ============================================
CREATE TABLE IF NOT EXISTS log_accessi_senza_licenza (
    id INT AUTO_INCREMENT PRIMARY KEY,
    hardware_id VARCHAR(64) NOT NULL,
    hostname VARCHAR(255) DEFAULT NULL,
    os_info VARCHAR(255) DEFAULT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(45) DEFAULT NULL,
    INDEX idx_hardware_id (hardware_id),
    INDEX idx_timestamp (timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- Tabella: app_versions
-- Gestisce le versioni dell'applicazione per notifiche update
-- Solo 1 versione attiva alla volta (is_active=1)
-- ============================================
CREATE TABLE IF NOT EXISTS app_versions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    version VARCHAR(20) NOT NULL UNIQUE,
    release_date DATE NOT NULL,
    download_url VARCHAR(500) NOT NULL,
    changelog TEXT DEFAULT NULL,
    is_active TINYINT(1) DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_version (version),
    INDEX idx_is_active (is_active),
    INDEX idx_release_date (release_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- Dati di esempio (opzionale)
-- ============================================

-- Inserisci alcune licenze di test
INSERT INTO licenze (license_key, nome, cognome, email, note, attiva) VALUES
('TEST-1234-5678-ABCD', 'Mario', 'Rossi', 'mario.rossi@example.com', 'Licenza di test', 1),
('DEMO-ABCD-1234-EFGH', 'Luca', 'Bianchi', 'luca.bianchi@example.com', 'Licenza demo', 1),
('TRIAL-9999-8888-7777', 'Test', 'Utente', 'test@example.com', 'Licenza trial', 0);

-- Inserisci versione corrente dell'app
INSERT INTO app_versions (version, release_date, download_url, changelog, is_active) VALUES
('3.4.0', '2025-10-25', 'https://github.com/tuousername/WhatsAppAnalyzer/releases/download/v3.4.0/WhatsAppAnalyzer_v3.4.0.exe',
 '- Sistema LLM puro per rilevamento chat\n- Modalità test per Report Chat\n- Fix bug minori', 1);

-- Note:
-- - license_key: Chiave univoca generata manualmente o automaticamente
-- - attiva: 1 = attiva, 0 = revocata/disabilitata
-- - data_scadenza: NULL = nessuna scadenza (licenza perpetua)
-- - Ogni licenza può essere attivata su più PC (tracciati in attivazioni_hardware)
-- - Ogni ping viene registrato in log_utilizzo per statistiche dettagliate
-- - app_versions: Solo 1 versione con is_active=1 alla volta (l'ultima pubblicata)
