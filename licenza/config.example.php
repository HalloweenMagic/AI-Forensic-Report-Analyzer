<?php
/**
 * WhatsApp Forensic Analyzer - Sistema Licenze
 * Configurazione Database - TEMPLATE
 *
 * © 2025 Luca Mercatanti
 */

// ============================================
// CONFIGURAZIONE DATABASE
// ⚠️ MODIFICA QUESTI VALORI CON I TUOI DATI
// ============================================

define('DB_HOST', 'localhost');              // Host database (es. localhost)
define('DB_NAME', 'your_database_name');     // Nome database
define('DB_USER', 'your_database_user');     // Username database
define('DB_PASS', 'your_database_password'); // Password database

// ============================================
// CREDENZIALI ADMIN BACKOFFICE
// ⚠️ MODIFICA QUESTI VALORI PER SICUREZZA
// ============================================

define('ADMIN_USERNAME', 'admin');
define('ADMIN_PASSWORD', 'change_this_password');  // ⚠️ CAMBIA QUESTA PASSWORD!

// ============================================
// IMPOSTAZIONI APPLICAZIONE
// ============================================

define('SESSION_NAME', 'afra_license_admin');
define('SESSION_TIMEOUT', 3600);  // 1 ora (in secondi)

// Timezone
date_default_timezone_set('Europe/Rome');

// ============================================
// FUNZIONI HELPER
// ============================================

/**
 * Crea connessione al database
 * @return mysqli
 */
function get_db_connection() {
    $conn = new mysqli(DB_HOST, DB_USER, DB_PASS, DB_NAME);

    if ($conn->connect_error) {
        die(json_encode([
            'success' => false,
            'message' => 'Errore connessione database'
        ]));
    }

    $conn->set_charset('utf8mb4');
    return $conn;
}

/**
 * Verifica se l'utente è autenticato
 * @return bool
 */
function is_authenticated() {
    session_name(SESSION_NAME);
    if (session_status() === PHP_SESSION_NONE) {
        session_start();
    }

    return isset($_SESSION['authenticated']) && $_SESSION['authenticated'] === true;
}

/**
 * Richiedi autenticazione (redirect se non autenticato)
 */
function require_auth() {
    if (!is_authenticated()) {
        header('Location: login.php');
        exit;
    }

    // Verifica timeout sessione
    if (isset($_SESSION['last_activity']) &&
        (time() - $_SESSION['last_activity']) > SESSION_TIMEOUT) {
        session_destroy();
        header('Location: login.php?timeout=1');
        exit;
    }

    $_SESSION['last_activity'] = time();
}

/**
 * Escape output HTML
 * @param string $text
 * @return string
 */
function h($text) {
    return htmlspecialchars($text, ENT_QUOTES, 'UTF-8');
}

/**
 * Formatta data italiana
 * @param string $datetime
 * @return string
 */
function format_date($datetime) {
    if (!$datetime) return '-';
    $dt = new DateTime($datetime);
    return $dt->format('d/m/Y H:i');
}

/**
 * Genera chiave di licenza casuale
 * @return string
 */
function generate_license_key() {
    $segments = [];
    for ($i = 0; $i < 4; $i++) {
        $segments[] = strtoupper(substr(bin2hex(random_bytes(4)), 0, 4));
    }
    return implode('-', $segments);
}
