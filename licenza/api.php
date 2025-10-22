<?php
/**
 * WhatsApp Forensic Analyzer - Sistema Licenze
 * API per validazione licenze e telemetria
 *
 * Versione: 1.2 - Tracking accessi senza licenza
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

    case 'version':
        // Endpoint per verificare versione API
        echo json_encode([
            'success' => true,
            'version' => '1.2',
            'message' => 'API Licenze - Versione 1.2 - Tracking accessi senza licenza'
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
