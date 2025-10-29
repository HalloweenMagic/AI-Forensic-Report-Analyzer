#!/usr/bin/env python3
"""
License Dialog - Dialog per inserimento e validazione licenza
Mostra all'avvio se la licenza non è presente o non valida

© 2025 Luca Mercatanti - https://mercatanti.com
"""

import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser
import threading
import queue
from license_manager import LicenseManager


class LicenseDialog:
    def __init__(self, parent, license_manager):
        """
        Dialog per inserimento licenza

        Args:
            parent: Finestra parent (Tk root)
            license_manager: Istanza LicenseManager
        """
        self.parent = parent
        self.license_manager = license_manager
        self.license_valid = False
        self.is_validating = False
        self.result_queue = queue.Queue()

        # Crea dialog modale
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Licenza - AI Forensics Report Analyzer")
        self.dialog.geometry("650x700")
        self.dialog.resizable(False, False)

        # Rendi il dialog modale
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self.setup_ui()

        # Centra il dialog DOPO aver creato l'UI
        self.center_dialog()

        # Impedisci chiusura dialog con X (deve validare la licenza)
        self.dialog.protocol("WM_DELETE_WINDOW", self.on_close_attempt)

    def center_dialog(self):
        """Centra il dialog sullo schermo"""
        # Forza aggiornamento geometria
        self.dialog.update_idletasks()

        # Usa dimensioni fisse (650x700) per maggiore leggibilità
        width = 650
        height = 700

        # Calcola posizione centrale
        screen_width = self.dialog.winfo_screenwidth()
        screen_height = self.dialog.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)

        # Imposta geometria
        self.dialog.geometry(f'{width}x{height}+{x}+{y}')

    def setup_ui(self):
        """Configura l'interfaccia grafica"""

        # Frame principale
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ===== HEADER =====
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 20))

        ttk.Label(
            header_frame,
            text="🔐 Licenza Richiesta",
            font=('Arial', 16, 'bold')
        ).pack(anchor=tk.W)

        ttk.Label(
            header_frame,
            text="Inserisci la tua chiave di licenza per utilizzare AI Forensics Report Analyzer",
            font=('Arial', 10),
            foreground='gray'
        ).pack(anchor=tk.W, pady=(5, 0))

        # ===== HARDWARE ID INFO =====
        info_frame = ttk.LabelFrame(main_frame, text="ℹ️ Informazioni Sistema", padding="12")
        info_frame.pack(fill=tk.X, pady=(0, 15))

        hardware_id = self.license_manager.get_hardware_id()
        ttk.Label(
            info_frame,
            text=f"Hardware ID: {hardware_id[:32]}...",
            font=('Courier', 9),
            foreground='#555'
        ).pack(anchor=tk.W)

        ttk.Label(
            info_frame,
            text="La licenza verrà associata automaticamente a questo PC",
            font=('Arial', 9),
            foreground='gray'
        ).pack(anchor=tk.W, pady=(5, 0))

        # ===== INPUT LICENZA =====
        input_frame = ttk.LabelFrame(main_frame, text="🔑 Chiave di Licenza", padding="15")
        input_frame.pack(fill=tk.X, pady=(0, 15))

        ttk.Label(
            input_frame,
            text="Inserisci la chiave di licenza ricevuta via email:",
            font=('Arial', 10)
        ).pack(anchor=tk.W, pady=(0, 10))

        # Entry per la licenza
        self.license_entry = ttk.Entry(input_frame, font=('Courier', 11), width=50)
        self.license_entry.pack(fill=tk.X, pady=(0, 10))
        self.license_entry.focus()

        # Bind Enter per validare
        self.license_entry.bind('<Return>', lambda e: self.validate_license())

        # Frame bottoni validazione
        buttons_frame = ttk.Frame(input_frame)
        buttons_frame.pack(fill=tk.X)

        self.validate_button = ttk.Button(
            buttons_frame,
            text="✓ Valida Licenza",
            command=self.validate_license,
            style='Accent.TButton'
        )
        self.validate_button.pack(side=tk.LEFT)

        # Spinner per validazione in corso
        self.spinner_label = ttk.Label(buttons_frame, text="", font=('Arial', 10))
        self.spinner_label.pack(side=tk.LEFT, padx=(10, 0))

        # ===== STATUS MESSAGE =====
        self.status_label = ttk.Label(
            main_frame,
            text="",
            font=('Arial', 10),
            foreground='red'
        )
        self.status_label.pack(fill=tk.X, pady=(0, 15))

        # ===== RICHIEDI LICENZA =====
        request_frame = ttk.LabelFrame(main_frame, text="📧 Non hai una licenza?", padding=(15, 20))
        request_frame.pack(fill=tk.X, pady=(0, 15))

        ttk.Label(
            request_frame,
            text="Genera la tua licenza gratuita istantaneamente:",
            font=('Arial', 10, 'bold')
        ).pack(anchor=tk.W, pady=(0, 10))

        # Form generazione licenza
        form_frame = ttk.Frame(request_frame)
        form_frame.pack(fill=tk.X, pady=(0, 12))

        # Nome
        ttk.Label(form_frame, text="Nome:", font=('Arial', 9)).grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.nome_entry = ttk.Entry(form_frame, width=25)
        self.nome_entry.grid(row=0, column=1, sticky=tk.W, padx=(5, 0), pady=(0, 5))

        # Cognome
        ttk.Label(form_frame, text="Cognome:", font=('Arial', 9)).grid(row=1, column=0, sticky=tk.W, pady=(0, 5))
        self.cognome_entry = ttk.Entry(form_frame, width=25)
        self.cognome_entry.grid(row=1, column=1, sticky=tk.W, padx=(5, 0), pady=(0, 5))

        # Email
        ttk.Label(form_frame, text="Email:", font=('Arial', 9)).grid(row=2, column=0, sticky=tk.W)
        self.email_entry = ttk.Entry(form_frame, width=25)
        self.email_entry.grid(row=2, column=1, sticky=tk.W, padx=(5, 0))

        # Bottone genera licenza
        ttk.Button(
            request_frame,
            text="⚡ Genera Licenza Gratuita",
            command=self.generate_license_auto,
            style='Accent.TButton',
            width=30
        ).pack(anchor=tk.W, pady=(0, 10))

        # Separator
        ttk.Separator(request_frame, orient='horizontal').pack(fill=tk.X, pady=(0, 10))

        ttk.Label(
            request_frame,
            text="Oppure richiedi via email:",
            font=('Arial', 9),
            foreground='gray'
        ).pack(anchor=tk.W, pady=(0, 8))

        ttk.Button(
            request_frame,
            text="📨 Contatta via Email",
            command=self.show_request_license_info,
            width=30
        ).pack(anchor=tk.W)

        # ===== FOOTER =====
        footer_frame = ttk.Frame(main_frame)
        footer_frame.pack(fill=tk.X, pady=(15, 0), side=tk.BOTTOM)

        ttk.Label(
            footer_frame,
            text="© 2025 Luca Mercatanti - https://mercatanti.com",
            font=('Arial', 9),
            foreground='gray'
        ).pack(side=tk.LEFT)

        ttk.Button(
            footer_frame,
            text="❌ Esci",
            command=self.exit_application
        ).pack(side=tk.RIGHT)

    def generate_license_auto(self):
        """Genera automaticamente una licenza gratuita"""
        nome = self.nome_entry.get().strip()
        cognome = self.cognome_entry.get().strip()
        email = self.email_entry.get().strip()

        # Validazione input
        if not nome:
            messagebox.showwarning(
                "Nome Mancante",
                "Inserisci il tuo nome",
                parent=self.dialog
            )
            self.nome_entry.focus()
            return

        if not cognome:
            messagebox.showwarning(
                "Cognome Mancante",
                "Inserisci il tuo cognome",
                parent=self.dialog
            )
            self.cognome_entry.focus()
            return

        if not email:
            messagebox.showwarning(
                "Email Mancante",
                "Inserisci la tua email",
                parent=self.dialog
            )
            self.email_entry.focus()
            return

        # Validazione email semplice
        if '@' not in email or '.' not in email.split('@')[-1]:
            messagebox.showwarning(
                "Email Non Valida",
                "Inserisci un'email valida (es. nome@esempio.com)",
                parent=self.dialog
            )
            self.email_entry.focus()
            return

        # Genera licenza tramite API
        self.status_label.config(text="⚡ Generazione licenza in corso...", foreground='blue')

        try:
            import requests
            import platform

            payload = {
                'action': 'generate_license',
                'nome': nome,
                'cognome': cognome,
                'email': email,
                'hardware_id': self.license_manager.get_hardware_id(),
                'hostname': platform.node(),
                'os': f"{platform.system()} {platform.release()}"
            }

            response = requests.post(
                self.license_manager.api_url,
                json=payload,
                timeout=10
            )

            result = response.json()

            if result.get('success'):
                # Licenza generata con successo (o trovata esistente per email)
                license_key = result.get('license_key')
                message = result.get('message')

                self.status_label.config(text=f"✓ {message}", foreground='green')

                # Inserisci automaticamente la licenza nel campo
                self.license_entry.delete(0, tk.END)
                self.license_entry.insert(0, license_key)

                # Mostra messaggio successo
                messagebox.showinfo(
                    "Licenza Pronta!",
                    f"{message}\n\n"
                    f"Chiave: {license_key}\n\n"
                    f"Clicca 'Valida Licenza' per attivarla.",
                    parent=self.dialog
                )

                # Focus sul bottone valida
                self.validate_button.focus()

            else:
                # Errore generazione
                error_msg = result.get('message', 'Errore sconosciuto')

                # Caso speciale: PC ha già generato una licenza
                if 'già generato una licenza' in error_msg:
                    existing_license = result.get('existing_license', '')
                    existing_email = result.get('existing_email', '')

                    self.status_label.config(text="⚠️ PC già utilizzato per generazione", foreground='orange')

                    # Mostra dialog con licenza esistente
                    response = messagebox.askyesno(
                        "Licenza Già Generata",
                        f"Questo PC ha già generato una licenza!\n\n"
                        f"Email associata: {existing_email}\n"
                        f"Chiave: {existing_license[:20]}...\n\n"
                        f"Vuoi usare la licenza esistente?",
                        parent=self.dialog
                    )

                    if response:
                        # Utente vuole usare la licenza esistente
                        self.license_entry.delete(0, tk.END)
                        self.license_entry.insert(0, existing_license)
                        self.status_label.config(text="✓ Licenza esistente caricata", foreground='green')
                        self.validate_button.focus()
                    else:
                        # Utente rifiuta, mostra opzione email
                        messagebox.showinfo(
                            "Richiesta Manuale",
                            "Se hai perso la tua licenza o vuoi generarne una nuova,\n"
                            "contatta l'amministratore via email usando il bottone\n"
                            "'📨 Contatta via Email' qui sotto.",
                            parent=self.dialog
                        )
                else:
                    # Altri errori
                    self.status_label.config(text=f"✗ {error_msg}", foreground='red')

                    messagebox.showerror(
                        "Errore Generazione",
                        f"Impossibile generare la licenza.\n\n{error_msg}",
                        parent=self.dialog
                    )

        except requests.exceptions.Timeout:
            self.status_label.config(text="✗ Timeout connessione", foreground='red')
            messagebox.showerror(
                "Errore Connessione",
                "Timeout durante la generazione della licenza.\nRiprova tra qualche istante.",
                parent=self.dialog
            )

        except Exception as e:
            self.status_label.config(text=f"✗ Errore: {str(e)}", foreground='red')
            messagebox.showerror(
                "Errore",
                f"Errore durante la generazione:\n{str(e)}",
                parent=self.dialog
            )

    def validate_license(self):
        """Valida la licenza inserita"""
        if self.is_validating:
            return

        license_key = self.license_entry.get().strip()

        if not license_key:
            messagebox.showwarning(
                "Licenza Mancante",
                "Inserisci una chiave di licenza valida",
                parent=self.dialog
            )
            return

        # Avvia validazione in thread separato
        self.is_validating = True
        self.validate_button.config(state='disabled')
        self.license_entry.config(state='disabled')
        self.status_label.config(text="⏳ Validazione in corso...", foreground='blue')

        thread = threading.Thread(target=self._validate_thread, args=(license_key,))
        thread.daemon = True
        thread.start()

        # Avvia controllo periodico della coda risultati
        self._check_result_queue()

    def _validate_thread(self, license_key):
        """Thread per validazione online (non blocca UI)"""
        try:
            # Valida online
            result = self.license_manager.validate_license_online(license_key)

            # Metti il risultato nella coda (thread-safe)
            self.result_queue.put(('success', license_key, result))

        except Exception as e:
            # Metti l'errore nella coda
            self.result_queue.put(('error', str(e), None))

    def _check_result_queue(self):
        """Controlla periodicamente la coda per risultati dal thread"""
        try:
            # Prova a prendere un risultato dalla coda (non-blocking)
            result_type, data1, data2 = self.result_queue.get_nowait()

            if result_type == 'success':
                license_key, result = data1, data2
                self._handle_validation_result(license_key, result)
            elif result_type == 'error':
                error_msg = data1
                self._handle_validation_error(error_msg)

        except queue.Empty:
            # Nessun risultato ancora, ricontrolla tra 100ms
            if self.is_validating:
                self.dialog.after(100, self._check_result_queue)

    def _handle_validation_result(self, license_key, result):
        """Gestisce il risultato della validazione"""
        self.is_validating = False
        self.validate_button.config(state='normal')
        self.license_entry.config(state='normal')

        if result.get('valid'):
            # Licenza valida!
            self.status_label.config(text="✓ Licenza valida!", foreground='green')

            # Salva localmente
            if self.license_manager.save_license(license_key):
                messagebox.showinfo(
                    "Licenza Attivata",
                    "La tua licenza è stata attivata con successo!\n\n"
                    "L'applicazione si avvierà ora.",
                    parent=self.dialog
                )

                self.license_valid = True

                # Chiudi dialog
                self.dialog.grab_release()
                self.dialog.destroy()
            else:
                messagebox.showerror(
                    "Errore Salvataggio",
                    "Impossibile salvare la licenza localmente.",
                    parent=self.dialog
                )
        else:
            # Licenza non valida
            message = result.get('message', 'Licenza non valida')
            self.status_label.config(text=f"✗ {message}", foreground='red')

            messagebox.showerror(
                "Licenza Non Valida",
                f"La licenza inserita non è valida.\n\n"
                f"Motivo: {message}\n\n"
                f"Verifica di aver inserito correttamente la chiave o richiedi "
                f"una nuova licenza.",
                parent=self.dialog
            )

    def _handle_validation_error(self, error_message):
        """Gestisce errori durante la validazione"""
        self.is_validating = False
        self.validate_button.config(state='normal')
        self.license_entry.config(state='normal')
        self.status_label.config(text=f"✗ Errore: {error_message}", foreground='red')

    def show_request_license_info(self):
        """Mostra dialog con istruzioni per richiedere licenza"""
        request_dialog = tk.Toplevel(self.dialog)
        request_dialog.title("Richiedi Licenza Gratuita")
        request_dialog.geometry("600x450")
        request_dialog.resizable(False, False)

        # Centra
        request_dialog.transient(self.dialog)
        request_dialog.grab_set()

        # Frame principale
        frame = ttk.Frame(request_dialog, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        # Header
        ttk.Label(
            frame,
            text="📧 Richiedi Licenza Gratuita",
            font=('Arial', 14, 'bold')
        ).pack(anchor=tk.W, pady=(0, 15))

        # Istruzioni
        instructions = (
            "Per ricevere gratuitamente la tua licenza personale, "
            "invia una richiesta via email includendo:\n\n"
            "• Nome e Cognome\n"
            "• Motivo utilizzo (opzionale)\n\n"
            "Riceverai la tua chiave di licenza entro 24-48 ore."
        )

        text_widget = tk.Text(
            frame,
            wrap=tk.WORD,
            height=7,
            relief=tk.FLAT,
            bg='#f0f0f0',
            font=('Arial', 10),
            padx=10,
            pady=10
        )
        text_widget.insert('1.0', instructions)
        text_widget.config(state='disabled')
        text_widget.pack(fill=tk.BOTH, pady=(0, 15))

        # Email section
        email_section = ttk.LabelFrame(frame, text="📨 Contatto", padding="15")
        email_section.pack(fill=tk.X, pady=(0, 15))

        ttk.Label(
            email_section,
            text="Invia la tua richiesta a:",
            font=('Arial', 10, 'bold')
        ).pack(anchor=tk.W, pady=(0, 8))

        # Email label
        email_label = tk.Label(
            email_section,
            text="luca.mercatanti@gmail.com",
            font=('Arial', 13, 'bold'),
            foreground='#0066cc',
            bg='#f0f0f0',
            padx=15,
            pady=10,
            relief=tk.RIDGE,
            borderwidth=2,
            cursor='hand2'
        )
        email_label.pack(fill=tk.X, pady=(0, 12))

        # Bottone per aprire client email
        def open_email(event=None):
            subject = "Richiesta Licenza - AI Forensics Report Analyzer"
            body = (
                "Nome e Cognome: [INSERISCI QUI]\n\n"
                "Motivo utilizzo: [OPZIONALE]\n\n"
                "Grazie!"
            )
            mailto_url = f"mailto:luca.mercatanti@gmail.com?subject={subject}&body={body}"
            webbrowser.open(mailto_url)

        # Rendi l'email cliccabile
        email_label.bind('<Button-1>', open_email)

        ttk.Button(
            email_section,
            text="✉️ Apri Client Email",
            command=open_email,
            style='Accent.TButton'
        ).pack(fill=tk.X)

        # Bottone chiudi
        ttk.Button(
            frame,
            text="Chiudi",
            command=request_dialog.destroy
        ).pack(side=tk.BOTTOM)

    def on_close_attempt(self):
        """Gestisce tentativo di chiusura dialog senza licenza valida"""
        result = messagebox.askyesno(
            "Esci dall'Applicazione",
            "Non hai ancora inserito una licenza valida.\n\n"
            "Vuoi uscire dall'applicazione?",
            parent=self.dialog
        )

        if result:
            self.exit_application()

    def exit_application(self):
        """Chiude l'applicazione"""
        # Traccia l'uscita senza licenza
        self._track_no_license_exit()

        self.dialog.grab_release()
        self.dialog.destroy()
        self.parent.quit()

    def _track_no_license_exit(self):
        """Invia telemetria quando utente esce senza inserire licenza"""
        try:
            import requests
            import platform

            payload = {
                'action': 'track_no_license',
                'hardware_id': self.license_manager.get_hardware_id(),
                'hostname': platform.node(),
                'os': f"{platform.system()} {platform.release()}"
            }

            # Timeout breve per non rallentare la chiusura
            requests.post(
                self.license_manager.api_url,
                json=payload,
                timeout=2
            )
        except Exception:
            # Ignora errori - non vogliamo bloccare la chiusura
            pass

    def is_valid(self):
        """Restituisce se la licenza è stata validata"""
        return self.license_valid


# Test standalone
if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()  # Nascondi finestra principale

    lm = LicenseManager()
    dialog = LicenseDialog(root, lm)

    root.wait_window(dialog.dialog)

    if dialog.is_valid():
        print("Licenza valida!")
    else:
        print("Licenza non valida o utente uscito")

    root.destroy()
