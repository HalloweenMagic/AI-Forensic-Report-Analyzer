"""
Dialog per Re-Analisi Avanzata con filtri
Permette di filtrare e rianalizzare chunk con prompt specifico

© 2025 Luca Mercatanti - https://mercatanti.com
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import os
import json
import threading
from pathlib import Path
from datetime import datetime
from ai_analyzer import AIAnalyzer


class AdvancedReanalysisDialog:
    def __init__(self, parent, main_app):
        """
        Inizializza il dialog di re-analisi avanzata

        Args:
            parent: Finestra parent (root)
            main_app: Istanza di WhatsAppAnalyzerGUI per accedere alle configurazioni
        """
        self.parent = parent
        self.main_app = main_app
        self.is_analyzing = False

        # Crea dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("🔁 Re-Analisi Avanzata - Post-Elaborazione")
        self.dialog.geometry("900x800")
        self.center_dialog(900, 800)
        self.dialog.resizable(True, True)

        self.setup_ui()

    def center_dialog(self, width, height):
        """Centra il dialog sullo schermo"""
        self.dialog.update_idletasks()
        screen_width = self.dialog.winfo_screenwidth()
        screen_height = self.dialog.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        self.dialog.geometry(f'{width}x{height}+{x}+{y}')

    def setup_ui(self):
        """Configura l'interfaccia del dialog"""

        # Frame principale con padding
        main_frame = ttk.Frame(self.dialog, padding="15")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.dialog.columnconfigure(0, weight=1)
        self.dialog.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(3, weight=1)  # Log area

        # ===== HEADER =====
        header_frame = ttk.Frame(main_frame)
        header_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 15))

        ttk.Label(header_frame, text="🔁 Re-Analisi Avanzata",
                 font=('Arial', 14, 'bold')).pack(anchor=tk.W)
        ttk.Label(header_frame, text="Filtra chunk e rianalizza con prompt specifico",
                 font=('Arial', 10), foreground='gray').pack(anchor=tk.W, pady=(5, 0))

        # Informazioni chunk disponibili
        info_text = self.get_chunks_info()
        info_label = ttk.Label(header_frame, text=info_text,
                              font=('Arial', 9), foreground='blue')
        info_label.pack(anchor=tk.W, pady=(10, 0))

        # ===== SEZIONE FILTRI =====
        filters_frame = ttk.LabelFrame(main_frame, text="Filtri", padding="10")
        filters_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        filters_frame.columnconfigure(1, weight=1)

        row = 0

        # Filtro Keywords
        ttk.Label(filters_frame, text="Parole chiave:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.keywords_var = tk.StringVar()
        ttk.Entry(filters_frame, textvariable=self.keywords_var, width=50).grid(
            row=row, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=5)
        ttk.Label(filters_frame, text="(separa con virgola: es. 'minaccia, violenza, arma')",
                 font=('Arial', 8), foreground='gray').grid(row=row, column=2, sticky=tk.W, padx=(10, 0))
        row += 1

        # Modalità keywords (AND/OR)
        ttk.Label(filters_frame, text="Modalità keywords:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.keywords_mode = tk.StringVar(value="OR")
        mode_frame = ttk.Frame(filters_frame)
        mode_frame.grid(row=row, column=1, sticky=tk.W, padx=(10, 0), pady=5)
        ttk.Radiobutton(mode_frame, text="OR (almeno una)", variable=self.keywords_mode,
                       value="OR").pack(side=tk.LEFT, padx=(0, 15))
        ttk.Radiobutton(mode_frame, text="AND (tutte)", variable=self.keywords_mode,
                       value="AND").pack(side=tk.LEFT)
        row += 1

        # Numero max chunk da rianalizzare
        ttk.Label(filters_frame, text="Max chunk da analizzare:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.max_chunks_var = tk.IntVar(value=50)
        max_frame = ttk.Frame(filters_frame)
        max_frame.grid(row=row, column=1, sticky=tk.W, padx=(10, 0), pady=5)
        ttk.Spinbox(max_frame, from_=1, to=1000, textvariable=self.max_chunks_var,
                   width=10).pack(side=tk.LEFT)
        ttk.Label(max_frame, text="(protezione da costi elevati)",
                 font=('Arial', 8), foreground='gray').pack(side=tk.LEFT, padx=(10, 0))
        row += 1

        # Pulsante applica filtri
        button_filter_frame = ttk.Frame(filters_frame)
        button_filter_frame.grid(row=row, column=0, columnspan=3, sticky=tk.E, pady=(10, 0))
        self.apply_filters_button = ttk.Button(button_filter_frame, text="🔍 Applica Filtri",
                  command=self.apply_filters)
        self.apply_filters_button.pack(side=tk.RIGHT, padx=5)
        self.chunks_filtered_label = ttk.Label(button_filter_frame, text="",
                                              foreground='blue', font=('Arial', 9, 'bold'))
        self.chunks_filtered_label.pack(side=tk.RIGHT, padx=10)

        # ===== SEZIONE PROMPT PERSONALIZZATO =====
        prompt_frame = ttk.LabelFrame(main_frame, text="Prompt Specifico per Re-Analisi", padding="10")
        prompt_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        prompt_frame.columnconfigure(0, weight=1)

        ttk.Label(prompt_frame, text="Cosa vuoi cercare nei chunk filtrati?",
                 font=('Arial', 9, 'bold')).grid(row=0, column=0, sticky=tk.W, pady=(0, 5))

        self.prompt_text = scrolledtext.ScrolledText(prompt_frame, height=6, width=80, wrap=tk.WORD)
        self.prompt_text.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        # Prompt di default
        default_prompt = """Analizza questo chunk focalizzandoti ESCLUSIVAMENTE sui seguenti aspetti:

[DESCRIVI QUI COSA CERCARE - es. "Trova solo minacce esplicite", "Cerca riferimenti a denaro", ecc.]

Per ogni elemento rilevante indica:
• Contenuto/Messaggio
• Utente coinvolto
• Data/Ora (se disponibile)
• Contesto
• Riferimento (pagina/chunk)

Se non trovi nulla di rilevante per la ricerca, indica semplicemente "Nessun elemento rilevante trovato"."""

        self.prompt_text.insert('1.0', default_prompt)

        # Pulsanti azione
        button_frame = ttk.Frame(prompt_frame)
        button_frame.grid(row=2, column=0, sticky=tk.E, pady=(10, 0))

        self.analyze_button = ttk.Button(button_frame, text="🔁 Avvia Re-Analisi",
                                        command=self.start_reanalysis)
        self.analyze_button.grid(row=0, column=0, padx=5)

        ttk.Button(button_frame, text="❌ Chiudi",
                  command=self.dialog.destroy).grid(row=0, column=1, padx=5)

        # ===== SEZIONE LOG =====
        log_frame = ttk.LabelFrame(main_frame, text="Log Operazioni", padding="10")
        log_frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, width=80,
                                                  wrap=tk.WORD, state='disabled')
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # ===== SEZIONE STATUS =====
        status_frame = ttk.Frame(main_frame)
        status_frame.grid(row=4, column=0, sticky=(tk.W, tk.E))
        status_frame.columnconfigure(0, weight=1)

        self.status_label = ttk.Label(status_frame, text="Pronto", foreground="green")
        self.status_label.grid(row=0, column=0, sticky=tk.W)

        self.cost_label = ttk.Label(status_frame, text="", foreground="blue")
        self.cost_label.grid(row=0, column=1, sticky=tk.E)

        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(status_frame, variable=self.progress_var,
                                           maximum=100, length=400)
        self.progress_bar.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(5, 0))
        self.progress_bar.grid_remove()  # Nascondi inizialmente

    def get_chunks_info(self):
        """Ottiene informazioni sui chunk disponibili"""
        chunks_dir = self.main_app.chunks_dir.get()

        if not os.path.exists(chunks_dir):
            return "❌ Cartella chunk non trovata"

        chunk_files = [f for f in os.listdir(chunks_dir)
                      if f.startswith("chunk_") and (f.endswith(".txt") or f.endswith(".json"))]

        if not chunk_files:
            return "❌ Nessun chunk trovato"

        return f"✓ Trovati {len(chunk_files)} chunk nella cartella: {chunks_dir}"

    def apply_filters(self):
        """Applica i filtri e conta i chunk corrispondenti (avvia thread)"""
        keywords = self.keywords_var.get().strip()

        if not keywords:
            messagebox.showwarning("Attenzione", "Inserisci almeno una parola chiave per filtrare!")
            return

        # Disabilita pulsante durante elaborazione
        self.apply_filters_button.config(state='disabled')
        self.chunks_filtered_label.config(text="")
        self.log("Applicazione filtri...")

        # Avvia thread per non bloccare la UI
        thread = threading.Thread(target=self._run_filter_chunks, daemon=True)
        thread.start()

    def _run_filter_chunks(self):
        """Esegue il filtraggio in background (thread separato)"""
        try:
            # Carica chunk e filtra
            filtered_chunks = self.filter_chunks()

            # Aggiorna UI nel main thread
            self.dialog.after(0, self._update_filter_results, filtered_chunks)

        except Exception as e:
            self.dialog.after(0, self._show_filter_error, str(e))

    def _update_filter_results(self, filtered_chunks):
        """Aggiorna la UI con i risultati del filtraggio (main thread)"""
        if filtered_chunks:
            self.chunks_filtered_label.config(
                text=f"✓ {len(filtered_chunks)} chunk corrispondenti ai filtri")
            self.log(f"✓ Filtri applicati: trovati {len(filtered_chunks)} chunk rilevanti")

            # Mostra stima costi
            model_costs = self.get_model_costs()
            # Stima token per chunk: ~4000 caratteri / 4 = 1000 token input + 500 output
            estimated_cost = (len(filtered_chunks) * 1000 / 1_000_000) * model_costs['input'] + \
                           (len(filtered_chunks) * 500 / 1_000_000) * model_costs['output']

            self.cost_label.config(text=f"Costo stimato re-analisi: ~${estimated_cost:.2f}")
        else:
            self.chunks_filtered_label.config(text="❌ Nessun chunk trovato con questi filtri")
            self.log("✗ Nessun chunk corrisponde ai filtri impostati")
            messagebox.showinfo("Nessun Risultato",
                              "Nessun chunk corrisponde ai filtri.\n"
                              "Prova con keywords diverse o meno specifiche.")

        # Riabilita pulsante
        self.apply_filters_button.config(state='normal')

    def _show_filter_error(self, error_msg):
        """Mostra errore durante il filtraggio (main thread)"""
        self.log(f"✗ Errore durante il filtraggio: {error_msg}")
        messagebox.showerror("Errore", f"Errore durante l'applicazione dei filtri:\n{error_msg}")
        self.apply_filters_button.config(state='normal')

    def filter_chunks(self):
        """Filtra i chunk in base ai criteri"""
        chunks_dir = self.main_app.chunks_dir.get()
        keywords = [kw.strip().lower() for kw in self.keywords_var.get().split(',') if kw.strip()]
        keywords_mode = self.keywords_mode.get()
        max_chunks = self.max_chunks_var.get()

        filtered = []

        # Lista tutti i chunk
        chunk_files = sorted([f for f in os.listdir(chunks_dir)
                             if f.startswith("chunk_") and (f.endswith(".txt") or f.endswith(".json"))])

        for chunk_file in chunk_files:
            file_path = os.path.join(chunks_dir, chunk_file)

            # Leggi chunk
            if chunk_file.endswith(".json"):
                with open(file_path, 'r', encoding='utf-8') as f:
                    chunk_data = json.load(f)
                    text = chunk_data.get('text', '')
            else:
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()

            text_lower = text.lower()

            # Filtra per keywords
            if keywords:
                if keywords_mode == "AND":
                    # Tutte le keywords devono essere presenti
                    if all(kw in text_lower for kw in keywords):
                        filtered.append({'path': file_path, 'filename': chunk_file})
                else:  # OR
                    # Almeno una keyword deve essere presente
                    if any(kw in text_lower for kw in keywords):
                        filtered.append({'path': file_path, 'filename': chunk_file})

            # Limita al massimo specificato
            if len(filtered) >= max_chunks:
                break

        return filtered

    def start_reanalysis(self):
        """Avvia la re-analisi in un thread separato"""
        # Valida che ci siano filtri applicati
        if not self.chunks_filtered_label.cget("text").startswith("✓"):
            messagebox.showwarning("Attenzione",
                                 "Applica prima i filtri per vedere quanti chunk verranno analizzati!")
            return

        # Valida prompt
        prompt = self.prompt_text.get('1.0', tk.END).strip()
        if not prompt:
            messagebox.showwarning("Attenzione", "Inserisci un prompt personalizzato!")
            return

        # Valida configurazione AI
        if not self.main_app.use_local_model.get() and not self.main_app.api_key.get():
            messagebox.showerror("Errore",
                               "Configura l'API Key nella schermata principale!")
            return

        # Filtra chunk
        filtered_chunks = self.filter_chunks()

        if not filtered_chunks:
            messagebox.showwarning("Nessun Chunk", "Nessun chunk da rianalizzare!")
            return

        # Conferma
        model_costs = self.get_model_costs()
        estimated_cost = (len(filtered_chunks) * 1000 / 1_000_000) * model_costs['input'] + \
                        (len(filtered_chunks) * 500 / 1_000_000) * model_costs['output']
        estimated_time = int(len(filtered_chunks) * 6 / 60)  # ~6 sec per chunk

        response = messagebox.askyesno("Conferma Re-Analisi",
                                      f"Chunk da rianalizzare: {len(filtered_chunks)}\n"
                                      f"Costo stimato: ~${estimated_cost:.2f}\n"
                                      f"Tempo stimato: ~{estimated_time} minuti\n\n"
                                      f"Procedere con la re-analisi?")

        if not response:
            return

        # Disabilita pulsanti e avvia
        self.analyze_button.config(state='disabled')
        self.is_analyzing = True
        self.progress_bar.grid()
        self.update_status("Re-analisi in corso...", "blue")

        # Avvia thread
        thread = threading.Thread(target=self.run_reanalysis,
                                 args=(filtered_chunks, prompt), daemon=True)
        thread.start()

    def run_reanalysis(self, filtered_chunks, custom_prompt):
        """Esegue la re-analisi (in thread separato)"""
        try:
            self.log(f"Avvio re-analisi di {len(filtered_chunks)} chunk...")
            self.progress_var.set(5)

            # Crea output directory per re-analisi
            output_base = self.main_app.output_dir.get()
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            reanalysis_output = Path(output_base) / f"reanalisi_{timestamp}"
            reanalysis_output.mkdir(exist_ok=True)

            self.log(f"Cartella risultati: {reanalysis_output}")

            # Crea analyzer
            if self.main_app.use_local_model.get():
                analyzer = AIAnalyzer(
                    api_key="",
                    model=self.main_app.local_model_name.get(),
                    use_local=True,
                    local_url=self.main_app.local_url.get()
                )
            else:
                analyzer = AIAnalyzer(
                    api_key=self.main_app.api_key.get(),
                    model=self.main_app.model_var.get()
                )

            self.progress_var.set(10)

            # Prepara chunk per analisi
            chunks_to_analyze = []
            for chunk_info in filtered_chunks:
                chunks_to_analyze.append({
                    'path': chunk_info['path'],
                    'chunk_num': len(chunks_to_analyze) + 1
                })

            # Analizza chunk filtrati
            analyses = analyzer.analyze_chunks(
                chunks_to_analyze,
                str(reanalysis_output),
                custom_prompt=custom_prompt,
                progress_callback=self.update_progress,
                stop_flag=lambda: not self.is_analyzing,
                log_callback=self.log
            )

            self.log(f"✓ Analizzati {len(analyses)} chunk")
            self.progress_var.set(90)

            # Crea riassunto finale
            self.log("Creazione riassunto finale...")
            summary = analyzer.create_final_summary(
                analyses,
                len(chunks_to_analyze),
                str(reanalysis_output),
                log_callback=self.log
            )

            self.progress_var.set(100)
            self.log("="*60)
            self.log("✅ RE-ANALISI COMPLETATA CON SUCCESSO!")
            self.log(f"Risultati salvati in: {reanalysis_output}")
            self.log("="*60)

            self.update_status("Re-analisi completata!", "green")

            # Mostra dialog finale
            messagebox.showinfo("Completato",
                              f"Re-analisi completata!\n\n"
                              f"Chunk rianalizzati: {len(analyses)}\n"
                              f"Risultati salvati in:\n{reanalysis_output}\n\n"
                              f"Troverai:\n"
                              f"• Analisi dettagliate dei chunk filtrati\n"
                              f"• RIASSUNTO_FINALE.txt\n"
                              f"• Report HTML interattivo")

        except Exception as e:
            self.log(f"✗ ERRORE: {str(e)}")
            self.update_status("Errore", "red")
            messagebox.showerror("Errore", f"Errore durante la re-analisi:\n{str(e)}")

        finally:
            self.is_analyzing = False
            self.analyze_button.config(state='normal')
            self.progress_bar.grid_remove()

    def log(self, message):
        """Aggiunge un messaggio al log"""
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')
        self.dialog.update_idletasks()

    def update_status(self, message, color="black"):
        """Aggiorna il label di stato"""
        self.status_label.config(text=message, foreground=color)
        self.dialog.update_idletasks()

    def update_progress(self, percentage):
        """Aggiorna la progress bar"""
        # Mappa 0-100 del analyzer a 10-90 della progress bar totale
        mapped = 10 + (percentage * 0.8)
        self.progress_var.set(mapped)
        self.dialog.update_idletasks()

    def get_model_costs(self):
        """Ottiene i costi del modello selezionato"""
        model = self.main_app.model_var.get()
        costs = {
            "gpt-4o": {"input": 3.00, "output": 10.00},
            "gpt-4-turbo": {"input": 10.00, "output": 30.00},
            "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
            "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
            "claude-3-opus-20240229": {"input": 15.00, "output": 75.00},
        }
        return costs.get(model, {"input": 3.00, "output": 10.00})
