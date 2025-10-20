"""
Dialog per Ricerca Rapida sulle analisi esistenti
Permette di fare domande mirate sulle analisi già prodotte

© 2025 Luca Mercatanti - https://mercatanti.com
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import os
import threading
from pathlib import Path
from ai_analyzer import AIAnalyzer


class QuickSearchDialog:
    def __init__(self, parent, main_app):
        """
        Inizializza il dialog di ricerca rapida

        Args:
            parent: Finestra parent (root)
            main_app: Istanza di WhatsAppAnalyzerGUI per accedere alle configurazioni
        """
        self.parent = parent
        self.main_app = main_app
        self.is_searching = False

        # Crea dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("🔍 Ricerca Rapida - Post-Elaborazione")
        self.dialog.geometry("800x700")
        self.dialog.resizable(True, True)

        self.setup_ui()

    def setup_ui(self):
        """Configura l'interfaccia del dialog"""

        # Frame principale con padding
        main_frame = ttk.Frame(self.dialog, padding="15")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.dialog.columnconfigure(0, weight=1)
        self.dialog.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)  # Text result area

        # ===== HEADER =====
        header_frame = ttk.Frame(main_frame)
        header_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 15))

        ttk.Label(header_frame, text="🔍 Ricerca Rapida",
                 font=('Arial', 14, 'bold')).pack(anchor=tk.W)
        ttk.Label(header_frame, text="Fai domande mirate sulle analisi già prodotte",
                 font=('Arial', 10), foreground='gray').pack(anchor=tk.W, pady=(5, 0))

        # Informazioni analisi disponibili
        info_text = self.get_analyses_info()
        info_label = ttk.Label(header_frame, text=info_text,
                              font=('Arial', 9), foreground='blue')
        info_label.pack(anchor=tk.W, pady=(10, 0))

        # ===== SEZIONE QUERY =====
        query_frame = ttk.LabelFrame(main_frame, text="Domanda", padding="10")
        query_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        query_frame.columnconfigure(0, weight=1)

        # TextArea per la domanda
        ttk.Label(query_frame, text="Cosa vuoi cercare nelle analisi?",
                 font=('Arial', 9, 'bold')).grid(row=0, column=0, sticky=tk.W, pady=(0, 5))

        self.query_text = scrolledtext.ScrolledText(query_frame, height=4, width=70, wrap=tk.WORD)
        self.query_text.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        # Esempi
        examples_label = ttk.Label(query_frame,
                                  text="💡 Esempi: 'Trova tutte le minacce', 'Elenca i luoghi menzionati', 'Chi ha parlato di denaro?'",
                                  font=('Arial', 8), foreground='gray')
        examples_label.grid(row=2, column=0, sticky=tk.W)

        # Pulsanti azione
        button_frame = ttk.Frame(query_frame)
        button_frame.grid(row=3, column=0, sticky=tk.E, pady=(10, 0))

        self.search_button = ttk.Button(button_frame, text="🔍 Cerca",
                                       command=self.start_search)
        self.search_button.grid(row=0, column=0, padx=5)

        ttk.Button(button_frame, text="❌ Chiudi",
                  command=self.dialog.destroy).grid(row=0, column=1, padx=5)

        # ===== SEZIONE RISULTATI =====
        result_frame = ttk.LabelFrame(main_frame, text="Risultati", padding="10")
        result_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(0, weight=1)

        self.result_text = scrolledtext.ScrolledText(result_frame, height=20, width=70,
                                                     wrap=tk.WORD, state='disabled')
        self.result_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # ===== SEZIONE STATUS =====
        status_frame = ttk.Frame(main_frame)
        status_frame.grid(row=3, column=0, sticky=(tk.W, tk.E))
        status_frame.columnconfigure(0, weight=1)

        self.status_label = ttk.Label(status_frame, text="Pronto", foreground="green")
        self.status_label.grid(row=0, column=0, sticky=tk.W)

        self.cost_label = ttk.Label(status_frame, text="", foreground="blue")
        self.cost_label.grid(row=0, column=1, sticky=tk.E)

        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(status_frame, variable=self.progress_var,
                                           maximum=100, length=300)
        self.progress_bar.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(5, 0))
        self.progress_bar.grid_remove()  # Nascondi inizialmente

    def get_analyses_info(self):
        """Ottiene informazioni sulle analisi disponibili"""
        output_dir = self.main_app.output_dir.get()

        if not os.path.exists(output_dir):
            return "❌ Nessuna analisi trovata"

        analysis_files = [f for f in os.listdir(output_dir)
                         if f.startswith("analisi_chunk_") and f.endswith(".txt")]

        if not analysis_files:
            return "❌ Nessuna analisi trovata"

        return f"✓ Trovate {len(analysis_files)} analisi nella cartella: {output_dir}"

    def start_search(self):
        """Avvia la ricerca in un thread separato"""
        query = self.query_text.get('1.0', tk.END).strip()

        if not query:
            messagebox.showwarning("Attenzione", "Inserisci una domanda!")
            return

        # Valida configurazione AI
        if not self.main_app.use_local_model.get() and not self.main_app.api_key.get():
            messagebox.showerror("Errore",
                               "Configura l'API Key nella schermata principale!")
            return

        # Stima costo
        output_dir = self.main_app.output_dir.get()
        analysis_files = [f for f in os.listdir(output_dir)
                         if f.startswith("analisi_chunk_") and f.endswith(".txt")]

        # Stima token: ~200 token per analisi + query
        estimated_tokens = len(analysis_files) * 200 + 100
        model_costs = self.get_model_costs()
        estimated_cost = (estimated_tokens / 1_000_000) * model_costs['input'] + \
                        (2000 / 1_000_000) * model_costs['output']

        self.cost_label.config(text=f"Costo stimato: ~${estimated_cost:.2f}")

        # Conferma
        response = messagebox.askyesno("Conferma Ricerca",
                                      f"Ricerca su {len(analysis_files)} analisi\n"
                                      f"Costo stimato: ~${estimated_cost:.2f}\n"
                                      f"Tempo stimato: ~20-30 secondi\n\n"
                                      f"Procedere?")

        if not response:
            return

        # Disabilita pulsante e avvia ricerca
        self.search_button.config(state='disabled')
        self.is_searching = True
        self.progress_bar.grid()
        self.update_status("Ricerca in corso...", "blue")

        # Pulisci risultati precedenti
        self.result_text.config(state='normal')
        self.result_text.delete('1.0', tk.END)
        self.result_text.config(state='disabled')

        # Avvia thread
        thread = threading.Thread(target=self.run_search, args=(query,), daemon=True)
        thread.start()

    def run_search(self, query):
        """Esegue la ricerca (in thread separato)"""
        try:
            self.progress_var.set(10)

            # Carica tutte le analisi
            output_dir = self.main_app.output_dir.get()
            analysis_files = sorted([f for f in os.listdir(output_dir)
                                    if f.startswith("analisi_chunk_") and f.endswith(".txt")])

            analyses = []
            for analysis_file in analysis_files:
                file_path = os.path.join(output_dir, analysis_file)
                with open(file_path, 'r', encoding='utf-8') as f:
                    analyses.append(f.read())

            self.progress_var.set(30)

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

            self.progress_var.set(50)

            # Esegui ricerca
            result = analyzer.quick_search_on_analyses(analyses, query)

            self.progress_var.set(100)

            # Mostra risultato
            self.display_result(result)
            self.update_status("Ricerca completata!", "green")

        except Exception as e:
            self.display_result(f"❌ ERRORE durante la ricerca:\n\n{str(e)}")
            self.update_status("Errore", "red")
            messagebox.showerror("Errore", f"Errore durante la ricerca:\n{str(e)}")

        finally:
            self.is_searching = False
            self.search_button.config(state='normal')
            self.progress_bar.grid_remove()

    def display_result(self, result):
        """Mostra il risultato nella text area"""
        self.result_text.config(state='normal')
        self.result_text.delete('1.0', tk.END)
        self.result_text.insert('1.0', result)
        self.result_text.config(state='disabled')

    def update_status(self, message, color="black"):
        """Aggiorna il label di stato"""
        self.status_label.config(text=message, foreground=color)
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
