@echo off
title WhatsApp Forensic Analyzer
echo ========================================
echo WhatsApp Forensic Analyzer
echo Analisi Report WhatsApp con AI
echo ========================================
echo.
echo Avvio applicazione in corso...
echo.
python whatsapp_analyzer_gui.py
if errorlevel 1 (
    echo.
    echo ERRORE: Impossibile avviare l'applicazione
    echo Verifica che Python sia installato correttamente
    echo e che tutte le dipendenze siano state installate.
    echo.
    echo Esegui: pip install -r requirements.txt
    echo.
    pause
)
