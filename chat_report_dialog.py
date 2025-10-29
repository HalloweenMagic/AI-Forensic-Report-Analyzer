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

        # Variabili modalità test (analisi preliminare)
        self.test_mode = tk.BooleanVar(value=False)
        self.test_chunks = tk.IntVar(value=5)

        # Crea dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("💬 Report per Chat - Post-Elaborazione")
        self.dialog.geometry("900x1000")
        self.center_dialog(900, 1000)
        self.dialog.resizable(True, True)

        self.setup_ui()

        # Carica info iniziali
        self.update_info_display()

    def center_dialog(self, width, height):
        """Centra il dialog sullo schermo"""
        self.dialog.update_idletasks()
        screen_width = self.dialog.winfo_screenwidth()
        screen_height = self.dialog.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        self.dialog.geometry(f'{width}x{height}+{x}+{y}')

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

        # ===== MODALITÀ TEST (ANALISI PRELIMINARE) =====
        test_frame = ttk.LabelFrame(main_frame, text="🧪 Modalità Test (Analisi Preliminare)", padding="10")
        test_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        test_frame.columnconfigure(1, weight=1)

        self.test_mode_check = ttk.Checkbutton(
            test_frame,
            text="Analizza solo un numero limitato di chunk (per test rapido)",
            variable=self.test_mode,
            command=self.on_test_mode_changed
        )
        self.test_mode_check.grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))

        ttk.Label(test_frame, text="Numero chunk da analizzare:").grid(row=1, column=0, sticky=tk.W, padx=(20, 10))
        self.test_chunks_spinbox = ttk.Spinbox(
            test_frame,
            from_=1,
            to=100,
            textvariable=self.test_chunks,
            width=10,
            state='disabled'
        )
        self.test_chunks_spinbox.grid(row=1, column=1, sticky=tk.W)

        ttk.Label(
            test_frame,
            text="💡 Utile per verificare rapidamente il rilevamento chat prima di analizzare tutto",
            font=('Arial', 8),
            foreground='gray'
        ).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(10, 0))
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

        # Info nuovo sistema LLM
        info_frame = ttk.Frame(main_frame)
        info_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        info_text = tk.Text(
            info_frame,
            height=3,
            width=90,
            wrap=tk.WORD,
            state='normal',
            bg='#E8F5E9',
            relief=tk.FLAT,
            font=('Arial', 9)
        )
        info_text.insert('1.0',
            "🤖 NUOVO SISTEMA: Rilevamento LLM con Sliding Window\n"
            "   • Rileva automaticamente TUTTE le chat (1v1 e gruppi) anche con header spezzati\n"
            "   • Utilizza il modello AI configurato nella finestra principale"
        )
        info_text.config(state='disabled')
        info_text.pack(fill=tk.X)
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

    def on_test_mode_changed(self):
        """Abilita/disabilita lo spinbox in base alla modalità test"""
        if self.test_mode.get():
            self.test_chunks_spinbox.config(state='normal')
            self.log("🧪 Modalità test attivata: verrà analizzato un numero limitato di chunk")
        else:
            self.test_chunks_spinbox.config(state='disabled')
            self.log("✓ Modalità normale: verranno analizzati tutti i chunk")

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
        """
        NUOVO SISTEMA: Rileva chat usando LLM con sliding window overlap.
        Elimina dipendenza da regex per gestire header spezzati e formati variabili.
        """
        try:
            self.log("🤖 NUOVO SISTEMA: Rilevamento LLM con Sliding Window")
            self.log("📊 Configurazione: Overlap 2000 caratteri tra chunk")

            # Carica chunk da disco
            chunks = self._load_chunks_from_disk()

            if not chunks:
                self.log("✗ Nessun chunk trovato")
                self.update_status("Errore", "red")
                return

            self.log(f"📄 Chunk caricati: {len(chunks)}")
            self.update_status("Analisi LLM in corso...", "blue")

            # Pass 1: Analisi con overlap
            self.log("🔍 PASS 1/3: Analisi chunk con contesto...")
            chat_candidates = self._analyze_chunks_with_overlap(chunks)

            if not chat_candidates:
                self.log("⚠️ Nessuna chat rilevata nei chunk")
                self.update_status("Completato - Nessuna chat", "orange")
                return

            self.log(f"✓ Pass 1 completato: {len(chat_candidates)} candidati trovati")

            # Pass 2: Deduplicazione
            self.log("🔄 PASS 2/3: Deduplicazione e merge chat...")
            unique_chats = self._deduplicate_chats(chat_candidates)
            self.log(f"✓ Pass 2 completato: {len(unique_chats)} chat uniche identificate")

            # Pass 3: Mapping chunk
            self.log("📊 PASS 3/3: Mapping chat ai chunk...")
            for chat in unique_chats:
                chat['chunks'] = self._find_chunks_containing_chat(chat, chunks)

            self.detected_chats = unique_chats
            self.update_progress(100)

            # Log finale con avviso modalità test
            if self.test_mode.get():
                self.log(f"✅ RILEVAMENTO PRELIMINARE COMPLETATO: {len(unique_chats)} chat trovate")
                self.log(f"   ⚠️ ATTENZIONE: Analisi limitata ai primi {self.test_chunks.get()} chunk")
                self.log(f"   💡 Per analizzare tutti i chunk, disattiva la modalità test e rilancia")
            else:
                self.log(f"✅ RILEVAMENTO COMPLETATO: {len(unique_chats)} chat pronte")

            self.update_status("Completato", "green")

            # Mostra risultati
            self.display_detected_chats()

        except Exception as e:
            self.log(f"✗ Errore durante il rilevamento: {str(e)}")
            import traceback
            self.log(f"   Dettagli: {traceback.format_exc()}")
            self.update_status("Errore", "red")
        finally:
            self.detect_button.config(state='normal')

    def _load_chunks_from_disk(self):
        """Carica tutti i chunk da disco"""
        chunks_dir = self.main_app.chunks_dir.get()

        if not os.path.exists(chunks_dir):
            self.log("✗ Errore: Cartella chunk non trovata")
            return []

        # Determina formato chunk
        chunk_format = self.main_app.chunk_format.get()
        extension = ".json" if chunk_format == "json" else ".txt"

        chunk_files = sorted([f for f in os.listdir(chunks_dir)
                             if f.startswith("chunk_") and f.endswith(extension)])

        if not chunk_files:
            return []

        chunks = []
        for idx, chunk_file in enumerate(chunk_files):
            chunk_path = os.path.join(chunks_dir, chunk_file)

            try:
                if extension == ".json":
                    import json
                    with open(chunk_path, 'r', encoding='utf-8') as f:
                        chunk_data = json.load(f)
                        chunks.append({
                            'id': idx + 1,
                            'filename': chunk_file,
                            'text': chunk_data.get('text', ''),
                            'metadata': chunk_data
                        })
                else:
                    with open(chunk_path, 'r', encoding='utf-8') as f:
                        chunks.append({
                            'id': idx + 1,
                            'filename': chunk_file,
                            'text': f.read(),
                            'metadata': {}
                        })
            except Exception as e:
                self.log(f"⚠️ Errore lettura {chunk_file}: {str(e)}")
                continue

        return chunks

    def _analyze_chunks_with_overlap(self, chunks, overlap_chars=2000):
        """
        Analizza chunk con overlap per catturare header spezzati.

        Args:
            chunks: Lista di chunk caricati
            overlap_chars: Caratteri di sovrapposizione (default 2000)

        Returns:
            Lista di candidati chat trovati
        """
        # Se modalità test attiva, limita i chunk
        original_total = len(chunks)
        if self.test_mode.get():
            max_chunks = self.test_chunks.get()
            chunks = chunks[:max_chunks]
            self.log(f"🧪 MODALITÀ TEST ATTIVA: Analisi limitata ai primi {len(chunks)} chunk (su {original_total} totali)")
            self.log(f"   ⚠️ Questa è un'analisi preliminare per verificare il rilevamento chat")
        else:
            self.log(f"📊 Modalità normale: Analisi di tutti i {len(chunks)} chunk disponibili")

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
            self.log(f"✓ Modello cloud: {self.main_app.model_var.get()}")

        chat_candidates = []

        for i, chunk in enumerate(chunks):
            self.log(f"🔍 Analisi chunk {i+1}/{len(chunks)} con contesto...")
            self.update_progress((i / len(chunks)) * 60)  # 0-60% per Pass 1

            # Costruisci testo con overlap
            text_parts = []

            # Contesto precedente
            if i > 0:
                prev_text = chunks[i-1]['text']
                text_parts.append(f"[CONTESTO PRECEDENTE]\n{prev_text[-overlap_chars:]}\n[/CONTESTO PRECEDENTE]\n\n")

            # Chunk corrente (PRINCIPALE)
            text_parts.append(f"[CHUNK CORRENTE - ID: {i+1}]\n{chunk['text']}\n[/CHUNK CORRENTE]\n\n")

            # Contesto successivo
            if i < len(chunks) - 1:
                next_text = chunks[i+1]['text']
                text_parts.append(f"[CONTESTO SUCCESSIVO]\n{next_text[:overlap_chars]}\n[/CONTESTO SUCCESSIVO]")

            full_text = "".join(text_parts)

            # Chiamata LLM
            result = analyzer.detect_chats_in_text(
                text=full_text,
                chunk_id=i+1,
                total_chunks=len(chunks),
                log_callback=self.log
            )

            # Aggiungi metadati ai candidati
            for idx, chat in enumerate(result.get('chats_detected', [])):
                chat['detected_in_chunk'] = i + 1
                chat['detected_in_filename'] = chunk['filename']
                chat['chunk_context'] = {
                    'has_prev': i > 0,
                    'has_next': i < len(chunks) - 1
                }
                chat_candidates.append(chat)

                # Log dettagli chat trovata
                chat_type = chat.get('type', '?')
                participants = chat.get('participants', [])
                participant_names = [p.get('name', p.get('id', '?')) for p in participants[:3]]
                self.log(f"      Chat {idx+1}: tipo={chat_type}, partecipanti={participant_names}, confidence={chat.get('confidence', '?')}")

            # Log risultati chunk
            num_found = len(result.get('chats_detected', []))
            if num_found > 0:
                self.log(f"   ✓ {num_found} chat trovate in chunk {i+1}")
            else:
                self.log(f"   ℹ️ Nessuna chat trovata in chunk {i+1}")

            # Stima costi (approssimativa)
            estimated_tokens = len(full_text) / 4
            cost_per_token = 0.00003 / 1000  # ~$0.03 per 1M token
            cost_this_chunk = estimated_tokens * cost_per_token
            self.log(f"   💰 Costo stimato chunk: ${cost_this_chunk:.4f}")

        return chat_candidates

    def _deduplicate_chats(self, chat_candidates):
        """
        Unifica chat duplicate trovate in chunk diversi.

        Due chat sono considerate uguali se:
        - Stesso identifier (se presente)
        - Stessi partecipanti (overlap significativo)
        - Identifier di una coincide con ID partecipante dell'altra
        """
        unique_chats = []

        self.log(f"   📋 Deduplicazione: {len(chat_candidates)} candidati da analizzare")

        for idx, candidate in enumerate(chat_candidates):
            # Log per debug
            chat_name = self.get_chat_display_name(candidate)
            detected_in = candidate.get('detected_in_chunk', '?')
            candidate_key = self._generate_chat_key(candidate)
            self.log(f"   🔑 Candidato {idx+1}: '{chat_name}' (chunk {detected_in}) -> chiave: '{candidate_key[:50]}...'")

            # Cerca se esiste già una chat simile
            found_duplicate = False

            for existing in unique_chats:
                if self._are_same_chat(candidate, existing):
                    # DUPLICATO trovato!
                    found_duplicate = True
                    self.log(f"      ♻️ DUPLICATO trovato! Merge con chat esistente...")

                    # Merge: aggiungi chunk rilevamento
                    if 'detected_in_chunk' not in existing:
                        existing['detected_in_chunk'] = []
                    if isinstance(candidate.get('detected_in_chunk'), list):
                        existing['detected_in_chunk'].extend(candidate['detected_in_chunk'])
                    else:
                        existing['detected_in_chunk'].append(candidate.get('detected_in_chunk'))

                    # Aggiorna metadati se confidence più alta
                    if (candidate.get('confidence') == 'high' and
                        existing.get('confidence') != 'high'):
                        # Aggiorna con i dati migliori
                        self.log(f"      📈 Aggiornamento dati (confidence più alta)")
                        for key, value in candidate.items():
                            if key not in ['detected_in_chunk', 'chunk_context']:
                                existing[key] = value
                    break

            if not found_duplicate:
                # Nuova chat
                self.log(f"      ✨ NUOVA chat aggiunta alla lista")
                if 'detected_in_chunk' in candidate and not isinstance(candidate['detected_in_chunk'], list):
                    candidate['detected_in_chunk'] = [candidate['detected_in_chunk']]
                unique_chats.append(candidate)

        self.log(f"   ✓ Deduplicazione completata: {len(unique_chats)} chat uniche (da {len(chat_candidates)} candidati)")
        return unique_chats

    def _are_same_chat(self, chat1, chat2):
        """
        Determina se due chat sono la stessa conversazione.

        Controlla:
        1. Identifier uguale
        2. Identifier di una coincide con participant ID dell'altra
        3. Partecipanti con overlap > 80%
        """
        # Estrai dati (con controllo None)
        id1_raw = chat1.get('metadata', {}).get('identifier')
        id2_raw = chat2.get('metadata', {}).get('identifier')

        id1 = (id1_raw or '').strip().lower()
        id2 = (id2_raw or '').strip().lower()

        participants1 = chat1.get('participants', [])
        participants2 = chat2.get('participants', [])

        # Estrai tutti gli ID partecipanti (normalizzati, con controllo None)
        ids1 = set()
        for p in participants1:
            pid = p.get('id')
            if pid:
                ids1.add(str(pid).strip().lower())

        ids2 = set()
        for p in participants2:
            pid = p.get('id')
            if pid:
                ids2.add(str(pid).strip().lower())

        # CHECK 1: Identifier identico (e non vuoto)
        if id1 and id2 and id1 == id2:
            if hasattr(self, 'log'):
                self.log(f"      🔗 CHECK 1: Identifier identico")
            return True

        # CHECK 2: Identifier di una è tra i partecipanti dell'altra
        # (L'AI a volte mette l'identifier di un partecipante nel campo identifier della chat)
        if id1 and id1 in ids2:
            if hasattr(self, 'log'):
                self.log(f"      🔗 CHECK 2: Identifier chat1 coincide con partecipante chat2")
            return True
        if id2 and id2 in ids1:
            if hasattr(self, 'log'):
                self.log(f"      🔗 CHECK 2: Identifier chat2 coincide con partecipante chat1")
            return True

        # CHECK 3: Partecipanti con overlap significativo
        if ids1 and ids2:
            intersection = ids1.intersection(ids2)
            union = ids1.union(ids2)
            overlap_ratio = len(intersection) / len(union) if union else 0

            # Se > 80% degli ID coincidono, è la stessa chat
            if overlap_ratio > 0.8:
                if hasattr(self, 'log'):
                    self.log(f"      🔗 CHECK 3: Partecipanti overlap {overlap_ratio*100:.0f}%")
                return True

        # CHECK 4: Per chat 1v1, se hanno lo stesso partner (escludendo owner)
        if chat1.get('type') == '1v1' and chat2.get('type') == '1v1':
            # Trova il partecipante non-owner
            partner1 = None
            partner2 = None

            for p in participants1:
                if not p.get('owner', False):
                    pid = p.get('id')
                    pname = p.get('name')
                    partner1 = (str(pid).strip().lower() if pid else '') or (str(pname).strip().lower() if pname else '')
                    if partner1:
                        break

            for p in participants2:
                if not p.get('owner', False):
                    pid = p.get('id')
                    pname = p.get('name')
                    partner2 = (str(pid).strip().lower() if pid else '') or (str(pname).strip().lower() if pname else '')
                    if partner2:
                        break

            if partner1 and partner2 and partner1 == partner2:
                if hasattr(self, 'log'):
                    self.log(f"      🔗 CHECK 4: Chat 1v1 con stesso partner")
                return True

        # CHECK 5: GRUPPO con/senza identifier - SUBSET partecipanti
        # Se un gruppo SENZA identifier ha partecipanti che sono SUBSET di un gruppo CON identifier
        # → È lo stesso gruppo (chunk successivo senza header)
        if chat1.get('type') == 'group' and chat2.get('type') == 'group':
            # Determina quale ha identifier e quale no
            chat_with_id = None
            chat_without_id = None

            if id1 and not id2:
                chat_with_id = chat1
                chat_without_id = chat2
                ids_with = ids1
                ids_without = ids2
            elif id2 and not id1:
                chat_with_id = chat2
                chat_without_id = chat1
                ids_with = ids2
                ids_without = ids1

            # Se uno ha identifier e l'altro no, controlla subset
            if chat_with_id and chat_without_id and ids_without:
                # Calcola quanti partecipanti del gruppo senza ID sono presenti nel gruppo con ID
                matching = ids_without.intersection(ids_with)

                # Se almeno il 60% dei partecipanti del gruppo senza ID
                # sono presenti nel gruppo con ID → è lo stesso gruppo
                match_ratio = len(matching) / len(ids_without) if ids_without else 0
                if match_ratio >= 0.6:
                    # Log per debug
                    if hasattr(self, 'log'):
                        self.log(f"      🔗 CHECK 5: Gruppo senza ID è SUBSET di gruppo con ID (match: {match_ratio*100:.0f}%)")
                    return True

        # Non sono la stessa chat
        return False

    def _generate_chat_key(self, chat):
        """
        Genera chiave univoca per identificare chat duplicate.
        Usa normalizzazione per gestire variazioni minori.
        """
        # Priorità 1: Identifier esplicito
        identifier = chat.get('metadata', {}).get('identifier')
        if identifier:
            identifier_str = str(identifier).strip().lower()
            if identifier_str:
                return f"id_{identifier_str}"

        # Priorità 2: Partecipanti (ordinati e normalizzati)
        participants = chat.get('participants', [])
        if participants:
            # Estrai ID/nomi e normalizza (lowercase, strip) - con controllo None
            participant_keys = []
            for p in participants:
                pid = p.get('id')
                pname = p.get('name')
                key = (str(pid).strip().lower() if pid else '') or (str(pname).strip().lower() if pname else '')
                if key:
                    participant_keys.append(key)

            if participant_keys:
                # Ordina per avere chiave consistente
                participant_keys_sorted = sorted(participant_keys)
                return f"parts_{'_'.join(participant_keys_sorted)}"

        # Priorità 3: Tipo + numero partecipanti (per riconoscere 1v1 con stesso partner)
        chat_type = chat.get('type', '')
        num_participants = len(participants)
        if chat_type and num_participants > 0:
            # Per 1v1, usa il nome dell'altro partecipante (non owner)
            if chat_type == '1v1' and num_participants >= 1:
                for p in participants:
                    if not p.get('owner', False):
                        pname = p.get('name')
                        pid = p.get('id')
                        partner_name = (str(pname).strip().lower() if pname else '') or (str(pid).strip().lower() if pid else '')
                        if partner_name:
                            return f"1v1_{partner_name}"
                # Se non trova non-owner, usa il primo
                if participants:
                    pname = participants[0].get('name')
                    pid = participants[0].get('id')
                    first_name = (str(pname).strip().lower() if pname else '') or (str(pid).strip().lower() if pid else '')
                    if first_name:
                        return f"1v1_{first_name}"

        # Fallback: chat_id se presente
        chat_id = chat.get('chat_id')
        if chat_id:
            return f"cid_{chat_id}"

        # Ultimo fallback: start_marker hashato
        start_marker = chat.get('start_marker', '')
        if start_marker:
            return f"marker_{abs(hash(start_marker[:100]))}"

        # Fallback finale: hash dell'intera struttura chat
        import json
        return f"struct_{abs(hash(json.dumps(chat, sort_keys=True)))}"

    def _find_chunks_containing_chat(self, chat, chunks):
        """
        Trova tutti i chunk che contengono messaggi di questa chat.

        Usa i marker start/end per identificare i confini.
        """
        # Per ora, usa il chunk dove è stata rilevata
        detected_chunks = chat.get('detected_in_chunk', [])
        if not isinstance(detected_chunks, list):
            detected_chunks = [detected_chunks]

        # Assumiamo che la chat occupi i chunk dal primo rilevamento in poi
        # fino al prossimo header o fine documento
        # (logica semplificata, può essere raffinata)

        return detected_chunks

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

        # Se modalità test, mostra avviso in alto
        if self.test_mode.get():
            warning_frame = ttk.Frame(self.chats_list_frame)
            warning_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 15))

            warning_text = tk.Text(
                warning_frame,
                height=3,
                wrap=tk.WORD,
                state='normal',
                bg='#FFF3CD',  # Giallo chiaro
                relief=tk.FLAT,
                font=('Arial', 9, 'bold'),
                foreground='#856404'
            )
            warning_text.insert('1.0',
                f"⚠️ MODALITÀ TEST ATTIVA\n"
                f"   Rilevate chat solo nei primi {self.test_chunks.get()} chunk.\n"
                f"   Per analisi completa, disattiva modalità test e rilancia."
            )
            warning_text.config(state='disabled')
            warning_text.pack(fill=tk.X)
            row += 1

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

        # Aggiungi indicazione modalità test
        cost_text = ""
        time_text = ""

        if model == "local":
            cost_text = "Gratuito (modello locale)"
        else:
            cost_text = f"~${total_cost:.2f}"

        # Aggiungi nota modalità test
        if self.test_mode.get():
            cost_text += " (modalità test)"

        self.cost_estimate_label.config(text=cost_text)

        minutes = total_time // 60
        seconds = total_time % 60
        if minutes > 0:
            time_text = f"~{minutes} min {seconds} sec"
        else:
            time_text = f"~{seconds} sec"

        if self.test_mode.get():
            time_text += " (test)"

        self.time_estimate_label.config(text=time_text)

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

        # Messaggio diverso se modalità test
        confirm_message = f"Generare report per {num_selected} chat?\n\n"
        confirm_message += f"Modello: {model}\n"
        confirm_message += f"Costo: {cost_text}\n"
        confirm_message += f"Tempo: {time_text}\n\n"

        if self.test_mode.get():
            confirm_message += f"⚠️ MODALITÀ TEST ATTIVA\n"
            confirm_message += f"Le chat sono state rilevate solo nei primi {self.test_chunks.get()} chunk.\n"
            confirm_message += f"Per report completi, disattiva modalità test.\n\n"

        confirm_message += "Procedere?"

        response = messagebox.askyesno(
            "Conferma Generazione",
            confirm_message
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
            from dashboard_manager import DashboardManager

            self.log("="*60)
            self.log("GENERAZIONE REPORT CHAT")
            self.log("="*60)
            self.update_status("Inizializzazione...", "blue")

            output_dir = self.main_app.output_dir.get()
            chat_report_dir = os.path.join(output_dir, "REPORT", "report_chat")

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

            # Registra nella dashboard
            chats_1v1 = len([c for c in chat_summaries if c['chat']['type'] == '1v1'])
            chats_group = len([c for c in chat_summaries if c['chat']['type'] == 'group'])

            dashboard = DashboardManager(output_dir)
            dashboard.register_report('chat', {
                'chats_1v1': chats_1v1,
                'chats_group': chats_group,
                'total_chats': len(chat_summaries)
            })

            # Rigenera dashboard
            dashboard.generate_dashboard()
            self.log(f"✓ Dashboard aggiornata")

            # Aggiorna stato bottone "Apri Report" nella GUI principale
            if hasattr(self.main_app, 'check_report_availability'):
                self.main_app.check_report_availability()

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
                f"Apri 'REPORT/index.html' per accedere alla dashboard."
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
