#!/usr/bin/env python3
"""
WhatsApp Forensic Analyzer - Dialog Report per Chat
Genera riassunti dedicati per ogni conversazione (1v1 o gruppo) rilevata nel PDF

© 2025 Luca Mercatanti - https://mercatanti.com
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import os
import re
import threading
from pathlib import Path
from datetime import datetime
from ai_analyzer import AIAnalyzer


class ChatReportDialog:
    def __init__(self, parent, main_app):
        """
        Dialog per generazione Report per Chat

        Args:
            parent: Finestra parent (Tk root)
            main_app: Istanza WhatsAppAnalyzerGUI
        """
        self.parent = parent
        self.main_app = main_app

        # Variabili stato
        self.detected_chats = []
        self.selected_chats = []
        self.is_running = False

        # Crea dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("💬 Report per Chat - Post-Elaborazione")
        self.dialog.geometry("900x800")
        self.dialog.resizable(True, True)

        self.setup_ui()

        # Carica info iniziali
        self.update_info_display()

    def setup_ui(self):
        """Configura l'interfaccia grafica del dialog"""

        # Frame principale con padding
        main_frame = ttk.Frame(self.dialog, padding="15")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.dialog.columnconfigure(0, weight=1)
        self.dialog.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)

        row = 0

        # ===== HEADER =====
        header_frame = ttk.Frame(main_frame)
        header_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 15))

        ttk.Label(header_frame, text="💬 Report per Chat",
                 font=('Arial', 14, 'bold')).pack(anchor=tk.W)
        ttk.Label(header_frame,
                 text="Genera riassunti dedicati per ogni conversazione (1v1 o gruppo) rilevata nel PDF",
                 font=('Arial', 9), foreground='gray').pack(anchor=tk.W, pady=(3, 0))
        row += 1

        # ===== INFO ANALISI DISPONIBILI =====
        info_frame = ttk.LabelFrame(main_frame, text="📊 Analisi Disponibili", padding="10")
        info_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        info_frame.columnconfigure(1, weight=1)

        self.chunks_info_label = ttk.Label(info_frame, text="Chunk: -")
        self.chunks_info_label.grid(row=0, column=0, sticky=tk.W, padx=5)

        self.analyses_info_label = ttk.Label(info_frame, text="Analisi: -")
        self.analyses_info_label.grid(row=0, column=1, sticky=tk.W, padx=5)
        row += 1

        # ===== PULSANTE RILEVA CHAT =====
        detect_frame = ttk.Frame(main_frame)
        detect_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        ttk.Label(detect_frame,
                 text="Clicca per scansionare i chunk e rilevare le conversazioni:",
                 font=('Arial', 9)).pack(side=tk.LEFT, padx=(0, 10))

        self.detect_button = ttk.Button(detect_frame, text="🔍 Rileva Chat",
                                       command=self.detect_chats_action,
                                       style='Accent.TButton')
        self.detect_button.pack(side=tk.LEFT)
        row += 1

        # ===== OPZIONI RILEVAMENTO =====
        options_frame = ttk.LabelFrame(main_frame, text="⚙️ Opzioni Rilevamento", padding="10")
        options_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        # Checkbox AI detection
        self.use_ai_detection = tk.BooleanVar(value=False)
        ai_checkbox = ttk.Checkbutton(
            options_frame,
            text="Usa AI per rilevamento avanzato (consigliato per PDF anomali)",
            variable=self.use_ai_detection,
            command=self.on_ai_detection_toggle
        )
        ai_checkbox.pack(anchor=tk.W, pady=(0, 5))

        # Info box costi AI detection
        self.ai_info_frame = ttk.Frame(options_frame)
        self.ai_info_frame.pack(anchor=tk.W, fill=tk.X, pady=(5, 0))

        info_text = tk.Text(
            self.ai_info_frame,
            height=3,
            width=80,
            wrap=tk.WORD,
            state='normal',
            bg='#FFF8DC',
            relief=tk.FLAT,
            font=('Arial', 8)
        )
        info_text.insert('1.0',
            "ℹ️  AI Detection: analizza i primi 800 caratteri di ogni chunk per identificare chat.\n"
            "   • Costo extra: ~$0.01 per chunk (~$0.50 per 50 chunk)\n"
            "   • Tempo extra: ~2-5 minuti\n"
            "   • Fallback automatico: l'AI viene suggerita se pattern matching trova <2 chat in >10 chunk"
        )
        info_text.config(state='disabled')
        info_text.pack(fill=tk.X)

        # Nascondi info box di default
        self.ai_info_frame.pack_forget()
        row += 1

        # ===== LISTA CHAT RILEVATE =====
        chats_frame = ttk.LabelFrame(main_frame, text="📱 Chat Rilevate", padding="10")
        chats_frame.grid(row=row, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        chats_frame.columnconfigure(0, weight=1)
        chats_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(row, weight=1)

        # Scrollable frame per lista chat
        canvas = tk.Canvas(chats_frame, height=200)
        scrollbar = ttk.Scrollbar(chats_frame, orient="vertical", command=canvas.yview)
        self.chats_list_frame = ttk.Frame(canvas)

        self.chats_list_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.chats_list_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        # Placeholder iniziale
        self.chats_placeholder = ttk.Label(self.chats_list_frame,
                                          text="Nessuna chat rilevata.\nClicca 'Rileva Chat' per iniziare.",
                                          font=('Arial', 10), foreground='gray')
        self.chats_placeholder.pack(pady=30)
        row += 1

        # ===== STIME =====
        estimates_frame = ttk.LabelFrame(main_frame, text="💰 Stime", padding="10")
        estimates_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        estimates_frame.columnconfigure(1, weight=1)

        ttk.Label(estimates_frame, text="Chat selezionate:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.selected_count_label = ttk.Label(estimates_frame, text="0")
        self.selected_count_label.grid(row=0, column=1, sticky=tk.W, padx=5)

        ttk.Label(estimates_frame, text="Costo stimato:").grid(row=1, column=0, sticky=tk.W, padx=5)
        self.cost_estimate_label = ttk.Label(estimates_frame, text="-")
        self.cost_estimate_label.grid(row=1, column=1, sticky=tk.W, padx=5)

        ttk.Label(estimates_frame, text="Tempo stimato:").grid(row=2, column=0, sticky=tk.W, padx=5)
        self.time_estimate_label = ttk.Label(estimates_frame, text="-")
        self.time_estimate_label.grid(row=2, column=1, sticky=tk.W, padx=5)
        row += 1

        # ===== LOG =====
        ttk.Label(main_frame, text="📝 Log Operazioni:",
                 font=('Arial', 10, 'bold')).grid(row=row, column=0, sticky=tk.W, pady=(10, 5))
        row += 1

        self.log_text = scrolledtext.ScrolledText(main_frame, height=8, width=80,
                                                  state='disabled', wrap=tk.WORD)
        self.log_text.grid(row=row, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        main_frame.rowconfigure(row, weight=0)
        row += 1

        # ===== PROGRESS BAR =====
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var,
                                           maximum=100, length=400)
        self.progress_bar.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        row += 1

        self.status_label = ttk.Label(main_frame, text="Pronto", foreground="green")
        self.status_label.grid(row=row, column=0, sticky=tk.W, pady=(0, 10))
        row += 1

        # ===== PULSANTI AZIONE =====
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=row, column=0, pady=10)

        self.generate_button = ttk.Button(button_frame, text="🔄 Genera Report",
                                         command=self.start_generation,
                                         state='disabled', style='Accent.TButton')
        self.generate_button.grid(row=0, column=0, padx=5)

        ttk.Button(button_frame, text="❌ Chiudi",
                  command=self.dialog.destroy).grid(row=0, column=1, padx=5)

    def update_info_display(self):
        """Aggiorna le informazioni su chunk e analisi disponibili"""
        chunks_dir = self.main_app.chunks_dir.get()
        output_dir = self.main_app.output_dir.get()

        num_chunks = 0
        num_analyses = 0

        if os.path.exists(chunks_dir):
            chunks = [f for f in os.listdir(chunks_dir)
                     if f.startswith("chunk_") and (f.endswith(".txt") or f.endswith(".json"))]
            num_chunks = len(chunks)

        if os.path.exists(output_dir):
            analyses = [f for f in os.listdir(output_dir)
                       if f.startswith("analisi_chunk_") and f.endswith(".txt")]
            num_analyses = len(analyses)

        self.chunks_info_label.config(text=f"Chunk: {num_chunks}")
        self.analyses_info_label.config(text=f"Analisi: {num_analyses}")

        if num_chunks == 0:
            self.log("⚠️ ATTENZIONE: Nessun chunk trovato. Esegui prima un'analisi completa.")
            self.detect_button.config(state='disabled')

    def on_ai_detection_toggle(self):
        """Mostra/nasconde info box AI detection quando checkbox viene cliccata"""
        if self.use_ai_detection.get():
            self.ai_info_frame.pack(anchor=tk.W, fill=tk.X, pady=(5, 0))
        else:
            self.ai_info_frame.pack_forget()

    def suggest_ai_fallback(self, num_chats_found, num_chunks):
        """
        Mostra dialog suggerimento per usare AI Detection

        Args:
            num_chats_found: Numero chat trovate con pattern matching
            num_chunks: Numero totale di chunk analizzati
        """
        # Calcola costo stimato AI detection
        estimated_cost = num_chunks * 0.01

        message = f"""⚠️ SUGGERIMENTO AI DETECTION

Pattern Matching ha rilevato solo {num_chats_found} chat in {num_chunks} chunk.

Questo potrebbe indicare un formato PDF anomalo o non standard.

💡 SOLUZIONE: Riprova con AI Detection
   • L'AI può rilevare header non standard
   • Costo extra stimato: ~${estimated_cost:.2f}
   • Tempo extra: ~2-5 minuti

Vuoi attivare AI Detection e riprovare?"""

        response = messagebox.askyesno(
            "💡 Suggerimento AI Detection",
            message,
            icon='question'
        )

        if response:
            # Attiva checkbox e rilancia rilevamento
            self.use_ai_detection.set(True)
            self.on_ai_detection_toggle()  # Mostra info box
            self.log("✓ AI Detection attivata. Riavvio rilevamento...")

            # Riavvia rilevamento in thread
            self.detect_button.config(state='disabled')
            thread = threading.Thread(target=self.detect_chats, daemon=True)
            thread.start()
        else:
            self.log("ℹ️ AI Detection non attivata. Continuando con i risultati attuali.")

    def log(self, message):
        """Aggiunge un messaggio al log"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_entry = f"[{timestamp}] {message}"

        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, f"{log_entry}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')
        self.dialog.update_idletasks()

    def detect_chats_action(self):
        """Avvia il rilevamento delle chat in un thread separato"""
        self.detect_button.config(state='disabled')
        self.log("Rilevamento chat in corso...")
        self.update_status("Scansione chunk...", "blue")

        # Avvia in thread
        thread = threading.Thread(target=self.detect_chats, daemon=True)
        thread.start()

    def detect_chats(self):
        """Rileva le chat dai chunk originali (routing tra pattern matching e AI)"""
        try:
            # ROUTING: scegli metodo in base a checkbox
            if self.use_ai_detection.get():
                self.log("🤖 Modalità: AI Detection attivata")
                self.detect_chats_with_ai()
                return

            # Altrimenti usa pattern matching (default)
            self.log("🔍 Modalità: Pattern Matching (default)")
            self._detect_chats_with_pattern()

        except Exception as e:
            self.log(f"✗ Errore durante il rilevamento: {str(e)}")
            self.update_status("Errore", "red")
        finally:
            self.detect_button.config(state='normal')

    def _detect_chats_with_pattern(self):
        """Rileva le chat usando pattern matching regex (metodo originale)"""
        try:
            chunks_dir = self.main_app.chunks_dir.get()

            if not os.path.exists(chunks_dir):
                self.log("✗ Errore: Cartella chunk non trovata")
                self.update_status("Errore", "red")
                return

            # Lista chunk
            chunk_format = self.main_app.chunk_format.get()
            extension = ".json" if chunk_format == "json" else ".txt"
            chunk_files = sorted([f for f in os.listdir(chunks_dir)
                                 if f.startswith("chunk_") and f.endswith(extension)])

            if not chunk_files:
                self.log("✗ Nessun chunk trovato")
                self.update_status("Errore", "red")
                return

            self.log(f"Scansione di {len(chunk_files)} chunk...")

            chats = []
            current_chat = None
            chat_id_counter = 1

            for idx, chunk_file in enumerate(chunk_files):
                chunk_path = os.path.join(chunks_dir, chunk_file)

                # Leggi chunk
                try:
                    if extension == ".json":
                        import json
                        with open(chunk_path, 'r', encoding='utf-8') as f:
                            chunk_data = json.load(f)
                            text = chunk_data.get('text', '')
                    else:
                        with open(chunk_path, 'r', encoding='utf-8') as f:
                            text = f.read()
                except Exception as e:
                    self.log(f"⚠️ Errore lettura {chunk_file}: {str(e)}")
                    continue

                # Cerca pattern header chat
                if self.is_chat_header(text):
                    # Salva chat precedente
                    if current_chat:
                        chats.append(current_chat)

                    # Estrai metadati nuova chat
                    metadata = self.extract_chat_metadata(text)

                    if metadata:
                        current_chat = {
                            'chat_id': f"chat_{chat_id_counter:03d}",
                            'identifier': metadata.get('identifier', ''),
                            'account': metadata.get('account', ''),
                            'participants': metadata.get('participants', []),
                            'type': 'group' if len(metadata.get('participants', [])) > 2 else '1v1',
                            'metadata': {
                                'start_time': metadata.get('start_time', ''),
                                'last_activity': metadata.get('last_activity', ''),
                                'num_attachments': metadata.get('num_attachments', 0),
                                'body_file': metadata.get('body_file', '')
                            },
                            'chunks': [idx + 1],  # Chunk number (1-based)
                            'chunk_files': [chunk_file]
                        }
                        chat_id_counter += 1
                        self.log(f"✓ Chat rilevata: {self.get_chat_display_name(current_chat)}")
                elif current_chat:
                    # Aggiungi chunk alla chat corrente
                    current_chat['chunks'].append(idx + 1)
                    current_chat['chunk_files'].append(chunk_file)

            # Aggiungi ultima chat
            if current_chat:
                chats.append(current_chat)

            self.detected_chats = chats

            if len(chats) > 0:
                self.log(f"✓ Rilevate {len(chats)} conversazioni")
                self.display_detected_chats()
                self.update_status("Chat rilevate", "green")

                # AUTO-FALLBACK: suggerisci AI se troppo poche chat in molti chunk
                if len(chats) < 2 and len(chunk_files) > 10:
                    self.log("⚠️ SUGGERIMENTO: Poche chat rilevate in molti chunk")
                    self.suggest_ai_fallback(len(chats), len(chunk_files))
            else:
                self.log("⚠️ Nessuna chat rilevata. Verifica il formato del PDF.")
                self.update_status("Nessuna chat trovata", "orange")

                # AUTO-FALLBACK: suggerisci AI se nessuna chat trovata
                if len(chunk_files) > 10:
                    self.suggest_ai_fallback(0, len(chunk_files))

        except Exception as e:
            self.log(f"✗ Errore durante il rilevamento pattern: {str(e)}")
            self.update_status("Errore", "red")

    def detect_chats_with_ai(self):
        """Rileva le chat usando AI per analizzare gli header dei chunk"""
        try:
            chunks_dir = self.main_app.chunks_dir.get()

            if not os.path.exists(chunks_dir):
                self.log("✗ Errore: Cartella chunk non trovata")
                self.update_status("Errore", "red")
                return

            # Lista chunk
            chunk_format = self.main_app.chunk_format.get()
            extension = ".json" if chunk_format == "json" else ".txt"
            chunk_files = sorted([f for f in os.listdir(chunks_dir)
                                 if f.startswith("chunk_") and f.endswith(extension)])

            if not chunk_files:
                self.log("✗ Nessun chunk trovato")
                self.update_status("Errore", "red")
                return

            self.log(f"🤖 AI Detection: analisi di {len(chunk_files)} chunk...")
            self.log(f"   Costo stimato: ~${len(chunk_files) * 0.01:.2f}")

            # Inizializza AI Analyzer
            if self.main_app.use_local_model.get():
                analyzer = AIAnalyzer(
                    api_key="",
                    model=self.main_app.local_model_name.get(),
                    use_local=True,
                    local_url=self.main_app.local_url.get()
                )
                self.log(f"✓ Modello locale: {self.main_app.local_model_name.get()}")
            else:
                analyzer = AIAnalyzer(
                    api_key=self.main_app.api_key.get(),
                    model=self.main_app.model_var.get()
                )
                self.log(f"✓ Modello AI: {self.main_app.model_var.get()}")

            chats = []
            current_chat = None
            chat_id_counter = 1

            for idx, chunk_file in enumerate(chunk_files):
                chunk_path = os.path.join(chunks_dir, chunk_file)

                # Aggiorna progress
                progress = (idx / len(chunk_files)) * 100
                self.update_progress(progress)
                self.update_status(f"AI Detection: chunk {idx+1}/{len(chunk_files)}", "blue")

                # Leggi chunk
                try:
                    if extension == ".json":
                        import json
                        with open(chunk_path, 'r', encoding='utf-8') as f:
                            chunk_data = json.load(f)
                            text = chunk_data.get('text', '')
                    else:
                        with open(chunk_path, 'r', encoding='utf-8') as f:
                            text = f.read()
                except Exception as e:
                    self.log(f"⚠️ Errore lettura {chunk_file}: {str(e)}")
                    continue

                # Usa AI per determinare se è un header
                ai_result = analyzer.analyze_chunk_header(text[:800])  # primi 800 caratteri

                if ai_result and ai_result.get('is_chat_header'):
                    # Salva chat precedente
                    if current_chat:
                        chats.append(current_chat)

                    # Crea nuova chat dai dati AI
                    metadata = ai_result.get('metadata', {})

                    current_chat = {
                        'chat_id': f"chat_{chat_id_counter:03d}",
                        'identifier': metadata.get('identifier', ''),
                        'account': metadata.get('account', ''),
                        'participants': metadata.get('participants', []),
                        'type': 'group' if len(metadata.get('participants', [])) > 2 else '1v1',
                        'metadata': {
                            'start_time': metadata.get('start_time', ''),
                            'last_activity': metadata.get('last_activity', ''),
                            'num_attachments': metadata.get('num_attachments', 0),
                            'body_file': metadata.get('body_file', '')
                        },
                        'chunks': [idx + 1],
                        'chunk_files': [chunk_file]
                    }
                    chat_id_counter += 1

                    display_name = self.get_chat_display_name(current_chat)
                    self.log(f"✓ Chat rilevata (AI): {display_name}")

                elif current_chat:
                    # Aggiungi chunk alla chat corrente
                    current_chat['chunks'].append(idx + 1)
                    current_chat['chunk_files'].append(chunk_file)

            # Aggiungi ultima chat
            if current_chat:
                chats.append(current_chat)

            self.detected_chats = chats
            self.update_progress(100)

            if len(chats) > 0:
                self.log(f"✓ AI Detection completato: {len(chats)} conversazioni rilevate")
                self.display_detected_chats()
                self.update_status("Chat rilevate (AI)", "green")
            else:
                self.log("⚠️ Nessuna chat rilevata con AI. Verifica il formato del PDF.")
                self.update_status("Nessuna chat trovata", "orange")

        except Exception as e:
            self.log(f"✗ Errore durante AI detection: {str(e)}")
            self.update_status("Errore", "red")
        finally:
            self.detect_button.config(state='normal')
            self.update_progress(0)

    def is_chat_header(self, text):
        """Verifica se il testo contiene un header di inizio chat"""
        # Pattern per identificare header chat Cellebrite/UFED/Oxygen
        patterns = [
            r'Start Time:\s*\d',
            r'Participants:\s*\n',
            r'Identifier:\s*[a-f0-9]{10,}',
        ]

        # Deve contenere almeno 2 dei 3 pattern
        matches = sum(1 for pattern in patterns if re.search(pattern, text, re.IGNORECASE))
        return matches >= 2

    def extract_chat_metadata(self, text):
        """Estrae metadati dall'header della chat"""
        metadata = {}

        try:
            # Start Time
            match = re.search(r'Start Time:\s*(.+)', text)
            if match:
                metadata['start_time'] = match.group(1).strip()

            # Last Activity
            match = re.search(r'Last Activity:\s*(.+)', text)
            if match:
                metadata['last_activity'] = match.group(1).strip()

            # Account
            match = re.search(r'Account:\s*(.+)', text)
            if match:
                metadata['account'] = match.group(1).strip()

            # Identifier
            match = re.search(r'Identifier:\s*([a-f0-9]+)', text, re.IGNORECASE)
            if match:
                metadata['identifier'] = match.group(1).strip()

            # Number of attachments
            match = re.search(r'Number of attachments:\s*(\d+)', text, re.IGNORECASE)
            if match:
                metadata['num_attachments'] = int(match.group(1))

            # Body file
            match = re.search(r'Body file:\s*(chat-\d+\.txt)', text, re.IGNORECASE)
            if match:
                metadata['body_file'] = match.group(1).strip()

            # Participants - cerca sezione partecipanti
            participants = []
            in_participants_section = False
            lines = text.split('\n')

            for line in lines:
                if 'Participants:' in line:
                    in_participants_section = True
                    continue

                if in_participants_section:
                    # Fine sezione partecipanti
                    if line.strip() and not line.startswith(' ') and 'Identifier:' in line:
                        break

                    # Estrai nome partecipante (cerca pattern wxid, numeri telefono, nomi)
                    # Pattern: nome utente o ID
                    participant_match = re.search(r'(wxid_[a-zA-Z0-9]+|[\+\d]{10,}|\w+)', line)
                    if participant_match:
                        participant_id = participant_match.group(1).strip()

                        # Cerca nome associato (di solito dopo l'ID o su stessa riga)
                        name_match = re.search(r'([A-Za-z\u4e00-\u9fff\s]+)', line)
                        name = name_match.group(1).strip() if name_match else participant_id

                        # Verifica se è owner
                        is_owner = 'owner' in line.lower()

                        if participant_id and participant_id not in [p['id'] for p in participants]:
                            participants.append({
                                'id': participant_id,
                                'name': name,
                                'owner': is_owner
                            })

            metadata['participants'] = participants

        except Exception as e:
            self.log(f"⚠️ Errore estrazione metadati: {str(e)}")

        return metadata if metadata else None

    def get_chat_display_name(self, chat):
        """Determina il nome visualizzato per la chat"""
        if chat['type'] == '1v1':
            # Chat 1v1: usa nome altro partecipante (non owner)
            participants = chat.get('participants', [])
            other_participants = [p for p in participants if not p.get('owner', False)]

            if other_participants:
                return other_participants[0].get('name', other_participants[0].get('id', 'Sconosciuto'))
            elif participants:
                return participants[0].get('name', participants[0].get('id', 'Sconosciuto'))
            else:
                return chat.get('account', 'Chat 1v1')
        else:
            # Gruppo: "Gruppo con X, Y, Z"
            participants = chat.get('participants', [])
            if len(participants) > 0:
                first_three = participants[:3]
                names = [p.get('name', p.get('id', '')) for p in first_three]

                if len(participants) > 3:
                    return f"Gruppo con {', '.join(names)}, +{len(participants)-3} altri"
                else:
                    return f"Gruppo con {', '.join(names)}"
            else:
                return f"Gruppo {chat.get('account', 'Sconosciuto')}"

    def display_detected_chats(self):
        """Mostra le chat rilevate nella lista"""
        # Rimuovi placeholder
        if hasattr(self, 'chats_placeholder'):
            self.chats_placeholder.destroy()

        # Pulisci lista
        for widget in self.chats_list_frame.winfo_children():
            widget.destroy()

        # Variabili per checkbox
        self.chat_vars = []

        # Separa 1v1 da gruppi
        chats_1v1 = [c for c in self.detected_chats if c['type'] == '1v1']
        chats_group = [c for c in self.detected_chats if c['type'] == 'group']

        row = 0

        # Pulsanti seleziona tutto/nessuno
        select_frame = ttk.Frame(self.chats_list_frame)
        select_frame.grid(row=row, column=0, sticky=tk.W, pady=(0, 10))
        ttk.Button(select_frame, text="Seleziona tutte",
                  command=self.select_all_chats).pack(side=tk.LEFT, padx=5)
        ttk.Button(select_frame, text="Deseleziona tutte",
                  command=self.deselect_all_chats).pack(side=tk.LEFT)
        row += 1

        # Chat 1v1
        if chats_1v1:
            ttk.Label(self.chats_list_frame, text="💬 Chat 1v1",
                     font=('Arial', 10, 'bold')).grid(row=row, column=0, sticky=tk.W, pady=(5, 5))
            row += 1

            for chat in chats_1v1:
                self.create_chat_item(chat, row)
                row += 1

        # Gruppi
        if chats_group:
            ttk.Label(self.chats_list_frame, text="👥 Gruppi",
                     font=('Arial', 10, 'bold')).grid(row=row, column=0, sticky=tk.W, pady=(15, 5))
            row += 1

            for chat in chats_group:
                self.create_chat_item(chat, row)
                row += 1

        # Abilita pulsante genera
        self.generate_button.config(state='normal')

        # Seleziona tutte di default
        self.select_all_chats()

    def create_chat_item(self, chat, row):
        """Crea un elemento nella lista chat"""
        frame = ttk.Frame(self.chats_list_frame, relief=tk.GROOVE, borderwidth=1, padding=5)
        frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=2)

        # Checkbox
        var = tk.BooleanVar(value=False)
        self.chat_vars.append((chat, var))

        checkbox = ttk.Checkbutton(frame, variable=var, command=self.update_estimates)
        checkbox.grid(row=0, column=0, rowspan=2, padx=5)

        # Nome chat
        display_name = self.get_chat_display_name(chat)
        name_label = ttk.Label(frame, text=display_name, font=('Arial', 10, 'bold'))
        name_label.grid(row=0, column=1, sticky=tk.W, padx=5)

        # Badge tipo
        badge_text = "1v1" if chat['type'] == '1v1' else "Gruppo"
        badge_color = "#34B7F1" if chat['type'] == '1v1' else "#25D366"
        badge = tk.Label(frame, text=badge_text, bg=badge_color, fg="white",
                        font=('Arial', 8, 'bold'), padx=5, pady=2)
        badge.grid(row=0, column=2, padx=5)

        # Info
        num_participants = len(chat.get('participants', []))
        num_chunks = len(chat.get('chunks', []))
        num_attachments = chat['metadata'].get('num_attachments', 0)

        info_text = f"👤 {num_participants} partecipanti  |  🧩 {num_chunks} chunk"
        if num_attachments > 0:
            info_text += f"  |  📎 {num_attachments} allegati"

        info_label = ttk.Label(frame, text=info_text, font=('Arial', 8), foreground='gray')
        info_label.grid(row=1, column=1, columnspan=2, sticky=tk.W, padx=5)

    def select_all_chats(self):
        """Seleziona tutte le chat"""
        for chat, var in self.chat_vars:
            var.set(True)
        self.update_estimates()

    def deselect_all_chats(self):
        """Deseleziona tutte le chat"""
        for chat, var in self.chat_vars:
            var.set(False)
        self.update_estimates()

    def update_estimates(self):
        """Aggiorna le stime di costo e tempo"""
        selected = [chat for chat, var in self.chat_vars if var.get()]
        num_selected = len(selected)

        self.selected_count_label.config(text=str(num_selected))

        if num_selected == 0:
            self.cost_estimate_label.config(text="-")
            self.time_estimate_label.config(text="-")
            return

        # Calcola costi (dipende dal modello)
        model = self.main_app.model_var.get() if not self.main_app.use_local_model.get() else "local"

        if model == "local":
            cost_per_chat = 0.0
        else:
            # Stima: ~500-1000 token input per chat (analisi combinate) + 500 token output
            costs = self.get_model_costs(model)
            cost_per_chat = ((750 / 1_000_000) * costs['input']) + ((500 / 1_000_000) * costs['output'])

        total_cost = cost_per_chat * num_selected
        total_time = num_selected * 25  # ~25 secondi per chat

        if model == "local":
            self.cost_estimate_label.config(text="Gratuito (modello locale)")
        else:
            self.cost_estimate_label.config(text=f"~${total_cost:.2f}")

        minutes = total_time // 60
        seconds = total_time % 60
        if minutes > 0:
            self.time_estimate_label.config(text=f"~{minutes} min {seconds} sec")
        else:
            self.time_estimate_label.config(text=f"~{seconds} sec")

    def get_model_costs(self, model):
        """Ritorna i costi per milione di token del modello"""
        costs = {
            "gpt-4o": {"input": 3.00, "output": 10.00},
            "gpt-4-turbo": {"input": 10.00, "output": 30.00},
            "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
            "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
            "claude-3-opus-20240229": {"input": 15.00, "output": 75.00},
        }
        return costs.get(model, {"input": 3.00, "output": 10.00})

    def start_generation(self):
        """Avvia la generazione dei report chat"""
        selected = [chat for chat, var in self.chat_vars if var.get()]

        if not selected:
            messagebox.showwarning("Attenzione", "Seleziona almeno una chat")
            return

        # Verifica API key (se non modello locale)
        if not self.main_app.use_local_model.get():
            if not self.main_app.api_key.get():
                messagebox.showerror("Errore", "Inserisci la chiave API prima di procedere")
                return

        # Conferma
        num_selected = len(selected)
        model = self.main_app.model_var.get() if not self.main_app.use_local_model.get() else "Modello locale"

        cost_text = self.cost_estimate_label.cget("text")
        time_text = self.time_estimate_label.cget("text")

        response = messagebox.askyesno(
            "Conferma Generazione",
            f"Generare report per {num_selected} chat?\n\n"
            f"Modello: {model}\n"
            f"Costo: {cost_text}\n"
            f"Tempo: {time_text}\n\n"
            f"Procedere?"
        )

        if not response:
            return

        # Disabilita pulsanti
        self.generate_button.config(state='disabled')
        self.detect_button.config(state='disabled')
        self.is_running = True

        # Avvia thread
        self.selected_chats = selected
        thread = threading.Thread(target=self.generate_reports, daemon=True)
        thread.start()

    def generate_reports(self):
        """Genera i report per le chat selezionate (eseguito in thread)"""
        try:
            self.log("="*60)
            self.log("GENERAZIONE REPORT CHAT")
            self.log("="*60)
            self.update_status("Inizializzazione...", "blue")

            output_dir = self.main_app.output_dir.get()
            chat_report_dir = os.path.join(output_dir, "report_chat")

            # Crea cartella output
            os.makedirs(chat_report_dir, exist_ok=True)
            self.log(f"✓ Cartella output: {chat_report_dir}")

            # Inizializza AI Analyzer
            if self.main_app.use_local_model.get():
                analyzer = AIAnalyzer(
                    api_key="",
                    model=self.main_app.local_model_name.get(),
                    use_local=True,
                    local_url=self.main_app.local_url.get()
                )
                self.log(f"✓ Modello locale: {self.main_app.local_model_name.get()}")
            else:
                analyzer = AIAnalyzer(
                    api_key=self.main_app.api_key.get(),
                    model=self.main_app.model_var.get()
                )
                self.log(f"✓ Modello AI: {self.main_app.model_var.get()}")

            total_chats = len(self.selected_chats)
            chat_summaries = []

            # Genera riassunto per ogni chat
            for idx, chat in enumerate(self.selected_chats):
                if not self.is_running:
                    self.log("✗ Operazione interrotta dall'utente")
                    break

                chat_name = self.get_chat_display_name(chat)
                self.log(f"[{idx+1}/{total_chats}] Analisi chat: {chat_name}")
                self.update_status(f"Analisi {idx+1}/{total_chats}: {chat_name}", "blue")
                self.update_progress((idx / total_chats) * 100)

                try:
                    # Genera riassunto
                    summary = analyzer.create_chat_summary(
                        chat=chat,
                        output_dir=output_dir,
                        log_callback=self.log
                    )

                    chat_summaries.append({
                        'chat': chat,
                        'summary': summary
                    })

                    self.log(f"✓ Chat '{chat_name}' completata")

                except Exception as e:
                    self.log(f"✗ Errore chat '{chat_name}': {str(e)}")

            if not self.is_running:
                return

            # Genera HTML
            self.log("Generazione HTML...")
            self.update_status("Generazione HTML...", "blue")
            self.update_progress(90)

            from html_templates import create_chat_index_page, create_chat_detail_page

            # Index page
            index_path = create_chat_index_page(
                chat_summaries=chat_summaries,
                output_dir=chat_report_dir,
                get_display_name_func=self.get_chat_display_name
            )

            # Detail pages
            for item in chat_summaries:
                create_chat_detail_page(
                    chat=item['chat'],
                    summary=item['summary'],
                    output_dir=chat_report_dir,
                    get_display_name_func=self.get_chat_display_name
                )

            self.log(f"✓ Report HTML salvati in: {chat_report_dir}")
            self.log("="*60)
            self.log("COMPLETATO!")
            self.log("="*60)

            self.update_status("Completato", "green")
            self.update_progress(100)

            messagebox.showinfo(
                "Completato",
                f"Report generati con successo!\n\n"
                f"Chat elaborate: {len(chat_summaries)}\n"
                f"Cartella: {chat_report_dir}\n\n"
                f"Apri 'index_chat.html' per visualizzare."
            )

        except Exception as e:
            self.log(f"✗ ERRORE: {str(e)}")
            self.update_status("Errore", "red")
            messagebox.showerror("Errore", f"Errore durante la generazione:\n{str(e)}")

        finally:
            self.is_running = False
            self.generate_button.config(state='normal')
            self.detect_button.config(state='normal')

    def update_status(self, message, color="black"):
        """Aggiorna il label di stato"""
        self.status_label.config(text=message, foreground=color)
        self.dialog.update_idletasks()

    def update_progress(self, percentage):
        """Aggiorna la barra di progresso"""
        self.progress_var.set(percentage)
        self.dialog.update_idletasks()


if __name__ == "__main__":
    # Test standalone
    print("Questo modulo deve essere importato da whatsapp_analyzer_gui.py")
