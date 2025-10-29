<?php
/**
 * WhatsApp Forensic Analyzer - Sistema Licenze
 * Dashboard Admin
 *
 * © 2025 Luca Mercatanti
 */

require_once 'config.php';
require_auth();

$conn = get_db_connection();

// Statistiche
$stats = [];

// Totale licenze
$result = $conn->query("SELECT COUNT(*) as total FROM licenze");
$stats['total_licenses'] = $result->fetch_assoc()['total'];

// Licenze attive
$result = $conn->query("SELECT COUNT(*) as total FROM licenze WHERE attiva = 1");
$stats['active_licenses'] = $result->fetch_assoc()['total'];

// Totale attivazioni hardware
$result = $conn->query("SELECT COUNT(*) as total FROM attivazioni_hardware");
$stats['total_activations'] = $result->fetch_assoc()['total'];

// Utilizzi oggi
$result = $conn->query("SELECT COUNT(*) as total FROM log_utilizzo WHERE DATE(timestamp) = CURDATE()");
$stats['today_usage'] = $result->fetch_assoc()['total'];

// Utilizzi questa settimana
$result = $conn->query("SELECT COUNT(*) as total FROM log_utilizzo WHERE YEARWEEK(timestamp, 1) = YEARWEEK(CURDATE(), 1)");
$stats['week_usage'] = $result->fetch_assoc()['total'];

// Licenze recenti (ultime 10)
$recent_licenses = $conn->query("
    SELECT license_key, nome, cognome, email, attiva, data_creazione, ultimo_utilizzo
    FROM licenze
    ORDER BY data_creazione DESC
    LIMIT 10
");

// Utilizzi recenti (ultimi 20)
$recent_usage = $conn->query("
    SELECT l.license_key, l.nome, l.cognome, u.hostname, u.timestamp
    FROM log_utilizzo u
    JOIN licenze l ON u.licenza_id = l.id
    ORDER BY u.timestamp DESC
    LIMIT 20
");

$conn->close();
?>
<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard - Sistema Licenze AFRA</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Dashboard - Sistema Licenze</h1>
            <div class="user-info">
                Admin: <?php echo h($_SESSION['username']); ?> |
                <a href="logout.php" style="color: #dc3545;">Logout</a>
            </div>
        </div>

        <div class="nav">
            <a href="index.php" class="active">Dashboard</a>
            <a href="licenze.php">Gestione Licenze</a>
            <a href="attivazioni.php">Attivazioni Hardware</a>
            <a href="logs.php">Log Utilizzo</a>
            <a href="accessi_senza_licenza.php">Accessi Senza Licenza</a>
            <a href="versioni.php">Versioni App</a>
        </div>

        <!-- Stats Cards -->
        <div class="stats">
            <div class="stat-card">
                <h3>Licenze Totali</h3>
                <div class="value"><?php echo $stats['total_licenses']; ?></div>
            </div>
            <div class="stat-card">
                <h3>Licenze Attive</h3>
                <div class="value"><?php echo $stats['active_licenses']; ?></div>
            </div>
            <div class="stat-card">
                <h3>Attivazioni Hardware</h3>
                <div class="value"><?php echo $stats['total_activations']; ?></div>
            </div>
            <div class="stat-card">
                <h3>Utilizzi Oggi</h3>
                <div class="value"><?php echo $stats['today_usage']; ?></div>
            </div>
            <div class="stat-card">
                <h3>Utilizzi Settimana</h3>
                <div class="value"><?php echo $stats['week_usage']; ?></div>
            </div>
        </div>

        <!-- Licenze Recenti -->
        <h2>📝 Licenze Recenti</h2>
        <table>
            <thead>
                <tr>
                    <th>Chiave Licenza</th>
                    <th>Nome</th>
                    <th>Email</th>
                    <th>Stato</th>
                    <th>Data Creazione</th>
                    <th>Ultimo Utilizzo</th>
                </tr>
            </thead>
            <tbody>
                <?php while ($row = $recent_licenses->fetch_assoc()): ?>
                <tr>
                    <td><code><?php echo h($row['license_key']); ?></code></td>
                    <td><?php echo h($row['nome'] . ' ' . $row['cognome']); ?></td>
                    <td><?php echo h($row['email']); ?></td>
                    <td>
                        <?php if ($row['attiva']): ?>
                            <span class="badge badge-success">Attiva</span>
                        <?php else: ?>
                            <span class="badge badge-danger">Revocata</span>
                        <?php endif; ?>
                    </td>
                    <td><?php echo format_date($row['data_creazione']); ?></td>
                    <td><?php echo format_date($row['ultimo_utilizzo']); ?></td>
                </tr>
                <?php endwhile; ?>
            </tbody>
        </table>

        <!-- Utilizzi Recenti -->
        <h2 style="margin-top: 40px;">🔔 Utilizzi Recenti</h2>
        <table>
            <thead>
                <tr>
                    <th>Chiave Licenza</th>
                    <th>Utente</th>
                    <th>Hostname</th>
                    <th>Timestamp</th>
                </tr>
            </thead>
            <tbody>
                <?php while ($row = $recent_usage->fetch_assoc()): ?>
                <tr>
                    <td><code><?php echo h($row['license_key']); ?></code></td>
                    <td><?php echo h($row['nome'] . ' ' . $row['cognome']); ?></td>
                    <td><?php echo h($row['hostname']); ?></td>
                    <td><?php echo format_date($row['timestamp']); ?></td>
                </tr>
                <?php endwhile; ?>
            </tbody>
        </table>
    </div>
</body>
</html>
