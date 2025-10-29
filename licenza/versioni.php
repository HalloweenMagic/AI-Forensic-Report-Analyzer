<?php
/**
 * WhatsApp Forensic Analyzer - Sistema Licenze
 * Gestione Versioni Applicazione
 *
 * © 2025 Luca Mercatanti
 */

require_once 'config.php';
require_auth();

$conn = get_db_connection();

// Gestione form inserimento/modifica
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $action = $_POST['action'] ?? '';

    if ($action === 'add') {
        // Aggiungi nuova versione
        $version = trim($_POST['version'] ?? '');
        $release_date = $_POST['release_date'] ?? '';
        $download_url = trim($_POST['download_url'] ?? '');
        $changelog = trim($_POST['changelog'] ?? '');

        if ($version && $release_date && $download_url) {
            // Disattiva TUTTE le versioni precedenti
            $conn->query("UPDATE app_versions SET is_active = 0");

            // Inserisci nuova versione come attiva
            $stmt = $conn->prepare("
                INSERT INTO app_versions (version, release_date, download_url, changelog, is_active)
                VALUES (?, ?, ?, ?, 1)
            ");
            $stmt->bind_param('ssss', $version, $release_date, $download_url, $changelog);

            if ($stmt->execute()) {
                $success_message = "✓ Versione $version aggiunta e pubblicata con successo!";
            } else {
                $error_message = "✗ Errore: " . $stmt->error;
            }
            $stmt->close();
        } else {
            $error_message = "✗ Compila tutti i campi obbligatori (versione, data, URL)";
        }
    } elseif ($action === 'delete') {
        // Elimina versione
        $id = intval($_POST['id'] ?? 0);
        if ($id > 0) {
            $stmt = $conn->prepare("DELETE FROM app_versions WHERE id = ?");
            $stmt->bind_param('i', $id);
            if ($stmt->execute()) {
                $success_message = "✓ Versione eliminata";
            }
            $stmt->close();
        }
    } elseif ($action === 'activate') {
        // Attiva una versione specifica (disattiva tutte le altre)
        $id = intval($_POST['id'] ?? 0);
        if ($id > 0) {
            // Disattiva tutte
            $conn->query("UPDATE app_versions SET is_active = 0");

            // Attiva solo quella selezionata
            $stmt = $conn->prepare("UPDATE app_versions SET is_active = 1 WHERE id = ?");
            $stmt->bind_param('i', $id);
            if ($stmt->execute()) {
                $success_message = "✓ Versione attivata e pubblicata";
            }
            $stmt->close();
        }
    }
}

