"""
Update Dialog - Notifica nuova versione disponibile
Mostra dialog modale con opzioni download automatico/manuale

© 2025 Luca Mercatanti - https://mercatanti.com
"""

import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser
import threading
import requests
from pathlib import Path
import os
import subprocess


class UpdateDialog:
    def __init__(self, parent, update_info, version_checker):
        """
        Dialog modale per notifica aggiornamento

        Args:
            parent: Finestra parent
            update_info: Dict con info versione (da VersionChecker)
            version_checker: Istanza VersionChecker
        """
        self.parent = parent
        self.update_info = update_info
        self.version_checker = version_checker
        self.download_path = None
        self.is_downloading = False

        # Dialog modale
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("🎉 Nuova Versione Disponibile!")
        self.dialog.geometry("700x600")
        self.center_dialog()
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self.setup_ui()

    def center_dialog(self):
        """Centra dialog sullo schermo"""
        self.dialog.update_idletasks()
        screen_width = self.dialog.winfo_screenwidth()
        screen_height = self.dialog.winfo_screenheight()
        x = (screen_width - 700) // 2
        y = (screen_height - 600) // 2
        self.dialog.geometry(f'700x600+{x}+{y}')

    def setup_ui(self):
        """Crea interfaccia dialog"""
        main_frame = ttk.Frame(self.dialog, padding="25")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ===== HEADER =====
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 25))

        title_label = ttk.Label(
            header_frame,
            text="🎉 Nuova Versione Disponibile!",
            font=('Arial', 18, 'bold'),
            foreground='#28a745'
        )
        title_label.pack(anchor=tk.W)

        subtitle_label = ttk.Label(
            header_frame,
            text="È disponibile un aggiornamento dell'applicazione",
            font=('Arial', 11),
            foreground='#6c757d'
        )
        subtitle_label.pack(anchor=tk.W, pady=(5, 0))

        # ===== INFO VERSIONE =====
        info_frame = ttk.LabelFrame(main_frame, text="📦 Dettagli Versione", padding="20")
        info_frame.pack(fill=tk.X, pady=(0, 20))

        # Versione attuale
        current_frame = ttk.Frame(info_frame)
        current_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(
            current_frame,
            text="Versione Attuale:",
            font=('Arial', 11, 'bold')
        ).pack(side=tk.LEFT)

        ttk.Label(
            current_frame,
            text=self.version_checker.current_version,
            font=('Arial', 11)
        ).pack(side=tk.LEFT, padx=(10, 0))

        # Nuova versione
        new_frame = ttk.Frame(info_frame)
        new_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(
            new_frame,
            text="Nuova Versione:",
            font=('Arial', 11, 'bold')
        ).pack(side=tk.LEFT)

        ttk.Label(
            new_frame,
            text=self.update_info['latest_version'],
            font=('Arial', 11, 'bold'),
            foreground='#28a745'
        ).pack(side=tk.LEFT, padx=(10, 0))

        # Data rilascio
        date_frame = ttk.Frame(info_frame)
        date_frame.pack(fill=tk.X)

        ttk.Label(
            date_frame,
            text="Rilasciata il:",
            font=('Arial', 10)
        ).pack(side=tk.LEFT)

        ttk.Label(
            date_frame,
            text=self.update_info['release_date'],
            font=('Arial', 10)
        ).pack(side=tk.LEFT, padx=(10, 0))

        # ===== CHANGELOG (solo se presente) =====
        if self.update_info.get('changelog'):
            changelog_frame = ttk.LabelFrame(main_frame, text="📋 Novità", padding="15")
            changelog_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))

            changelog_text = tk.Text(
                changelog_frame,
                wrap=tk.WORD,
                height=8,
                font=('Arial', 10),
                relief=tk.FLAT,
                bg='#f8f9fa',
                state='normal',
                cursor="arrow"
            )
            changelog_text.pack(fill=tk.BOTH, expand=True)
            changelog_text.insert('1.0', self.update_info['changelog'])
            changelog_text.config(state='disabled')

        # ===== PROGRESS BAR (nascosta inizialmente) =====
        self.progress_frame = ttk.Frame(main_frame)
        self.progress_frame.pack(fill=tk.X, pady=(0, 15))
        self.progress_frame.pack_forget()  # Nascondi inizialmente

        self.progress_label = ttk.Label(
            self.progress_frame,
            text="Download in corso...",
            font=('Arial', 10)
        )
        self.progress_label.pack(anchor=tk.W)

        self.progress_bar = ttk.Progressbar(
            self.progress_frame,
            mode='determinate',
            length=500
        )
        self.progress_bar.pack(fill=tk.X, pady=(5, 0))

        self.progress_status = ttk.Label(
            self.progress_frame,
            text="0%",
            font=('Arial', 9)
        )
        self.progress_status.pack(anchor=tk.E, pady=(5, 0))

        # ===== PULSANTI =====
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        # Pulsante Download Automatico
        self.download_auto_button = ttk.Button(
            button_frame,
            text="⬇️ Scarica e Installa",
            command=self.download_and_install,
            style='Accent.TButton',
            width=24
        )
        self.download_auto_button.pack(side=tk.LEFT, padx=(0, 10))

        # Pulsante Download Manuale
        ttk.Button(
            button_frame,
            text="🌐 Download Manuale",
            command=self.open_download_page,
            width=24
        ).pack(side=tk.LEFT, padx=(0, 10))

        # Pulsante Ignora
        ttk.Button(
            button_frame,
            text="🔕 Ignora Questa Versione",
            command=self.ignore_version,
            width=28
        ).pack(side=tk.LEFT)

        # Pulsante Chiudi
        ttk.Button(
            button_frame,
            text="❌ Chiudi",
            command=self.close_dialog
        ).pack(side=tk.RIGHT)

    def download_and_install(self):
        """Download automatico e installazione"""
        if self.is_downloading:
            return

        self.is_downloading = True
        self.download_auto_button.config(state='disabled')
        self.progress_frame.pack(fill=tk.X, pady=(0, 15))

        # Avvia download in thread
        thread = threading.Thread(target=self._download_file, daemon=True)
        thread.start()

    def _download_file(self):
        """Scarica file in background (thread separato)"""
        try:
            url = self.update_info['download_url']
            filename = url.split('/')[-1]
            download_path = Path.home() / "Downloads" / filename

            self.dialog.after(0, self.progress_label.config, {'text': f"Scaricamento {filename}..."})

            response = requests.get(url, stream=True, timeout=60)
            total_size = int(response.headers.get('content-length', 0))

            downloaded = 0

            with open(download_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

                        # Aggiorna progress bar
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            self.dialog.after(0, self._update_progress, percent)

            self.download_path = download_path

            # Download completato
            self.dialog.after(0, self._download_complete)

        except Exception as e:
            self.dialog.after(0, self._download_error, str(e))

    def _update_progress(self, percent):
        """Aggiorna progress bar (main thread)"""
        self.progress_bar['value'] = percent
        self.progress_status.config(text=f"{percent:.1f}%")

    def _download_complete(self):
        """Download completato con successo"""
        self.is_downloading = False
        self.progress_label.config(text="✅ Download completato!")
        self.progress_bar['value'] = 100
        self.progress_status.config(text="100%")

        response = messagebox.askyesno(
            "Download Completato",
            f"Download completato con successo!\n\n"
            f"File salvato in:\n{self.download_path}\n\n"
            f"Vuoi installare ora?\n"
            f"(L'applicazione verrà chiusa)",
            parent=self.dialog
        )

        if response:
            self._install_update()
        else:
            messagebox.showinfo(
                "Installazione Manuale",
                f"Puoi installare l'aggiornamento manualmente eseguendo:\n{self.download_path}",
                parent=self.dialog
            )

    def _download_error(self, error_msg):
        """Errore durante download"""
        self.is_downloading = False
        self.progress_frame.pack_forget()
        self.download_auto_button.config(state='normal')

        messagebox.showerror(
            "Errore Download",
            f"Errore durante il download:\n{error_msg}\n\n"
            f"Usa il pulsante 'Download Manuale' per scaricare dal browser.",
            parent=self.dialog
        )

    def _install_update(self):
        """Avvia installazione e chiude app"""
        try:
            # Apri installer
            if os.name == 'nt':  # Windows
                os.startfile(str(self.download_path))
            else:  # Linux/Mac
                subprocess.Popen(['xdg-open', str(self.download_path)])

            # Chiudi applicazione
            self.parent.quit()

        except Exception as e:
            messagebox.showerror(
                "Errore",
                f"Impossibile avviare installer:\n{e}\n\n"
                f"Esegui manualmente: {self.download_path}",
                parent=self.dialog
            )

    def open_download_page(self):
        """Apri pagina download nel browser (GitHub Release)"""
        webbrowser.open(self.update_info['download_url'])

        messagebox.showinfo(
            "Download Manuale",
            "Pagina download aperta nel browser.\n\n"
            "Dopo il download, chiudi l'applicazione e installa la nuova versione.",
            parent=self.dialog
        )

    def ignore_version(self):
        """Ignora questa versione"""
        response = messagebox.askyesno(
            "Ignora Versione",
            f"Vuoi ignorare la versione {self.update_info['latest_version']}?\n\n"
            f"Non riceverai più notifiche per questa specifica versione.",
            parent=self.dialog
        )

        if response:
            self.version_checker.ignore_version(self.update_info['latest_version'])
            messagebox.showinfo(
                "Versione Ignorata",
                f"La versione {self.update_info['latest_version']} è stata ignorata.\n\n"
                f"Riceverai notifiche solo per versioni successive.",
                parent=self.dialog
            )
            self.dialog.destroy()

    def close_dialog(self):
        """Chiudi dialog"""
        self.dialog.destroy()


# Test standalone
if __name__ == "__main__":
    from version_checker import VersionChecker

    root = tk.Tk()
    root.withdraw()  # Nascondi finestra principale

    # Simula info update
    fake_update_info = {
        'update_available': True,
        'latest_version': '4.0.0',
        'release_date': '2025-11-15',
        'download_url': 'https://github.com/user/repo/releases/download/v4.0.0/app.exe',
        'changelog': '- Nuova funzionalità X\n- Miglioramento performance Y\n- Fix bug critici Z'
    }

    checker = VersionChecker(
        api_url="https://www.winesommelier.it/licenza/api.php",
        current_version="3.4.0"
    )

    dialog = UpdateDialog(root, fake_update_info, checker)

    root.mainloop()
