<?php
/**
 * WhatsApp Forensic Analyzer - Sistema Licenze
 * API per validazione licenze e telemetria
 *
 * Versione: 1.3 - Auto-generazione licenze utente
 * © 2025 Luca Mercatanti
 */

// Disabilita display errori (per produzione)
// error_reporting(0);
// ini_set('display_errors', 0);

// Per debug (decommentare se necessario):
error_reporting(E_ALL);
ini_set('display_errors', 1);

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST');

require_once 'config.php';

// Leggi input JSON
$input = file_get_contents('php://input');
$data = json_decode($input, true);

if (!$data) {
    echo json_encode([
        'success' => false,
        'message' => 'Input JSON non valido'
    ]);
    exit;
}

$action = $data['action'] ?? '';

switch ($action) {
    case 'validate':
        handle_validate($data);
        break;

    case 'ping':
        handle_ping($data);
        break;

    case 'track_no_license':
        handle_track_no_license($data);
        break;

    case 'generate_license':
        handle_generate_license($data);
        break;

    case 'check_version':
        handle_check_version($data);
        break;

    case 'version':
        // Endpoint per verificare versione API
        echo json_encode([
            'success' => true,
            'version' => '1.4',
            'message' => 'API Licenze - Versione 1.4 - Sistema aggiornamenti app'
        ]);
        break;

    default:
        echo json_encode([
            'success' => false,
            'message' => 'Azione non riconosciuta'
        ]);
}

/**
 * Gestisce la validazione di una licenza
 */