// Recupera tutte le versioni (ordinate dalla più recente)
$versions = $conn->query("
    SELECT id, version, release_date, download_url, changelog, is_active, created_at
    FROM app_versions
    ORDER BY id DESC
");

$conn->close();
?>
<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gestione Versioni - Sistema Licenze AFRA</title>
    <link rel="stylesheet" href="style.css">
    <style>
        .form-container {
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            padding: 25px;
            margin-bottom: 30px;
        }
        .form-row {
            display: flex;
            gap: 15px;
            margin-bottom: 15px;
            align-items: flex-start;
        }
        .form-group {
            flex: 1;
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
            padding: 10px;
            border: 1px solid #ced4da;
            border-radius: 4px;
            font-size: 14px;
        }
        .form-group textarea {
            min-height: 100px;
            resize: vertical;
            font-family: monospace;
        }
        .form-group small {
            display: block;
            color: #6c757d;
            margin-top: 5px;
            font-size: 12px;
        }
        .btn-primary {
            background: #667eea;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
            font-weight: 600;
        }
        .btn-primary:hover {
            background: #5568d3;
        }
        .version-card {
            background: white;
            border: 2px solid #e9ecef;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 15px;
            transition: all 0.2s;
        }
        .version-card.active {
            border-color: #28a745;
            background: #f0fff4;
        }
        .version-card:hover {
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .version-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        .version-title {
            font-size: 1.3em;
            font-weight: bold;
            color: #333;
        }
        .version-date {
            color: #6c757d;
            font-size: 0.9em;
        }
        .version-status {
            display: inline-block;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 600;
            margin-left: 10px;
        }
        .status-active {
            background: #28a745;
            color: white;
        }
        .status-inactive {
            background: #6c757d;
            color: white;
        }
        .version-url {
            color: #667eea;
            word-break: break-all;
            font-size: 0.9em;
            display: block;
            margin: 10px 0;
        }
        .version-changelog {
            background: #f8f9fa;
            padding: 15px;
            border-left: 4px solid #667eea;
            margin: 15px 0;
            white-space: pre-wrap;
            font-family: monospace;
            font-size: 0.85em;
        }
        .version-actions {
            display: flex;
            gap: 10px;
            margin-top: 15px;
        }
        .btn-sm {
            padding: 6px 12px;
            font-size: 0.85em;
            border-radius: 4px;
            cursor: pointer;
            border: none;
            font-weight: 600;
        }
        .btn-activate {
            background: #28a745;
            color: white;
        }
        .btn-delete {
            background: #dc3545;
            color: white;
        }
        .alert {
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
        .alert-success {
            background: #d4edda;
            border: 1px solid #c3e6cb;
            color: #155724;
        }
        .alert-error {
            background: #f8d7da;
            border: 1px solid #f5c6cb;
            color: #721c24;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Gestione Versioni App</h1>
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
            <a href="accessi_senza_licenza.php">Accessi Senza Licenza</a>
            <a href="versioni.php" class="active">Versioni App</a>
        </div>

        <?php if (isset($success_message)): ?>
            <div class="alert alert-success"><?php echo h($success_message); ?></div>
        <?php endif; ?>

        <?php if (isset($error_message)): ?>
            <div class="alert alert-error"><?php echo h($error_message); ?></div>
        <?php endif; ?>

        <!-- Form Aggiunta Nuova Versione -->
        <div class="form-container">
            <h2>➕ Aggiungi Nuova Versione</h2>
            <form method="POST">
                <input type="hidden" name="action" value="add">

                <div class="form-row">
                    <div class="form-group" style="flex: 0 0 150px;">
                        <label>Versione *</label>
                        <input type="text" name="version" placeholder="es. 4.0.0" required>
                        <small>Formato: X.Y.Z</small>
                    </div>

                    <div class="form-group" style="flex: 0 0 180px;">
                        <label>Data Rilascio *</label>
                        <input type="date" name="release_date" value="<?php echo date('Y-m-d'); ?>" required>
                        <small>Data pubblicazione</small>
                    </div>

                    <div class="form-group" style="flex: 1;">
                        <label>URL Download (GitHub) *</label>
                        <input type="url" name="download_url" placeholder="https://github.com/user/repo/releases/download/v4.0.0/file.exe" required>
                        <small>Link diretto al file .exe su GitHub Releases</small>
                    </div>
                </div>

                <div class="form-group">
                    <label>Changelog (opzionale)</label>
                    <textarea name="changelog" placeholder="- Nuova feature X&#10;- Fix bug Y&#10;- Miglioramento Z"></textarea>
                    <small>Se vuoto, il dialog utente non mostrerà il changelog. Una riga per punto.</small>
                </div>

                <button type="submit" class="btn-primary">✓ Aggiungi e Pubblica Versione</button>
                <small style="display: block; margin-top: 10px; color: #6c757d;">
                    ⚠️ La nuova versione verrà automaticamente attivata e tutte le precedenti disattivate
                </small>
            </form>
        </div>

        <!-- Lista Versioni -->
        <h2>📦 Versioni Rilasciate</h2>

        <?php if ($versions->num_rows === 0): ?>
            <p style="text-align: center; color: #6c757d; padding: 40px;">
                Nessuna versione inserita. Aggiungi la prima versione utilizzando il form sopra.
            </p>
        <?php else: ?>
            <?php while ($v = $versions->fetch_assoc()): ?>
                <div class="version-card <?php echo $v['is_active'] ? 'active' : ''; ?>">
                    <div class="version-header">
                        <div>
                            <span class="version-title">v<?php echo h($v['version']); ?></span>
                            <span class="version-status <?php echo $v['is_active'] ? 'status-active' : 'status-inactive'; ?>">
                                <?php echo $v['is_active'] ? '🟢 ATTIVA (Pubblicata)' : '⚪ Storico'; ?>
                            </span>
                        </div>
                        <div class="version-date">
                            Rilasciata: <?php echo date('d/m/Y', strtotime($v['release_date'])); ?>
                        </div>
                    </div>

                    <strong>URL Download:</strong>
                    <a href="<?php echo h($v['download_url']); ?>" target="_blank" class="version-url">
                        <?php echo h($v['download_url']); ?>
                    </a>

                    <?php if ($v['changelog']): ?>
                        <strong>Changelog:</strong>
                        <div class="version-changelog"><?php echo h($v['changelog']); ?></div>
                    <?php else: ?>
                        <p style="color: #6c757d; font-style: italic;">Nessun changelog</p>
                    <?php endif; ?>

                    <small style="color: #6c757d;">
                        Inserita il: <?php echo date('d/m/Y H:i', strtotime($v['created_at'])); ?>
                    </small>

                    <div class="version-actions">
                        <?php if (!$v['is_active']): ?>
                            <form method="POST" style="display: inline;">
                                <input type="hidden" name="action" value="activate">
                                <input type="hidden" name="id" value="<?php echo $v['id']; ?>">
                                <button type="submit" class="btn-sm btn-activate"
                                        onclick="return confirm('Attivare questa versione? Tutte le altre verranno disattivate.')">
                                    🟢 Attiva e Pubblica
                                </button>
                            </form>
                        <?php endif; ?>

                        <form method="POST" style="display: inline;">
                            <input type="hidden" name="action" value="delete">
                            <input type="hidden" name="id" value="<?php echo $v['id']; ?>">
                            <button type="submit" class="btn-sm btn-delete"
                                    onclick="return confirm('Eliminare questa versione? Azione irreversibile!')">
                                🗑️ Elimina
                            </button>
                        </form>
                    </div>
                </div>
            <?php endwhile; ?>
        <?php endif; ?>

        <div style="margin-top: 40px; padding: 20px; background: #e7f3ff; border-radius: 8px;">
            <h3>ℹ️ Come Funziona</h3>
            <ol style="line-height: 2;">
                <li><strong>Aggiungi versione:</strong> Compila il form sopra con versione, data e URL GitHub</li>
                <li><strong>Pubblicazione automatica:</strong> La nuova versione viene automaticamente attivata</li>
                <li><strong>Notifica utenti:</strong> Gli utenti all'avvio dell'app vedranno il dialog di aggiornamento</li>
                <li><strong>Storico:</strong> Le versioni precedenti rimangono nel database per statistiche</li>
                <li><strong>Riattivazione:</strong> Puoi riattivare una versione precedente se necessario (es. rollback)</li>
            </ol>
        </div>
    </div>
</body>
</html>
