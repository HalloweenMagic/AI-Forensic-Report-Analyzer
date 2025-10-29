"""
Dialog per configurazione analisi posizioni geografiche
Permette di estrarre e mappare tutte le location menzionate nel report

© 2025 Luca Mercatanti - https://mercatanti.com
"""

import tkinter as tk
from tkinter import ttk, messagebox
import os
from pathlib import Path


class LocationAnalysisDialog:
    def __init__(self, parent, output_dir, chunks_dir, ai_analyzer):
        """
        Inizializza il dialog per l'analisi delle posizioni geografiche

        Args:
            parent: Finestra parent
            output_dir: Percorso della cartella output
            chunks_dir: Percorso della cartella con i chunk
            ai_analyzer: Istanza di AIAnalyzer per l'elaborazione
        """
        self.parent = parent
        self.output_dir = output_dir
        self.chunks_dir = chunks_dir
        self.ai_analyzer = ai_analyzer
        self.result = None

        # Variabili di configurazione
        self.geocoding_provider = tk.StringVar(value="nominatim")
        self.google_api_key = tk.StringVar(value="")
        self.confidence_threshold = tk.IntVar(value=50)  # 0-100%
        self.context_deduction = tk.BooleanVar(value=False)

        # Variabili modalità test (analisi preliminare)
        self.test_mode = tk.BooleanVar(value=False)
        self.test_chunks = tk.IntVar(value=5)

        # Crea dialog modale
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Analisi Posizioni Geografiche")
        self.dialog.geometry("600x650")
        self.center_dialog(600, 650)
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()

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
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # === DESCRIZIONE ===
        desc_frame = ttk.LabelFrame(main_frame, text="Descrizione", padding="10")
        desc_frame.pack(fill=tk.X, pady=(0, 15))

        desc_text = (
            "Questa funzione identifica tutte le posizioni geografiche menzionate nel documento\n"
            "e genera un report interattivo con mappa e riepilogo dettagliato.\n\n"
            "Vengono rilevate: coordinate GPS, indirizzi completi, luoghi nominati e punti di interesse."
        )
        ttk.Label(desc_frame, text=desc_text, justify=tk.LEFT, wraplength=540).pack()

        # === GEOCODING PROVIDER ===
        geo_frame = ttk.LabelFrame(main_frame, text="Provider Geocoding", padding="10")
        geo_frame.pack(fill=tk.X, pady=(0, 15))

        # Radio Nominatim
        nominatim_radio = ttk.Radiobutton(
            geo_frame,
            text="Nominatim (OpenStreetMap) - Gratuito",
            variable=self.geocoding_provider,
            value="nominatim",
            command=self.on_provider_change
        )
        nominatim_radio.pack(anchor=tk.W, pady=(0, 5))

        # Radio Google Maps
        google_radio = ttk.Radiobutton(
            geo_frame,
            text="Google Maps - Richiede API key",
            variable=self.geocoding_provider,
            value="google",
            command=self.on_provider_change
        )
        google_radio.pack(anchor=tk.W, pady=(0, 5))

        # Campo API Key Google (nascosto inizialmente)
        self.api_key_frame = ttk.Frame(geo_frame)
        self.api_key_frame.pack(fill=tk.X, padx=(20, 0), pady=(5, 0))

        ttk.Label(self.api_key_frame, text="Google Maps API Key:").pack(anchor=tk.W)
        self.api_key_entry = ttk.Entry(self.api_key_frame, textvariable=self.google_api_key, width=50)
        self.api_key_entry.pack(fill=tk.X, pady=(2, 0))

        # Nascondi campo API key inizialmente
        self.api_key_frame.pack_forget()

        # === CONFIDENCE THRESHOLD ===
        confidence_frame = ttk.LabelFrame(main_frame, text="Soglia Confidence", padding="10")
        confidence_frame.pack(fill=tk.X, pady=(0, 15))

        # Header con label e icona info
        header_frame = ttk.Frame(confidence_frame)
        header_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(header_frame, text="Analizza solo posizioni con confidence ≥").pack(side=tk.LEFT)

        # Label valore confidence
        self.confidence_label = ttk.Label(header_frame, text="50%", font=('Arial', 10, 'bold'))
        self.confidence_label.pack(side=tk.LEFT, padx=(5, 10))

        # Icona info con tooltip
        info_button = tk.Label(header_frame, text="ℹ️", cursor="hand2", font=('Arial', 12))
        info_button.pack(side=tk.LEFT)
        self.create_tooltip(info_button,
            "Confidence indica quanto l'AI è sicura che sia una posizione:\n\n"
            "• Alta (70-100%): Posizioni esplicite chiare\n"
            "  Es: 'Via Roma 10, Milano', coordinate GPS\n\n"
            "• Media (40-69%): Luoghi generici o ambigui\n"
            "  Es: 'al bar', 'in centro'\n\n"
            "• Bassa (0-39%): Possibili falsi positivi\n"
            "  Es: nomi propri simili a luoghi"
        )

        # Slider confidence
        self.confidence_slider = ttk.Scale(
            confidence_frame,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            variable=self.confidence_threshold,
            command=self.on_confidence_change
        )
        self.confidence_slider.pack(fill=tk.X)

        # Label indicatori sotto lo slider
        indicators_frame = ttk.Frame(confidence_frame)
        indicators_frame.pack(fill=tk.X)
        ttk.Label(indicators_frame, text="Bassa", font=('Arial', 8)).pack(side=tk.LEFT)
        ttk.Label(indicators_frame, text="Media", font=('Arial', 8)).pack(side=tk.LEFT, expand=True)
        ttk.Label(indicators_frame, text="Alta", font=('Arial', 8)).pack(side=tk.RIGHT)

        # === DEDUZIONE CONTESTO ===
        context_frame = ttk.LabelFrame(main_frame, text="Opzioni Avanzate", padding="10")
        context_frame.pack(fill=tk.X, pady=(0, 15))

        # Frame checkbox + info
        checkbox_frame = ttk.Frame(context_frame)
        checkbox_frame.pack(fill=tk.X)

        ttk.Checkbutton(
            checkbox_frame,
            text="Deduci posizioni dal contesto",
            variable=self.context_deduction
        ).pack(side=tk.LEFT)

        # Icona info deduzione contesto
        context_info_button = tk.Label(checkbox_frame, text="ℹ️", cursor="hand2", font=('Arial', 12))
        context_info_button.pack(side=tk.LEFT, padx=(5, 0))
        self.create_tooltip(context_info_button,
            "Se attivato, l'AI cerca di dedurre posizioni implicite:\n\n"
            "Es: 'torno a casa' → cerca l'indirizzo di casa\n"
            "     nei messaggi precedenti\n\n"
            "Es: 'ci vediamo al solito posto' → cerca riferimenti\n"
            "     a luoghi già menzionati\n\n"
            "⚠️ Può aumentare falsi positivi ma trova più location"
        )

        # === MODALITÀ TEST ===
        test_frame = ttk.LabelFrame(main_frame, text="Modalità Test", padding="10")
        test_frame.pack(fill=tk.X, pady=(0, 15))

        self.test_mode_check = ttk.Checkbutton(
            test_frame,
            text="Analizza solo un numero limitato di chunk (per test rapido)",
            variable=self.test_mode,
            command=self.on_test_mode_changed
        )
        self.test_mode_check.pack(anchor=tk.W, pady=(0, 10))

        # Frame spinbox
        spinbox_frame = ttk.Frame(test_frame)
        spinbox_frame.pack(fill=tk.X, padx=(20, 0))

        ttk.Label(spinbox_frame, text="Numero chunk da analizzare:").pack(side=tk.LEFT, padx=(0, 10))
        self.test_chunks_spinbox = ttk.Spinbox(
            spinbox_frame,
            from_=1,
            to=100,
            textvariable=self.test_chunks,
            width=10,
            state='disabled'
        )
        self.test_chunks_spinbox.pack(side=tk.LEFT)

        ttk.Label(
            spinbox_frame,
            text="(per verificare il funzionamento prima dell'analisi completa)",
            font=('Arial', 8),
            foreground='gray'
        ).pack(side=tk.LEFT, padx=(10, 0))

        # === PULSANTI ===
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=(10, 0))

        ttk.Button(button_frame, text="Annulla", command=self.cancel, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Avvia Analisi", command=self.start_analysis, width=15).pack(side=tk.LEFT, padx=5)

    def on_provider_change(self):
        """Mostra/nasconde campo API key in base al provider selezionato"""
        if self.geocoding_provider.get() == "google":
            self.api_key_frame.pack(fill=tk.X, padx=(20, 0), pady=(5, 0))
        else:
            self.api_key_frame.pack_forget()

    def on_confidence_change(self, value):
        """Aggiorna label quando lo slider cambia"""
        self.confidence_label.config(text=f"{int(float(value))}%")

    def on_test_mode_changed(self):
        """Abilita/disabilita lo spinbox in base alla modalità test"""
        if self.test_mode.get():
            self.test_chunks_spinbox.config(state='normal')
        else:
            self.test_chunks_spinbox.config(state='disabled')

    def create_tooltip(self, widget, text):
        """
        Crea un tooltip per un widget

        Args:
            widget: Widget a cui associare il tooltip
            text: Testo del tooltip
        """
        def show_tooltip(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root + 10}+{event.y_root + 10}")

            label = tk.Label(
                tooltip,
                text=text,
                justify=tk.LEFT,
                background="#ffffe0",
                relief=tk.SOLID,
                borderwidth=1,
                font=('Arial', 9),
                padx=10,
                pady=5
            )
            label.pack()

            # Salva riferimento al tooltip
            widget.tooltip = tooltip

        def hide_tooltip(event):
            if hasattr(widget, 'tooltip'):
                widget.tooltip.destroy()
                del widget.tooltip

        widget.bind("<Enter>", show_tooltip)
        widget.bind("<Leave>", hide_tooltip)

    def validate_config(self):
        """
        Valida la configurazione inserita

        Returns:
            bool: True se valida, False altrimenti
        """
        # Verifica cartella output esiste
        if not os.path.exists(self.output_dir):
            messagebox.showerror(
                "Errore",
                f"Cartella output non trovata:\n{self.output_dir}"
            )
            return False

        # Verifica presenza cartella chunk
        if not os.path.exists(self.chunks_dir):
            messagebox.showerror(
                "Errore",
                f"Cartella chunk non trovata:\n{self.chunks_dir}\n\n"
                "Assicurati di aver completato un'analisi prima di\n"
                "utilizzare questa funzione."
            )
            return False

        # Conta chunk disponibili
        from glob import glob
        json_chunks = glob(os.path.join(self.chunks_dir, "chunk_*.json"))
        txt_chunks = glob(os.path.join(self.chunks_dir, "chunk_*.txt"))

        if not json_chunks and not txt_chunks:
            messagebox.showerror(
                "Errore",
                f"Nessun chunk trovato nella cartella:\n{self.chunks_dir}\n\n"
                "Completa un'analisi prima di usare questa funzione."
            )
            return False

        # Verifica API key se Google Maps selezionato
        if self.geocoding_provider.get() == "google":
            api_key = self.google_api_key.get().strip()
            if not api_key:
                messagebox.showerror(
                    "Errore",
                    "Inserisci una API key valida per Google Maps\n"
                    "oppure seleziona Nominatim."
                )
                return False

        return True

    def start_analysis(self):
        """Avvia l'analisi dopo validazione"""
        if not self.validate_config():
            return

        # Prepara configurazione
        self.result = {
            'geocoding_provider': self.geocoding_provider.get(),
            'google_api_key': self.google_api_key.get().strip() if self.geocoding_provider.get() == "google" else None,
            'confidence_threshold': self.confidence_threshold.get(),
            'context_deduction': self.context_deduction.get(),
            'output_dir': self.output_dir,
            'chunks_dir': self.chunks_dir,
            'test_mode': self.test_mode.get(),
            'test_chunks': self.test_chunks.get()
        }

        self.dialog.destroy()

    def cancel(self):
        """Annulla l'operazione"""
        self.result = None
        self.dialog.destroy()

    def show(self):
        """
        Mostra il dialog e attende la chiusura

        Returns:
            dict or None: Configurazione se confermata, None se annullata
        """
        self.dialog.wait_window()
        return self.result