function handle_validate($data) {
    $license_key = $data['license_key'] ?? '';
    $hardware_id = $data['hardware_id'] ?? '';
    $hostname = $data['hostname'] ?? '';
    $os = $data['os'] ?? '';

    if (!$license_key || !$hardware_id) {
        echo json_encode([
            'valid' => false,
            'message' => 'Dati mancanti (license_key o hardware_id)'
        ]);
        return;
    }

    $conn = get_db_connection();

    // Verifica se la licenza esiste ed è attiva
    $stmt = $conn->prepare("SELECT id, nome, cognome, email, attiva, data_scadenza FROM licenze WHERE license_key = ? LIMIT 1");
    $stmt->bind_param('s', $license_key);
    $stmt->execute();
    $result = $stmt->get_result();

    if ($result->num_rows === 0) {
        echo json_encode([
            'valid' => false,
            'message' => 'Licenza non trovata'
        ]);
        $stmt->close();
        $conn->close();
        return;
    }

    $license = $result->fetch_assoc();
    $stmt->close();

    // Verifica se è attiva
    if ($license['attiva'] != 1) {
        echo json_encode([
            'valid' => false,
            'message' => 'Licenza revocata o disabilitata'
        ]);
        $conn->close();
        return;
    }

    // Verifica scadenza (se presente)
    if ($license['data_scadenza']) {
        $now = new DateTime();
        $scadenza = new DateTime($license['data_scadenza']);
        if ($now > $scadenza) {
            echo json_encode([
                'valid' => false,
                'message' => 'Licenza scaduta'
            ]);
            $conn->close();
            return;
        }
    }

    // Licenza valida! Registra/aggiorna attivazione hardware
    $licenza_id = $license['id'];

    $stmt = $conn->prepare("
        INSERT INTO attivazioni_hardware (licenza_id, hardware_id, hostname, os_info, prima_attivazione, ultimo_ping, conteggio_ping)
        VALUES (?, ?, ?, ?, NOW(), NOW(), 1)
        ON DUPLICATE KEY UPDATE
            hostname = VALUES(hostname),
            os_info = VALUES(os_info),
            ultimo_ping = NOW(),
            conteggio_ping = conteggio_ping + 1
    ");
    $stmt->bind_param('isss', $licenza_id, $hardware_id, $hostname, $os);
    $stmt->execute();
    $stmt->close();

    // Aggiorna ultimo utilizzo nella tabella licenze
    $stmt = $conn->prepare("UPDATE licenze SET ultimo_utilizzo = NOW() WHERE id = ?");
    $stmt->bind_param('i', $licenza_id);
    $stmt->execute();
    $stmt->close();

    // NON registrare log utilizzo qui - lo fa solo handle_ping()
    // Questo evita duplicati nel log quando l'app si avvia

    $conn->close();

    // Risposta successo
    echo json_encode([
        'valid' => true,
        'message' => 'Licenza valida',
        'license_info' => [
            'nome' => $license['nome'],
            'cognome' => $license['cognome'],
            'email' => $license['email']
        ]
    ]);
}

/**
 * Gestisce il ping di telemetria
 */
function handle_ping($data) {
    $license_key = $data['license_key'] ?? '';
    $hardware_id = $data['hardware_id'] ?? '';
    $hostname = $data['hostname'] ?? '';
    $os = $data['os'] ?? '';
    $app_version = $data['app_version'] ?? '';

    if (!$license_key || !$hardware_id) {
        echo json_encode([
            'success' => false,
            'message' => 'Dati mancanti'
        ]);
        return;
    }

    $conn = get_db_connection();

    // Recupera ID licenza
    $stmt = $conn->prepare("SELECT id, attiva FROM licenze WHERE license_key = ? LIMIT 1");
    $stmt->bind_param('s', $license_key);
    $stmt->execute();
    $result = $stmt->get_result();

    if ($result->num_rows === 0) {
        echo json_encode([
            'success' => false,
            'message' => 'Licenza non trovata'
        ]);
        $stmt->close();
        $conn->close();
        return;
    }

    $license = $result->fetch_assoc();
    $licenza_id = $license['id'];
    $stmt->close();

    // Aggiorna ultimo ping in attivazioni_hardware
    $stmt = $conn->prepare("
        UPDATE attivazioni_hardware
        SET ultimo_ping = NOW(), conteggio_ping = conteggio_ping + 1
        WHERE licenza_id = ? AND hardware_id = ?
    ");
    $stmt->bind_param('is', $licenza_id, $hardware_id);
    $stmt->execute();
    $stmt->close();

    // Registra log utilizzo
    $ip = $_SERVER['REMOTE_ADDR'] ?? null;
    $stmt = $conn->prepare("
        INSERT INTO log_utilizzo (licenza_id, hardware_id, hostname, os_info, app_version, ip_address)
        VALUES (?, ?, ?, ?, ?, ?)
    ");
    $stmt->bind_param('isssss', $licenza_id, $hardware_id, $hostname, $os, $app_version, $ip);
    $stmt->execute();
    $stmt->close();

    $conn->close();

    echo json_encode([
        'success' => true,
        'message' => 'Telemetria registrata'
    ]);
}

/**
 * Gestisce il tracking di accessi senza licenza
 * Registra quando qualcuno apre il programma ma esce senza inserire licenza
 */
function handle_track_no_license($data) {
    $hardware_id = $data['hardware_id'] ?? '';
    $hostname = $data['hostname'] ?? '';
    $os = $data['os'] ?? '';

    if (!$hardware_id) {
        echo json_encode([
            'success' => false,
            'message' => 'Hardware ID mancante'
        ]);
        return;
    }

    $conn = get_db_connection();

    // Registra accesso senza licenza
    $ip = $_SERVER['REMOTE_ADDR'] ?? null;
    $stmt = $conn->prepare("
        INSERT INTO log_accessi_senza_licenza (hardware_id, hostname, os_info, ip_address)
        VALUES (?, ?, ?, ?)
    ");
    $stmt->bind_param('ssss', $hardware_id, $hostname, $os, $ip);
    $stmt->execute();
    $stmt->close();

    $conn->close();

    echo json_encode([
        'success' => true,
        'message' => 'Accesso tracciato'
    ]);
}

/**
 * Genera automaticamente una nuova licenza
 * Per utenti che vogliono ottenere licenza istantaneamente
 */
function handle_generate_license($data) {
    $nome = trim($data['nome'] ?? '');
    $cognome = trim($data['cognome'] ?? '');
    $email = trim($data['email'] ?? '');
    $hardware_id = $data['hardware_id'] ?? '';

    // Validazione input
    if (!$nome || !$cognome || !$email) {
        echo json_encode([
            'success' => false,
            'message' => 'Nome, cognome ed email sono obbligatori'
        ]);
        return;
    }

    // Validazione email
    if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
        echo json_encode([
            'success' => false,
            'message' => 'Email non valida'
        ]);
        return;
    }

    // Validazione hardware_id
    if (!$hardware_id) {
        echo json_encode([
            'success' => false,
            'message' => 'Hardware ID mancante'
        ]);
        return;
    }

    $conn = get_db_connection();

    // ⚠️ PROTEZIONE ANTI-FLOOD: Verifica se questo PC ha già generato una licenza
    // Controlla nella tabella attivazioni_hardware se l'hardware_id esiste già
    $stmt = $conn->prepare("
        SELECT l.license_key, l.email, l.nome, l.cognome
        FROM licenze l
        INNER JOIN attivazioni_hardware ah ON l.id = ah.licenza_id
        WHERE ah.hardware_id = ?
        LIMIT 1
    ");
    $stmt->bind_param('s', $hardware_id);
    $stmt->execute();
    $result = $stmt->get_result();

    if ($result->num_rows > 0) {
        // Questo PC ha già generato una licenza!
        $existing = $result->fetch_assoc();
        $stmt->close();
        $conn->close();

        echo json_encode([
            'success' => false,
            'message' => 'Questo PC ha già generato una licenza',
            'existing_license' => $existing['license_key'],
            'existing_email' => $existing['email']
        ]);
        return;
    }
    $stmt->close();

    // Verifica se email già esiste (controllo secondario)
    $stmt = $conn->prepare("SELECT license_key FROM licenze WHERE email = ? LIMIT 1");
    $stmt->bind_param('s', $email);
    $stmt->execute();
    $result = $stmt->get_result();

    if ($result->num_rows > 0) {
        // Email già registrata, restituisci licenza esistente
        $existing = $result->fetch_assoc();
        $stmt->close();
        $conn->close();

        echo json_encode([
            'success' => true,
            'license_key' => $existing['license_key'],
            'message' => 'Licenza esistente trovata per questa email'
        ]);
        return;
    }
    $stmt->close();

    // Genera nuova licenza
    $license_key = generate_license_key();

    // Inserisci nel database
    $stmt = $conn->prepare("
        INSERT INTO licenze (license_key, nome, cognome, email, attiva, note)
        VALUES (?, ?, ?, ?, 1, 'Auto-generata da utente')
    ");
    $stmt->bind_param('ssss', $license_key, $nome, $cognome, $email);

    if (!$stmt->execute()) {
        $stmt->close();
        $conn->close();

        echo json_encode([
            'success' => false,
            'message' => 'Errore creazione licenza'
        ]);
        return;
    }

    $licenza_id = $conn->insert_id;
    $stmt->close();

    // Se fornito hardware_id, registra attivazione iniziale
    if ($hardware_id) {
        $hostname = $data['hostname'] ?? '';
        $os = $data['os'] ?? '';

        $stmt = $conn->prepare("
            INSERT INTO attivazioni_hardware (licenza_id, hardware_id, hostname, os_info, prima_attivazione, ultimo_ping, conteggio_ping)
            VALUES (?, ?, ?, ?, NOW(), NOW(), 0)
        ");
        $stmt->bind_param('isss', $licenza_id, $hardware_id, $hostname, $os);
        $stmt->execute();
        $stmt->close();
    }

    $conn->close();

    // Successo! Restituisci la licenza generata
    echo json_encode([
        'success' => true,
        'license_key' => $license_key,
        'message' => 'Licenza generata con successo!'
    ]);
}

/**
 * Controlla se disponibile nuova versione dell'applicazione
 */
function handle_check_version($data) {
    $conn = get_db_connection();

    // Recupera ultima versione attiva (is_active=1)
    $stmt = $conn->prepare("
        SELECT version, release_date, download_url, changelog
        FROM app_versions
        WHERE is_active = 1
        ORDER BY id DESC
        LIMIT 1
    ");
    $stmt->execute();
    $result = $stmt->get_result();

    if ($result->num_rows === 0) {
        echo json_encode([
            'success' => false,
            'message' => 'Nessuna versione disponibile'
        ]);
        $stmt->close();
        $conn->close();
        return;
    }

    $version = $result->fetch_assoc();
    $stmt->close();
    $conn->close();

    // Risposta con info versione
    echo json_encode([
        'success' => true,
        'latest_version' => $version['version'],
        'release_date' => $version['release_date'],
        'download_url' => $version['download_url'],
        'changelog' => $version['changelog'] ?? ''
    ]);
}
