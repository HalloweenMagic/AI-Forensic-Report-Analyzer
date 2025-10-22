<?php
/**
 * WhatsApp Forensic Analyzer - Sistema Licenze
 * Logout Admin
 *
 * © 2025 Luca Mercatanti
 */

require_once 'config.php';

session_name(SESSION_NAME);
session_start();
session_destroy();

header('Location: login.php');
exit;
