@echo off
chcp 65001 >nul
cls
echo ╔═══════════════════════════════════════════════════════════════╗
echo ║   WhatsApp Forensic Analyzer v3.2.2 - Installazione         ║
echo ║   © 2025 Luca Mercatanti - https://mercatanti.com            ║
echo ╚═══════════════════════════════════════════════════════════════╝
echo.
echo Installazione dipendenze Python in corso...
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRORE] Python non trovato!
    echo.
    echo Installa Python da: https://www.python.org/downloads/
    echo Assicurati di spuntare "Add Python to PATH" durante l'installazione.
    echo.
    pause
    exit /b 1
)

echo [1/3] Verifica Python...
python --version
echo.

echo [2/3] Aggiornamento pip...
python -m pip install --upgrade pip --quiet
echo.

echo [3/3] Installazione librerie richieste...
python -m pip install -r requirements.txt
echo.

if errorlevel 1 (
    echo.
    echo [ERRORE] Installazione fallita!
    echo Controlla gli errori sopra e riprova.
    echo.
    pause
    exit /b 1
)

echo.
echo ╔═══════════════════════════════════════════════════════════════╗
echo ║                  INSTALLAZIONE COMPLETATA!                    ║
echo ╚═══════════════════════════════════════════════════════════════╝
echo.
echo Librerie installate:
echo   • PyPDF2         - Lettura PDF
echo   • openai         - API OpenAI (GPT-4o, GPT-3.5)
echo   • anthropic      - API Anthropic (Claude 3.5)
echo   • requests       - API Ollama (modelli locali)
echo   • cryptography   - Sicurezza API keys
echo.
echo Ora puoi avviare il programma con: avvia.bat
echo.
pause
