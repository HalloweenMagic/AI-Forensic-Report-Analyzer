"""
Dialog di benvenuto con informazioni preliminari sull'applicazione
Mostra logo, testo informativo e checkbox "Non mostrare più"

© 2025 Luca Mercatanti - https://mercatanti.com
"""

import tkinter as tk
from tkinter import ttk
import json
import os
import webbrowser
from pathlib import Path

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class WelcomeDialog:
    PREFERENCES_FILE = ".app_preferences"

    def __init__(self, parent, logo_path="logo.jpg", force_show=False):
        """
        Inizializza il dialog di benvenuto

        Args:
            parent: Finestra parent
            logo_path: Path al file logo (default: logo.jpg)
            force_show: Se True, mostra sempre il dialog (per menu Aiuto)
        """
        self.parent = parent
        self.logo_path = logo_path
        self.force_show = force_show
        self.dont_show_again = tk.BooleanVar(value=False)

        # Sistema multi-pagina
        self.current_page = 1
        self.total_pages = 3

        # Dimensioni per ogni pagina
        self.page_dimensions = {
            1: (750, 1030),   # Pagina 1
            2: (750, 1230),   # Pagina 2
            3: (750, 1200)    # Pagina 3
        }

        # Crea dialog modale
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Informazioni preliminari")
        # Inizia con dimensioni della pagina 1
        width, height = self.page_dimensions[1]
        self.dialog.geometry(f"{width}x{height}")
        self.center_dialog(width, height)
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

    def resize_dialog_for_page(self, page_number):
        """
        Ridimensiona il dialog in base alla pagina visualizzata

        Args:
            page_number: Numero della pagina (1 o 2)
        """
        if page_number in self.page_dimensions:
            width, height = self.page_dimensions[page_number]
            self.center_dialog(width, height)

    def setup_ui(self):
        """Configura l'interfaccia del dialog"""

        # Frame principale con scrollbar
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # === LOGO ===
        logo_frame = ttk.Frame(main_frame)
        logo_frame.pack(pady=(0, 20))

        if PIL_AVAILABLE and os.path.exists(self.logo_path):
            try:
                # Carica e ridimensiona logo
                image = Image.open(self.logo_path)
                image = image.resize((350, 350), Image.Resampling.LANCZOS)
                self.logo_photo = ImageTk.PhotoImage(image)

                logo_label = ttk.Label(logo_frame, image=self.logo_photo)
                logo_label.pack()
            except Exception as e:
                # Fallback: mostra placeholder
                ttk.Label(logo_frame, text="[Logo]",
                         font=('Arial', 24, 'bold')).pack()
        else:
            # Fallback se PIL non disponibile o logo non trovato
            ttk.Label(logo_frame, text="AI Forensics Report Analyzer",
                     font=('Arial', 16, 'bold')).pack()

        # === CONTENITORE CONTENUTO PAGINE ===
        self.content_frame = ttk.Frame(main_frame)
        self.content_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))

        # Crea il contenuto della prima pagina
        self.create_page_content(self.current_page)

        # === NAVIGAZIONE FRECCE ===
        nav_frame = ttk.Frame(main_frame)
        nav_frame.pack(pady=(10, 20))

        # Freccia sinistra
        self.btn_prev = ttk.Button(nav_frame, text="← Indietro",
                                   command=self.prev_page, width=15)
        self.btn_prev.pack(side=tk.LEFT, padx=10)

        # Indicatore pagina
        self.page_label = ttk.Label(nav_frame, text=f"Pagina {self.current_page} di {self.total_pages}",
                                    font=('Arial', 10))
        self.page_label.pack(side=tk.LEFT, padx=20)

        # Freccia destra
        self.btn_next = ttk.Button(nav_frame, text="Avanti →",
                                   command=self.next_page, width=15)
        self.btn_next.pack(side=tk.LEFT, padx=10)

        # Aggiorna stato pulsanti
        self.update_navigation_buttons()

        # === CHECKBOX ===
        if not self.force_show:  # Mostra checkbox solo se non è chiamato dal menu
            checkbox_frame = ttk.Frame(main_frame)
            checkbox_frame.pack(pady=(10, 20))

            ttk.Checkbutton(checkbox_frame,
                          text="Non mostrare più questo messaggio",
                          variable=self.dont_show_again).pack()

        # === PULSANTE ===
        button_frame = ttk.Frame(main_frame)
        button_frame.pack()

        ttk.Button(button_frame, text="Ho capito",
                  command=self.close_dialog, width=20).pack()

    def create_page_content(self, page_number):
        """
        Crea il contenuto della pagina specificata

        Args:
            page_number: Numero della pagina da visualizzare (1, 2 o 3)
        """
        # Pulisci il frame contenuto
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        if page_number == 1:
            self.create_page_1_content()
        elif page_number == 2:
            self.create_page_2_content()
        elif page_number == 3:
            self.create_page_3_content()

    def create_page_1_content(self):
        """Crea il contenuto della pagina 1 (testo informativo originale)"""
        # Creo un Text widget con formattazione
        text_widget = tk.Text(self.content_frame, wrap=tk.WORD, height=25, width=80,
                             font=('Arial', 11), relief=tk.FLAT,
                             bg=self.dialog.cget('bg'), cursor="arrow")
        text_widget.pack(fill=tk.BOTH, expand=True)

        # Configura tag per grassetto
        text_widget.tag_configure("bold", font=('Arial', 11, 'bold'))
        text_widget.tag_configure("link", foreground="blue", underline=True)

        # Inserisci il testo
        text_widget.insert('1.0',
            "AI Forensics Report Analyzer è un tool il cui scopo è quello di analizzare "
            "rapidamente le chat (WhatsApp, WeChat, Telegram, etc…) esportate da sistemi "
            "forensi, senza doversi basare esclusivamente su parole chiave o essere obbligati "
            "a leggere migliaia di messaggi scambiati.\n\n"
            "Lo strumento è in grado di riassumere perfettamente report di ")

        # Grassetto
        start_idx = text_widget.index("insert")
        text_widget.insert('insert', "conversazioni singole (1v1 oppure di gruppo)")
        end_idx = text_widget.index("insert")
        text_widget.tag_add("bold", start_idx, end_idx)

        text_widget.insert('insert',
            " senza particolari accorgimenti. È infatti sufficiente impostare le API del modello "
            "AI che si desidera utilizzare, indicare il file .PDF esportato dallo strumento "
            "forense e lanciare l'analisi.\n\n"
            "Nel caso in cui si volesse importare il ")

        # Grassetto
        start_idx = text_widget.index("insert")
        text_widget.insert('insert', "report completo di TUTTE le chat esportate da uno smartphone")
        end_idx = text_widget.index("insert")
        text_widget.tag_add("bold", start_idx, end_idx)

        text_widget.insert('insert',
            ", è anch'esso possibile, ma a tre condizioni:\n\n"
            "1)  Il riassunto generico che verrà generato potrebbe non contenere tutte le "
            "informazioni essenziali, in quanto, allo stato attuale (Novembre 2025), i LLM "
            "disponibili non sono in grado di elaborare input estremamente grandi. Per tale motivo, "
            "si consiglia di prestare attenzione al riassunto generato e di procedere anche con il "
            "punto 2 qui sotto indicato, per una panoramica più completa.\n\n"
            "2)  Per ovviare al problema del punto di cui sopra è necessario accedere alla funzione "
            "\"Report per chat\".\n"
            "Grazie a questa implementazione, il sistema sarà in grado di identificare ogni "
            "singola chat presente nel report caricato (sia esse 1v1 che di gruppo), creando un "
            "riassunto per ogni singola chat.\n\n"
            "3)  Interrogare i LLM Cloud (come OpenAI) ha un costo e richiede tempo. Non è sempre "
            "intelligente, quindi, caricare tutte le conversazioni WhatsApp/WeChat/Telegram di "
            "un'utente all'interno del sistema, a meno che non sia estremamente necessario. È molto "
            "più efficace esportare le chat esclusivamente dei contatti di interesse e processarli!\n\n"
            "Per ogni dubbio o segnalazione, basta inviare una email a: ")

        # Email cliccabile
        email_start = text_widget.index("insert")
        text_widget.insert('insert', "luca.mercatanti@gmail.com")
        email_end = text_widget.index("insert")
        text_widget.tag_add("link", email_start, email_end)
        text_widget.tag_bind("link", "<Button-1>",
                            lambda e: self.open_email("luca.mercatanti@gmail.com"))
        text_widget.tag_bind("link", "<Enter>",
                            lambda e: text_widget.config(cursor="hand2"))
        text_widget.tag_bind("link", "<Leave>",
                            lambda e: text_widget.config(cursor="arrow"))

        text_widget.insert('insert', " (e non dimenticare di visitare ")

        # Link sito cliccabile
        site_start = text_widget.index("insert")
        text_widget.insert('insert', "mercatanti.com")
        site_end = text_widget.index("insert")
        text_widget.tag_add("link", site_start, site_end)
        # Bind separato per il sito
        text_widget.tag_bind("link", "<Button-1>",
                            lambda e: self.open_website("https://mercatanti.com"), add="+")

        text_widget.insert('insert', " !)")

        # Rendi il text widget non editabile
        text_widget.config(state='disabled')

    def create_page_2_content(self):
        """Crea il contenuto della pagina 2 (Come si usa e Disclaimer)"""
        # Creo un Text widget con formattazione
        text_widget = tk.Text(self.content_frame, wrap=tk.WORD, height=25, width=80,
                             font=('Arial', 11), relief=tk.FLAT,
                             bg=self.dialog.cget('bg'), cursor="arrow")
        text_widget.pack(fill=tk.BOTH, expand=True)

        # Configura tag per formattazione
        text_widget.tag_configure("title", font=('Arial', 14, 'bold'), justify='center')
        text_widget.tag_configure("bold", font=('Arial', 11, 'bold'))
        text_widget.tag_configure("link", foreground="blue", underline=True)

        # === TITOLO: COME SI USA? ===
        text_widget.insert('1.0', "\n")
        title_start = text_widget.index("insert")
        text_widget.insert('insert', "Come si usa?")
        title_end = text_widget.index("insert")
        text_widget.tag_add("title", title_start, title_end)

        text_widget.insert('insert',
            "\n\nPer poter utilizzare il tool è necessario usare le API di un LLM tra: OpenAI (ChatGpt), "
            "Antrophic o modello locale installato usando il software Ollama.\n"
            "Il metodo più veloce per iniziare ad usare il software è quello di utilizzare le API di "
            "OpenAI o Antrophic. Una volta generata la chiave, sarà sufficiente inserirla all'interno del tool.\n\n")

        # === OPENAI ===
        start_idx = text_widget.index("insert")
        text_widget.insert('insert', "OpenAI")
        end_idx = text_widget.index("insert")
        text_widget.tag_add("bold", start_idx, end_idx)

        text_widget.insert('insert', "\n1) Vai su ")

        # Link OpenAI platform
        link_start = text_widget.index("insert")
        text_widget.insert('insert', "https://platform.openai.com")
        link_end = text_widget.index("insert")
        text_widget.tag_add("link", link_start, link_end)
        text_widget.tag_bind("link", "<Button-1>",
                            lambda e: self.open_website("https://platform.openai.com"))
        text_widget.tag_bind("link", "<Enter>",
                            lambda e: text_widget.config(cursor="hand2"))
        text_widget.tag_bind("link", "<Leave>",
                            lambda e: text_widget.config(cursor="arrow"))

        text_widget.insert('insert',
            " e accedi (o crea un account).\n"
            "2) Dal menu apri Dashboard → API keys\n"
            "3) Clicca \"Create new secret key\", assegna un nome e copia la chiave generata: "
            "la vedrai solo una volta\n"
            "4) Verifica di avere il billing/crediti attivi se necessario per l'uso dell'API "
            "(dovrai associare una carta di credito e ricaricare l'account. Puoi iniziare anche "
            "con 10$ per i test)\n\n")

        # === ANTHROPIC ===
        start_idx = text_widget.index("insert")
        text_widget.insert('insert', "Antrophic")
        end_idx = text_widget.index("insert")
        text_widget.tag_add("bold", start_idx, end_idx)

        text_widget.insert('insert', "\n1) Vai su ")

        # Link Anthropic console
        link_start = text_widget.index("insert")
        text_widget.insert('insert', "https://console.anthropic.com")
        link_end = text_widget.index("insert")
        text_widget.tag_add("link", link_start, link_end)
        text_widget.tag_bind("link", "<Button-1>",
                            lambda e: self.open_website("https://console.anthropic.com"), add="+")

        text_widget.insert('insert', " e accedi (o crea un account)\n"
            "2) Dal menu in alto seleziona API Keys oppure vai direttamente su ")

        # Link Anthropic API keys
        link_start = text_widget.index("insert")
        text_widget.insert('insert', "https://console.anthropic.com/settings/keys")
        link_end = text_widget.index("insert")
        text_widget.tag_add("link", link_start, link_end)
        text_widget.tag_bind("link", "<Button-1>",
                            lambda e: self.open_website("https://console.anthropic.com/settings/keys"), add="+")

        text_widget.insert('insert',
            "\n3) Clicca su \"Create Key\", assegna un nome e copia la chiave generata: "
            "non sarà più visibile dopo la creazione\n"
            "4) Associa una carta di credito nella sezione Billing e ricarica l'account\n\n")

        # === OLLAMA ===
        start_idx = text_widget.index("insert")
        text_widget.insert('insert', "Ollama")
        end_idx = text_widget.index("insert")
        text_widget.tag_add("bold", start_idx, end_idx)

        text_widget.insert('insert',
            "\nSe puoi far girare un modello di AI in locale, non hai bisogno di spiegazioni su come usarlo!\n\n"
            "NB: Utilizzare le API ha un costo, seppur minimo.\n"
            "Il software calcola automaticamente il costo medio di ogni singola analisi.\n"
            "Analizzare una singola chat ha generalmente un costo inferiore a 1$.\n\n\n")

        # === TITOLO: DISCLAIMER ===
        title_start = text_widget.index("insert")
        text_widget.insert('insert', "Disclaimer")
        title_end = text_widget.index("insert")
        text_widget.tag_add("title", title_start, title_end)

        text_widget.insert('insert',
            "\n\nIl presente tool è fornito \"così com'è\", ")

        # Grassetto sul testo del disclaimer
        start_idx = text_widget.index("insert")
        text_widget.insert('insert', "senza alcuna garanzia di corretto funzionamento o affidabilità dei risultati.")
        end_idx = text_widget.index("insert")
        text_widget.tag_add("bold", start_idx, end_idx)

        text_widget.insert('insert',
            "\nIl software integra modelli di intelligenza artificiale e processi automatizzati la cui logica "
            "interna non è completamente nota, pertanto il comportamento può variare in modo imprevedibile.")

        # Rendi il text widget non editabile
        text_widget.config(state='disabled')

    def create_page_3_content(self):
        """Crea il contenuto della pagina 3 (Come funziona - dettaglio tecnico)"""
        # Creo un Text widget con formattazione
        text_widget = tk.Text(self.content_frame, wrap=tk.WORD, height=25, width=80,
                             font=('Arial', 11), relief=tk.FLAT,
                             bg=self.dialog.cget('bg'), cursor="arrow")
        text_widget.pack(fill=tk.BOTH, expand=True)

        # Configura tag per formattazione
        text_widget.tag_configure("title", font=('Arial', 14, 'bold'), justify='center')
        text_widget.tag_configure("bold", font=('Arial', 11, 'bold'))

        # === TITOLO: COME FUNZIONA? ===
        text_widget.insert('1.0', "\n")
        title_start = text_widget.index("insert")
        text_widget.insert('insert', "Come funziona?")
        title_end = text_widget.index("insert")
        text_widget.tag_add("title", title_start, title_end)

        text_widget.insert('insert',
            "\n\nLa seguente sezione descrive in modo sintetico il funzionamento interno dello strumento. "
            "Non è necessario che l'utente conosca nel dettaglio questi processi: la spiegazione è fornita "
            "unicamente per trasparenza.\n\n")

        # === 1 - CARICAMENTO DEL REPORT ===
        start_idx = text_widget.index("insert")
        text_widget.insert('insert', "1 – Caricamento del report")
        end_idx = text_widget.index("insert")
        text_widget.tag_add("bold", start_idx, end_idx)

        text_widget.insert('insert',
            "\nQuando viene caricato un file PDF, il programma esegue una scansione preliminare per stimare "
            "parametri chiave come il numero di pagine, la lunghezza media del testo e la quantità prevista "
            "di segmenti (\"chunk\") che verranno generati. Successivamente, il sistema procede all'estrazione "
            "completa del testo dal PDF, pagina per pagina.\n\n")

        # === 2 - SUDDIVISIONE IN CHUNK ===
        start_idx = text_widget.index("insert")
        text_widget.insert('insert', "2 – Suddivisione in chunk")
        end_idx = text_widget.index("insert")
        text_widget.tag_add("bold", start_idx, end_idx)

        text_widget.insert('insert',
            "\nIl testo estratto viene poi suddiviso in blocchi di testo (\"chunk\"), necessari per consentire "
            "l'elaborazione da parte dei modelli di intelligenza artificiale, che possono gestire solo una quantità "
            "limitata di contenuto per singola richiesta.\n"
            "Il programma segmenta quindi il documento in porzioni di dimensione configurabile (di default 15.000 "
            "caratteri), evitando di spezzare una pagina a metà per preservare la coerenza del contesto. Ogni chunk "
            "viene infine salvato su disco in formato TXT o JSON, a seconda della scelta dell'utente.\n\n")

        # === 3 - ANALISI TRAMITE AI ===
        start_idx = text_widget.index("insert")
        text_widget.insert('insert', "3 – Analisi tramite AI")
        end_idx = text_widget.index("insert")
        text_widget.tag_add("bold", start_idx, end_idx)

        text_widget.insert('insert',
            "\nCompletata la fase di segmentazione, il software avvia l'analisi automatizzata. Ogni chunk viene "
            "inviato singolarmente al modello AI selezionato (OpenAI, Anthropic o Ollama locale), insieme a un "
            "prompt di analisi.\n"
            "Il prompt può essere di tipo forense generico, volto a identificare pattern sospetti, eventi rilevanti, "
            "allegati o messaggi di particolare interesse, oppure personalizzato, basato su template salvati per "
            "specifici casi d'uso (ad esempio: \"cerca riferimenti a sostanze\", \"identifica minacce\", \"riconosci "
            "linguaggio ostile\").\n"
            "Durante questa fase il sistema applica un rate limiting automatico, regolando in modo intelligente "
            "l'intervallo tra una richiesta e l'altra per non superare i limiti di utilizzo del provider "
            "(TPM – Tokens Per Minute).\n\n")

        # === 4 - GENERAZIONE DEL REPORT ===
        start_idx = text_widget.index("insert")
        text_widget.insert('insert', "4 – Generazione del report")
        end_idx = text_widget.index("insert")
        text_widget.tag_add("bold", start_idx, end_idx)

        text_widget.insert('insert',
            "\nTerminata l'analisi dei singoli chunk, il programma elabora un riassunto finale che integra e "
            "sintetizza i risultati parziali. A seconda delle dimensioni del documento, viene creato automaticamente "
            "un report HTML multipagina con un layout professionale ispirato all'interfaccia di WhatsApp, progettato "
            "per facilitare la consultazione e la presentazione dei risultati.")

        # Rendi il text widget non editabile
        text_widget.config(state='disabled')

    def next_page(self):
        """Passa alla pagina successiva"""
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.resize_dialog_for_page(self.current_page)
            self.create_page_content(self.current_page)
            self.update_navigation_buttons()

    def prev_page(self):
        """Passa alla pagina precedente"""
        if self.current_page > 1:
            self.current_page -= 1
            self.resize_dialog_for_page(self.current_page)
            self.create_page_content(self.current_page)
            self.update_navigation_buttons()

    def update_navigation_buttons(self):
        """Aggiorna lo stato dei pulsanti di navigazione"""
        # Disabilita freccia sinistra se siamo alla prima pagina
        if self.current_page == 1:
            self.btn_prev.config(state='disabled')
        else:
            self.btn_prev.config(state='normal')

        # Disabilita freccia destra se siamo all'ultima pagina
        if self.current_page == self.total_pages:
            self.btn_next.config(state='disabled')
        else:
            self.btn_next.config(state='normal')

        # Aggiorna label pagina
        self.page_label.config(text=f"Pagina {self.current_page} di {self.total_pages}")

    def open_email(self, email):
        """Apre il client email predefinito"""
        webbrowser.open(f"mailto:{email}")

    def open_website(self, url):
        """Apre il sito web nel browser predefinito"""
        webbrowser.open(url)

    def close_dialog(self):
        """Chiude il dialog e salva le preferenze"""
        if not self.force_show and self.dont_show_again.get():
            self.save_preference(show_welcome=False)

        self.dialog.destroy()

    @staticmethod
    def should_show():
        """
        Verifica se il dialog deve essere mostrato

        Returns:
            bool: True se deve essere mostrato, False altrimenti
        """
        prefs_file = Path(WelcomeDialog.PREFERENCES_FILE)

        if not prefs_file.exists():
            return True  # Primo avvio, mostra sempre

        try:
            with open(prefs_file, 'r', encoding='utf-8') as f:
                prefs = json.load(f)
                return prefs.get('show_welcome', True)
        except Exception:
            return True  # In caso di errore, mostra comunque

    @staticmethod
    def save_preference(show_welcome=False):
        """
        Salva la preferenza dell'utente

        Args:
            show_welcome: Se True, mostra il dialog all'avvio
        """
        prefs_file = Path(WelcomeDialog.PREFERENCES_FILE)

        try:
            # Leggi preferenze esistenti
            if prefs_file.exists():
                with open(prefs_file, 'r', encoding='utf-8') as f:
                    prefs = json.load(f)
            else:
                prefs = {}

            # Aggiorna
            prefs['show_welcome'] = show_welcome

            # Salva
            with open(prefs_file, 'w', encoding='utf-8') as f:
                json.dump(prefs, f, indent=4)

        except Exception as e:
            print(f"Errore salvataggio preferenze: {e}")
