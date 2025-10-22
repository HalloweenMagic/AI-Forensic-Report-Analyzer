<?php
/**
 * WhatsApp Forensic Analyzer - Backoffice Licenze
 * Visualizza accessi al programma senza licenza
 *
 * © 2025 Luca Mercatanti
 */

require_once 'config.php';
require_auth();

$conn = get_db_connection();

// Paginazione
$page = isset($_GET['page']) ? (int)$_GET['page'] : 1;
$per_page = 50;
$offset = ($page - 1) * $per_page;

// Filtri
$filter_hardware_id = $_GET['hardware_id'] ?? '';
$filter_hostname = $_GET['hostname'] ?? '';

// Query base
$where_conditions = [];
$params = [];
$types = '';

if ($filter_hardware_id) {
    $where_conditions[] = "hardware_id LIKE ?";
    $params[] = "%{$filter_hardware_id}%";
    $types .= 's';
}

if ($filter_hostname) {
    $where_conditions[] = "hostname LIKE ?";
    $params[] = "%{$filter_hostname}%";
    $types .= 's';
}

$where_sql = '';
if (count($where_conditions) > 0) {
    $where_sql = 'WHERE ' . implode(' AND ', $where_conditions);
}

// Conta totale
$count_sql = "SELECT COUNT(*) as total FROM log_accessi_senza_licenza $where_sql";
$count_stmt = $conn->prepare($count_sql);
if (count($params) > 0) {
    $count_stmt->bind_param($types, ...$params);
}
$count_stmt->execute();
$total = $count_stmt->get_result()->fetch_assoc()['total'];
$count_stmt->close();

$total_pages = ceil($total / $per_page);

// Recupera accessi (crea nuovi array params per evitare conflitti)
$sql = "SELECT * FROM log_accessi_senza_licenza $where_sql ORDER BY timestamp DESC LIMIT ? OFFSET ?";
$stmt = $conn->prepare($sql);

// Ricrea array params per la SELECT
$select_params = $params;
$select_params[] = $per_page;
$select_params[] = $offset;
$select_types = $types . 'ii';

if (count($select_params) > 0) {
    $stmt->bind_param($select_types, ...$select_params);
}
$stmt->execute();
$result = $stmt->get_result();
$accessi = $result->fetch_all(MYSQLI_ASSOC);
$stmt->close();

// Statistiche
$stats_sql = "
    SELECT
        COUNT(*) as totale_accessi,
        COUNT(DISTINCT hardware_id) as pc_unici,
        COUNT(DISTINCT DATE(timestamp)) as giorni_unici
    FROM log_accessi_senza_licenza
";
$stats = $conn->query($stats_sql)->fetch_assoc();

$conn->close();
?>
<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Accessi Senza Licenza - Backoffice Licenze</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Accessi Senza Licenza</h1>
            <div class="user-info">
                Admin: <?php echo h($_SESSION['username']); ?> |
                <a href="logout.php" style="color: #dc3545;">Logout</a>
            </div>
        </div>

        <div class="nav">
            <a href="index.php">Dashboard</a>
            <a href="licenze.php">Gestione Licenze</a>
            <a href="attivazioni.php">Attivazioni Hardware</a>
            <a href="logs.php">Log Utilizzo</a>
            <a href="accessi_senza_licenza.php" class="active">Accessi Senza Licenza</a>
        </div>

        <!-- Statistiche -->
        <div class="stats">
            <div class="stat-card">
                <h3>Totale Accessi</h3>
                <div class="value"><?php echo number_format($stats['totale_accessi']); ?></div>
            </div>
            <div class="stat-card">
                <h3>PC Unici</h3>
                <div class="value"><?php echo number_format($stats['pc_unici']); ?></div>
            </div>
            <div class="stat-card">
                <h3>Giorni con Accessi</h3>
                <div class="value"><?php echo number_format($stats['giorni_unici']); ?></div>
            </div>
        </div>

        <!-- Filtri -->
        <div class="card">
            <h2>🔍 Filtri</h2>
            <form method="GET" class="filter-form">
                <div class="form-row">
                    <div class="form-group">
                        <label>Hardware ID:</label>
                        <input type="text" name="hardware_id" value="<?php echo htmlspecialchars($filter_hardware_id); ?>" placeholder="Cerca per Hardware ID">
                    </div>
                    <div class="form-group">
                        <label>Hostname:</label>
                        <input type="text" name="hostname" value="<?php echo htmlspecialchars($filter_hostname); ?>" placeholder="Cerca per Hostname">
                    </div>
                </div>
                <button type="submit" class="btn-primary">Applica Filtri</button>
                <a href="accessi_senza_licenza.php" class="btn-secondary">Reset</a>
            </form>
        </div>

        <!-- Tabella Accessi -->
        <div class="card">
            <h2>📋 Elenco Accessi (<?php echo number_format($total); ?>)</h2>

            <?php if (count($accessi) > 0): ?>
                <table>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Data/Ora</th>
                            <th>Hardware ID</th>
                            <th>Hostname</th>
                            <th>Sistema Operativo</th>
                            <th>IP</th>
                        </tr>
                    </thead>
                    <tbody>
                        <?php foreach ($accessi as $accesso): ?>
                            <tr>
                                <td><?php echo $accesso['id']; ?></td>
                                <td><?php echo date('d/m/Y H:i:s', strtotime($accesso['timestamp'])); ?></td>
                                <td title="<?php echo htmlspecialchars($accesso['hardware_id']); ?>">
                                    <code><?php echo substr(htmlspecialchars($accesso['hardware_id']), 0, 16); ?>...</code>
                                </td>
                                <td><?php echo htmlspecialchars($accesso['hostname']) ?: '-'; ?></td>
                                <td><?php echo htmlspecialchars($accesso['os_info']) ?: '-'; ?></td>
                                <td><?php echo htmlspecialchars($accesso['ip_address']) ?: '-'; ?></td>
                            </tr>
                        <?php endforeach; ?>
                    </tbody>
                </table>

                <!-- Paginazione -->
                <?php if ($total_pages > 1): ?>
                    <div class="pagination">
                        <?php if ($page > 1): ?>
                            <a href="?page=<?php echo $page - 1; ?><?php echo $filter_hardware_id ? '&hardware_id=' . urlencode($filter_hardware_id) : ''; ?><?php echo $filter_hostname ? '&hostname=' . urlencode($filter_hostname) : ''; ?>">
                                &laquo; Precedente
                            </a>
                        <?php endif; ?>

                        <span>Pagina <?php echo $page; ?> di <?php echo $total_pages; ?></span>

                        <?php if ($page < $total_pages): ?>
                            <a href="?page=<?php echo $page + 1; ?><?php echo $filter_hardware_id ? '&hardware_id=' . urlencode($filter_hardware_id) : ''; ?><?php echo $filter_hostname ? '&hostname=' . urlencode($filter_hostname) : ''; ?>">
                                Successiva &raquo;
                            </a>
                        <?php endif; ?>
                    </div>
                <?php endif; ?>

            <?php else: ?>
                <p class="info-message">ℹ️ Nessun accesso senza licenza registrato.</p>
            <?php endif; ?>
        </div>

        <footer>
            <p>© 2025 Luca Mercatanti - Sistema Gestione Licenze</p>
        </footer>
    </div>
</body>
</html>
