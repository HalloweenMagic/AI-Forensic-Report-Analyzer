<?php
/**
 * WhatsApp Forensic Analyzer - Sistema Licenze
 * Pagina Login Admin
 *
 * © 2025 Luca Mercatanti
 */

require_once 'config.php';

session_name(SESSION_NAME);
session_start();

// Se già autenticato, redirect alla dashboard
if (is_authenticated()) {
    header('Location: index.php');
    exit;
}

$error = '';

// Gestione form login
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $username = $_POST['username'] ?? '';
    $password = $_POST['password'] ?? '';

    if ($username === ADMIN_USERNAME && $password === ADMIN_PASSWORD) {
        // Login successo
        $_SESSION['authenticated'] = true;
        $_SESSION['username'] = $username;
        $_SESSION['last_activity'] = time();

        header('Location: index.php');
        exit;
    } else {
        $error = 'Username o password errati';
    }
}

// Gestione timeout sessione
$timeout_message = '';
if (isset($_GET['timeout'])) {
    $timeout_message = 'Sessione scaduta. Effettua nuovamente il login.';
}
?>
<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - Sistema Licenze AFRA</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <div class="login-container">
        <div style="text-align: center; margin-bottom: 30px;">
            <h1 style="color: #667eea;">🔐 Sistema Licenze</h1>
            <p style="color: #666; margin-top: 10px;">WhatsApp Forensic Analyzer</p>
        </div>

        <?php if ($error): ?>
            <div class="alert alert-danger">
                <?php echo h($error); ?>
            </div>
        <?php endif; ?>

        <?php if ($timeout_message): ?>
            <div class="alert alert-info">
                <?php echo h($timeout_message); ?>
            </div>
        <?php endif; ?>

        <form method="POST" action="">
            <div class="form-group">
                <label for="username">Username</label>
                <input type="text" id="username" name="username" required autofocus>
            </div>

            <div class="form-group">
                <label for="password">Password</label>
                <input type="password" id="password" name="password" required>
            </div>

            <button type="submit" class="btn btn-primary" style="width: 100%;">
                Accedi
            </button>
        </form>

        <div style="margin-top: 30px; text-align: center; color: #999; font-size: 12px;">
            © 2025 Luca Mercatanti
        </div>
    </div>
</body>
</html>
