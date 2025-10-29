<?php
/**
 * WhatsApp Forensic Analyzer - Sistema Licenze
 * Dettagli Utente Completi
 *
 * © 2025 Luca Mercatanti
 */

require_once 'config.php';
require_auth();

$conn = get_db_connection();
$message = '';
$message_type = '';

// Recupera ID utente/licenza
$licenza_id = isset($_GET['id']) ? intval($_GET['id']) : 0;

if ($licenza_id <= 0) {
    header('Location: licenze.php');
    exit;
}

// Gestione azioni
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $action = $_POST['action'] ?? '';

    switch ($action) {
        case 'update':
            // Aggiorna dati licenza
            $nome = trim($_POST['nome'] ?? '');
            $cognome = trim($_POST['cognome'] ?? '');
            $email = trim($_POST['email'] ?? '');
            $note = trim($_POST['note'] ?? '');

            $stmt = $conn->prepare("UPDATE licenze SET nome = ?, cognome = ?, email = ?, note = ? WHERE id = ?");
            $stmt->bind_param('ssssi', $nome, $cognome, $email, $note, $licenza_id);

            if ($stmt->execute()) {
                $message = '✓ Dati aggiornati con successo!';
                $message_type = 'success';
            } else {
                $message = '✗ Errore aggiornamento: ' . $stmt->error;
                $message_type = 'danger';
            }
            $stmt->close();
            break;

        case 'toggle':
            // Revoca/Attiva licenza
            $stmt = $conn->prepare("UPDATE licenze SET attiva = NOT attiva WHERE id = ?");
            $stmt->bind_param('i', $licenza_id);

            if ($stmt->execute()) {
                $message = '✓ Stato licenza modificato!';
                $message_type = 'success';
            }
            $stmt->close();
            break;

        case 'delete':
            // Elimina licenza (CASCADE eliminerà anche attivazioni e log)
            $stmt = $conn->prepare("DELETE FROM licenze WHERE id = ?");
            $stmt->bind_param('i', $licenza_id);

            if ($stmt->execute()) {
                header('Location: licenze.php?deleted=1');
                exit;
            }
            $stmt->close();
            break;

        case 'delete_activation':
            // Elimina singola attivazione hardware
            $activation_id = intval($_POST['activation_id'] ?? 0);
            if ($activation_id > 0) {
                $stmt = $conn->prepare("DELETE FROM attivazioni_hardware WHERE id = ? AND licenza_id = ?");
                $stmt->bind_param('ii', $activation_id, $licenza_id);

                if ($stmt->execute()) {
                    $message = '✓ Attivazione hardware rimossa!';
                    $message_type = 'success';
                }
                $stmt->close();
            }
            break;
    }
}

// Recupera dati licenza
$stmt = $conn->prepare("SELECT * FROM licenze WHERE id = ?");
$stmt->bind_param('i', $licenza_id);
$stmt->execute();
$licenza = $stmt->get_result()->fetch_assoc();
$stmt->close();

if (!$licenza) {
    header('Location: licenze.php');
    exit;
}

