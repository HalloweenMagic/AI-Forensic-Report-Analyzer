<?php
/**
 * WhatsApp Forensic Analyzer - Sistema Licenze
 * Log Utilizzo Dettagliato
 *
 * © 2025 Luca Mercatanti
 */

require_once 'config.php';
require_auth();

$conn = get_db_connection();

// Paginazione
$page = $_GET['page'] ?? 1;
$per_page = 50;
$offset = ($page - 1) * $per_page;

// Conta totale log
$total_result = $conn->query("SELECT COUNT(*) as total FROM log_utilizzo");
$total_logs = $total_result->fetch_assoc()['total'];
$total_pages = ceil($total_logs / $per_page);

// Recupera log con paginazione
$logs = $conn->query("
    SELECT u.*, l.license_key, l.nome, l.cognome
    FROM log_utilizzo u
    JOIN licenze l ON u.licenza_id = l.id
    ORDER BY u.timestamp DESC
    LIMIT $per_page OFFSET $offset
");

$conn->close();
?>
<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Log Utilizzo - Sistema Licenze AFRA</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📜 Log Utilizzo</h1>
            <div class="user-info">
                Admin: <?php echo h($_SESSION['username']); ?> |
                <a href="logout.php" style="color: #dc3545;">Logout</a>
            </div>
        </div>

        <div class="nav">
            <a href="index.php">Dashboard</a>
            <a href="licenze.php">Gestione Licenze</a>
            <a href="attivazioni.php">Attivazioni Hardware</a>
            <a href="logs.php" class="active">Log Utilizzo</a>
            <a href="accessi_senza_licenza.php">Accessi Senza Licenza</a>
        </div>

        <div style="background: #e3f2fd; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
            <strong>📊 Statistiche:</strong> Totale log: <?php echo number_format($total_logs); ?> |
            Pagina <?php echo $page; ?> di <?php echo $total_pages; ?>
        </div>

        <table>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Licenza</th>
                    <th>Utente</th>
                    <th>Hostname</th>
                    <th>OS</th>
                    <th>Versione App</th>
                    <th>IP Address</th>
                    <th>Timestamp</th>
                </tr>
            </thead>
            <tbody>
                <?php if ($logs->num_rows === 0): ?>
                    <tr>
                        <td colspan="8" style="text-align: center; color: #999;">
                            Nessun log trovato
                        </td>
                    </tr>
                <?php else: ?>
                    <?php while ($row = $logs->fetch_assoc()): ?>
                    <tr>
                        <td><?php echo $row['id']; ?></td>
                        <td><code><?php echo h($row['license_key']); ?></code></td>
                        <td><?php echo h($row['nome'] . ' ' . $row['cognome']); ?></td>
                        <td><?php echo h($row['hostname']); ?></td>
                        <td><?php echo h($row['os_info']); ?></td>
                        <td><?php echo h($row['app_version'] ?: '-'); ?></td>
                        <td><?php echo h($row['ip_address'] ?: '-'); ?></td>
                        <td><?php echo format_date($row['timestamp']); ?></td>
                    </tr>
                    <?php endwhile; ?>
                <?php endif; ?>
            </tbody>
        </table>

        <!-- Paginazione -->
        <?php if ($total_pages > 1): ?>
            <div class="pagination">
                <?php if ($page > 1): ?>
                    <a href="?page=<?php echo $page - 1; ?>">« Precedente</a>
                <?php endif; ?>

                <?php for ($i = max(1, $page - 2); $i <= min($total_pages, $page + 2); $i++): ?>
                    <a href="?page=<?php echo $i; ?>" class="<?php echo $i === $page ? 'active' : ''; ?>">
                        <?php echo $i; ?>
                    </a>
                <?php endfor; ?>

                <?php if ($page < $total_pages): ?>
                    <a href="?page=<?php echo $page + 1; ?>">Successiva »</a>
                <?php endif; ?>
            </div>
        <?php endif; ?>
    </div>
</body>
</html>
