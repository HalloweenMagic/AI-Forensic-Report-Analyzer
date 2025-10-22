<?php
/**
 * WhatsApp Forensic Analyzer - Sistema Licenze
 * Vista Attivazioni Hardware
 *
 * © 2025 Luca Mercatanti
 */

require_once 'config.php';
require_auth();

$conn = get_db_connection();

// Filtro per licenza specifica (opzionale)
$licenza_id = $_GET['licenza_id'] ?? null;

$query = "
    SELECT a.*, l.license_key, l.nome, l.cognome, l.email
    FROM attivazioni_hardware a
    JOIN licenze l ON a.licenza_id = l.id
";

if ($licenza_id) {
    $query .= " WHERE a.licenza_id = " . intval($licenza_id);
}

$query .= " ORDER BY a.ultimo_ping DESC";

$activations = $conn->query($query);

$conn->close();
?>
<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Attivazioni Hardware - Sistema Licenze AFRA</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>💻 Attivazioni Hardware</h1>
            <div class="user-info">
                Admin: <?php echo h($_SESSION['username']); ?> |
                <a href="logout.php" style="color: #dc3545;">Logout</a>
            </div>
        </div>

        <div class="nav">
            <a href="index.php">Dashboard</a>
            <a href="licenze.php">Gestione Licenze</a>
            <a href="attivazioni.php" class="active">Attivazioni Hardware</a>
            <a href="logs.php">Log Utilizzo</a>
            <a href="accessi_senza_licenza.php">Accessi Senza Licenza</a>
        </div>

        <?php if ($licenza_id): ?>
            <div class="alert alert-info">
                <strong>Filtro attivo:</strong> Mostrando attivazioni solo per la licenza ID #<?php echo intval($licenza_id); ?>
                | <a href="attivazioni.php">Rimuovi filtro</a>
            </div>
        <?php endif; ?>

        <h2>📋 Tutte le Attivazioni Hardware</h2>
        <p style="color: #666; margin-bottom: 20px;">
            Ogni licenza può essere usata su uno o più PC. Qui puoi vedere tutti i PC su cui ogni licenza è stata attivata.
        </p>

        <table>
            <thead>
                <tr>
                    <th>Licenza</th>
                    <th>Utente</th>
                    <th>Hardware ID</th>
                    <th>Hostname</th>
                    <th>OS</th>
                    <th>Prima Attivazione</th>
                    <th>Ultimo Ping</th>
                    <th>Ping Totali</th>
                </tr>
            </thead>
            <tbody>
                <?php if ($activations->num_rows === 0): ?>
                    <tr>
                        <td colspan="8" style="text-align: center; color: #999;">
                            Nessuna attivazione trovata
                        </td>
                    </tr>
                <?php else: ?>
                    <?php while ($row = $activations->fetch_assoc()): ?>
                    <tr>
                        <td><code><?php echo h($row['license_key']); ?></code></td>
                        <td><?php echo h($row['nome'] . ' ' . $row['cognome']); ?></td>
                        <td><code style="font-size: 10px;"><?php echo h(substr($row['hardware_id'], 0, 16)); ?>...</code></td>
                        <td><?php echo h($row['hostname']); ?></td>
                        <td><?php echo h($row['os_info']); ?></td>
                        <td><?php echo format_date($row['prima_attivazione']); ?></td>
                        <td><?php echo format_date($row['ultimo_ping']); ?></td>
                        <td><?php echo number_format($row['conteggio_ping']); ?></td>
                    </tr>
                    <?php endwhile; ?>
                <?php endif; ?>
            </tbody>
        </table>
    </div>
</body>
</html>
