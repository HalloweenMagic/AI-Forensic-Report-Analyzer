<?php
/**
 * WhatsApp Forensic Analyzer - Sistema Licenze
 * Gestione Licenze (CRUD)
 *
 * © 2025 Luca Mercatanti
 */

require_once 'config.php';
require_auth();

$conn = get_db_connection();
$message = '';
$message_type = '';

// Gestione azioni
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $action = $_POST['action'] ?? '';

    switch ($action) {
        case 'create':
            $license_key = $_POST['license_key'] ?? generate_license_key();
            $nome = $_POST['nome'] ?? '';
            $cognome = $_POST['cognome'] ?? '';
            $email = $_POST['email'] ?? '';
            $note = $_POST['note'] ?? '';

            $stmt = $conn->prepare("INSERT INTO licenze (license_key, nome, cognome, email, note) VALUES (?, ?, ?, ?, ?)");
            $stmt->bind_param('sssss', $license_key, $nome, $cognome, $email, $note);

            if ($stmt->execute()) {
                $message = 'Licenza creata con successo!';
                $message_type = 'success';
            } else {
                $message = 'Errore creazione licenza: ' . $stmt->error;
                $message_type = 'danger';
            }
            $stmt->close();
            break;

        case 'toggle':
            $id = $_POST['id'] ?? 0;
            $stmt = $conn->prepare("UPDATE licenze SET attiva = NOT attiva WHERE id = ?");
            $stmt->bind_param('i', $id);

            if ($stmt->execute()) {
                $message = 'Stato licenza aggiornato!';
                $message_type = 'success';
            }
            $stmt->close();
            break;

        case 'delete':
            $id = $_POST['id'] ?? 0;
            $stmt = $conn->prepare("DELETE FROM licenze WHERE id = ?");
            $stmt->bind_param('i', $id);

            if ($stmt->execute()) {
                $message = 'Licenza eliminata!';
                $message_type = 'success';
            }
            $stmt->close();
            break;
    }
}

// Recupera tutte le licenze
$licenses = $conn->query("
    SELECT l.*,
           (SELECT COUNT(*) FROM attivazioni_hardware WHERE licenza_id = l.id) as num_attivazioni
    FROM licenze l
    ORDER BY data_creazione DESC
");

$conn->close();
?>
<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gestione Licenze - Sistema Licenze AFRA</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔑 Gestione Licenze</h1>
            <div class="user-info">
                Admin: <?php echo h($_SESSION['username']); ?> |
                <a href="logout.php" style="color: #dc3545;">Logout</a>
            </div>
        </div>

        <div class="nav">
            <a href="index.php">Dashboard</a>
            <a href="licenze.php" class="active">Gestione Licenze</a>
            <a href="attivazioni.php">Attivazioni Hardware</a>
            <a href="logs.php">Log Utilizzo</a>
            <a href="accessi_senza_licenza.php">Accessi Senza Licenza</a>
        </div>

        <?php if ($message): ?>
            <div class="alert alert-<?php echo $message_type; ?>">
                <?php echo h($message); ?>
            </div>
        <?php endif; ?>

        <!-- Form Creazione Nuova Licenza -->
        <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 30px;">
            <h3>➕ Crea Nuova Licenza</h3>
            <form method="POST" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-top: 15px;">
                <input type="hidden" name="action" value="create">

                <div class="form-group" style="margin: 0;">
                    <label>Chiave Licenza</label>
                    <input type="text" name="license_key" placeholder="Auto-generata" value="<?php echo generate_license_key(); ?>">
                </div>

                <div class="form-group" style="margin: 0;">
                    <label>Nome</label>
                    <input type="text" name="nome" required>
                </div>

                <div class="form-group" style="margin: 0;">
                    <label>Cognome</label>
                    <input type="text" name="cognome" required>
                </div>

                <div class="form-group" style="margin: 0;">
                    <label>Email</label>
                    <input type="email" name="email" required>
                </div>

                <div class="form-group" style="margin: 0; grid-column: 1 / -1;">
                    <label>Note (opzionale)</label>
                    <textarea name="note" rows="2"></textarea>
                </div>

                <div style="grid-column: 1 / -1;">
                    <button type="submit" class="btn btn-success">✓ Crea Licenza</button>
                </div>
            </form>
        </div>

        <!-- Tabella Licenze -->
        <h2>📋 Tutte le Licenze</h2>
        <table>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Chiave Licenza</th>
                    <th>Nome</th>
                    <th>Email</th>
                    <th>Attivazioni</th>
                    <th>Stato</th>
                    <th>Data Creazione</th>
                    <th>Ultimo Utilizzo</th>
                    <th>Azioni</th>
                </tr>
            </thead>
            <tbody>
                <?php while ($row = $licenses->fetch_assoc()): ?>
                <tr>
                    <td><?php echo $row['id']; ?></td>
                    <td><code><?php echo h($row['license_key']); ?></code></td>
                    <td><?php echo h($row['nome'] . ' ' . $row['cognome']); ?></td>
                    <td><?php echo h($row['email']); ?></td>
                    <td>
                        <?php if ($row['num_attivazioni'] > 0): ?>
                            <a href="attivazioni.php?licenza_id=<?php echo $row['id']; ?>">
                                <?php echo $row['num_attivazioni']; ?> PC
                            </a>
                        <?php else: ?>
                            -
                        <?php endif; ?>
                    </td>
                    <td>
                        <?php if ($row['attiva']): ?>
                            <span class="badge badge-success">Attiva</span>
                        <?php else: ?>
                            <span class="badge badge-danger">Revocata</span>
                        <?php endif; ?>
                    </td>
                    <td><?php echo format_date($row['data_creazione']); ?></td>
                    <td><?php echo format_date($row['ultimo_utilizzo']); ?></td>
                    <td>
                        <form method="POST" style="display: inline;">
                            <input type="hidden" name="action" value="toggle">
                            <input type="hidden" name="id" value="<?php echo $row['id']; ?>">
                            <button type="submit" class="btn btn-warning btn-sm">
                                <?php echo $row['attiva'] ? 'Revoca' : 'Attiva'; ?>
                            </button>
                        </form>

                        <form method="POST" style="display: inline;" onsubmit="return confirm('Eliminare questa licenza?');">
                            <input type="hidden" name="action" value="delete">
                            <input type="hidden" name="id" value="<?php echo $row['id']; ?>">
                            <button type="submit" class="btn btn-danger btn-sm">Elimina</button>
                        </form>
                    </td>
                </tr>
                <?php endwhile; ?>
            </tbody>
        </table>
    </div>
</body>
</html>