// Recupera attivazioni hardware
$attivazioni = $conn->query("
    SELECT * FROM attivazioni_hardware
    WHERE licenza_id = $licenza_id
    ORDER BY ultimo_ping DESC
");

// Recupera statistiche utilizzo
$stats = $conn->query("
    SELECT
        COUNT(*) as utilizzi_totali,
        COUNT(DISTINCT hardware_id) as pc_diversi,
        COUNT(CASE WHEN DATE(timestamp) = CURDATE() THEN 1 END) as utilizzi_oggi,
        COUNT(CASE WHEN YEARWEEK(timestamp, 1) = YEARWEEK(CURDATE(), 1) THEN 1 END) as utilizzi_settimana,
        GROUP_CONCAT(DISTINCT app_version ORDER BY app_version DESC SEPARATOR ', ') as versioni_usate,
        MAX(timestamp) as ultimo_utilizzo
    FROM log_utilizzo
    WHERE licenza_id = $licenza_id
")->fetch_assoc();

// Filtri log
$filter_pc = $_GET['filter_pc'] ?? '';
$filter_period = $_GET['filter_period'] ?? '7days';

// Query log con filtri
$where_conditions = ["licenza_id = $licenza_id"];
$having_clause = "";

if ($filter_pc && $filter_pc !== 'all') {
    $filter_pc_safe = $conn->real_escape_string($filter_pc);
    $where_conditions[] = "hardware_id = '$filter_pc_safe'";
}

// Filtro periodo
switch ($filter_period) {
    case 'today':
        $where_conditions[] = "DATE(timestamp) = CURDATE()";
        break;
    case '7days':
        $where_conditions[] = "timestamp >= DATE_SUB(NOW(), INTERVAL 7 DAY)";
        break;
    case '30days':
        $where_conditions[] = "timestamp >= DATE_SUB(NOW(), INTERVAL 30 DAY)";
        break;
    case 'all':
    default:
        // Nessun filtro periodo
        break;
}

$where_sql = implode(' AND ', $where_conditions);

// Log utilizzo (ultimi 50)
$logs = $conn->query("
    SELECT * FROM log_utilizzo
    WHERE $where_sql
    ORDER BY timestamp DESC
    LIMIT 50
");

// Dati per grafico timeline (ultimi 30 giorni)
$timeline_data = $conn->query("
    SELECT
        DATE(timestamp) as data,
        COUNT(*) as utilizzi
    FROM log_utilizzo
    WHERE licenza_id = $licenza_id
      AND timestamp >= DATE_SUB(NOW(), INTERVAL 30 DAY)
    GROUP BY DATE(timestamp)
    ORDER BY data ASC
");

// Lista PC unici per filtro dropdown
$pc_list = $conn->query("
    SELECT DISTINCT hardware_id, hostname
    FROM log_utilizzo
    WHERE licenza_id = $licenza_id
    ORDER BY hostname
");

$conn->close();
?>
<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dettagli Utente - <?php echo h($licenza['nome'] . ' ' . $licenza['cognome']); ?></title>
    <link rel="stylesheet" href="style.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        .breadcrumb {
            background: #f8f9fa;
            padding: 12px 20px;
            border-radius: 5px;
            margin-bottom: 20px;
            font-size: 14px;
        }
        .breadcrumb a {
            color: #667eea;
            text-decoration: none;
        }
        .breadcrumb a:hover {
            text-decoration: underline;
        }
        .info-card {
            background: white;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            padding: 25px;
            margin-bottom: 25px;
        }
        .info-card h2 {
            margin-top: 0;
            color: #333;
            font-size: 1.3em;
            margin-bottom: 20px;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }
        .form-row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin-bottom: 15px;
        }
        .form-group {
            margin-bottom: 15px;
        }
        .form-group label {
            display: block;
            font-weight: 600;
            margin-bottom: 5px;
            color: #495057;
        }
        .form-group input,
        .form-group textarea {
            width: 100%;
            padding: 8px 12px;
            border: 1px solid #ced4da;
            border-radius: 4px;
            font-size: 14px;
        }
        .form-group textarea {
            min-height: 80px;
            resize: vertical;
        }
        .info-row {
            display: flex;
            padding: 10px 0;
            border-bottom: 1px solid #f0f0f0;
        }
        .info-row:last-child {
            border-bottom: none;
        }
        .info-label {
            font-weight: 600;
            width: 180px;
            color: #6c757d;
        }
        .info-value {
            flex: 1;
            color: #333;
        }
        .activation-box {
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 5px;
            padding: 15px;
            margin-bottom: 12px;
        }
        .activation-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        .activation-title {
            font-weight: bold;
            font-size: 1.1em;
            color: #333;
        }
        .activation-detail {
            font-size: 0.9em;
            color: #6c757d;
            margin: 5px 0;
        }
        .btn {
            padding: 8px 16px;
            border-radius: 4px;
            border: none;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            text-decoration: none;
            display: inline-block;
        }
        .btn-primary {
            background: #667eea;
            color: white;
        }
        .btn-primary:hover {
            background: #5568d3;
        }
        .btn-success {
            background: #28a745;
            color: white;
        }
        .btn-success:hover {
            background: #218838;
        }
        .btn-warning {
            background: #ffc107;
            color: #333;
        }
        .btn-warning:hover {
            background: #e0a800;
        }
        .btn-danger {
            background: #dc3545;
            color: white;
        }
        .btn-danger:hover {
            background: #c82333;
        }
        .btn-sm {
            padding: 5px 10px;
            font-size: 12px;
        }
        .button-group {
            display: flex;
            gap: 10px;
            margin-top: 15px;
        }
        .badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
        }
        .badge-success {
            background: #d4edda;
            color: #155724;
        }
        .badge-danger {
            background: #f8d7da;
            color: #721c24;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        .stat-box {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }
        .stat-value {
            font-size: 2em;
            font-weight: bold;
            margin-bottom: 5px;
        }
        .stat-label {
            font-size: 0.9em;
            opacity: 0.9;
        }
        .chart-container {
            position: relative;
            height: 300px;
            margin-bottom: 30px;
        }
        .filter-bar {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 15px;
            display: flex;
            gap: 15px;
            align-items: center;
        }
        .filter-bar select {
            padding: 8px 12px;
            border: 1px solid #ced4da;
            border-radius: 4px;
            font-size: 14px;
        }
        .log-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }
        .log-table th {
            background: #f8f9fa;
            padding: 10px;
            text-align: left;
            font-weight: 600;
            border-bottom: 2px solid #dee2e6;
        }
        .log-table td {
            padding: 10px;
            border-bottom: 1px solid #f0f0f0;
        }
        .log-table tr:hover {
            background: #f8f9fa;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>👤 Dettagli Utente: <?php echo h($licenza['nome'] . ' ' . $licenza['cognome']); ?></h1>
            <div class="user-info">
                Admin: <?php echo h($_SESSION['username']); ?> |
                <a href="logout.php" style="color: #dc3545;">Logout</a>
            </div>
        </div>

        <div class="breadcrumb">
            <a href="index.php">Dashboard</a> &gt;
            <a href="licenze.php">Gestione Licenze</a> &gt;
            <strong><?php echo h($licenza['nome'] . ' ' . $licenza['cognome']); ?></strong>
        </div>

        <?php if ($message): ?>
            <div class="alert alert-<?php echo $message_type; ?>" style="margin-bottom: 20px;">
                <?php echo h($message); ?>
            </div>
        <?php endif; ?>

        <!-- INFORMAZIONI LICENZA -->
        <div class="info-card">
            <h2>📋 Informazioni Licenza</h2>

            <form method="POST">
                <input type="hidden" name="action" value="update">

                <div class="info-row">
                    <div class="info-label">Chiave Licenza:</div>
                    <div class="info-value"><code><?php echo h($licenza['license_key']); ?></code></div>
                </div>

                <div class="info-row">
                    <div class="info-label">Stato:</div>
                    <div class="info-value">
                        <?php if ($licenza['attiva']): ?>
                            <span class="badge badge-success">🟢 Attiva</span>
                        <?php else: ?>
                            <span class="badge badge-danger">🔴 Revocata</span>
                        <?php endif; ?>
                    </div>
                </div>

                <div class="form-row">
                    <div class="form-group">
                        <label>Nome:</label>
                        <input type="text" name="nome" value="<?php echo h($licenza['nome']); ?>" required>
                    </div>
                    <div class="form-group">
                        <label>Cognome:</label>
                        <input type="text" name="cognome" value="<?php echo h($licenza['cognome']); ?>" required>
                    </div>
                </div>

                <div class="form-group">
                    <label>Email:</label>
                    <input type="email" name="email" value="<?php echo h($licenza['email']); ?>" required>
                </div>

                <div class="form-group">
                    <label>Note:</label>
                    <textarea name="note"><?php echo h($licenza['note']); ?></textarea>
                </div>

                <div class="info-row">
                    <div class="info-label">Data Creazione:</div>
                    <div class="info-value"><?php echo format_date($licenza['data_creazione']); ?></div>
                </div>

                <div class="info-row">
                    <div class="info-label">Ultimo Utilizzo:</div>
                    <div class="info-value"><?php echo format_date($licenza['ultimo_utilizzo']); ?></div>
                </div>

                <?php if ($licenza['data_scadenza']): ?>
                <div class="info-row">
                    <div class="info-label">Data Scadenza:</div>
                    <div class="info-value"><?php echo format_date($licenza['data_scadenza']); ?></div>
                </div>
                <?php else: ?>
                <div class="info-row">
                    <div class="info-label">Data Scadenza:</div>
                    <div class="info-value"><strong>Perpetua</strong></div>
                </div>
                <?php endif; ?>

                <div class="button-group">
                    <button type="submit" class="btn btn-success">💾 Salva Modifiche</button>
                </div>
            </form>

            <div class="button-group" style="border-top: 1px solid #dee2e6; padding-top: 15px; margin-top: 15px;">
                <form method="POST" style="display: inline;">
                    <input type="hidden" name="action" value="toggle">
                    <button type="submit" class="btn btn-warning"
                            onclick="return confirm('Vuoi <?php echo $licenza['attiva'] ? 'revocare' : 'attivare'; ?> questa licenza?')">
                        🔄 <?php echo $licenza['attiva'] ? 'Revoca' : 'Attiva'; ?> Licenza
                    </button>
                </form>

                <form method="POST" style="display: inline;">
                    <input type="hidden" name="action" value="delete">
                    <button type="submit" class="btn btn-danger"
                            onclick="return confirm('ATTENZIONE: Eliminare questa licenza?\nVerranno eliminate anche tutte le attivazioni e i log associati.\n\nQuesta azione è IRREVERSIBILE!')">
                        🗑️ Elimina Licenza
                    </button>
                </form>
            </div>
        </div>

        <!-- ATTIVAZIONI HARDWARE -->
        <div class="info-card">
            <h2>💻 Attivazioni Hardware (<?php echo $attivazioni->num_rows; ?>)</h2>

            <?php if ($attivazioni->num_rows === 0): ?>
                <p style="color: #6c757d; text-align: center; padding: 20px;">
                    Nessuna attivazione hardware registrata per questa licenza.
                </p>
            <?php else: ?>
                <?php while ($att = $attivazioni->fetch_assoc()): ?>
                    <div class="activation-box">
                        <div class="activation-header">
                            <div class="activation-title">
                                💻 <?php echo h($att['hostname'] ?: 'PC Sconosciuto'); ?>
                            </div>
                            <form method="POST" style="display: inline;">
                                <input type="hidden" name="action" value="delete_activation">
                                <input type="hidden" name="activation_id" value="<?php echo $att['id']; ?>">
                                <button type="submit" class="btn btn-danger btn-sm"
                                        onclick="return confirm('Rimuovere questa attivazione hardware?')">
                                    🗑️ Rimuovi
                                </button>
                            </form>
                        </div>
                        <div class="activation-detail">
                            <strong>Hardware ID:</strong> <?php echo h(substr($att['hardware_id'], 0, 16)); ?>...
                        </div>
                        <div class="activation-detail">
                            <strong>Sistema Operativo:</strong> <?php echo h($att['os_info'] ?: 'N/A'); ?>
                        </div>
                        <div class="activation-detail">
                            <strong>Prima Attivazione:</strong> <?php echo format_date($att['prima_attivazione']); ?>
                        </div>
                        <div class="activation-detail">
                            <strong>Ultimo Ping:</strong> <?php echo format_date($att['ultimo_ping']); ?>
                        </div>
                        <div class="activation-detail">
                            <strong>Ping Totali:</strong> <?php echo number_format($att['conteggio_ping']); ?>
                        </div>
                    </div>
                <?php endwhile; ?>
            <?php endif; ?>
        </div>

        <!-- STATISTICHE -->
        <div class="info-card">
            <h2>📊 Statistiche Utilizzo</h2>

            <div class="stats-grid">
                <div class="stat-box">
                    <div class="stat-value"><?php echo number_format($stats['utilizzi_totali'] ?? 0); ?></div>
                    <div class="stat-label">Utilizzi Totali</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value"><?php echo number_format($stats['utilizzi_settimana'] ?? 0); ?></div>
                    <div class="stat-label">Questa Settimana</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value"><?php echo number_format($stats['utilizzi_oggi'] ?? 0); ?></div>
                    <div class="stat-label">Oggi</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value"><?php echo number_format($stats['pc_diversi'] ?? 0); ?></div>
                    <div class="stat-label">PC Diversi</div>
                </div>
            </div>

            <?php if ($stats['versioni_usate']): ?>
            <div style="margin-bottom: 20px;">
                <strong>Versioni App Usate:</strong> <?php echo h($stats['versioni_usate']); ?>
            </div>
            <?php endif; ?>

            <!-- GRAFICO TIMELINE -->
            <h3 style="margin-top: 30px; margin-bottom: 15px;">📈 Timeline Utilizzi (Ultimi 30 Giorni)</h3>
            <div class="chart-container">
                <canvas id="timelineChart"></canvas>
            </div>
        </div>

        <!-- LOG UTILIZZO -->
        <div class="info-card">
            <h2>📜 Log Utilizzo</h2>

            <form method="GET" class="filter-bar">
                <input type="hidden" name="id" value="<?php echo $licenza_id; ?>">

                <label>
                    <strong>Filtra PC:</strong>
                    <select name="filter_pc" onchange="this.form.submit()">
                        <option value="all" <?php echo $filter_pc === 'all' ? 'selected' : ''; ?>>Tutti i PC</option>
                        <?php
                        $pc_list->data_seek(0);
                        while ($pc = $pc_list->fetch_assoc()):
                        ?>
                            <option value="<?php echo h($pc['hardware_id']); ?>"
                                    <?php echo $filter_pc === $pc['hardware_id'] ? 'selected' : ''; ?>>
                                <?php echo h($pc['hostname'] ?: substr($pc['hardware_id'], 0, 12) . '...'); ?>
                            </option>
                        <?php endwhile; ?>
                    </select>
                </label>

                <label>
                    <strong>Periodo:</strong>
                    <select name="filter_period" onchange="this.form.submit()">
                        <option value="today" <?php echo $filter_period === 'today' ? 'selected' : ''; ?>>Oggi</option>
                        <option value="7days" <?php echo $filter_period === '7days' ? 'selected' : ''; ?>>Ultimi 7 giorni</option>
                        <option value="30days" <?php echo $filter_period === '30days' ? 'selected' : ''; ?>>Ultimi 30 giorni</option>
                        <option value="all" <?php echo $filter_period === 'all' ? 'selected' : ''; ?>>Tutti</option>
                    </select>
                </label>
            </form>

            <?php if ($logs->num_rows === 0): ?>
                <p style="text-align: center; color: #6c757d; padding: 30px;">
                    Nessun log trovato con i filtri selezionati.
                </p>
            <?php else: ?>
                <table class="log-table">
                    <thead>
                        <tr>
                            <th>Timestamp</th>
                            <th>Hostname</th>
                            <th>OS</th>
                            <th>Versione App</th>
                            <th>IP Address</th>
                        </tr>
                    </thead>
                    <tbody>
                        <?php while ($log = $logs->fetch_assoc()): ?>
                            <tr>
                                <td><?php echo format_date($log['timestamp']); ?></td>
                                <td><?php echo h($log['hostname'] ?: 'N/A'); ?></td>
                                <td><?php echo h($log['os_info'] ?: 'N/A'); ?></td>
                                <td><?php echo h($log['app_version'] ?: 'N/A'); ?></td>
                                <td><?php echo h($log['ip_address'] ?: 'N/A'); ?></td>
                            </tr>
                        <?php endwhile; ?>
                    </tbody>
                </table>

                <?php if ($logs->num_rows >= 50): ?>
                    <p style="text-align: center; color: #6c757d; margin-top: 15px; font-size: 13px;">
                        Mostrati ultimi 50 log. Usa i filtri per raffinare la ricerca.
                    </p>
                <?php endif; ?>
            <?php endif; ?>
        </div>

        <div style="margin-top: 30px;">
            <a href="licenze.php" class="btn btn-primary">⬅️ Torna a Gestione Licenze</a>
        </div>
    </div>

    <script>
    // Dati per grafico timeline
    const timelineLabels = <?php
        $labels = [];
        $data = [];
        $timeline_data->data_seek(0);
        while ($row = $timeline_data->fetch_assoc()) {
            $labels[] = date('d/m', strtotime($row['data']));
            $data[] = $row['utilizzi'];
        }
        echo json_encode($labels);
    ?>;
    const timelineData = <?php echo json_encode($data); ?>;

    // Grafico timeline
    const ctx = document.getElementById('timelineChart').getContext('2d');
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: timelineLabels,
            datasets: [{
                label: 'Utilizzi',
                data: timelineData,
                borderColor: '#667eea',
                backgroundColor: 'rgba(102, 126, 234, 0.1)',
                tension: 0.3,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    }
                }
            }
        }
    });
    </script>
</body>
</html>
