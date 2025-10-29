"""
Dialog informativo post-analisi
Mostra suggerimenti sulle funzionalità di post-elaborazione disponibili

© 2025 Luca Mercatanti - https://mercatanti.com
"""

import tkinter as tk
from tkinter import ttk
import json
from pathlib import Path


class PostAnalysisInfoDialog:
    PREFERENCES_FILE = ".app_preferences"

    def __init__(self, parent):
        """
        Inizializza il dialog informativo post-analisi

        Args:
            parent: Finestra parent
        """
        self.parent = parent
        self.dont_show_again = tk.BooleanVar(value=False)

        # Crea dialog modale
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Analisi completata!")
        self.dialog.geometry("500x200")
        self.center_dialog(500, 200)
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

        # Frame principale con padding ridotto
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # === TESTO INFORMATIVO ===
        text_frame = ttk.Frame(main_frame)
        text_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        # Creo un Text widget per il testo (altezza ridotta)
        text_widget = tk.Text(text_frame, wrap=tk.WORD, height=4, width=55,
                             font=('Arial', 11), relief=tk.FLAT,
                             bg=self.dialog.cget('bg'), cursor="arrow")
        text_widget.pack(fill=tk.BOTH, expand=True)

        # Inserisci il testo
        text_widget.insert('1.0',
            "Sapevi che puoi sfruttare ulteriormente i risultati ottenuti?\n"
            "Dal menu \"Post-elaborazione\" in alto hai accesso a funzionalità "
            "aggiuntive per migliorare il report.")

        # Rendi il text widget non editabile
        text_widget.config(state='disabled')

        # === CHECKBOX ===
        checkbox_frame = ttk.Frame(main_frame)
        checkbox_frame.pack(pady=(0, 12))

        ttk.Checkbutton(checkbox_frame,
                      text="Non mostrare più questo messaggio",
                      variable=self.dont_show_again).pack()

        # === PULSANTE ===
        button_frame = ttk.Frame(main_frame)
        button_frame.pack()

        ttk.Button(button_frame, text="Ho capito",
                  command=self.close_dialog, width=20).pack()

    def close_dialog(self):
        """Chiude il dialog e salva le preferenze"""
        if self.dont_show_again.get():
            self.save_preference(show_post_analysis_info=False)

        self.dialog.destroy()

    @staticmethod
    def should_show():
        """
        Verifica se il dialog deve essere mostrato

        Returns:
            bool: True se deve essere mostrato, False altrimenti
        """
        prefs_file = Path(PostAnalysisInfoDialog.PREFERENCES_FILE)

        if not prefs_file.exists():
            return True  # Primo avvio, mostra sempre

        try:
            with open(prefs_file, 'r', encoding='utf-8') as f:
                prefs = json.load(f)
                return prefs.get('show_post_analysis_info', True)
        except Exception:
            return True  # In caso di errore, mostra comunque

    @staticmethod
    def save_preference(show_post_analysis_info=False):
        """
        Salva la preferenza dell'utente

        Args:
            show_post_analysis_info: Se True, mostra il dialog dopo l'analisi
        """
        prefs_file = Path(PostAnalysisInfoDialog.PREFERENCES_FILE)

        try:
            # Leggi preferenze esistenti
            if prefs_file.exists():
                with open(prefs_file, 'r', encoding='utf-8') as f:
                    prefs = json.load(f)
            else:
                prefs = {}

            # Aggiorna
            prefs['show_post_analysis_info'] = show_post_analysis_info

            # Salva
            with open(prefs_file, 'w', encoding='utf-8') as f:
                json.dump(prefs, f, indent=4)

        except Exception as e:
            print(f"Errore salvataggio preferenze: {e}")
