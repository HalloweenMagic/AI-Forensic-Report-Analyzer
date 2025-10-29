#!/usr/bin/env python3
"""
WhatsApp Forensic Analyzer - Interfaccia Grafica
Analizza report WhatsApp da Cellebrite e altri tool forensi usando AI

Specializzato per: Export PDF da Cellebrite, UFED, Oxygen Forensics
Supporta: OpenAI GPT / Anthropic Claude

© 2025 Luca Mercatanti - https://mercatanti.com
"""

# VERSIONE APPLICAZIONE (aggiorna ad ogni release)
APP_VERSION = "4.0.0"
APP_VERSION_DATE = "2025-10-28"
APP_NAME = "WhatsApp Forensic Analyzer"

import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import threading
import os
import sys
from pathlib import Path
import time

# Importa i moduli backend
sys.path.append(str(Path(__file__).parent))
from whatsapp_processor import WhatsAppProcessor
from ai_analyzer import AIAnalyzer
from api_key_manager import APIKeyManager
from license_manager import LicenseManager
from license_dialog import LicenseDialog
from welcome_dialog import WelcomeDialog
from post_analysis_info_dialog import PostAnalysisInfoDialog
from version_checker import VersionChecker
from update_dialog import UpdateDialog
from location_analysis_dialog import LocationAnalysisDialog
from location_analyzer import LocationAnalyzer
from location_report_generator import LocationReportGenerator

class WhatsAppAnalyzerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Forensics Report Analyzer - by Luca Mercatanti")
        self.root.geometry("910x1050")
        self.root.resizable(True, True)

        # Centra la finestra principale
        self.center_window(self.root, 910, 1050)

        # Crea License Manager (ma non valida ancora)
        self.license_manager = LicenseManager(
            license_file=".license.enc",
            api_url="https://www.winesommelier.it/licenza/api.php"
        )

        # Variabili
        self.pdf_path = tk.StringVar()
        self.api_key = tk.StringVar()
        self.model_var = tk.StringVar(value="gpt-4o")
        self.output_dir = tk.StringVar(value="output")
        self.chunks_dir = tk.StringVar(value="pdf_chunks")
        self.max_chars = tk.IntVar(value=15000)
        self.use_local_model = tk.BooleanVar(value=False)
        self.local_url = tk.StringVar(value="http://localhost:11434")
        self.local_model_name = tk.StringVar(value="llama3.2")

        # Variabili per analisi immagini
        self.analyze_images = tk.BooleanVar(value=False)
        self.extraction_folder = tk.StringVar()

        # Variabili per formato chunk
        self.chunk_format = tk.StringVar(value="txt")  # "txt" o "json"

        # Variabili per analisi preliminare
        self.test_mode = tk.BooleanVar(value=False)
        self.test_chunks = tk.IntVar(value=5)

        # Statistiche
        self.total_pages = 0
        self.total_chunks = 0
        self.estimated_cost = 0.0
        self.estimated_time = 0

        # Stato processo
        self.is_running = False
        self.processor = None
        self.analyzer = None
        self.skip_to_summary = False  # Flag per saltare all'analisi finale

        # Logger per salvare log su file
        self.log_buffer = []  # Buffer per salvare tutti i log
        self.analysis_start_time = None
        self.analysis_config = {}  # Configurazioni utilizzate

        # API Key Manager per salvare chiavi cifrate
        self.api_key_manager = APIKeyManager()
        self.save_api_key_var = tk.BooleanVar(value=False)

        # Setup menu bar PRIMA della UI
        self.setup_menu_bar()

        self.setup_ui()

        # ===== CONTROLLO LICENZA (DOPO setup_ui) =====
        self._check_license()

        # Carica API key salvata (dopo aver creato l'UI)
        self.load_saved_api_key()

        # Carica le ultime cartelle usate
        self.load_last_folders()

        # Controlla analisi esistenti dopo aver creato l'UI
        self.root.after(500, self.check_existing_analyses)

        # Controlla se abilitare menu post-elaborazione
        self.root.after(1000, self.update_post_analysis_menu_state)

        # Mostra welcome dialog se necessario (dopo che la GUI è completamente caricata)
        self.root.after(1500, self._show_welcome_if_needed)

        # Controlla versione app (solo per utenti con licenza valida, non invasivo)
        self.root.after(2500, self._check_version_async)

    def setup_menu_bar(self):
        """Crea la barra menu in alto"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # ===== MENU POST-ELABORAZIONE =====
        self.post_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Post-Elaborazione", menu=self.post_menu)
        self.post_menu.add_command(label="🔍 Ricerca Rapida",
                                    command=self.open_quick_search,
                                    state='disabled')
        self.post_menu.add_command(label="🔁 Re-Analisi Avanzata",
                                    command=self.open_advanced_reanalysis,
                                    state='disabled')
        self.post_menu.add_separator()
        self.post_menu.add_command(label="🗺️ Analisi Posizioni Geografiche",
                                    command=self.open_location_analysis,
                                    state='disabled')
        self.post_menu.add_separator()
        self.post_menu.add_command(label="💬 Report per Chat",
                                    command=self.open_chat_report,
                                    state='disabled')

        # ===== MENU IMPOSTAZIONI =====
        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Impostazioni", menu=settings_menu)
        settings_menu.add_command(label="⚙️ Impostazioni API", command=self.open_api_settings)
        settings_menu.add_command(label="⚠️ Info Limiti API", command=self.show_api_limits_warning)

        # ===== MENU AIUTO =====
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Aiuto", menu=help_menu)
        help_menu.add_command(label="📖 Guida Utilizzo", command=self.show_usage_guide)
        help_menu.add_command(label="💡 Guida Post-Elaborazione", command=self.show_post_analysis_info)
        help_menu.add_command(label="💬 Messaggio di benvenuto", command=self.show_welcome_message)
        help_menu.add_separator()
        help_menu.add_command(label="ℹ️ Informazioni", command=self.show_about)

    def center_window(self, window, width, height):
        """Centra una finestra sullo schermo"""
        window.update_idletasks()
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        window.geometry(f'{width}x{height}+{x}+{y}')

    def update_post_analysis_menu_state(self):
        """Abilita/disabilita menu post-elaborazione in base alla presenza di analisi"""
        output_dir = self.output_dir.get()
        chunks_dir = self.chunks_dir.get()

        # Verifica presenza analisi e chunk
        has_analyses = False
        has_chunks = False

        if os.path.exists(output_dir):
            analysis_files = [f for f in os.listdir(output_dir)
                            if f.startswith("analisi_chunk_") and f.endswith(".txt")]
            has_analyses = len(analysis_files) > 0

        if os.path.exists(chunks_dir):
            chunk_files = [f for f in os.listdir(chunks_dir)
                          if f.startswith("chunk_") and (f.endswith(".txt") or f.endswith(".json"))]
            has_chunks = len(chunk_files) > 0

        if has_analyses:
            # Abilita Ricerca Rapida e Re-Analisi
            self.post_menu.entryconfig(0, state='normal')  # 🔍 Ricerca Rapida
            self.post_menu.entryconfig(1, state='normal')  # 🔁 Re-Analisi Avanzata

            # Abilita Analisi Posizioni e Report per Chat solo se ci sono anche i chunk
            if has_chunks:
                self.post_menu.entryconfig(3, state='normal')  # 🗺️ Analisi Posizioni Geografiche
                self.post_menu.entryconfig(5, state='normal')  # 💬 Report per Chat
            else:
                self.post_menu.entryconfig(3, state='disabled')
                self.post_menu.entryconfig(5, state='disabled')
        else:
            # Disabilita tutti
            self.post_menu.entryconfig(0, state='disabled')  # Ricerca Rapida
            self.post_menu.entryconfig(1, state='disabled')  # Re-Analisi Avanzata
            self.post_menu.entryconfig(3, state='disabled')  # Analisi Posizioni
            self.post_menu.entryconfig(5, state='disabled')  # Report per Chat

    def open_quick_search(self):
        """Apre il dialog per ricerca rapida"""
        try:
            from quick_search_dialog import QuickSearchDialog
            QuickSearchDialog(self.root, self)
        except ImportError as e:
            messagebox.showerror("Errore", f"Impossibile aprire Ricerca Rapida:\n{str(e)}")

    def open_advanced_reanalysis(self):
        """Apre il dialog per re-analisi avanzata"""
        try:
            from advanced_reanalysis_dialog import AdvancedReanalysisDialog
            AdvancedReanalysisDialog(self.root, self)
        except ImportError as e:
            messagebox.showerror("Errore", f"Impossibile aprire Re-Analisi Avanzata:\n{str(e)}")

    def open_location_analysis(self):
        """Apre il dialog per l'analisi delle posizioni geografiche"""
        try:
            # Verifica che ci sia un'analisi completata
            if not hasattr(self, 'output_dir') or not self.output_dir.get():
                messagebox.showwarning(
                    "Attenzione",
                    "Devi prima completare un'analisi prima di utilizzare questa funzione."
                )
                return

            output_dir = self.output_dir.get()

            # Verifica esistenza cartella
            if not os.path.exists(output_dir):
                messagebox.showerror(
                    "Errore",
                    f"Cartella output non trovata:\n{output_dir}"
                )
                return

            # Crea istanza AIAnalyzer con configurazione corrente
            if self.use_local_model.get():
                ai_analyzer = AIAnalyzer(
                    api_key="",
                    model=self.local_model_name.get(),
                    use_local=True,
                    local_url=self.local_url.get()
                )
            else:
                ai_analyzer = AIAnalyzer(
                    api_key=self.api_key.get(),
                    model=self.model_var.get()
                )

            # Apri dialog configurazione
            config_dialog = LocationAnalysisDialog(self.root, output_dir, self.chunks_dir.get(), ai_analyzer)
            config = config_dialog.show()

            if not config:
                # Utente ha annullato
                return

            # Crea finestra di elaborazione
            processing_window = tk.Toplevel(self.root)
            processing_window.title("Analisi Posizioni in Corso...")
            processing_window.geometry("800x600")
            processing_window.transient(self.root)
            processing_window.grab_set()

            # Center window
            self.center_window(processing_window, 800, 600)

            # Frame principale
            main_frame = ttk.Frame(processing_window, padding="20")
            main_frame.pack(fill=tk.BOTH, expand=True)

            # Label status
            status_label = ttk.Label(main_frame, text="Inizializzazione...", font=('Arial', 12, 'bold'))
            status_label.pack(pady=(0, 10))

            # Progress bar
            progress = ttk.Progressbar(main_frame, length=700, mode='determinate')
            progress.pack(pady=(0, 20))

            # Log area
            log_frame = ttk.Frame(main_frame)
            log_frame.pack(fill=tk.BOTH, expand=True)

            log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=25, width=90,
                                                 font=('Consolas', 9))
            log_text.pack(fill=tk.BOTH, expand=True)

            # Callbacks per analyzer
            def log_callback(message):
                log_text.insert(tk.END, message + '\n')
                log_text.see(tk.END)
                processing_window.update()

            def progress_callback(value):
                progress['value'] = value
                processing_window.update()

            def status_callback(text):
                status_label.config(text=text)
                processing_window.update()

            # Avvia analisi in thread separato
            def run_analysis():
                try:
                    status_callback("🔍 Analisi in corso...")

                    # Crea analyzer
                    analyzer = LocationAnalyzer(
                        ai_analyzer=ai_analyzer,
                        config=config,
                        log_callback=log_callback,
                        progress_callback=progress_callback
                    )

                    # Esegui analisi
                    results = analyzer.analyze()

                    # Genera report
                    status_callback("📄 Generazione report HTML...")
                    log_callback("\n" + "="*60)
                    log_callback("📊 GENERAZIONE REPORT HTML")
                    log_callback("="*60)

                    generator = LocationReportGenerator(results, output_dir)
                    html_path = generator.generate_report()

                    log_callback(f"\n✅ Report generato: {html_path}")

                    # Aggiorna stato bottone "Apri Report" nella GUI principale
                    self.check_report_availability()

                    # Completato
                    status_callback("✅ Analisi completata!")
                    progress_callback(100)

                    # Chiudi finestra processing e apri report
                    processing_window.after(1000, lambda: self._open_location_report(processing_window, html_path, results, config))

                except Exception as e:
                    log_callback(f"\n❌ ERRORE: {str(e)}")
                    status_callback("❌ Errore durante l'analisi")
                    messagebox.showerror(
                        "Errore",
                        f"Errore durante l'analisi delle posizioni:\n{str(e)}"
                    )

            # Avvia thread
            import threading
            thread = threading.Thread(target=run_analysis, daemon=True)
            thread.start()

        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile avviare analisi posizioni:\n{str(e)}")

    def _open_location_report(self, processing_window, html_path, results, config):
        """Apre il report e mostra dialog di completamento"""
        try:
            # Chiudi finestra processing
            processing_window.destroy()

            # Mostra messagebox con statistiche
            stats = results['stats']
            message = (
                f"🗺️ Analisi Posizioni Geografiche completata!\n\n"
                f"📊 Statistiche:\n"
                f"  • Posizioni trovate: {stats['locations_found']}\n"
                f"  • Posizioni geocodificate: {stats['locations_geocoded']}\n"
                f"  • Posizioni uniche: {stats['unique_locations']}\n"
                f"  • Eventi totali: {stats['total_events']}\n\n"
            )

            # Aggiungi avviso se modalità test
            if config.get('test_mode', False):
                message += (
                    f"⚠️ MODALITÀ TEST ATTIVA\n"
                    f"Analisi limitata ai primi {config.get('test_chunks', 5)} chunk.\n"
                    f"Per analisi completa, disattiva modalità test.\n\n"
                )

            message += (
                f"📁 Report salvato in:\n{os.path.dirname(html_path)}\n\n"
                f"Il report verrà aperto nel browser."
            )

            messagebox.showinfo("Analisi Completata", message)

            # Apri report nel browser
            import webbrowser
            webbrowser.open('file://' + os.path.abspath(html_path))

        except Exception as e:
            messagebox.showerror("Errore", f"Errore apertura report:\n{str(e)}")

    def open_chat_report(self):
        """Apre il dialog per report per chat"""
        try:
            from chat_report_dialog import ChatReportDialog
            ChatReportDialog(self.root, self)
        except ImportError as e:
            messagebox.showerror("Errore", f"Impossibile aprire Report per Chat:\n{str(e)}")

    def show_usage_guide(self):
        """Mostra la guida all'utilizzo"""
        guide_text = """GUIDA ALL'UTILIZZO - AI Forensics Report Analyzer v3.4

════════════════════════════════════════════════════════════════

=== 1. CONFIGURAZIONE INIZIALE ===

PRIMO AVVIO:
1. Menu "Impostazioni" > "⚙️ Impostazioni API"
2. Seleziona il PROVIDER che userai:
   • 🤖 OpenAI (GPT-4o, GPT-3.5-turbo)
   • 🧠 Anthropic (Claude 3.5 Sonnet)
   • 💻 Ollama Locale (nessun costo)
3. Seleziona il tuo TIER (controlla su piattaforma provider)
4. Il programma calcolerà automaticamente i delay ottimali
5. Clicca "💾 SALVA IMPOSTAZIONI"

IMPORTANTE: Configurare correttamente provider e tier evita errori
di timeout (429) e ottimizza la velocità di analisi!

════════════════════════════════════════════════════════════════

=== 2. ANALISI INIZIALE ===

PASSO 1 - Carica il PDF:
• Clicca "📂 Seleziona Report PDF"
• Supporta: Cellebrite, Oxygen Forensics e report generici

PASSO 2 - Configura AI:
• API Key: inserisci la tua chiave (viene salvata criptata)
• Modello: seleziona il modello AI
  - GPT-4o: massima qualità, più costoso
  - GPT-3.5-turbo: ottimo per riassunti, economico
  - Claude 3.5: qualità GPT-4o, limiti più generosi
  - Ollama locale: zero costi, hardware dipendente

PASSO 3 - Opzioni avanzate:
• Formato chunk: TXT (standard) o JSON (con immagini)
• Dimensione chunk: default 15,000 caratteri
• Modalità test: analizza solo primi N chunk (per test)

PASSO 4 - Personalizza prompt (opzionale):
• Usa il prompt di default o personalizza
• Salva template per riutilizzo
• Carica template salvati

PASSO 5 - Stima e avvio:
• Clicca "📊 Calcola Stime" per vedere costi/tempi
• Clicca "🚀 Avvia Analisi" per iniziare

L'analisi creerà:
• Cartella "nome_analisi/" con tutti i risultati
• Chunk di testo numerati (chunk_001.txt, ...)
• Analisi AI per ogni chunk (analisi_chunk_001.txt, ...)
• RIASSUNTO_FINALE.txt completo
• Report HTML interattivo (report_html/index.html)

RATE LIMITING AUTOMATICO:
Durante l'analisi vedrai messaggi come:
"⚙️ Rate Limiting (OpenAI): TPM=30,000, Delay=3.6s"
"⏳ Attesa 3.6s (rate limiting TPM)..."

Questo è NORMALE! Il programma rispetta i limiti API per evitare
errori 429. I delay variano in base al tuo tier configurato.

════════════════════════════════════════════════════════════════

=== 3. ANALISI IMMAGINI (OPZIONALE) ===

Supporto per immagini nei report Cellebrite.

REQUISITI:
• Formato chunk: JSON (non TXT)
• Cartella estrazione Cellebrite completa
• Percorso immagini corretto
• Modelli vision: GPT-4o, Claude 3.5, llava (Ollama)

COME ATTIVARE:
1. Seleziona "Formato chunk: JSON"
2. Spunta "📷 Analizza immagini (se presenti)"
3. Specifica percorso cartella Cellebrite
4. Le immagini verranno inviate all'AI insieme al testo

NOTA: L'analisi immagini aumenta costi e tempi (~2-3x)

════════════════════════════════════════════════════════════════

=== 4. POST-ELABORAZIONE ===

Menu "Post-Elaborazione" offre 3 funzioni avanzate:

📂 REPORT PER CHAT
• Analizza conversazioni per chat individuale o gruppo
• Crea riassunti dedicati per ogni chat rilevata
• Estrae metadati (partecipanti, periodo, allegati)
• Output: cartella con report per ogni chat

🔍 RICERCA RAPIDA
• Fai domande mirate sulle analisi esistenti
• Cerca informazioni specifiche senza rianalizzare
• ESEMPI:
  - "Trova tutte le minacce con armi"
  - "Elenca i viaggi menzionati"
  - "Chi ha parlato di denaro?"
• Veloce (~20-60 secondi)
• Economico (~$0.20-0.50)
• Supporta approccio gerarchico per grandi documenti

🔁 RE-ANALISI AVANZATA
• Filtra chunk per criteri specifici
• Rianalizza solo quelli rilevanti con prompt personalizzato

FILTRI DISPONIBILI:
• Parole chiave (AND/OR)
• Max chunk da analizzare (protezione costi)

QUANDO USARLA:
• Vuoi massima accuratezza su aspetto specifico
• Cerchi dettagli non trovati prima
• Hai bisogno di focus mirato

COSTI: ~$0.30-2.00 (dipende da quanti chunk filtrati)
TEMPO: ~1-10 minuti

════════════════════════════════════════════════════════════════

=== 5. MENU IMPOSTAZIONI ===

⚙️ IMPOSTAZIONI API (IMPORTANTE!)
Configura provider, tier e limiti TPM:

PROVIDER:
• OpenAI: GPT-4o, GPT-3.5-turbo
• Anthropic: Claude 3.5 Sonnet, Claude Opus
• Locale: Ollama (senza limiti API)

LIMITI TPM (Tokens Per Minute):
• Tier 1 OpenAI: 30,000 TPM → delay 3.6s
• Tier 1 Anthropic: 40,000 TPM → delay 2.7s
• Tier 2 OpenAI: 450,000 TPM → delay 0.2s
• Locale: nessun rate limiting

SOGLIA GERARCHICA:
• Default: 30 chunk
• Conservativo (10): più sicuro, evita errori 429
• Aggressivo (100): più veloce, richiede tier alto

ADATTAMENTO AUTOMATICO:
• Attivo: riduce automaticamente soglia se errore 429
• Consigliato per la maggior parte degli utenti

⚠️ INFO LIMITI API
Guida completa ai limiti OpenAI/Anthropic:
• Spiegazione tier e TPM
• Tabelle comparative
• Soluzioni per documenti grandi
• Rate limiting intelligente

════════════════════════════════════════════════════════════════

=== 6. RISOLUZIONE PROBLEMI ===

ERRORE 429 (TIMEOUT/RATE LIMIT):
✓ Vai in Impostazioni > Impostazioni API
✓ Verifica il provider selezionato
✓ Verifica il tier configurato (controlla su piattaforma)
✓ Riduci soglia gerarchica a 20 se Tier 1
✓ Considera GPT-3.5-turbo o Anthropic per documenti grandi
✓ Considera Ollama locale per zero limiti

FILE RIASSUNTO NON TROVATO:
✓ Controlla il log per errori specifici
✓ Verifica connessione internet
✓ Verifica crediti API disponibili
✓ L'approccio gerarchico si attiva automaticamente

ANALISI LENTA:
• NORMALE con Tier 1: ~3.6s di attesa tra chunk
• Velocizza con tier superiore o Anthropic
• Ollama locale: dipende dall'hardware

════════════════════════════════════════════════════════════════

=== 7. SUGGERIMENTI BEST PRACTICE ===

✓ CONFIGURA PROVIDER E TIER prima di iniziare
✓ Usa "Calcola Stime" prima di ogni analisi
✓ Salva le API key (vengono criptate)
✓ Usa template per prompt frequenti
✓ Verifica sempre il report HTML (report_html/index.html)
✓ Per documenti >100 chunk: usa Anthropic o Ollama
✓ Analisi iniziale: GPT-4o o Claude 3.5 (qualità)
✓ Riassunto finale: GPT-3.5-turbo (veloce ed economico)
✓ Per test: attiva "Modalità test" con 5-10 chunk

════════════════════════════════════════════════════════════════

© 2025 Luca Mercatanti - https://mercatanti.com
Versione 3.2.1 - Rate Limiting Multi-Provider"""

        # Crea finestra per la guida
        guide_window = tk.Toplevel(self.root)
        guide_window.title("📖 Guida Utilizzo Completa")
        guide_window.geometry("900x700")
        self.center_window(guide_window, 900, 700)

        text_widget = scrolledtext.ScrolledText(guide_window, wrap=tk.WORD, font=('Courier', 10))
        text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text_widget.insert('1.0', guide_text)
        text_widget.config(state='disabled')

        ttk.Button(guide_window, text="Chiudi", command=guide_window.destroy).pack(pady=5)

    def show_post_analysis_info(self):
        """Mostra informazioni dettagliate sulla post-elaborazione"""
        info_text = """POST-ELABORAZIONE - Informazioni Dettagliate

La post-elaborazione ti permette di approfondire aspetti specifici
DOPO aver completato l'analisi iniziale, senza dover riprocessare
tutto il documento.

════════════════════════════════════════

🔍 RICERCA RAPIDA

COSA FA:
• Cerca nelle analisi già prodotte
• Risponde a domande mirate
• Estrae informazioni specifiche

QUANDO USARLA:
• Vuoi trovare rapidamente qualcosa
• Hai una domanda specifica
• Non serve rianalizzare tutto

ESEMPI:
• "Trova tutte le minacce con armi"
• "Elenca i viaggi menzionati"
• "Chi ha parlato di denaro?"

COSTI: ~$0.20-0.50
TEMPO: ~10-30 secondi

════════════════════════════════════════

🔁 RE-ANALISI AVANZATA

COSA FA:
• Filtra i chunk originali per criteri specifici
• Rianalizza solo quelli rilevanti
• Usa un nuovo prompt personalizzato

QUANDO USARLA:
• Vuoi massima accuratezza
• Cerchi dettagli non trovati prima
• Hai bisogno di un focus specifico

FILTRI DISPONIBILI:
• Periodo temporale (data inizio-fine)
• Utente specifico
• Parole chiave (AND/OR)
• Presenza GPS/Posizioni

COSTI: ~$0.30-2.00 (dipende da filtri)
TEMPO: ~1-10 minuti

════════════════════════════════════════

💡 CONSIGLIO

Per la maggior parte dei casi, inizia con la RICERCA RAPIDA.
Se non trovi ciò che cerchi o serve più dettaglio,
passa alla RE-ANALISI AVANZATA.

════════════════════════════════════════"""

        info_window = tk.Toplevel(self.root)
        info_window.title("Info Post-Elaborazione")
        info_window.geometry("700x650")
        self.center_window(info_window, 700, 650)

        text_widget = scrolledtext.ScrolledText(info_window, wrap=tk.WORD, font=('Courier', 10))
        text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text_widget.insert('1.0', info_text)
        text_widget.config(state='disabled')

        ttk.Button(info_window, text="Chiudi", command=info_window.destroy).pack(pady=5)

    def show_about(self):
        """Mostra informazioni sull'applicazione"""
        about_text = f"""╔═══════════════════════════════════════════════════════╗
║   AI Forensics Report Analyzer v{APP_VERSION}                ║
║   Sistema Analisi Posizioni Geografiche             ║
╚═══════════════════════════════════════════════════════╝

Strumento professionale per l'analisi forense automatizzata
di report WhatsApp, WeChat, Telegram e altre chat esportate
da Cellebrite, Oxygen Forensics, UFED e tool forensi simili.

✨ FUNZIONALITÀ PRINCIPALI:

📄 ANALISI REPORT PDF
• Importazione automatica report forensi
• Segmentazione intelligente in chunk
• Supporto documenti di qualsiasi dimensione
• Modalità test preliminare (chunk limitati)
• Estrazione immagini da path Cellebrite
• Formati: TXT (base) o JSON (con immagini)

🤖 INTELLIGENZA ARTIFICIALE
• Multi-provider: OpenAI, Anthropic, Ollama
• Rate limiting intelligente per ogni tier
• Vision support (GPT-4o, Claude 3.5, llava)
• Analisi multimodale: testo + immagini
• Template prompt personalizzabili
• Approccio gerarchico per documenti grandi

💬 REPORT PER CHAT (v3.4 - Sistema LLM Puro)
• Rilevamento automatico chat con AI
• Sliding window con overlap (header spezzati)
• Deduplicazione intelligente a 5 livelli
• Riassunti dedicati per ogni conversazione
• Supporto chat 1v1 e gruppi
• Modalità test per analisi preliminare

🔍 POST-ELABORAZIONE AVANZATA
• Ricerca Rapida: domande su analisi esistenti
• Re-Analisi: filtri keyword + prompt personalizzato
• Report Chat: riassunti per conversazione

📊 OUTPUT E REPORT
• Report HTML interattivi multi-pagina
• Riassunto finale completo
• Timeline eventi e metadati
• Stima costi e tempi in tempo reale
• Navigazione intuitiva tra chunk

🔐 SICUREZZA E PRIVACY
• API keys cifrate con AES-256
• Machine binding per protezione
• Supporto modelli locali (zero cloud con Ollama)
• Nessun dato inviato a server esterni

🔄 AGGIORNAMENTI AUTOMATICI
• Notifiche nuove versioni disponibili
• Controllo automatico (1 volta al giorno)
• Download automatico o manuale
• Changelog integrato

📈 PROVIDER AI SUPPORTATI:
• OpenAI: GPT-4o, GPT-3.5-turbo
• Anthropic: Claude 3.5 Sonnet, Claude 3 Opus
• Ollama (locale): Llama3, Mistral, Qwen, LLaVA

⚙️ CONFIGURAZIONI AVANZATE:
• Impostazioni API per provider e tier
• Soglia gerarchica configurabile (10-100 chunk)
• Adattamento automatico errori rate limit
• Dimensione chunk personalizzabile
• Template prompt riutilizzabili

═══════════════════════════════════════════════════════

© 2025 Luca Mercatanti
🌐 https://mercatanti.com
📧 luca.mercatanti@gmail.com

Versione {APP_VERSION} - {APP_VERSION_DATE}
Sistema Analisi Posizioni Geografiche + Persistenza Cartelle

Tutti i diritti riservati."""

        # Crea dialog personalizzato con dimensioni controllabili
        about_window = tk.Toplevel(self.root)
        about_window.title("ℹ️ Informazioni")
        about_window.geometry("650x750")
        self.center_window(about_window, 650, 750)
        about_window.resizable(False, False)

        text_widget = scrolledtext.ScrolledText(about_window, wrap=tk.WORD, font=('Courier', 9))
        text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text_widget.insert('1.0', about_text)
        text_widget.config(state='disabled')

        ttk.Button(about_window, text="Chiudi", command=about_window.destroy).pack(pady=5)

    def _check_version_async(self):
        """
        Controlla versione app in background (non bloccante)
        Eseguito SOLO se l'utente ha licenza valida
        """
        def check():
            try:
                checker = VersionChecker(
                    api_url=self.license_manager.api_url,
                    current_version=APP_VERSION
                )

                # Controlla solo se è passato 1 giorno dall'ultimo controllo
                if checker.should_check():
                    update_info = checker.check_for_updates()

                    if update_info and update_info.get('update_available'):
                        # Mostra notifica nel main thread
                        self.root.after(0, self._show_update_dialog, update_info, checker)
            except Exception as e:
                # Fallimento silenzioso - il controllo versione non deve mai bloccare l'app
                print(f"Controllo versione fallito (silenzioso): {e}")

        # Esegui in thread separato per non bloccare UI
        thread = threading.Thread(target=check, daemon=True)
        thread.start()

    def _show_update_dialog(self, update_info, checker):
        """Mostra dialog aggiornamento disponibile (main thread)"""
        try:
            UpdateDialog(self.root, update_info, checker)
        except Exception as e:
            print(f"Errore mostrando dialog aggiornamento: {e}")

    def _show_welcome_if_needed(self):
        """Mostra il welcome dialog se l'utente non ha disabilitato la visualizzazione"""
        if WelcomeDialog.should_show():
            WelcomeDialog(self.root, logo_path="logo.jpg", force_show=False)

    def show_welcome_message(self):
        """Mostra il welcome dialog (chiamato dal menu Aiuto)"""
        WelcomeDialog(self.root, logo_path="logo.jpg", force_show=True)

    def setup_ui(self):
        """Configura l'interfaccia grafica"""

        # ===== FRAME PRINCIPALE =====
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

        row = 0

        # ===== SEZIONE FILE PDF =====
        ttk.Label(main_frame, text="Report di Chat (PDF):",
                 font=('Arial', 10, 'bold')).grid(
            row=row, column=0, sticky=tk.W, pady=(0, 5)
        )
        row += 1

        pdf_frame = ttk.Frame(main_frame)
        pdf_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        pdf_frame.columnconfigure(0, weight=1)

        ttk.Entry(pdf_frame, textvariable=self.pdf_path, width=60).grid(
            row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5)
        )
        ttk.Button(pdf_frame, text="Sfoglia...", command=self.browse_pdf).grid(
            row=0, column=1
        )
        row += 1

        # ===== SEZIONE CONFIGURAZIONE AI =====
        ai_header_frame = ttk.Frame(main_frame)
        ai_header_frame.grid(row=row, column=0, columnspan=3, sticky=tk.W, pady=(10, 5))

        ttk.Label(ai_header_frame, text="Configurazione AI:",
                 font=('Arial', 10, 'bold')).pack(side=tk.LEFT)
        ttk.Label(ai_header_frame, text="(OpenAI, Anthropic o Modello Locale)",
                 font=('Arial', 9), foreground='gray').pack(side=tk.LEFT, padx=5)
        row += 1

        # Checkbox modello locale
        local_checkbox = ttk.Checkbutton(main_frame, text="Usa modello locale (Ollama)",
                                         variable=self.use_local_model,
                                         command=self.toggle_local_model)
        local_checkbox.grid(row=row, column=0, columnspan=3, sticky=tk.W, pady=(0, 5))
        row += 1

        # Frame configurazione locale (nascosto inizialmente)
        self.local_config_frame = ttk.LabelFrame(main_frame, text="Configurazione Modello Locale", padding="10")
        self.local_config_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        self.local_config_frame.columnconfigure(1, weight=1)
        self.local_config_frame.grid_remove()  # Nasconde il frame

        # URL Ollama
        ttk.Label(self.local_config_frame, text="URL Ollama:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Entry(self.local_config_frame, textvariable=self.local_url, width=40).grid(
            row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=2
        )

        # Nome modello locale con dropdown e pulsante refresh
        ttk.Label(self.local_config_frame, text="Nome modello:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)

        model_local_frame = ttk.Frame(self.local_config_frame)
        model_local_frame.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5, pady=2)
        model_local_frame.columnconfigure(0, weight=1)

        self.local_model_combo = ttk.Combobox(model_local_frame, textvariable=self.local_model_name, width=30)
        self.local_model_combo.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))

        ttk.Button(model_local_frame, text="🔄 Aggiorna", width=12,
                  command=self.refresh_ollama_models).grid(row=0, column=1)

        # Box informativo modelli locali
        info_frame = ttk.Frame(self.local_config_frame)
        info_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(5, 0))

        info_text = tk.Text(info_frame, height=4, width=70, wrap=tk.WORD, bg='#f0f0f0', relief=tk.FLAT, font=('Arial', 9))
        info_text.grid(row=0, column=0, sticky=(tk.W, tk.E))

        info_content = """📦 Installa Ollama da https://ollama.ai/download
   Scarica modello: ollama pull llama3.2
   Verifica sia avviato su http://localhost:11434
💡 Modelli locali: GRATUITI e PRIVATI (nessun dato online)"""

        info_text.insert('1.0', info_content)
        info_text.config(state='disabled')
        row += 1

        # API Key
        api_label_frame = ttk.Frame(main_frame)
        api_label_frame.grid(row=row, column=0, sticky=tk.W)

        help_api = ttk.Button(api_label_frame, text="ℹ️", width=3,
                  command=lambda: self.show_help("API Key",
                      "Chiave API per accedere ai servizi AI.\n\n"
                      "OPENAI:\n"
                      "• Ottieni su: platform.openai.com/api-keys\n"
                      "• Modelli: gpt-4o, gpt-4-turbo, gpt-3.5-turbo\n\n"
                      "ANTHROPIC:\n"
                      "• Ottieni su: console.anthropic.com\n"
                      "• Modelli: claude-3-5-sonnet, claude-3-opus\n\n"
                      "Usa la chiave del provider che preferisci.\n\n"
                      "NON NECESSARIA per modelli locali!"
                  ))
        help_api.pack(side=tk.LEFT, padx=(0, 5))
        ttk.Label(api_label_frame, text="API Key:").pack(side=tk.LEFT)

        api_input_frame = ttk.Frame(main_frame)
        api_input_frame.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2)
        api_input_frame.columnconfigure(0, weight=1)

        self.api_entry = ttk.Entry(api_input_frame, textvariable=self.api_key, width=40, show="*")
        self.api_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))

        # Pulsante Salva API Key
        ttk.Button(api_input_frame, text="💾", width=3,
                  command=self.toggle_save_api_key).grid(row=0, column=1)

        # Pulsante Cancella chiave salvata
        ttk.Button(api_input_frame, text="🗑️", width=3,
                  command=self.clear_saved_api_key).grid(row=0, column=2)

        row += 1

        # Modello
        model_label_frame = ttk.Frame(main_frame)
        model_label_frame.grid(row=row, column=0, sticky=tk.W)

        help_model = ttk.Button(model_label_frame, text="ℹ️", width=3,
                  command=lambda: self.show_help("Modello AI",
                      "Scegli il modello AI da utilizzare.\n\n"
                      "OPENAI (usa chiave OpenAI):\n"
                      "• gpt-4o → Consigliato ($3/$10 per 1M token)\n"
                      "• gpt-4-turbo → Premium ($10/$30 per 1M token)\n"
                      "• gpt-3.5-turbo → Economico ($0.5/$1.5 per 1M token)\n\n"
                      "ANTHROPIC (usa chiave Anthropic):\n"
                      "• claude-3-5-sonnet → Ottimo ($3/$15 per 1M token)\n"
                      "• claude-3-opus → Top quality ($15/$75 per 1M token)\n\n"
                      "Prezzi aggiornati 2025 (input/output per milione token)\n"
                      "La chiave API deve corrispondere al provider del modello!\n\n"
                      "DISABILITATO quando usi modelli locali."
                  ))
        help_model.pack(side=tk.LEFT, padx=(0, 5))
        ttk.Label(model_label_frame, text="Modello:").pack(side=tk.LEFT)

        model_frame = ttk.Frame(main_frame)
        model_frame.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2)

        models = [
            "gpt-4o",
            "gpt-4-turbo",
            "gpt-3.5-turbo",
            "claude-3-5-sonnet-20241022",
            "claude-3-opus-20240229"
        ]

        self.model_combo = ttk.Combobox(model_frame, textvariable=self.model_var,
                                   values=models, width=40, state="readonly")
        self.model_combo.grid(row=0, column=0, sticky=tk.W)
        self.model_combo.bind('<<ComboboxSelected>>', self.update_estimates)
        row += 1

        # ===== SEZIONE PROMPT PERSONALIZZATO =====
        prompt_header_frame = ttk.Frame(main_frame)
        prompt_header_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 5))
        prompt_header_frame.columnconfigure(1, weight=1)

        ttk.Label(prompt_header_frame, text="Prompt personalizzato (opzionale):",
                 font=('Arial', 10, 'bold')).grid(row=0, column=0, sticky=tk.W)

        # Template dropdown
        ttk.Label(prompt_header_frame, text="Template:").grid(row=0, column=1, sticky=tk.E, padx=(20, 5))
        self.template_var = tk.StringVar(value="Personalizzato")
        self.template_combo = ttk.Combobox(prompt_header_frame, textvariable=self.template_var,
                                           width=25, state="readonly")
        self.template_combo.grid(row=0, column=2, sticky=tk.E, padx=(0, 5))
        self.template_combo.bind('<<ComboboxSelected>>', self.load_template)

        ttk.Button(prompt_header_frame, text="💾 Salva", width=8,
                  command=self.save_template).grid(row=0, column=3, padx=2)
        ttk.Button(prompt_header_frame, text="❌ Elimina", width=8,
                  command=self.delete_template).grid(row=0, column=4, padx=2)

        row += 1

        self.prompt_text = scrolledtext.ScrolledText(main_frame, height=6, width=70, wrap=tk.WORD)
        self.prompt_text.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 5))

        # Carica templates salvati
        self.templates = self.load_templates()
        self.update_template_list()

        # Imposta template default
        if "Default" in self.templates:
            self.template_var.set("Default")
            self.prompt_text.insert('1.0', self.templates["Default"])
        else:
            self.prompt_text.insert('1.0',
                "Analizza questo report WhatsApp e fornisci un'analisi forense strutturata:\n\n"
                "## 1. Partecipanti e Struttura\n"
                "- Identifica tutti i partecipanti della conversazione\n"
                "- Individua ruoli (amministratori, membri, ecc.)\n"
                "- Indica date di ingresso/uscita dal gruppo\n\n"
                "## 2. Timeline e Cronologia\n"
                "- Periodo temporale delle conversazioni (data inizio - data fine)\n"
                "- Eventi significativi con timestamp precisi\n"
                "- Pattern temporali (orari di attività, pause, ecc.)\n\n"
                "## 3. Contenuti e Messaggi Rilevanti\n"
                "- Messaggi importanti con citazione e timestamp\n"
                "- Media condivisi (foto, video, documenti) con autore e data\n"
                "- Link esterni condivisi\n\n"
                "## 4. Posizioni e Spostamenti\n"
                "Per ogni menzione di posizioni o spostamenti indica:\n"
                "- **Posizioni GPS condivise**: coordinate o nome luogo, autore, timestamp, riferimento messaggio\n"
                "- **Menzioni di luoghi**: qualsiasi riferimento a indirizzi, città, luoghi specifici\n"
                "- **Discussioni su spostamenti**: viaggi, appuntamenti in luoghi fisici, ecc.\n"
                "Formato richiesto per ogni voce:\n"
                "  • Luogo/Posizione: [descrizione]\n"
                "  • Utente: [nome]\n"
                "  • Data/Ora: [timestamp]\n"
                "  • Contesto: [breve descrizione del messaggio]\n"
                "  • Riferimento: [numero pagina o identificativo messaggio]\n\n"
                "## 5. Minacce e Contenuti Problematici\n"
                "⚠️ SEZIONE CRITICA - Analizza attentamente per rilevare:\n"
                "- **Minacce**: esplicite o implicite, dirette o indirette\n"
                "- **Offese e insulti**: linguaggio offensivo, discriminatorio\n"
                "- **Aggressioni verbali**: tono aggressivo, intimidatorio\n"
                "- **Circonvenzioni**: manipolazione, estorsione, ricatti\n"
                "- **Contenuti illeciti**: riferimenti a attività illegali\n"
                "- **Molestie**: comportamenti persecutori, stalking\n"
                "- **Violenza**: riferimenti a violenza fisica o psicologica\n\n"
                "Formato richiesto per OGNI contenuto problematico:\n"
                "  • Tipo: [minaccia/offesa/aggressione/circonvenzione/altro]\n"
                "  • Gravità: [bassa/media/alta/critica]\n"
                "  • Utente: [autore del messaggio]\n"
                "  • Destinatario: [a chi è rivolto]\n"
                "  • Data/Ora: [timestamp preciso]\n"
                "  • Messaggio: [citazione testuale o parafrasi]\n"
                "  • Contesto: [situazione in cui è avvenuto]\n"
                "  • Riferimento: [pagina/messaggio originale]\n\n"
                "Se non ci sono contenuti problematici: indica 'Nessun contenuto problematico rilevato in questo chunk'\n\n"
                "## 6. Informazioni Sensibili (Dati Personali)\n"
                "- Numeri di telefono\n"
                "- Indirizzi email\n"
                "- Indirizzi fisici\n"
                "- Documenti identificativi\n"
                "- Dati finanziari\n\n"
                "## 7. Pattern di Comunicazione\n"
                "- Relazioni tra i partecipanti\n"
                "- Temi ricorrenti\n"
                "- Linguaggio e tono utilizzato\n\n"
                "## 8. Note Forensi\n"
                "- Eventuali anomalie\n"
                "- Messaggi eliminati (se visibili)\n"
                "- Cambiamenti di gruppo\n\n"
                "**IMPORTANTE**: \n"
                "- Per ogni informazione rilevante, indica SEMPRE il timestamp e il riferimento alla pagina/messaggio originale\n"
                "- Se non ci sono posizioni o spostamenti menzionati, indica esplicitamente 'Nessuna posizione rilevata in questo chunk'\n"
                "- Ignora messaggi di sistema sulla crittografia end-to-end"
            )
        row += 1

        # ===== SEZIONE ANALISI IMMAGINI =====
        images_header_frame = ttk.Frame(main_frame)
        images_header_frame.grid(row=row, column=0, columnspan=3, sticky=tk.W, pady=(10, 5))

        ttk.Label(images_header_frame, text="Analisi Immagini:",
                 font=('Arial', 10, 'bold')).pack(side=tk.LEFT)
        ttk.Label(images_header_frame, text="🧪 BETA - Solo Cellebrite",
                 font=('Arial', 8), foreground='red').pack(side=tk.LEFT, padx=10)

        help_images = ttk.Button(images_header_frame, text="ℹ️", width=3,
                  command=lambda: self.show_help("Analisi Immagini (BETA)",
                      "🧪 FUNZIONE SPERIMENTALE\n\n"
                      "Analizza anche le immagini/media presenti nelle conversazioni.\n\n"
                      "COMPATIBILITÀ:\n"
                      "• Attualmente supporta SOLO report Cellebrite\n"
                      "• Richiede formato chunk JSON\n"
                      "• Funziona con GPT-4o, Claude e modelli Ollama (llava)\n\n"
                      "REQUISITI:\n"
                      "• Cartella estrazione Cellebrite completa\n"
                      "• Immagini nella posizione originale\n"
                      "• Formato chunk impostato su JSON\n\n"
                      "NOTA: Le immagini aumentano i costi e i tempi di analisi."
                  ))
        help_images.pack(side=tk.LEFT, padx=5)
        row += 1

        # Checkbox analisi immagini
        self.images_checkbox = ttk.Checkbutton(main_frame,
                                               text="Analizza anche immagini/media (richiede formato JSON)",
                                               variable=self.analyze_images,
                                               command=self.toggle_image_analysis)
        self.images_checkbox.grid(row=row, column=0, columnspan=3, sticky=tk.W, pady=(0, 5))
        row += 1

        # Frame per cartella estrazione (nascosto inizialmente)
        self.extraction_frame = ttk.Frame(main_frame)
        self.extraction_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        self.extraction_frame.columnconfigure(1, weight=1)
        self.extraction_frame.grid_remove()

        ttk.Label(self.extraction_frame, text="Cartella estrazione Cellebrite:").grid(
            row=0, column=0, sticky=tk.W, padx=(20, 5))

        extraction_entry_frame = ttk.Frame(self.extraction_frame)
        extraction_entry_frame.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        extraction_entry_frame.columnconfigure(0, weight=1)

        ttk.Entry(extraction_entry_frame, textvariable=self.extraction_folder).grid(
            row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        ttk.Button(extraction_entry_frame, text="Sfoglia...",
                  command=self.browse_extraction_folder).grid(row=0, column=1)
        row += 1

        # ===== SEZIONE ANALISI PRELIMINARE =====
        test_header_frame = ttk.Frame(main_frame)
        test_header_frame.grid(row=row, column=0, columnspan=3, sticky=tk.W, pady=(10, 5))

        ttk.Label(test_header_frame, text="Analisi Preliminare:",
                 font=('Arial', 10, 'bold')).pack(side=tk.LEFT)
        ttk.Label(test_header_frame, text="🧪 Test prima dell'analisi completa",
                 font=('Arial', 8), foreground='blue').pack(side=tk.LEFT, padx=10)

        help_test = ttk.Button(test_header_frame, text="ℹ️", width=3,
                  command=lambda: self.show_help("Analisi Preliminare",
                      "Testa l'analisi su un numero limitato di chunk prima\n"
                      "di procedere con l'analisi completa.\n\n"
                      "VANTAGGI:\n"
                      "• Verifica la qualità dell'output AI\n"
                      "• Testa il prompt personalizzato\n"
                      "• Valuta i risultati prima di spendere\n"
                      "• Utile per documenti molto grandi\n\n"
                      "FUNZIONAMENTO:\n"
                      "• Analizza solo i primi N chunk\n"
                      "• Crea un riassunto parziale\n"
                      "• Puoi poi decidere se procedere\n\n"
                      "Consigliato: 3-10 chunk per il test."
                  ))
        help_test.pack(side=tk.LEFT, padx=5)
        row += 1

        # Checkbox e campo numero chunk
        test_control_frame = ttk.Frame(main_frame)
        test_control_frame.grid(row=row, column=0, columnspan=3, sticky=tk.W, pady=(0, 10))

        self.test_checkbox = ttk.Checkbutton(test_control_frame,
                                            text="Modalità test - Analizza solo i primi",
                                            variable=self.test_mode,
                                            command=self.toggle_test_mode)
        self.test_checkbox.pack(side=tk.LEFT)

        self.test_spinbox = ttk.Spinbox(test_control_frame, from_=1, to=100,
                                       textvariable=self.test_chunks, width=5)
        self.test_spinbox.pack(side=tk.LEFT, padx=5)

        ttk.Label(test_control_frame, text="chunk").pack(side=tk.LEFT)
        row += 1

        # ===== SEZIONE CONFIGURAZIONE OUTPUT =====
        ttk.Label(main_frame, text="Configurazione Output:",
                 font=('Arial', 10, 'bold')).grid(
            row=row, column=0, sticky=tk.W, pady=(10, 5)
        )
        row += 1

        # Formato chunk
        format_label_frame = ttk.Frame(main_frame)
        format_label_frame.grid(row=row, column=0, sticky=tk.W)

        help_format = ttk.Button(format_label_frame, text="ℹ️", width=3,
                  command=lambda: self.show_help("Formato Chunk",
                      "Scegli il formato per salvare i chunk di testo.\n\n"
                      "TXT (Classico):\n"
                      "• File di testo semplici (.txt)\n"
                      "• Retrocompatibile con versioni precedenti\n"
                      "• Non supporta analisi immagini\n"
                      "• Leggibile con qualsiasi editor\n\n"
                      "JSON (Avanzato):\n"
                      "• File strutturati (.json)\n"
                      "• Supporta metadata e immagini\n"
                      "• Richiesto per analisi immagini\n"
                      "• Include informazioni aggiuntive\n\n"
                      "Entrambi i formati funzionano con l'analisi AI."
                  ))
        help_format.pack(side=tk.LEFT, padx=(0, 5))
        ttk.Label(format_label_frame, text="Formato chunk:").pack(side=tk.LEFT)

        format_frame = ttk.Frame(main_frame)
        format_frame.grid(row=row, column=1, sticky=tk.W, pady=2)

        ttk.Radiobutton(format_frame, text="TXT (classico)",
                       variable=self.chunk_format, value="txt",
                       command=self.on_format_change).grid(row=0, column=0, padx=(0, 15))
        ttk.Radiobutton(format_frame, text="JSON (con metadata)",
                       variable=self.chunk_format, value="json",
                       command=self.on_format_change).grid(row=0, column=1)
        row += 1

        # Directory chunks
        chunks_label_frame = ttk.Frame(main_frame)
        chunks_label_frame.grid(row=row, column=0, sticky=tk.W)

        help_btn1 = ttk.Button(chunks_label_frame, text="ℹ️", width=3,
                  command=lambda: self.show_help("Cartella Chunk",
                      "Cartella dove vengono salvati i chunk (segmenti) del PDF.\n\n"
                      "Il PDF viene diviso in parti piccole per essere analizzato dall'AI.\n"
                      "Ogni chunk è salvato come file .txt\n\n"
                      "Esempio: 'documento_chunks' → chunk_001.txt, chunk_002.txt..."
                  ))
        help_btn1.pack(side=tk.LEFT, padx=(0, 5))
        ttk.Label(chunks_label_frame, text="Cartella chunk:").pack(side=tk.LEFT)

        chunks_entry_frame = ttk.Frame(main_frame)
        chunks_entry_frame.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2)
        chunks_entry_frame.columnconfigure(0, weight=1)
        ttk.Entry(chunks_entry_frame, textvariable=self.chunks_dir).grid(
            row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5)
        )
        ttk.Button(chunks_entry_frame, text="Sfoglia...",
                  command=self.browse_chunks_dir).grid(row=0, column=1)
        row += 1

        # Directory output
        output_label_frame = ttk.Frame(main_frame)
        output_label_frame.grid(row=row, column=0, sticky=tk.W)

        help_btn2 = ttk.Button(output_label_frame, text="ℹ️", width=3,
                  command=lambda: self.show_help("Cartella Analisi",
                      "Cartella dove vengono salvate le analisi AI.\n\n"
                      "Qui troverai:\n"
                      "• analisi_chunk_001.txt, 002.txt... (analisi dettagliate)\n"
                      "• RIASSUNTO_FINALE.txt (riassunto completo)\n\n"
                      "💡 RISPARMIA TEMPO E COSTI:\n"
                      "Se questa cartella contiene già file analisi_chunk_*.txt,\n"
                      "puoi creare un nuovo riassunto finale senza rielaborare\n"
                      "tutti i chunk. Il programma rileverà i chunk esistenti\n"
                      "e ti chiederà se vuoi usarli direttamente!"
                  ))
        help_btn2.pack(side=tk.LEFT, padx=(0, 5))
        ttk.Label(output_label_frame, text="Cartella analisi:").pack(side=tk.LEFT)

        output_entry_frame = ttk.Frame(main_frame)
        output_entry_frame.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2)
        output_entry_frame.columnconfigure(0, weight=1)
        ttk.Entry(output_entry_frame, textvariable=self.output_dir).grid(
            row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5)
        )
        ttk.Button(output_entry_frame, text="Sfoglia...",
                  command=self.browse_output_dir).grid(row=0, column=1)
        row += 1

        # Max caratteri per chunk
        chars_label_frame = ttk.Frame(main_frame)
        chars_label_frame.grid(row=row, column=0, sticky=tk.W)

        help_btn3 = ttk.Button(chars_label_frame, text="ℹ️", width=3,
                  command=lambda: self.show_help("Caratteri per Chunk",
                      "Numero max di caratteri per chunk.\n\n"
                      "CONSIGLIATO: 15000\n\n"
                      "• Alto (20000+): Meno costi, analisi meno dettagliata\n"
                      "• Basso (10000): Più costi, analisi più accurata\n\n"
                      "15000 è il miglior equilibrio tra costo e qualità.\n\n"
                      "Info: 1 carattere ≈ 0.25 token"
                  ))
        help_btn3.pack(side=tk.LEFT, padx=(0, 5))
        ttk.Label(chars_label_frame, text="Caratteri per chunk:").pack(side=tk.LEFT)

        ttk.Entry(main_frame, textvariable=self.max_chars, width=20).grid(
            row=row, column=1, sticky=tk.W, pady=2
        )
        row += 1

        # ===== SEZIONE STIME =====
        ttk.Separator(main_frame, orient='horizontal').grid(
            row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10
        )
        row += 1

        estimate_frame = ttk.LabelFrame(main_frame, text="Stime", padding="10")
        estimate_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        estimate_frame.columnconfigure(1, weight=1)

        self.pages_label = ttk.Label(estimate_frame, text="Pagine: -")
        self.pages_label.grid(row=0, column=0, sticky=tk.W, padx=5)

        self.chunks_label = ttk.Label(estimate_frame, text="Chunk: -")
        self.chunks_label.grid(row=0, column=1, sticky=tk.W, padx=5)

        self.cost_label = ttk.Label(estimate_frame, text="Costo stimato: -")
        self.cost_label.grid(row=1, column=0, sticky=tk.W, padx=5)

        self.time_label = ttk.Label(estimate_frame, text="Tempo stimato: -")
        self.time_label.grid(row=1, column=1, sticky=tk.W, padx=5)

        ttk.Button(estimate_frame, text="Calcola Stime",
                  command=self.calculate_estimates).grid(row=0, column=2, rowspan=2, padx=10)

        row += 1

        # ===== SEZIONE AVANZAMENTO =====
        progress_frame = ttk.LabelFrame(main_frame, text="Avanzamento", padding="10")
        progress_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        progress_frame.columnconfigure(0, weight=1)

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            progress_frame, variable=self.progress_var, maximum=100, length=400
        )
        self.progress_bar.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=5)

        self.status_label = ttk.Label(progress_frame, text="Pronto", foreground="green")
        self.status_label.grid(row=1, column=0, sticky=tk.W)

        row += 1

        # ===== SEZIONE LOG =====
        ttk.Label(main_frame, text="Log:", font=('Arial', 10, 'bold')).grid(
            row=row, column=0, sticky=tk.W, pady=(10, 5)
        )
        row += 1

        self.log_text = scrolledtext.ScrolledText(main_frame, height=12, width=70,
                                                  state='disabled', wrap=tk.WORD)
        self.log_text.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S),
                          pady=(0, 10))

        main_frame.rowconfigure(row, weight=1)
        row += 1

        # ===== PULSANTI AZIONE =====
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=row, column=0, columnspan=3, pady=10)

        self.start_button = ttk.Button(button_frame, text="Avvia Analisi",
                                       command=self.start_analysis, style='Accent.TButton')
        self.start_button.grid(row=0, column=0, padx=5)

        self.stop_button = ttk.Button(button_frame, text="Interrompi",
                                      command=self.stop_analysis, state='disabled')
        self.stop_button.grid(row=0, column=1, padx=5)

        ttk.Button(button_frame, text="Apri Cartella Output",
                  command=self.open_output_folder).grid(row=0, column=2, padx=5)

        # Bottone Apri Report Dashboard
        self.open_report_button = ttk.Button(button_frame, text="📊 Apri Report",
                                             command=self.open_report_dashboard,
                                             state='disabled')
        self.open_report_button.grid(row=0, column=3, padx=5)

        # Controlla se il report esiste già all'avvio
        self.check_report_availability()

        # ===== COPYRIGHT =====
        copyright_frame = ttk.Frame(main_frame)
        copyright_frame.grid(row=row+1, column=0, columnspan=3, pady=(10, 0))

        ttk.Label(copyright_frame, text="© 2025 ",
                 font=('Arial', 9)).pack(side=tk.LEFT)

        copyright_link = ttk.Label(copyright_frame, text="Luca Mercatanti - mercatanti.com",
                                   font=('Arial', 9), foreground='blue', cursor='hand2')
        copyright_link.pack(side=tk.LEFT)
        copyright_link.bind('<Button-1>', lambda e: self.open_website('https://mercatanti.com'))

    def check_existing_analyses(self):
        """Controlla se esistono analisi precedenti all'avvio"""
        # Cerca nelle cartelle comuni
        common_folders = [
            self.output_dir.get(),
            "output",
            "Report_analisi",
        ]

        # Aggiungi anche le cartelle nella directory corrente
        if os.path.exists("."):
            for item in os.listdir("."):
                if os.path.isdir(item) and ("analisi" in item.lower() or "output" in item.lower()):
                    common_folders.append(item)

        # Rimuovi duplicati
        common_folders = list(set(common_folders))

        for folder in common_folders:
            if os.path.exists(folder):
                self.check_existing_analyses_in_folder(folder)
                if self.skip_to_summary:  # Se trovato, interrompi la ricerca
                    break

    def check_existing_analyses_in_folder(self, output_dir):
        """Controlla analisi esistenti in una cartella specifica"""
        if not os.path.exists(output_dir):
            return

        existing_analyses = [f for f in os.listdir(output_dir)
                           if f.startswith("analisi_chunk_") and f.endswith(".txt")]

        if existing_analyses and not self.skip_to_summary:
            num_existing = len(existing_analyses)
            response = messagebox.askyesno(
                "Analisi esistenti trovate",
                f"Trovati {num_existing} chunk già analizzati in:\n{output_dir}\n\n"
                f"Vuoi creare un nuovo riassunto finale usando questi chunk?\n\n"
                f"• SÌ: Configura API e modello per creare il riassunto finale\n"
                f"• NO: Continua normalmente per una nuova analisi completa"
            )

            if response:
                self.skip_to_summary = True
                self.output_dir.set(output_dir)  # Imposta questa come cartella di output

                self.log(f"Trovati {num_existing} analisi in: {output_dir}")
                self.log("Modalità: Creazione riassunto finale da analisi esistenti")
                self.log("")
                self.log("ISTRUZIONI:")
                self.log("1. Inserisci la tua chiave API")
                self.log("2. Seleziona il modello da utilizzare")
                self.log("3. Premi 'Avvia Analisi' per generare il riassunto finale")
                self.log("")

                # Abilita menu post-elaborazione
                self.update_post_analysis_menu_state()

    def log(self, message):
        """Aggiunge un messaggio al log (GUI e buffer)"""
        from datetime import datetime

        # Timestamp per il log
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] {message}"

        # Salva nel buffer
        self.log_buffer.append(log_entry)

        # Mostra nella GUI
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')
        self.root.update_idletasks()

    def save_log_file(self, output_dir):
        """Salva il log delle operazioni in un file .txt"""
        from datetime import datetime

        log_file = Path(output_dir) / "LOG_OPERAZIONI.txt"
        try:
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write("="*80 + "\n")
                f.write("WHATSAPP FORENSIC ANALYZER - LOG OPERAZIONI\n")
                f.write("="*80 + "\n\n")

                # Scrivi tutte le entry del log
                for entry in self.log_buffer:
                    f.write(f"{entry}\n")

                f.write("\n" + "="*80 + "\n")
                f.write(f"Fine log - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("="*80 + "\n")

            self.log(f"✓ Log salvato in: LOG_OPERAZIONI.txt")
            return str(log_file)
        except Exception as e:
            self.log(f"✗ Errore salvataggio log: {str(e)}")
            return None

    def browse_pdf(self):
        """Apre dialog per selezione PDF"""
        filename = filedialog.askopenfilename(
            title="Seleziona file PDF",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        if filename:
            self.pdf_path.set(filename)
            # Suggerisci cartelle output basate sul nome file
            base_name = Path(filename).stem
            self.chunks_dir.set(f"{base_name}_chunks")
            self.output_dir.set(f"{base_name}_analisi")
            self.log(f"File selezionato: {filename}")

    def browse_chunks_dir(self):
        """Apre dialog per selezione cartella chunk"""
        directory = filedialog.askdirectory(
            title="Seleziona cartella per i chunk",
            initialdir=self.chunks_dir.get() if self.chunks_dir.get() else "."
        )
        if directory:
            self.chunks_dir.set(directory)
            self.log(f"Cartella chunk: {directory}")

    def browse_output_dir(self):
        """Apre dialog per selezione cartella output"""
        directory = filedialog.askdirectory(
            title="Seleziona cartella per le analisi",
            initialdir=self.output_dir.get() if self.output_dir.get() else "."
        )
        if directory:
            self.output_dir.set(directory)
            self.log(f"Cartella analisi: {directory}")

            # Controlla subito se ci sono analisi esistenti
            self.check_existing_analyses_in_folder(directory)

            # Controlla se esiste il report dashboard
            self.check_report_availability()

    def show_help(self, title, message):
        """Mostra una finestra di aiuto"""
        messagebox.showinfo(title, message)

    def calculate_estimates(self):
        """Calcola stime di pagine, chunk, costo e tempo"""
        pdf_file = self.pdf_path.get()

        if not pdf_file or not os.path.exists(pdf_file):
            messagebox.showerror("Errore", "Seleziona un file PDF valido")
            return

        try:
            self.log("Calcolo stime in corso...")

            # Crea processor per analisi
            processor = WhatsAppProcessor(pdf_file, self.max_chars.get())
            stats = processor.get_statistics()

            self.total_pages = stats['total_pages']
            self.total_chunks = stats['estimated_chunks']

            # Calcola costo basato sul modello
            model = self.model_var.get()
            costs = self.get_model_costs(model)

            # Stima più realistica: 1 token ≈ 4 caratteri + prompt overhead
            chars_per_chunk = self.max_chars.get()
            tokens_per_chunk = (chars_per_chunk / 4) + 200  # +200 per il prompt
            avg_output_tokens = 500  # Output medio per chunk

            input_tokens = self.total_chunks * tokens_per_chunk
            output_tokens = self.total_chunks * avg_output_tokens

            input_cost = (input_tokens / 1_000_000) * costs['input']
            output_cost = (output_tokens / 1_000_000) * costs['output']

            # Stima riassunto finale (dipende dal numero di chunk)
            summary_input_tokens = min(self.total_chunks * 200, 50000)  # Max 50k token
            summary_output_tokens = 2000
            summary_cost = ((summary_input_tokens / 1_000_000) * costs['input'] +
                          (summary_output_tokens / 1_000_000) * costs['output'])

            self.estimated_cost = input_cost + output_cost + summary_cost

            # Calcola tempo (6 sec per chunk: ~5 sec API + 1 sec rate limiting)
            self.estimated_time = int(self.total_chunks * 6 / 60)  # minuti

            # Aggiorna labels
            self.pages_label.config(text=f"Pagine: {self.total_pages:,}")
            self.chunks_label.config(text=f"Chunk: {self.total_chunks:,}")
            self.cost_label.config(text=f"Costo stimato: ${self.estimated_cost:.2f}")
            self.time_label.config(text=f"Tempo stimato: ~{self.estimated_time} minuti")

            self.log(f"✓ Stime calcolate: {self.total_pages} pagine, "
                    f"{self.total_chunks} chunk, ${self.estimated_cost:.2f}, "
                    f"~{self.estimated_time} min")

        except Exception as e:
            self.log(f"✗ Errore nel calcolo stime: {str(e)}")
            messagebox.showerror("Errore", f"Impossibile calcolare stime:\n{str(e)}")

    def get_model_costs(self, model):
        """Ritorna i costi per milione di token del modello (aggiornati 2025)"""
        costs = {
            "gpt-4o": {"input": 3.00, "output": 10.00},
            "gpt-4-turbo": {"input": 10.00, "output": 30.00},
            "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
            "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
            "claude-3-opus-20240229": {"input": 15.00, "output": 75.00},
        }
        return costs.get(model, {"input": 3.00, "output": 10.00})

    def update_estimates(self, event=None):
        """Aggiorna stime quando cambia il modello"""
        if self.total_chunks > 0:
            self.calculate_estimates()

    def start_analysis(self):
        """Avvia l'analisi in un thread separato"""
        # Validazione API key (solo se non usa modello locale)
        if not self.use_local_model.get() and not self.api_key.get():
            messagebox.showerror("Errore", "Inserisci la chiave API")
            return

        # Salva la API key se richiesto (solo se non usa modello locale)
        if not self.use_local_model.get():
            self.save_api_key_if_checked()

        # Validazione modello locale
        if self.use_local_model.get():
            if not self.local_model_name.get():
                messagebox.showerror("Errore", "Inserisci il nome del modello locale")
                return
            # Verifica che Ollama sia raggiungibile
            try:
                import requests
                response = requests.get(f"{self.local_url.get()}/api/tags", timeout=5)
                response.raise_for_status()
            except Exception as e:
                messagebox.showerror("Errore",
                    f"Impossibile connettersi a Ollama su {self.local_url.get()}\n\n"
                    f"Assicurati che Ollama sia in esecuzione.\n\n"
                    f"Errore: {str(e)}")
                return

        # Se siamo in modalità skip_to_summary, non serve il PDF
        if not self.skip_to_summary:
            if not self.pdf_path.get() or not os.path.exists(self.pdf_path.get()):
                messagebox.showerror("Errore", "Seleziona un file PDF valido")
                return

            # Controlla se esistono già analisi nella cartella output (solo se NON siamo già in modalità skip)
            output_dir = self.output_dir.get()
            existing_analyses = []
            if os.path.exists(output_dir):
                existing_analyses = [f for f in os.listdir(output_dir)
                                   if f.startswith("analisi_chunk_") and f.endswith(".txt")]

            if existing_analyses and not self.skip_to_summary:
                num_existing = len(existing_analyses)
                response = messagebox.askyesnocancel(
                    "Analisi esistenti trovate",
                    f"Trovati {num_existing} chunk già analizzati in:\n{output_dir}\n\n"
                    f"Vuoi saltare l'analisi e creare direttamente il riassunto finale?\n\n"
                    f"• SÌ: Crea solo il riassunto finale dai chunk esistenti\n"
                    f"• NO: Rianalizza tutto da capo (sovrascrive i file esistenti)\n"
                    f"• ANNULLA: Interrompi operazione"
                )

                if response is None:  # Annulla
                    return
                elif response:  # Sì - salta all'analisi finale
                    self.skip_to_summary = True
                    self.log(f"Utilizzo {num_existing} analisi esistenti per creare il riassunto finale")
                else:  # No - procedi con analisi completa
                    self.log(f"Rielaborazione completa: i {num_existing} file esistenti verranno sovrascritti")

            # Conferma costi (solo se non si salta l'analisi)
            if not self.skip_to_summary and self.estimated_cost > 0:
                # Calcola stime adattate per modalità test
                if self.test_mode.get():
                    test_limit = min(self.test_chunks.get(), self.total_chunks)
                    test_cost = (self.estimated_cost / self.total_chunks) * test_limit
                    test_time = int((self.estimated_time / self.total_chunks) * test_limit)

                    response = messagebox.askyesno(
                        "Conferma - Modalità Test",
                        f"⚠️ MODALITÀ TEST ATTIVA\n\n"
                        f"Chunk da analizzare: {test_limit} (su {self.total_chunks} totali)\n"
                        f"Costo stimato: ${test_cost:.2f}\n"
                        f"Tempo stimato: ~{test_time} minuti\n\n"
                        f"Questa è un'analisi preliminare.\n"
                        f"Potrai verificare l'output prima di procedere\n"
                        f"con l'analisi completa del documento.\n\n"
                        f"Procedere con il test?"
                    )
                else:
                    response = messagebox.askyesno(
                        "Conferma",
                        f"Costo stimato: ${self.estimated_cost:.2f}\n"
                        f"Tempo stimato: ~{self.estimated_time} minuti\n"
                        f"Chunk da analizzare: {self.total_chunks}\n\n"
                        f"Procedere con l'analisi?"
                    )
                if not response:
                    return

        # Disabilita pulsanti
        self.start_button.config(state='disabled')
        self.stop_button.config(state='normal')
        self.is_running = True

        # Salva le cartelle SUBITO (anche se l'analisi viene interrotta, saranno disponibili al prossimo avvio)
        self.save_last_folders()

        # Avvia thread
        thread = threading.Thread(target=self.run_analysis, args=(self.skip_to_summary,), daemon=True)
        thread.start()

    def run_analysis(self, skip_analysis=False):
        """Esegue l'analisi (chiamato in thread separato)"""
        from datetime import datetime

        try:
            # Salva configurazioni analisi
            self.analysis_start_time = datetime.now()
            self.analysis_config = {
                'pdf_path': self.pdf_path.get(),
                'model': self.local_model_name.get() if self.use_local_model.get() else self.model_var.get(),
                'use_local_model': self.use_local_model.get(),
                'chunk_format': self.chunk_format.get(),
                'max_chars': self.max_chars.get(),
                'analyze_images': self.analyze_images.get(),
                'extraction_folder': self.extraction_folder.get() if self.analyze_images.get() else None,
                'custom_prompt': self.prompt_text.get('1.0', tk.END).strip(),
                'total_pages': self.total_pages,
                'total_chunks': self.total_chunks,
                'estimated_cost': self.estimated_cost,
                'estimated_time': self.estimated_time,
                'skip_analysis': skip_analysis
            }

            self.update_status("Preparazione in corso...", "blue")
            self.log("="*60)
            self.log("AVVIO ANALISI")
            self.log("="*60)

            analyses = []
            chunks = []

            if skip_analysis:
                # Carica le analisi esistenti
                self.log("Caricamento analisi esistenti...")
                output_dir = self.output_dir.get()
                analysis_files = sorted([f for f in os.listdir(output_dir)
                                       if f.startswith("analisi_chunk_") and f.endswith(".txt")])

                for analysis_file in analysis_files:
                    file_path = os.path.join(output_dir, analysis_file)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        analyses.append(f.read())

                self.log(f"✓ Caricate {len(analyses)} analisi esistenti")
                self.update_progress(90)

            else:
                # Step 1: Segmentazione PDF
                self.update_status("Segmentazione PDF...", "blue")
                self.log(f"1. Segmentazione PDF: {self.pdf_path.get()}")
                self.log(f"   Formato: {self.chunk_format.get().upper()}")

                if self.analyze_images.get():
                    self.log(f"   Analisi immagini: ATTIVA")
                    self.log(f"   Cartella estrazione: {self.extraction_folder.get()}")

                processor = WhatsAppProcessor(
                    self.pdf_path.get(),
                    self.max_chars.get(),
                    chunk_format=self.chunk_format.get(),
                    extract_images=self.analyze_images.get(),
                    extraction_folder=self.extraction_folder.get() if self.analyze_images.get() else None
                )

                chunks = processor.split_pdf(self.chunks_dir.get(),
                                            progress_callback=self.update_progress)

                self.log(f"✓ Creati {len(chunks)} chunk in '{self.chunks_dir.get()}'")

                # Limita chunk se in modalità test
                original_chunks_count = len(chunks)
                if self.test_mode.get():
                    test_limit = self.test_chunks.get()
                    chunks = chunks[:test_limit]
                    self.log(f"⚠️ MODALITÀ TEST: limitazione a {len(chunks)} chunk (su {original_chunks_count} totali)")
                    self.analysis_config['test_mode'] = True
                    self.analysis_config['test_chunks_analyzed'] = len(chunks)
                    self.analysis_config['original_total_chunks'] = original_chunks_count

                # Log immagini trovate
                total_images = sum(chunk.get('images_count', 0) for chunk in chunks)
                if total_images > 0:
                    self.log(f"✓ Trovate {total_images} immagini nei chunk")

                if not self.is_running:
                    self.log("✗ Analisi interrotta dall'utente")
                    return

                # Step 2: Analisi AI
                self.update_status("Analisi AI in corso...", "blue")

                if self.use_local_model.get():
                    self.log(f"2. Analisi con modello locale: {self.local_model_name.get()}")
                else:
                    self.log(f"2. Analisi con {self.model_var.get()}")

                custom_prompt = self.prompt_text.get('1.0', tk.END).strip()
                if not custom_prompt:
                    custom_prompt = None

                if self.use_local_model.get():
                    analyzer = AIAnalyzer(
                        api_key="",  # Non necessaria per modelli locali
                        model=self.local_model_name.get(),
                        use_local=True,
                        local_url=self.local_url.get()
                    )
                else:
                    analyzer = AIAnalyzer(
                        api_key=self.api_key.get(),
                        model=self.model_var.get()
                    )

                analyses = analyzer.analyze_chunks(
                    chunks,
                    self.output_dir.get(),
                    custom_prompt=custom_prompt,
                    progress_callback=self.update_progress,
                    stop_flag=lambda: not self.is_running,
                    log_callback=self.log
                )

                if not self.is_running:
                    self.log("✗ Analisi interrotta dall'utente")
                    return

                self.log(f"✓ Analizzati {len(analyses)} chunk")

            # Inizializza analyzer se necessario (per skip_analysis)
            if skip_analysis:
                if self.use_local_model.get():
                    analyzer = AIAnalyzer(
                        api_key="",
                        model=self.local_model_name.get(),
                        use_local=True,
                        local_url=self.local_url.get()
                    )
                else:
                    analyzer = AIAnalyzer(
                        api_key=self.api_key.get(),
                        model=self.model_var.get()
                    )

            # Step 3: Riassunto finale
            self.update_status("Creazione riassunto finale...", "blue")
            self.log("3. Generazione riassunto finale")

            if len(analyses) > 100:
                self.log(f"   [INFO] Documento molto grande ({len(analyses)} chunk)")
                self.log(f"   [INFO] Utilizzo approccio gerarchico (questo potrebbe richiedere alcuni minuti)")

            try:
                # Usa len(analyses) se skip_analysis, altrimenti len(chunks)
                total_chunks = len(analyses) if skip_analysis else len(chunks)
                summary = analyzer.create_final_summary(
                    analyses,
                    total_chunks,
                    self.output_dir.get(),
                    log_callback=self.log,
                    analysis_config=self.analysis_config
                )

                # Verifica che il file sia stato effettivamente creato
                summary_path = Path(self.output_dir.get()) / "RIASSUNTO_FINALE.txt"
                if summary_path.exists():
                    self.log(f"✓ Riassunto finale salvato come: RIASSUNTO_FINALE.txt")
                else:
                    self.log(f"✗ ATTENZIONE: Il riassunto non è stato salvato correttamente")
                    raise Exception("File RIASSUNTO_FINALE.txt non trovato dopo la creazione")

            except Exception as e:
                self.log(f"✗ Errore nella creazione del riassunto finale: {str(e)}")
                raise

            # Salva il log delle operazioni
            self.save_log_file(self.output_dir.get())

            # Completato
            self.update_status("Analisi completata!", "green")
            self.update_progress(100)
            self.log("="*60)
            self.log("ANALISI COMPLETATA CON SUCCESSO!")
            self.log("="*60)

            # Salva le cartelle usate per il prossimo avvio
            self.save_last_folders()

            # Abilita menu post-elaborazione
            self.update_post_analysis_menu_state()

            # Abilita bottone "Apri Report" se il report esiste
            self.check_report_availability()

            # Mostra dialog informativo post-analisi (solo se non in modalità test)
            if not self.analysis_config.get('test_mode', False):
                if PostAnalysisInfoDialog.should_show():
                    PostAnalysisInfoDialog(self.root)

            # Messaggio di completamento differenziato per modalità test
            if self.analysis_config.get('test_mode', False):
                original_total = self.analysis_config.get('original_total_chunks', 0)
                messagebox.showinfo(
                    "Test Completato",
                    f"⚠️ ANALISI PRELIMINARE COMPLETATA\n\n"
                    f"Chunk analizzati: {len(analyses)} (su {original_total} totali)\n"
                    f"Report parziale:\n"
                    f"  • index.html (report interattivo)\n"
                    f"  • RIASSUNTO_FINALE.txt (parziale)\n"
                    f"  • LOG_OPERAZIONI.txt\n\n"
                    f"Cartella risultati: {self.output_dir.get()}\n\n"
                    f"💡 Verifica l'output generato.\n"
                    f"Se soddisfacente, disattiva la modalità test e\n"
                    f"procedi con l'analisi completa del documento."
                )
            else:
                messagebox.showinfo(
                    "Completato",
                    f"Analisi completata!\n\n"
                    f"Chunk analizzati: {len(analyses)}\n"
                    f"Report finale:\n"
                    f"  • index.html (report interattivo)\n"
                    f"  • RIASSUNTO_FINALE.txt\n"
                    f"  • LOG_OPERAZIONI.txt\n\n"
                    f"Cartella risultati: {self.output_dir.get()}"
                )

        except Exception as e:
            self.log(f"✗ ERRORE: {str(e)}")
            self.update_status("Errore durante l'analisi", "red")
            messagebox.showerror("Errore", f"Errore durante l'analisi:\n{str(e)}")

        finally:
            self.is_running = False
            self.start_button.config(state='normal')
            self.stop_button.config(state='disabled')

    def stop_analysis(self):
        """Interrompe l'analisi"""
        self.is_running = False
        self.update_status("Interruzione in corso...", "orange")
        self.log("Interruzione richiesta dall'utente...")

    def update_status(self, message, color="black"):
        """Aggiorna il label di stato"""
        self.status_label.config(text=message, foreground=color)
        self.root.update_idletasks()

    def update_progress(self, percentage):
        """Aggiorna la barra di progresso"""
        self.progress_var.set(percentage)
        self.root.update_idletasks()

    def open_output_folder(self):
        """Apre la cartella di output"""
        output = self.output_dir.get()
        if os.path.exists(output):
            os.startfile(output)
        else:
            messagebox.showinfo("Info", f"La cartella '{output}' non esiste ancora")

    def open_report_dashboard(self):
        """Apre la dashboard dei report nel browser"""
        import webbrowser
        output = self.output_dir.get()
        report_path = os.path.join(output, "REPORT", "index.html")

        if os.path.exists(report_path):
            # Converte il path in URL file://
            report_url = f"file:///{os.path.abspath(report_path).replace(os.sep, '/')}"
            webbrowser.open(report_url)
            self.log("📊 Dashboard report aperta nel browser")
        else:
            messagebox.showinfo(
                "Report non disponibile",
                "La dashboard dei report non è ancora stata generata.\n\n"
                "Completa un'analisi principale per generare il report."
            )

    def check_report_availability(self):
        """Controlla se il report esiste e abilita/disabilita il bottone"""
        output = self.output_dir.get()
        report_path = os.path.join(output, "REPORT", "index.html")

        if os.path.exists(report_path):
            self.open_report_button.config(state='normal')
        else:
            self.open_report_button.config(state='disabled')

    def open_website(self, url):
        """Apre un URL nel browser predefinito"""
        import webbrowser
        webbrowser.open(url)

    def toggle_local_model(self):
        """Mostra/nasconde configurazione modello locale"""
        if self.use_local_model.get():
            # Mostra configurazione locale
            self.local_config_frame.grid()
            # Disabilita API key e modello cloud
            self.api_entry.config(state='disabled')
            self.model_combo.config(state='disabled')
            # Aumenta altezza finestra
            self.root.geometry("910x1200")
            # Carica modelli Ollama disponibili
            self.refresh_ollama_models()
            self.log("Modalità modello locale attivata")
        else:
            # Nascondi configurazione locale
            self.local_config_frame.grid_remove()
            # Riabilita API key e modello cloud
            self.api_entry.config(state='normal')
            self.model_combo.config(state='readonly')
            # Ripristina altezza originale
            self.root.geometry("910x1050")
            self.log("Modalità modello cloud attivata")

    def refresh_ollama_models(self):
        """Recupera la lista dei modelli Ollama disponibili"""
        try:
            import requests
            response = requests.get(f"{self.local_url.get()}/api/tags", timeout=5)
            response.raise_for_status()
            data = response.json()

            models = [model['name'] for model in data.get('models', [])]

            if models:
                self.local_model_combo['values'] = models
                self.log(f"Trovati {len(models)} modelli Ollama: {', '.join(models)}")
                if not self.local_model_name.get() and models:
                    self.local_model_name.set(models[0])
            else:
                self.local_model_combo['values'] = []
                self.log("Nessun modello Ollama trovato. Scaricane uno con: ollama pull llama3.2")

        except Exception as e:
            self.log(f"Impossibile connettersi a Ollama: {str(e)}")
            self.local_model_combo['values'] = []
            messagebox.showwarning("Ollama non disponibile",
                f"Non riesco a connettersi a Ollama su {self.local_url.get()}\n\n"
                f"Assicurati che Ollama sia installato e in esecuzione.\n"
                f"Scarica da: https://ollama.ai/download")

    def load_templates(self):
        """Carica i template salvati da file JSON"""
        import json
        templates_file = Path("prompt_templates.json")

        # Template predefinito aggiornato con analisi posizioni
        default_templates = {
            "Default": (
                "Analizza questo report WhatsApp e fornisci un'analisi forense strutturata:\n\n"
                "## 1. Partecipanti e Struttura\n"
                "- Identifica tutti i partecipanti della conversazione\n"
                "- Individua ruoli (amministratori, membri, ecc.)\n"
                "- Indica date di ingresso/uscita dal gruppo\n\n"
                "## 2. Timeline e Cronologia\n"
                "- Periodo temporale delle conversazioni (data inizio - data fine)\n"
                "- Eventi significativi con timestamp precisi\n"
                "- Pattern temporali (orari di attività, pause, ecc.)\n\n"
                "## 3. Contenuti e Messaggi Rilevanti\n"
                "- Messaggi importanti con citazione e timestamp\n"
                "- Media condivisi (foto, video, documenti) con autore e data\n"
                "- Link esterni condivisi\n\n"
                "## 4. Posizioni e Spostamenti\n"
                "Per ogni menzione di posizioni o spostamenti indica:\n"
                "- **Posizioni GPS condivise**: coordinate o nome luogo, autore, timestamp, riferimento messaggio\n"
                "- **Menzioni di luoghi**: qualsiasi riferimento a indirizzi, città, luoghi specifici\n"
                "- **Discussioni su spostamenti**: viaggi, appuntamenti in luoghi fisici, ecc.\n"
                "Formato richiesto per ogni voce:\n"
                "  • Luogo/Posizione: [descrizione]\n"
                "  • Utente: [nome]\n"
                "  • Data/Ora: [timestamp]\n"
                "  • Contesto: [breve descrizione del messaggio]\n"
                "  • Riferimento: [numero pagina o identificativo messaggio]\n\n"
                "## 5. Minacce e Contenuti Problematici\n"
                "⚠️ SEZIONE CRITICA - Analizza attentamente per rilevare:\n"
                "- **Minacce**: esplicite o implicite, dirette o indirette\n"
                "- **Offese e insulti**: linguaggio offensivo, discriminatorio\n"
                "- **Aggressioni verbali**: tono aggressivo, intimidatorio\n"
                "- **Circonvenzioni**: manipolazione, estorsione, ricatti\n"
                "- **Contenuti illeciti**: riferimenti a attività illegali\n"
                "- **Molestie**: comportamenti persecutori, stalking\n"
                "- **Violenza**: riferimenti a violenza fisica o psicologica\n\n"
                "Formato richiesto per OGNI contenuto problematico:\n"
                "  • Tipo: [minaccia/offesa/aggressione/circonvenzione/altro]\n"
                "  • Gravità: [bassa/media/alta/critica]\n"
                "  • Utente: [autore del messaggio]\n"
                "  • Destinatario: [a chi è rivolto]\n"
                "  • Data/Ora: [timestamp preciso]\n"
                "  • Messaggio: [citazione testuale o parafrasi]\n"
                "  • Contesto: [situazione in cui è avvenuto]\n"
                "  • Riferimento: [pagina/messaggio originale]\n\n"
                "Se non ci sono contenuti problematici: indica 'Nessun contenuto problematico rilevato in questo chunk'\n\n"
                "## 6. Informazioni Sensibili (Dati Personali)\n"
                "- Numeri di telefono\n"
                "- Indirizzi email\n"
                "- Indirizzi fisici\n"
                "- Documenti identificativi\n"
                "- Dati finanziari\n\n"
                "## 7. Pattern di Comunicazione\n"
                "- Relazioni tra i partecipanti\n"
                "- Temi ricorrenti\n"
                "- Linguaggio e tono utilizzato\n\n"
                "## 8. Note Forensi\n"
                "- Eventuali anomalie\n"
                "- Messaggi eliminati (se visibili)\n"
                "- Cambiamenti di gruppo\n\n"
                "**IMPORTANTE**: \n"
                "- Per ogni informazione rilevante, indica SEMPRE il timestamp e il riferimento alla pagina/messaggio originale\n"
                "- Se non ci sono posizioni o spostamenti menzionati, indica esplicitamente 'Nessuna posizione rilevata in questo chunk'\n"
                "- Ignora messaggi di sistema sulla crittografia end-to-end"
            )
        }

        if templates_file.exists():
            try:
                with open(templates_file, 'r', encoding='utf-8') as f:
                    saved_templates = json.load(f)
                    # Merge con i default
                    default_templates.update(saved_templates)
            except Exception as e:
                self.log(f"Errore caricamento template: {str(e)}")

        return default_templates

    def save_templates_to_file(self):
        """Salva i template su file JSON"""
        import json
        templates_file = Path("prompt_templates.json")

        # Rimuovi il template predefinito dal salvataggio
        templates_to_save = {k: v for k, v in self.templates.items() if k != "Default"}

        try:
            with open(templates_file, 'w', encoding='utf-8') as f:
                json.dump(templates_to_save, f, indent=2, ensure_ascii=False)
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile salvare template:\n{str(e)}")

    def update_template_list(self):
        """Aggiorna la lista dei template nel dropdown"""
        template_names = ["Personalizzato"] + list(self.templates.keys())
        self.template_combo['values'] = template_names

    def load_template(self, event=None):
        """Carica un template selezionato"""
        template_name = self.template_var.get()

        if template_name == "Personalizzato":
            return

        if template_name in self.templates:
            self.prompt_text.delete('1.0', tk.END)
            self.prompt_text.insert('1.0', self.templates[template_name])
            self.log(f"Template caricato: {template_name}")

    def save_template(self):
        """Salva il prompt corrente come template"""
        from tkinter import simpledialog

        template_name = simpledialog.askstring("Salva Template",
                                               "Nome del template:",
                                               parent=self.root)

        if not template_name:
            return

        if template_name == "Personalizzato":
            messagebox.showerror("Errore", "Non puoi usare 'Personalizzato' come nome")
            return

        prompt_content = self.prompt_text.get('1.0', tk.END).strip()

        if not prompt_content:
            messagebox.showerror("Errore", "Il prompt è vuoto")
            return

        self.templates[template_name] = prompt_content
        self.save_templates_to_file()
        self.update_template_list()
        self.template_var.set(template_name)
        self.log(f"Template salvato: {template_name}")
        messagebox.showinfo("Successo", f"Template '{template_name}' salvato correttamente")

    def delete_template(self):
        """Elimina il template selezionato"""
        template_name = self.template_var.get()

        if template_name == "Personalizzato":
            messagebox.showinfo("Info", "Seleziona un template da eliminare")
            return

        # Non permettere di eliminare il template predefinito
        if template_name == "Default":
            messagebox.showerror("Errore", "Non puoi eliminare il template predefinito")
            return

        response = messagebox.askyesno("Conferma",
                                      f"Eliminare il template '{template_name}'?")

        if response:
            del self.templates[template_name]
            self.save_templates_to_file()
            self.update_template_list()
            self.template_var.set("Personalizzato")
            self.prompt_text.delete('1.0', tk.END)
            self.log(f"Template eliminato: {template_name}")
            messagebox.showinfo("Successo", f"Template '{template_name}' eliminato")

    def toggle_image_analysis(self):
        """Mostra/nasconde campo cartella estrazione"""
        if self.analyze_images.get():
            # Mostra campo cartella
            self.extraction_frame.grid()

            # Se formato è TXT, avvisa e suggerisci JSON
            if self.chunk_format.get() == "txt":
                response = messagebox.askyesno(
                    "Formato non compatibile",
                    "L'analisi immagini richiede il formato JSON.\n\n"
                    "Vuoi cambiare automaticamente il formato in JSON?"
                )
                if response:
                    self.chunk_format.set("json")
                    self.log("Formato chunk cambiato in JSON per supportare le immagini")
                else:
                    # Se dice no, disattiva l'analisi immagini
                    self.analyze_images.set(False)
                    self.extraction_frame.grid_remove()
                    return

            self.log("Analisi immagini attivata")
        else:
            # Nascondi campo cartella
            self.extraction_frame.grid_remove()
            self.log("Analisi immagini disattivata")

    def on_format_change(self):
        """Gestisce il cambio di formato chunk"""
        # Se cambio a TXT ma ho immagini attive, avvisa
        if self.chunk_format.get() == "txt" and self.analyze_images.get():
            messagebox.showwarning(
                "Formato non compatibile",
                "Il formato TXT non supporta l'analisi immagini.\n\n"
                "L'analisi immagini verrà disattivata."
            )
            self.analyze_images.set(False)
            self.extraction_frame.grid_remove()
            self.log("Analisi immagini disattivata (formato TXT non compatibile)")

        self.log(f"Formato chunk: {self.chunk_format.get().upper()}")

    def browse_extraction_folder(self):
        """Apre dialog per selezione cartella estrazione Cellebrite"""
        directory = filedialog.askdirectory(
            title="Seleziona cartella estrazione Cellebrite",
            initialdir=self.extraction_folder.get() if self.extraction_folder.get() else "."
        )
        if directory:
            self.extraction_folder.set(directory)
            self.log(f"Cartella estrazione: {directory}")

    def toggle_test_mode(self):
        """Gestisce attivazione/disattivazione modalità test"""
        if self.test_mode.get():
            self.log(f"✓ Modalità test attivata: analisi limitata a {self.test_chunks.get()} chunk")
            messagebox.showinfo(
                "Modalità Test Attiva",
                f"Verranno analizzati solo i primi {self.test_chunks.get()} chunk.\n\n"
                "Potrai verificare la qualità dell'output prima di\n"
                "procedere con l'analisi completa del documento."
            )
        else:
            self.log("Modalità test disattivata: analisi completa")

    def load_saved_api_key(self):
        """Carica la chiave API salvata all'avvio"""
        # Determina il tipo di chiave da caricare (OpenAI o Anthropic)
        model = self.model_var.get()
        key_type = "anthropic" if "claude" in model.lower() else "openai"

        saved_key = self.api_key_manager.load_api_key(key_type)

        if saved_key:
            self.api_key.set(saved_key)
            self.save_api_key_var.set(True)
            # Log solo se è in modalità non-locale
            if not self.use_local_model.get():
                self.log(f"✓ API Key {key_type.upper()} caricata da file cifrato")

    def toggle_save_api_key(self):
        """Salva o aggiorna la chiave API quando si clicca il pulsante"""
        api_key = self.api_key.get()
        if not api_key or not api_key.strip():
            messagebox.showwarning("Attenzione", "Inserisci prima una chiave API da salvare")
            return

        # Determina il tipo di chiave (OpenAI o Anthropic)
        model = self.model_var.get()
        key_type = "anthropic" if "claude" in model.lower() else "openai"

        # Mostra avviso limiti API solo per OpenAI e solo la prima volta
        if key_type == "openai" and not self.api_key_manager.has_saved_key(key_type):
            if not self.check_api_limits_warning_shown():
                self.show_api_limits_warning()

        success = self.api_key_manager.save_api_key(api_key, key_type)

        if success:
            self.save_api_key_var.set(True)
            self.log(f"✓ API Key {key_type.upper()} salvata in modo sicuro")
            messagebox.showinfo("Successo", f"Chiave API {key_type.upper()} salvata localmente (cifrata)")
        else:
            self.log(f"✗ Errore nel salvataggio della API Key")
            messagebox.showerror("Errore", "Impossibile salvare la chiave API")

    def save_api_key_if_checked(self):
        """Salva la chiave API se la variabile è attiva"""
        if not self.save_api_key_var.get():
            return

        api_key = self.api_key.get()
        if not api_key or not api_key.strip():
            return

        # Determina il tipo di chiave (OpenAI o Anthropic)
        model = self.model_var.get()
        key_type = "anthropic" if "claude" in model.lower() else "openai"

        success = self.api_key_manager.save_api_key(api_key, key_type)

        if success:
            self.log(f"✓ API Key {key_type.upper()} salvata in modo sicuro")
        else:
            self.log(f"✗ Errore nel salvataggio della API Key")

    def clear_saved_api_key(self):
        """Cancella la chiave API salvata"""
        # Controlla se esiste una chiave salvata
        has_openai = self.api_key_manager.has_saved_key("openai")
        has_anthropic = self.api_key_manager.has_saved_key("anthropic")

        if not has_openai and not has_anthropic:
            messagebox.showinfo("Info", "Nessuna chiave API salvata da eliminare")
            return

        # Chiedi conferma
        message = "Eliminare le chiavi API salvate?\n\n"
        if has_openai:
            message += "• OpenAI\n"
        if has_anthropic:
            message += "• Anthropic\n"

        response = messagebox.askyesno("Conferma Eliminazione", message)

        if response:
            success = self.api_key_manager.delete_all_keys()

            if success:
                # Pulisci il campo
                self.api_key.set("")
                self.save_api_key_var.set(False)
                self.log("✓ Chiavi API eliminate")
                messagebox.showinfo("Successo", "Chiavi API eliminate correttamente")
            else:
                self.log("✗ Errore nell'eliminazione delle chiavi")
                messagebox.showerror("Errore", "Impossibile eliminare le chiavi")

    def check_api_limits_warning_shown(self):
        """Verifica se l'avviso sui limiti API è già stato mostrato"""
        import json
        preferences_file = Path(".user_preferences.json")

        if not preferences_file.exists():
            return False

        try:
            with open(preferences_file, 'r', encoding='utf-8') as f:
                prefs = json.load(f)
                return prefs.get('api_limits_warning_shown', False)
        except:
            return False

    def save_api_limits_warning_preference(self, dont_show_again):
        """Salva la preferenza dell'utente sull'avviso limiti API"""
        import json
        preferences_file = Path(".user_preferences.json")

        prefs = {}
        if preferences_file.exists():
            try:
                with open(preferences_file, 'r', encoding='utf-8') as f:
                    prefs = json.load(f)
            except:
                pass

        prefs['api_limits_warning_shown'] = dont_show_again

        try:
            with open(preferences_file, 'w', encoding='utf-8') as f:
                json.dump(prefs, f, indent=2)
        except Exception as e:
            self.log(f"⚠️ Impossibile salvare preferenza: {str(e)}")

    def show_api_limits_warning(self):
        """Mostra dialog informativo sui limiti API OpenAI"""
        # Crea finestra dialog personalizzata
        dialog = tk.Toplevel(self.root)
        dialog.title("⚠️ Informazioni Importanti - Limiti API OpenAI")
        dialog.geometry("750x650")
        self.center_window(dialog, 750, 650)
        dialog.resizable(False, False)
        dialog.grab_set()  # Modale

        # Frame principale
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Titolo
        title_label = ttk.Label(main_frame,
                               text="⚠️ LIMITI API OPENAI - INFORMAZIONI IMPORTANTI",
                               font=('Arial', 12, 'bold'),
                               foreground='#D32F2F')
        title_label.pack(pady=(0, 15))

        # Testo informativo scrollabile
        text_frame = ttk.Frame(main_frame)
        text_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        info_text = tk.Text(text_frame, wrap=tk.WORD, width=80, height=25,
                           font=('Arial', 10), yscrollcommand=scrollbar.set)
        info_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=info_text.yview)

        # Contenuto informativo
        content = """TUTTI i provider API (OpenAI, Anthropic) applicano limiti di utilizzo.
Questi limiti NON dipendono dal credito disponibile, ma dalla CRONOLOGIA dei pagamenti.

═══════════════════════════════════════════════════════════════

📊 TIER OPENAI E LIMITI TPM (Tokens Per Minute)

┌─────────────┬──────────────┬────────────────┬─────────────────┐
│ TIER        │ TPM GPT-4o   │ TPM GPT-3.5    │ Come Ottenerlo  │
├─────────────┼──────────────┼────────────────┼─────────────────┤
│ Free Trial  │ 30,000       │ 40,000         │ Account nuovo   │
│ Tier 1      │ 30,000-90k   │ 200,000        │ $5+ spesi       │
│ Tier 2      │ 450,000      │ 2,000,000      │ $50+ + 7 giorni │
│ Tier 3      │ 10,000,000   │ 10,000,000     │ $1,000+ spesi   │
└─────────────┴──────────────┴────────────────┴─────────────────┘

📊 TIER ANTHROPIC (CLAUDE) E LIMITI TPM

┌──────────┬─────────────────┬─────────────────┬──────────────┐
│ TIER     │ TPM Input       │ TPM Output      │ Come Ottenerlo│
├──────────┼─────────────────┼─────────────────┼──────────────┤
│ Tier 1   │ 40,000          │ 8,000           │ Default      │
│ Tier 2   │ 80,000          │ 16,000          │ $5+ spesi    │
│ Tier 3   │ 160,000         │ 32,000          │ $40+ spesi   │
│ Tier 4   │ 400,000         │ 80,000          │ $200+ spesi  │
└──────────┴─────────────────┴─────────────────┴──────────────┘

⚠️ NOTA: Anthropic conta separatamente input/output!
   Per documenti grandi, Tier 1 Anthropic (40k) > OpenAI Tier 1 (30k)

💻 MODELLI LOCALI (OLLAMA): NESSUN LIMITE API!
   • Nessun costo per token
   • Nessun rate limiting
   • Velocità limitata solo dall'hardware

═══════════════════════════════════════════════════════════════

⚠️ PROBLEMA 1: DOCUMENTI GRANDI (>30 CHUNK)

Quando questo programma crea il RIASSUNTO FINALE, combina tutte le analisi
dei chunk. Con documenti grandi, la richiesta può superare i limiti TPM.

ESEMPIO CON 50 CHUNK:
• 50 analisi × 800 caratteri = 40,000 caratteri
• ÷ 4 = ~10,000 token input
• + 8,000 token max output
• = ~18,000 token in una richiesta

❌ SE SEI IN FREE TRIAL O TIER 1 → ERRORE 429!
   "Request too large for gpt-4o on tokens per min (TPM)"

═══════════════════════════════════════════════════════════════

⚠️ PROBLEMA 2: ANALISI SEQUENZIALE CHUNK (TIMEOUT)

Durante l'analisi iniziale, il programma analizza i chunk UNO ALLA VOLTA.
Se il delay tra richieste è troppo breve, si supera il limite TPM:

CON TIER 1 (30,000 TPM):
• Ogni chunk: ~1,500 token (1,000 input + 500 output)
• Max chunk/minuto: 30,000 ÷ 1,500 = 20 chunk/minuto
• Delay necessario: 60 secondi ÷ 20 = 3 secondi tra chunk

❌ CON DELAY 1 SECONDO → TIMEOUT/ERRORE 429!
✅ IL PROGRAMMA ORA CALCOLA AUTOMATICAMENTE IL DELAY CORRETTO

DELAY AUTOMATICI IN BASE AL TUO TIER:
• Tier 1 (30k TPM):   ~3.6 secondi tra chunk
• Tier 1 (90k TPM):   ~1.2 secondi tra chunk
• Tier 2 (450k TPM):  ~0.2 secondi tra chunk
• Tier 3 (10M TPM):   ~0.01 secondi tra chunk

═══════════════════════════════════════════════════════════════

✅ SOLUZIONI IMMEDIATE

1. CONFIGURA IL TUO PROVIDER E TIER (⚙️ Impostazioni > Impostazioni API)
   • Seleziona il provider che usi (OpenAI/Anthropic/Locale)
   • Seleziona il tuo tier corrente
   • Il programma calcolerà automaticamente i delay corretti
   • Evita timeout ed errori 429

2. CONSIDERA ANTHROPIC CLAUDE per documenti grandi
   • Tier 1 ha 40,000 TPM input (vs 30,000 di OpenAI GPT-4o)
   • Qualità simile a GPT-4o
   • Più generoso con i limiti
   📝 COME: Configura API Key Anthropic e seleziona "claude-3-5-sonnet"

3. USA GPT-3.5-TURBO per documenti grandi
   • Tier 1 ha 200,000 TPM (vs 30,000 di GPT-4o)
   • Costa 10x meno ($0.50/$1.50 vs $3/$10 per 1M token)
   • Ottima qualità per riassunti
   📝 COME: Nel dropdown "Modello", seleziona "gpt-3.5-turbo"

4. APPROCCIO GERARCHICO (automatico >30 chunk)
   • Il programma divide automaticamente documenti grandi
   • Crea riassunti intermedi per evitare limiti TPM
   • Configurabile in: ⚙️ Impostazioni > Impostazioni API

5. USA MODELLO LOCALE OLLAMA (senza limiti!)
   • Installa Ollama (https://ollama.ai)
   • Scarica modelli come llama3, mistral, etc.
   • ZERO limiti API, ZERO costi
   • Velocità dipende dall'hardware

6. UPGRADE AL TIER SUPERIORE (per uso intensivo)
   • OpenAI Tier 2: Spendi $50+ + 7 giorni → 450k TPM (15x più veloce!)
   • Anthropic Tier 2: Spendi $5+ → 80k TPM (2x più veloce!)

═══════════════════════════════════════════════════════════════

🎯 RATE LIMITING INTELLIGENTE MULTI-PROVIDER (NOVITÀ!)

Il programma ora implementa un sistema di rate limiting intelligente che:

✓ Rileva automaticamente il provider (OpenAI/Anthropic/Locale)
✓ Applica limiti specifici per ogni provider
✓ Disabilita rate limiting per modelli locali Ollama
✓ Calcola delay ottimale in base al tuo TPM configurato
✓ Aggiunge margine di sicurezza del 20%
✓ Mostra nel log il tempo di attesa tra chunk

Vedrai messaggi come:
"⚙️ Rate Limiting (OpenAI): TPM=30,000, Delay=3.6s tra richieste"
"⏳ Attesa 3.6s (rate limiting TPM)..."
"⚙️ Modello locale rilevato: rate limiting disabilitato"

Questo è NORMALE e NECESSARIO per rispettare i limiti API!

═══════════════════════════════════════════════════════════════

📖 MAGGIORI INFORMAZIONI

OpenAI - Documentazione limiti:
https://platform.openai.com/docs/guides/rate-limits
OpenAI - Controlla il tuo tier:
https://platform.openai.com/settings/organization/limits

Anthropic - Documentazione limiti:
https://docs.anthropic.com/en/api/rate-limits
Anthropic - Console:
https://console.anthropic.com

═══════════════════════════════════════════════════════════════

💡 CONSIGLI FINALI

📌 CONFIGURA IL PROVIDER in "⚙️ Impostazioni > Impostazioni API"
   • Seleziona il provider corretto (OpenAI/Anthropic/Locale)
   • Imposta il tuo Tier per evitare timeout
   • Il rate limiting si adatterà automaticamente!

🚀 SCELTA MODELLO per ottimizzare:
   • Analisi iniziale chunk: GPT-4o o Claude 3.5 Sonnet (massima qualità)
   • Riassunto finale: GPT-3.5-turbo (evita limiti, ottimo per riassunti)
   • Uso locale: Ollama con llama3/mistral (zero costi, zero limiti)

⚡ Per documenti >100 chunk: considera Anthropic o modelli locali!
"""

        info_text.insert('1.0', content)
        info_text.config(state='disabled')

        # Checkbox "Non mostrare più"
        dont_show_var = tk.BooleanVar(value=False)
        checkbox = ttk.Checkbutton(main_frame,
                                   text="✓ Non mostrare più questo avviso",
                                   variable=dont_show_var)
        checkbox.pack(pady=(10, 15))

        # Frame pulsanti
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=(0, 10))

        def on_close():
            # Salva preferenza se checkbox è spuntata
            if dont_show_var.get():
                self.save_api_limits_warning_preference(True)
                self.log("✓ Preferenza salvata: avviso limiti API non verrà più mostrato")
            dialog.destroy()

        ttk.Button(button_frame, text="✓ Ho Capito",
                  command=on_close,
                  style='Accent.TButton',
                  width=20).pack()

        # Centra la finestra
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")

        # Attendi chiusura
        dialog.wait_window()

    def load_api_settings(self):
        """Carica le impostazioni API salvate"""
        import json
        preferences_file = Path(".user_preferences.json")

        # Default values
        defaults = {
            'provider': 'openai',  # Provider di default
            'max_tpm_limit': 30000,  # Tier 1 GPT-4o default
            'hierarchical_threshold': 30,  # Chunk threshold
            'enable_auto_adapt': True
        }

        if not preferences_file.exists():
            return defaults

        try:
            with open(preferences_file, 'r', encoding='utf-8') as f:
                prefs = json.load(f)
                return {
                    'provider': prefs.get('provider', defaults['provider']),
                    'max_tpm_limit': prefs.get('max_tpm_limit', defaults['max_tpm_limit']),
                    'hierarchical_threshold': prefs.get('hierarchical_threshold', defaults['hierarchical_threshold']),
                    'enable_auto_adapt': prefs.get('enable_auto_adapt', defaults['enable_auto_adapt'])
                }
        except:
            return defaults

    def save_api_settings(self, provider, max_tpm, threshold, auto_adapt):
        """Salva le impostazioni API"""
        import json
        preferences_file = Path(".user_preferences.json")

        prefs = {}
        if preferences_file.exists():
            try:
                with open(preferences_file, 'r', encoding='utf-8') as f:
                    prefs = json.load(f)
            except:
                pass

        prefs['provider'] = provider
        prefs['max_tpm_limit'] = max_tpm
        prefs['hierarchical_threshold'] = threshold
        prefs['enable_auto_adapt'] = auto_adapt

        try:
            with open(preferences_file, 'w', encoding='utf-8') as f:
                json.dump(prefs, f, indent=2)
            return True
        except Exception as e:
            self.log(f"⚠️ Errore salvataggio impostazioni: {str(e)}")
            return False

    def save_last_folders(self):
        """Salva le ultime cartelle usate nelle preferenze"""
        import json
        preferences_file = Path(".user_preferences.json")

        prefs = {}
        if preferences_file.exists():
            try:
                with open(preferences_file, 'r', encoding='utf-8') as f:
                    prefs = json.load(f)
            except:
                pass

        prefs['last_output_dir'] = self.output_dir.get()
        prefs['last_chunks_dir'] = self.chunks_dir.get()

        try:
            with open(preferences_file, 'w', encoding='utf-8') as f:
                json.dump(prefs, f, indent=2)
        except Exception as e:
            print(f"Errore salvataggio cartelle: {str(e)}")

    def load_last_folders(self):
        """Carica le ultime cartelle usate dalle preferenze"""
        import json
        preferences_file = Path(".user_preferences.json")

        if not preferences_file.exists():
            return

        try:
            with open(preferences_file, 'r', encoding='utf-8') as f:
                prefs = json.load(f)

            # Carica output_dir se esiste
            if 'last_output_dir' in prefs and prefs['last_output_dir']:
                last_output = prefs['last_output_dir']
                if os.path.exists(last_output):
                    self.output_dir.set(last_output)

            # Carica chunks_dir se esiste
            if 'last_chunks_dir' in prefs and prefs['last_chunks_dir']:
                last_chunks = prefs['last_chunks_dir']
                if os.path.exists(last_chunks):
                    self.chunks_dir.set(last_chunks)

        except Exception as e:
            print(f"Errore caricamento cartelle: {str(e)}")

    def open_api_settings(self):
        """Apre il dialog per le impostazioni API avanzate"""
        # Carica impostazioni correnti
        current_settings = self.load_api_settings()

        # Crea dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("⚙️ Impostazioni API Avanzate")
        dialog.geometry("700x1180")  # Aumentato a 1180 per mostrare completamente i pulsanti
        self.center_window(dialog, 700, 1180)
        dialog.resizable(False, False)
        dialog.grab_set()

        # Frame principale
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Titolo
        title_label = ttk.Label(main_frame,
                               text="⚙️ IMPOSTAZIONI API AVANZATE",
                               font=('Arial', 12, 'bold'))
        title_label.pack(pady=(0, 10))

        subtitle_label = ttk.Label(main_frame,
                                   text="Configura i limiti per adattare il programma al tuo account API",
                                   font=('Arial', 9),
                                   foreground='gray')
        subtitle_label.pack(pady=(0, 20))

        # ===== SEZIONE 0: SELEZIONE PROVIDER =====
        provider_frame = ttk.LabelFrame(main_frame, text="🌐 Provider API", padding="15")
        provider_frame.pack(fill=tk.X, pady=(0, 15))

        ttk.Label(provider_frame,
                 text="Seleziona il provider che stai utilizzando:",
                 font=('Arial', 9)).pack(anchor=tk.W, pady=(0, 10))

        provider_var = tk.StringVar(value=current_settings.get('provider', 'openai'))

        providers = [
            ("🤖 OpenAI (GPT-4o, GPT-3.5-turbo)", "openai"),
            ("🧠 Anthropic (Claude 3.5 Sonnet, Claude 3 Opus)", "anthropic"),
            ("💻 Modello Locale (Ollama) - Rate limiting disabilitato", "local")
        ]

        for label, value in providers:
            ttk.Radiobutton(provider_frame, text=label, variable=provider_var, value=value).pack(anchor=tk.W, pady=2)

        # Info box provider
        info_provider = tk.Text(provider_frame, height=2, wrap=tk.WORD, bg='#E3F2FD',
                               relief=tk.FLAT, font=('Arial', 8))
        info_provider.insert('1.0',
            "ℹ️  Il rate limiting si applica solo ai modelli cloud (OpenAI/Anthropic).\n"
            "   I modelli locali non hanno limiti API.")
        info_provider.config(state='disabled')
        info_provider.pack(fill=tk.X, pady=(10, 0))

        # ===== SEZIONE 1: LIMITE TPM =====
        tpm_frame = ttk.LabelFrame(main_frame, text="🔢 Limite Token Per Minuto (TPM)", padding="15")
        tpm_frame.pack(fill=tk.X, pady=(0, 15))

        ttk.Label(tpm_frame,
                 text="Imposta il limite massimo di token al minuto del tuo account:",
                 font=('Arial', 9)).pack(anchor=tk.W, pady=(0, 10))

        # Radio buttons per preset (variano in base al provider)
        tpm_var = tk.IntVar(value=current_settings['max_tpm_limit'])

        # Container per i preset (verrà aggiornato dinamicamente)
        presets_container = ttk.Frame(tpm_frame)
        presets_container.pack(fill=tk.X)

        def update_tpm_presets():
            """Aggiorna i preset TPM in base al provider selezionato"""
            # Rimuovi widget esistenti
            for widget in presets_container.winfo_children():
                widget.destroy()

            selected_provider = provider_var.get()

            if selected_provider == 'openai':
                presets = [
                    ("Free Trial / Tier 1 (30,000 TPM)", 30000, "#FFC107"),
                    ("Tier 1 High (90,000 TPM)", 90000, "#FF9800"),
                    ("Tier 2 (450,000 TPM)", 450000, "#4CAF50"),
                    ("Tier 3+ (10,000,000 TPM)", 10000000, "#2196F3"),
                    ("Personalizzato", -1, "#9E9E9E")
                ]
            elif selected_provider == 'anthropic':
                presets = [
                    ("Tier 1 (40,000 TPM input)", 40000, "#FFC107"),
                    ("Tier 2 (80,000 TPM input)", 80000, "#FF9800"),
                    ("Tier 3 (160,000 TPM input)", 160000, "#4CAF50"),
                    ("Tier 4 (400,000 TPM input)", 400000, "#2196F3"),
                    ("Personalizzato", -1, "#9E9E9E")
                ]
            else:  # local
                presets = [
                    ("Nessun limite (modello locale)", 999999, "#4CAF50")
                ]
                tpm_var.set(999999)

            for label, value, color in presets:
                frame = ttk.Frame(presets_container)
                frame.pack(fill=tk.X, pady=2)

                radio = ttk.Radiobutton(frame, text=label, variable=tpm_var, value=value)
                radio.pack(side=tk.LEFT)

                if value != -1:
                    badge = tk.Label(frame, text=f"{value:,}", bg=color, fg="white",
                                   font=('Arial', 8, 'bold'), padx=8, pady=2)
                    badge.pack(side=tk.LEFT, padx=10)

        # NON chiamare update_summary() qui perché non è ancora definita

        # Campo personalizzato
        custom_frame = ttk.Frame(tpm_frame)
        custom_frame.pack(fill=tk.X, pady=(10, 5))

        ttk.Label(custom_frame, text="Valore personalizzato:").pack(side=tk.LEFT, padx=(20, 5))
        custom_tpm_entry = ttk.Entry(custom_frame, width=15)
        custom_tpm_entry.pack(side=tk.LEFT)
        ttk.Label(custom_frame, text="TPM", font=('Arial', 9), foreground='gray').pack(side=tk.LEFT, padx=5)

        # Auto-select "Personalizzato" quando si scrive nel campo
        def on_custom_entry_change(event):
            if custom_tpm_entry.get().strip():
                tpm_var.set(-1)  # Seleziona radio "Personalizzato"

        custom_tpm_entry.bind('<KeyRelease>', on_custom_entry_change)

        # Pre-compila campo se valore corrente non è un preset
        if current_settings['max_tpm_limit'] not in [30000, 90000, 450000, 10000000]:
            tpm_var.set(-1)
            custom_tpm_entry.insert(0, str(current_settings['max_tpm_limit']))

        # Info box
        info_tpm = tk.Text(tpm_frame, height=3, wrap=tk.WORD, bg='#E3F2FD',
                          relief=tk.FLAT, font=('Arial', 8))
        info_tpm.insert('1.0',
            "ℹ️  TPM = Tokens Per Minute. Controlla il tuo tier su:\n"
            "   https://platform.openai.com/settings/organization/limits\n"
            "   Se non sei sicuro, lascia il valore di default (30,000).")
        info_tpm.config(state='disabled')
        info_tpm.pack(fill=tk.X, pady=(10, 0))

        # ===== SEZIONE 2: SOGLIA GERARCHICA =====
        threshold_frame = ttk.LabelFrame(main_frame, text="🔀 Soglia Riassunto Gerarchico", padding="15")
        threshold_frame.pack(fill=tk.X, pady=(0, 15))

        ttk.Label(threshold_frame,
                 text="Numero di chunk oltre il quale attivare l'approccio gerarchico:",
                 font=('Arial', 9)).pack(anchor=tk.W, pady=(0, 10))

        slider_frame = ttk.Frame(threshold_frame)
        slider_frame.pack(fill=tk.X, pady=(0, 5))

        threshold_var = tk.IntVar(value=current_settings['hierarchical_threshold'])
        threshold_label = ttk.Label(slider_frame, text=f"{threshold_var.get()} chunk",
                                    font=('Arial', 10, 'bold'))
        threshold_label.pack(side=tk.RIGHT, padx=10)

        def update_threshold_label(val):
            threshold_label.config(text=f"{int(float(val))} chunk")

        threshold_slider = tk.Scale(slider_frame, from_=10, to=100, orient=tk.HORIZONTAL,
                                   variable=threshold_var, command=update_threshold_label,
                                   showvalue=False, length=400)
        threshold_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Markers
        markers_frame = ttk.Frame(threshold_frame)
        markers_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(markers_frame, text="Conservativo (10)", font=('Arial', 7),
                 foreground='gray').pack(side=tk.LEFT)
        ttk.Label(markers_frame, text="Bilanciato (30)", font=('Arial', 7),
                 foreground='gray').pack(side=tk.LEFT, expand=True)
        ttk.Label(markers_frame, text="Aggressivo (100)", font=('Arial', 7),
                 foreground='gray').pack(side=tk.RIGHT)

        # Info box
        info_threshold = tk.Text(threshold_frame, height=4, wrap=tk.WORD, bg='#FFF3E0',
                                relief=tk.FLAT, font=('Arial', 8))
        info_threshold.insert('1.0',
            "ℹ️  Approccio gerarchico: divide i chunk in gruppi, li riassume\n"
            "   separatamente e poi combina i riassunti. Più efficiente per\n"
            "   documenti grandi e account con limiti TPM bassi.\n"
            "   • Valori bassi (10-20): Più sicuro, evita errori 429\n"
            "   • Valori alti (50-100): Più veloce, richiede Tier alto")
        info_threshold.config(state='disabled')
        info_threshold.pack(fill=tk.X, pady=(10, 0))

        # ===== SEZIONE 3: ADATTAMENTO AUTOMATICO =====
        auto_frame = ttk.LabelFrame(main_frame, text="🤖 Adattamento Automatico", padding="15")
        auto_frame.pack(fill=tk.X, pady=(0, 15))

        auto_adapt_var = tk.BooleanVar(value=current_settings['enable_auto_adapt'])

        checkbox = ttk.Checkbutton(auto_frame,
                                  text="Abilita adattamento automatico in caso di errore 429",
                                  variable=auto_adapt_var)
        checkbox.pack(anchor=tk.W, pady=(0, 5))

        info_auto = tk.Text(auto_frame, height=3, wrap=tk.WORD, bg='#E8F5E9',
                           relief=tk.FLAT, font=('Arial', 8))
        info_auto.insert('1.0',
            "ℹ️  Se abilitato, in caso di errore 429 il programma ridurrà\n"
            "   automaticamente la soglia gerarchica e riproverà.\n"
            "   Consigliato per la maggior parte degli utenti.")
        info_auto.config(state='disabled')
        info_auto.pack(fill=tk.X, pady=(5, 0))

        # ===== RIEPILOGO =====
        summary_frame = ttk.LabelFrame(main_frame, text="📊 Riepilogo Configurazione", padding="15")
        summary_frame.pack(fill=tk.X, pady=(0, 15))

        summary_text = tk.Text(summary_frame, height=4, wrap=tk.WORD, bg='#F5F5F5',
                              relief=tk.FLAT, font=('Arial', 9, 'bold'))
        summary_text.pack(fill=tk.X)

        def update_summary():
            selected_tpm = tpm_var.get()
            if selected_tpm == -1:
                try:
                    selected_tpm = int(custom_tpm_entry.get())
                except:
                    selected_tpm = 30000

            # Calcola delay tra chunk (stessa formula di ai_analyzer.py)
            estimated_tokens_per_chunk = 1500
            max_chunks_per_minute = selected_tpm / estimated_tokens_per_chunk
            delay_seconds = (60.0 / max_chunks_per_minute) * 1.2  # +20% margine

            summary_text.config(state='normal')
            summary_text.delete('1.0', tk.END)
            summary_text.insert('1.0',
                f"• Limite TPM: {selected_tpm:,} token/min\n"
                f"• Delay tra chunk: ~{delay_seconds:.1f} secondi (rate limiting automatico)\n"
                f"• Max chunk/minuto: ~{max_chunks_per_minute:.0f} chunk\n"
                f"• Soglia gerarchica: {threshold_var.get()} chunk\n"
                f"• Adattamento automatico: {'✓ Abilitato' if auto_adapt_var.get() else '✗ Disabilitato'}"
            )
            summary_text.config(state='disabled')

        # Aggiorna summary quando cambia qualcosa
        tpm_var.trace_add('write', lambda *args: update_summary())
        threshold_var.trace_add('write', lambda *args: update_summary())
        auto_adapt_var.trace_add('write', lambda *args: update_summary())
        custom_tpm_entry.bind('<KeyRelease>', lambda e: update_summary())

        # Collegamento per aggiornare preset quando cambia provider
        provider_var.trace_add('write', lambda *args: [update_tpm_presets(), update_summary()])

        # Inizializza i preset e il summary
        update_tpm_presets()
        update_summary()  # Iniziale

        # ===== PULSANTI =====
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=(20, 5), fill=tk.X)

        def save_and_close():
            selected_tpm = tpm_var.get()
            if selected_tpm == -1:
                try:
                    selected_tpm = int(custom_tpm_entry.get())
                except:
                    messagebox.showerror("Errore", "Inserisci un valore TPM personalizzato valido")
                    return

            if selected_tpm < 1000 or selected_tpm > 100000000:
                messagebox.showerror("Errore", "Il valore TPM deve essere tra 1,000 e 100,000,000")
                return

            selected_provider = provider_var.get()
            success = self.save_api_settings(selected_provider, selected_tpm, threshold_var.get(), auto_adapt_var.get())

            if success:
                provider_names = {'openai': 'OpenAI', 'anthropic': 'Anthropic', 'local': 'Locale'}
                self.log(f"✓ Impostazioni API salvate: Provider={provider_names.get(selected_provider)}, TPM={selected_tpm:,}, Soglia={threshold_var.get()}")
                messagebox.showinfo("Successo",
                    f"Impostazioni salvate correttamente!\n\n"
                    f"• Provider: {provider_names.get(selected_provider, selected_provider)}\n"
                    f"• Limite TPM: {selected_tpm:,}\n"
                    f"• Soglia gerarchica: {threshold_var.get()} chunk\n\n"
                    f"Le nuove impostazioni saranno attive dalla prossima analisi.")
                dialog.destroy()
            else:
                messagebox.showerror("Errore", "Impossibile salvare le impostazioni")

        # Pulsante SALVA grande e visibile con sfondo verde
        save_btn = tk.Button(button_frame,
                            text="💾  SALVA IMPOSTAZIONI  ",
                            command=save_and_close,
                            bg='#4CAF50',
                            fg='white',
                            font=('Arial', 11, 'bold'),
                            relief=tk.RAISED,
                            borderwidth=2,
                            padx=20,
                            pady=10,
                            cursor='hand2')
        save_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 10))

        # Effetto hover
        def on_enter(e):
            save_btn.config(bg='#45a049')
        def on_leave(e):
            save_btn.config(bg='#4CAF50')
        save_btn.bind('<Enter>', on_enter)
        save_btn.bind('<Leave>', on_leave)

        # Pulsante Annulla
        cancel_btn = tk.Button(button_frame,
                              text="❌ Annulla",
                              command=dialog.destroy,
                              bg='#f44336',
                              fg='white',
                              font=('Arial', 10),
                              relief=tk.RAISED,
                              borderwidth=2,
                              padx=15,
                              pady=10,
                              cursor='hand2')
        cancel_btn.pack(side=tk.LEFT, padx=(0, 0))

        def on_enter_cancel(e):
            cancel_btn.config(bg='#da190b')
        def on_leave_cancel(e):
            cancel_btn.config(bg='#f44336')
        cancel_btn.bind('<Enter>', on_enter_cancel)
        cancel_btn.bind('<Leave>', on_leave_cancel)

        # Centra finestra
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")

    def _check_license(self):
        """Verifica licenza all'avvio (chiamato DOPO setup_ui)"""
        # Verifica se esiste una licenza salvata
        if self.license_manager.has_saved_license():
            # Licenza presente, carica e valida
            license_data = self.license_manager.load_license()

            if license_data:
                license_key = license_data.get('license_key')

                # Valida online (timeout 5 secondi)
                validation_result = self.license_manager.validate_license_online(license_key, timeout=5)

                if not validation_result.get('valid'):
                    # Licenza non più valida (revocata o scaduta)
                    messagebox.showerror(
                        "Licenza Non Valida",
                        f"La tua licenza non è più valida.\n\n"
                        f"Motivo: {validation_result.get('message', 'Sconosciuto')}\n\n"
                        f"L'applicazione verrà chiusa.",
                        parent=self.root
                    )
                    self.root.destroy()
                    return

                # Licenza valida, invia telemetria
                self.license_manager.send_telemetry(license_key, app_version="3.2.2")
            else:
                # Errore caricamento licenza, richiedi nuovamente
                self._show_license_dialog()
        else:
            # Nessuna licenza salvata, mostra dialog
            self._show_license_dialog()

    def _show_license_dialog(self):
        """Mostra il dialog per l'inserimento della licenza"""
        license_dialog = LicenseDialog(self.root, self.license_manager)
        self.root.wait_window(license_dialog.dialog)

        # Se l'utente ha chiuso senza validare, esce dall'applicazione
        if not license_dialog.is_valid():
            messagebox.showinfo(
                "Applicazione Chiusa",
                "L'applicazione verrà chiusa perché non è stata fornita una licenza valida.",
                parent=self.root
            )
            self.root.destroy()

def main():
    root = tk.Tk()
    app = WhatsAppAnalyzerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
