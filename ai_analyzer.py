"""
Modulo per l'analisi AI dei chunk di testo
Supporta OpenAI, Anthropic e Modelli Locali (Ollama)

© 2025 Luca Mercatanti - https://mercatanti.com
"""

from openai import OpenAI
import anthropic
import os
import time
import base64
import mimetypes
from pathlib import Path
import requests

class AIAnalyzer:
    def __init__(self, api_key, model="gpt-4o", use_local=False, local_url="http://localhost:11434"):
        self.api_key = api_key
        self.model = model
        self.use_local = use_local
        self.local_url = local_url
        self.is_anthropic = "claude" in model.lower()

        if self.use_local:
            # Modalità modello locale (Ollama)
            self.client = None
        elif self.is_anthropic:
            self.client = anthropic.Anthropic(api_key=api_key)
        else:
            self.client = OpenAI(api_key=api_key)

    def _get_hierarchical_threshold(self):
        """Carica la soglia gerarchica dalle impostazioni utente"""
        import json
        from pathlib import Path

        preferences_file = Path(".user_preferences.json")

        # Default: 30 chunk
        default_threshold = 30

        if not preferences_file.exists():
            return default_threshold

        try:
            with open(preferences_file, 'r', encoding='utf-8') as f:
                prefs = json.load(f)
                return prefs.get('hierarchical_threshold', default_threshold)
        except:
            return default_threshold

    def _get_provider_type(self):
        """
        Rileva il tipo di provider in base al modello e alla configurazione

        Returns:
            str: 'local', 'openai', o 'anthropic'
        """
        if self.use_local:
            return 'local'
        elif self.is_anthropic or 'claude' in self.model.lower():
            return 'anthropic'
        else:
            return 'openai'

    def _calculate_rate_limit_delay(self, log_callback=None):
        """
        Calcola il delay necessario tra richieste API in base al provider e limiti TPM configurati

        Returns:
            float: secondi di delay da attendere tra una richiesta e l'altra
        """
        import json
        from pathlib import Path

        # Determina il provider
        provider = self._get_provider_type()

        # MODELLI LOCALI: Nessun rate limiting necessario!
        if provider == 'local':
            if log_callback:
                log_callback(f"   ⚙️ Modello locale rilevato: rate limiting disabilitato")
            return 0.5  # Delay minimo per non sovraccaricare il sistema locale

        preferences_file = Path(".user_preferences.json")

        # Default TPM basati sul provider
        if provider == 'anthropic':
            # Anthropic Tier 1: 40,000 TPM input (più generoso di OpenAI)
            default_tpm_limit = 40000
        else:  # openai
            # OpenAI Tier 1: 30,000 TPM
            default_tpm_limit = 30000

        # Carica TPM dalle preferenze utente
        if preferences_file.exists():
            try:
                with open(preferences_file, 'r', encoding='utf-8') as f:
                    prefs = json.load(f)
                    # Cerca chiave specifica per provider, altrimenti usa default
                    tpm_key = f'{provider}_max_tpm_limit'
                    tpm_limit = prefs.get(tpm_key, prefs.get('max_tpm_limit', default_tpm_limit))
            except:
                tpm_limit = default_tpm_limit
        else:
            tpm_limit = default_tpm_limit

        # Stima token per chunk: ~1000 input + 500 output = 1500 totali
        estimated_tokens_per_chunk = 1500

        # Calcola max chunk/minuto consentiti
        max_chunks_per_minute = tpm_limit / estimated_tokens_per_chunk

        # Calcola delay in secondi (60 secondi / max_chunks_per_minute)
        delay_seconds = 60.0 / max_chunks_per_minute

        # Aggiungi margine di sicurezza del 20%
        delay_seconds *= 1.2

        # Log informativo con nome provider
        provider_name = {
            'openai': 'OpenAI',
            'anthropic': 'Anthropic Claude',
            'local': 'Locale'
        }.get(provider, provider)

        if log_callback:
            log_callback(f"   ⚙️ Rate Limiting ({provider_name}): TPM={tpm_limit:,}, Delay={delay_seconds:.1f}s tra richieste")

        return delay_seconds

    def load_image_as_base64(self, image_path):
        """Carica un'immagine e la converte in base64"""
        try:
            with open(image_path, 'rb') as image_file:
                image_data = image_file.read()
                base64_image = base64.b64encode(image_data).decode('utf-8')

                # Determina il mime type
                mime_type, _ = mimetypes.guess_type(image_path)
                if not mime_type:
                    # Fallback based on extension
                    ext = os.path.splitext(image_path)[1].lower()
                    mime_types = {
                        '.jpg': 'image/jpeg',
                        '.jpeg': 'image/jpeg',
                        '.png': 'image/png',
                        '.gif': 'image/gif',
                        '.webp': 'image/webp'
                    }
                    mime_type = mime_types.get(ext, 'image/jpeg')

                return base64_image, mime_type
        except Exception as e:
            print(f"Errore caricamento immagine {image_path}: {str(e)}")
            return None, None

    def prepare_images_for_analysis(self, images, log_callback=None):
        """Prepara le immagini per l'analisi (carica solo quelle esistenti)"""
        prepared_images = []

        for img_info in images:
            if img_info.get('exists') and img_info.get('resolved_path'):
                if log_callback:
                    log_callback(f"   Caricamento immagine: {img_info['filename']}")

                base64_img, mime_type = self.load_image_as_base64(img_info['resolved_path'])
                if base64_img:
                    prepared_images.append({
                        'base64': base64_img,
                        'mime_type': mime_type,
                        'filename': img_info['filename']
                    })
                    if log_callback:
                        log_callback(f"   ✓ Immagine caricata: {img_info['filename']} ({mime_type}, {len(base64_img)} chars)")
                else:
                    if log_callback:
                        log_callback(f"   ✗ Errore caricamento: {img_info['filename']}")

        return prepared_images

    def analyze_chunk(self, chunk_path, chunk_num, total_chunks, custom_prompt=None, log_callback=None):
        """Analizza un singolo chunk (supporta TXT e JSON)"""
        import json

        # Determina il formato del chunk
        is_json = chunk_path.endswith('.json')

        if is_json:
            # Leggi chunk JSON
            with open(chunk_path, 'r', encoding='utf-8') as f:
                chunk_data = json.load(f)
                content = chunk_data['text']
                images = chunk_data.get('images', [])
        else:
            # Leggi chunk TXT (formato classico)
            with open(chunk_path, 'r', encoding='utf-8') as f:
                content = f.read()
                images = []

        # Prepara le immagini se presenti
        prepared_images = []
        if images:
            if log_callback:
                log_callback(f"   Trovate {len(images)} immagini nel chunk {chunk_num}")
            prepared_images = self.prepare_images_for_analysis(images, log_callback)

        # Prompt di default o personalizzato
        if custom_prompt is None:
            base_prompt = f"""Analizza questo chunk ({chunk_num}/{total_chunks}) di un documento PDF e:

1. Estrai i concetti chiave e le informazioni principali
2. Identifica argomenti trattati
3. Evidenzia dati importanti, numeri, date, nomi
4. Riassumi in modo conciso ma completo"""

            if prepared_images:
                base_prompt += f"\n\n⚠️ IMPORTANTE: Questo chunk contiene {len(prepared_images)} immagine/i. Analizza anche il contenuto visivo delle immagini insieme al testo."

            prompt = f"""{base_prompt}

Chunk da analizzare:
{content}

Fornisci un'analisi strutturata e chiara."""
        else:
            prompt = f"{custom_prompt}\n\nChunk {chunk_num}/{total_chunks}:\n{content}"
            if prepared_images:
                prompt += f"\n\n[Questo chunk include {len(prepared_images)} immagine/i da analizzare]"

        try:
            if self.use_local:
                # Modello locale (Ollama) - con o senza immagini
                request_data = {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                }

                # Se ci sono immagini, aggiungile (Ollama llava supporta immagini)
                if prepared_images:
                    if log_callback:
                        log_callback(f"   📷 Invio {len(prepared_images)} immagini al modello {self.model}")
                    request_data["images"] = [img['base64'] for img in prepared_images]

                response = requests.post(
                    f"{self.local_url}/api/generate",
                    json=request_data,
                    timeout=300
                )
                response.raise_for_status()
                return response.json()['response']

            elif self.is_anthropic and prepared_images:
                # Anthropic Claude con immagini
                if log_callback:
                    log_callback(f"   📷 Invio {len(prepared_images)} immagini a Claude")

                content_parts = [{"type": "text", "text": prompt}]

                # Aggiungi immagini
                for img in prepared_images:
                    content_parts.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": img['mime_type'],
                            "data": img['base64']
                        }
                    })

                message = self.client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    messages=[
                        {"role": "user", "content": content_parts}
                    ]
                )
                return message.content[0].text

            elif self.is_anthropic:
                # Anthropic Claude
                message = self.client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                return message.content[0].text

            elif prepared_images:
                # OpenAI con immagini (GPT-4o vision)
                if log_callback:
                    log_callback(f"   📷 Invio {len(prepared_images)} immagini a GPT-4o")

                content_parts = [{"type": "text", "text": prompt}]

                # Aggiungi immagini
                for img in prepared_images:
                    content_parts.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{img['mime_type']};base64,{img['base64']}"
                        }
                    })

                response = self.client.chat.completions.create(
                    model=self.model,
                    max_tokens=4096,
                    messages=[
                        {"role": "user", "content": content_parts}
                    ]
                )
                return response.choices[0].message.content

            else:
                # OpenAI senza immagini
                response = self.client.chat.completions.create(
                    model=self.model,
                    max_tokens=4096,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                return response.choices[0].message.content

        except Exception as e:
            return f"ERRORE nell'analisi del chunk {chunk_num}: {str(e)}"

    def analyze_chunks(self, chunks, output_dir, custom_prompt=None,
                      progress_callback=None, stop_flag=None, log_callback=None):
        """Analizza tutti i chunk con rate limiting intelligente"""

        os.makedirs(output_dir, exist_ok=True)
        all_analyses = []
        total_chunks = len(chunks)

        # Calcola delay intelligente basato su limiti TPM configurati
        rate_limit_delay = self._calculate_rate_limit_delay(log_callback)

        for i, chunk in enumerate(chunks, 1):
            # Controlla se l'utente ha interrotto
            if stop_flag and stop_flag():
                break

            # Log chunk in analisi
            if log_callback:
                log_callback(f"Analisi chunk {i}/{total_chunks} in corso...")

            # Analizza chunk
            analysis = self.analyze_chunk(
                chunk['path'],
                i,
                total_chunks,
                custom_prompt,
                log_callback
            )

            # Salva analisi
            output_file = Path(output_dir) / f"analisi_chunk_{i:03d}.txt"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(analysis)

            all_analyses.append(analysis)

            # Log completamento chunk
            if log_callback:
                log_callback(f"[OK] Chunk {i}/{total_chunks} completato")

            # Aggiorna progresso (50-90%)
            if progress_callback:
                progress = 50 + ((i / total_chunks) * 40)
                progress_callback(progress)

            # Rate limiting intelligente: pausa tra le richieste
            if i < total_chunks:
                if log_callback:
                    log_callback(f"   ⏳ Attesa {rate_limit_delay:.1f}s (rate limiting TPM)...")
                time.sleep(rate_limit_delay)

        return all_analyses

    def create_final_summary(self, analyses, total_chunks, output_dir, log_callback=None, analysis_config=None):
        """Crea un riassunto finale basato su tutte le analisi"""

        # Carica soglia configurabile dall'utente (default 30)
        hierarchical_threshold = self._get_hierarchical_threshold()

        # Se ci sono troppe analisi, usa approccio gerarchico
        if len(analyses) > hierarchical_threshold:
            if log_callback:
                log_callback(f"   Utilizzo approccio gerarchico (soglia: {hierarchical_threshold} chunk)")
            return self.create_hierarchical_summary(analyses, total_chunks, output_dir, log_callback, analysis_config)

        # Combina tutte le analisi
        combined = "\n\n" + "="*80 + "\n\n".join(
            [f"ANALISI CHUNK {i+1}:\n{analysis}" for i, analysis in enumerate(analyses)]
        )

        prompt = f"""Ho analizzato un documento PDF WhatsApp di {total_chunks} chunk.
Ecco le analisi di tutti i chunk.

Crea un RIASSUNTO FINALE FORENSE COMPLETO strutturato come segue:

## 1. Panoramica Generale
- Sintesi del documento
- Periodo temporale coperto
- Numero di partecipanti

## 2. Partecipanti e Struttura
- Lista completa partecipanti con ruoli
- Dinamiche del gruppo

## 3. Timeline Eventi
- Cronologia eventi significativi con timestamp

## 4. Posizioni e Spostamenti (SEZIONE CRITICA)
Aggrega TUTTE le posizioni menzionate in qualsiasi chunk, creando una lista completa:
- Posizioni GPS condivise (coordinate o luoghi)
- Menzioni di luoghi, indirizzi, città
- Discussioni su viaggi e spostamenti

Per ogni voce indica:
• Luogo/Posizione: [descrizione completa]
• Utente: [chi ha menzionato/condiviso]
• Data/Ora: [timestamp preciso]
• Contesto: [sintesi del messaggio]
• Riferimento: [chunk/pagina originale]

Se non ci sono posizioni: indica "Nessuna posizione o spostamento rilevato nel documento"

## 5. Minacce e Contenuti Problematici (SEZIONE CRITICA)
⚠️ Aggrega TUTTI i contenuti problematici rilevati in qualsiasi chunk:
- Minacce (esplicite/implicite)
- Offese e insulti
- Aggressioni verbali
- Circonvenzioni e manipolazioni
- Contenuti illeciti
- Molestie
- Violenza

Per OGNI contenuto problematico indica:
• Tipo: [categoria]
• Gravità: [livello]
• Utente: [autore]
• Destinatario: [target]
• Data/Ora: [timestamp]
• Messaggio: [citazione]
• Contesto: [situazione]
• Riferimento: [chunk/pagina]

Ordina per gravità (critici prima). Se non ci sono: indica "Nessun contenuto problematico rilevato"

## 6. Contenuti Rilevanti
- Messaggi chiave
- Media condivisi
- Link esterni

## 7. Informazioni Sensibili (Dati Personali)
- Numeri di telefono
- Email
- Indirizzi fisici
- Documenti identificativi
- Dati finanziari

## 8. Pattern e Analisi
- Pattern di comunicazione
- Relazioni tra partecipanti
- Temi ricorrenti

## 9. Note Forensi
- Anomalie
- Osservazioni importanti

ANALISI DEI CHUNK:
{combined}

**IMPORTANTE**:
- La sezione "Posizioni e Spostamenti" deve essere COMPLETA e includere TUTTE le menzioni trovate nei chunk
- Mantieni timestamp e riferimenti precisi per ogni informazione
- Organizza il tutto in modo chiaro e strutturato con titoli H2 (##) e H3 (###)"""

        try:
            if self.use_local:
                # Modello locale (Ollama) - timeout aumentato a 900 secondi (15 min)
                response = requests.post(
                    f"{self.local_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False
                    },
                    timeout=900
                )
                response.raise_for_status()
                summary = response.json()['response']
            elif self.is_anthropic:
                message = self.client.messages.create(
                    model=self.model,
                    max_tokens=8000,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                summary = message.content[0].text
            else:
                response = self.client.chat.completions.create(
                    model=self.model,
                    max_tokens=8000,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                summary = response.choices[0].message.content

            # Salva riassunto TXT
            summary_file = Path(output_dir) / "RIASSUNTO_FINALE.txt"
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write("="*80 + "\n")
                f.write("RIASSUNTO FINALE - ANALISI COMPLETA DEL DOCUMENTO\n")
                f.write("="*80 + "\n\n")
                f.write(f"Chunk analizzati: {len(analyses)}/{total_chunks}\n")
                f.write("="*80 + "\n\n")
                f.write(summary)

            # Salva riassunto HTML (multi-pagina)
            self._save_html_report(summary, analyses, len(analyses), total_chunks, output_dir,
                                   analysis_config=analysis_config, log_callback=log_callback)

            return summary

        except Exception as e:
            # Salva un riassunto parziale anche in caso di errore per evitare perdita totale
            error_summary = f"ERRORE nella creazione del riassunto finale: {str(e)}\n\n"
            error_summary += "⚠️ Il riassunto automatico non è stato generato a causa di un errore.\n\n"
            error_summary += f"Numero di chunk analizzati: {len(analyses)}/{total_chunks}\n\n"
            error_summary += "SUGGERIMENTI:\n"
            error_summary += "- Verifica la connessione internet\n"
            error_summary += "- Controlla che l'API key sia valida e abbia crediti\n"
            error_summary += "- Se il documento è molto grande (>50 chunk), l'approccio gerarchico dovrebbe attivarsi automaticamente\n"
            error_summary += "- Prova a usare 'Post-Elaborazione > Ricerca Rapida' per estrarre informazioni specifiche\n\n"
            error_summary += f"Dettaglio errore tecnico:\n{str(e)}"

            # Salva comunque il file con l'errore per evitare il blocco totale
            summary_file = Path(output_dir) / "RIASSUNTO_FINALE.txt"
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write("="*80 + "\n")
                f.write("RIASSUNTO FINALE - ERRORE DURANTE LA GENERAZIONE\n")
                f.write("="*80 + "\n\n")
                f.write(error_summary)

            if log_callback:
                log_callback(f"✗ Errore durante riassunto finale: {str(e)}")
                log_callback(f"✓ File RIASSUNTO_FINALE.txt salvato con dettagli errore")

            return error_summary

    def create_hierarchical_summary(self, analyses, total_chunks, output_dir, log_callback=None, analysis_config=None):
        """Crea un riassunto gerarchico per documenti molto grandi"""

        # Ridotto da 50 a 20 per evitare errori 429 anche in approccio gerarchico
        # Con 20 chunk: ~16,000 token input + 4,096 output = ~20,000 totali (sotto 30k TPM)
        group_size = 20
        group_summaries = []
        num_groups = (len(analyses) + group_size - 1) // group_size

        # Riassumi ogni gruppo
        for i in range(0, len(analyses), group_size):
            group_num = (i // group_size) + 1
            if log_callback:
                log_callback(f"   Creazione riassunto gruppo {group_num}/{num_groups}...")

            group = analyses[i:i+group_size]
            combined = "\n\n".join([f"Chunk {i+j+1}: {analysis}"
                                   for j, analysis in enumerate(group)])

            prompt = f"""Riassumi questo gruppo di analisi:

{combined}

Estrai i punti chiave e crea un riassunto conciso."""

            try:
                if self.use_local:
                    # Modello locale (Ollama)
                    response = requests.post(
                        f"{self.local_url}/api/generate",
                        json={
                            "model": self.model,
                            "prompt": prompt,
                            "stream": False
                        },
                        timeout=300
                    )
                    response.raise_for_status()
                    group_summaries.append(response.json()['response'])
                elif self.is_anthropic:
                    message = self.client.messages.create(
                        model=self.model,
                        max_tokens=4096,
                        messages=[{"role": "user", "content": prompt}]
                    )
                    group_summaries.append(message.content[0].text)
                else:
                    response = self.client.chat.completions.create(
                        model=self.model,
                        max_tokens=4096,
                        messages=[{"role": "user", "content": prompt}]
                    )
                    group_summaries.append(response.choices[0].message.content)

                if log_callback:
                    log_callback(f"   [OK] Gruppo {group_num}/{num_groups} completato")

                time.sleep(1)
            except Exception as e:
                error_msg = f"Errore nel gruppo {group_num}: {str(e)}"
                group_summaries.append(error_msg)
                if log_callback:
                    log_callback(f"   [ERRORE] {error_msg}")

        # Combina i riassunti di gruppo
        final_combined = "\n\n".join([f"GRUPPO {i+1}:\n{summary}"
                                     for i, summary in enumerate(group_summaries)])

        prompt = f"""Ho riassunto un documento WhatsApp molto grande in {len(group_summaries)} gruppi.
Crea ora un RIASSUNTO FINALE FORENSE COMPLETO strutturato come segue:

## 1. Panoramica Generale
## 2. Partecipanti e Struttura
## 3. Timeline Eventi
## 4. Posizioni e Spostamenti (SEZIONE CRITICA)
   Aggrega TUTTE le posizioni da tutti i gruppi con:
   • Luogo/Posizione
   • Utente
   • Data/Ora
   • Contesto
   • Riferimento
## 5. Minacce e Contenuti Problematici (SEZIONE CRITICA)
   ⚠️ Aggrega TUTTI i contenuti problematici da tutti i gruppi:
   • Tipo
   • Gravità
   • Utente/Destinatario
   • Timestamp
   • Messaggio
   • Contesto
   • Riferimento
   Ordina per gravità (critici prima)
## 6. Contenuti Rilevanti
## 7. Informazioni Sensibili
## 8. Pattern e Analisi
## 9. Note Forensi

RIASSUNTI DEI GRUPPI:
{final_combined}

**IMPORTANTE**:
- La sezione "Posizioni e Spostamenti" deve aggregare TUTTE le posizioni da tutti i gruppi
- Mantieni timestamp e riferimenti precisi
- Usa titoli H2 (##) e H3 (###) per strutturare"""

        try:
            if self.use_local:
                # Modello locale (Ollama) - timeout aumentato a 900 secondi (15 min)
                response = requests.post(
                    f"{self.local_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False
                    },
                    timeout=900
                )
                response.raise_for_status()
                summary = response.json()['response']
            elif self.is_anthropic:
                message = self.client.messages.create(
                    model=self.model,
                    max_tokens=8000,
                    messages=[{"role": "user", "content": prompt}]
                )
                summary = message.content[0].text
            else:
                response = self.client.chat.completions.create(
                    model=self.model,
                    max_tokens=8000,
                    messages=[{"role": "user", "content": prompt}]
                )
                summary = response.choices[0].message.content

            # Salva riassunto TXT
            summary_file = Path(output_dir) / "RIASSUNTO_FINALE.txt"
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write("="*80 + "\n")
                f.write("RIASSUNTO FINALE - ANALISI COMPLETA DEL DOCUMENTO\n")
                f.write("="*80 + "\n\n")
                f.write(f"Chunk analizzati: {len(analyses)}/{total_chunks}\n")
                f.write(f"Approccio: Riassunto gerarchico ({len(group_summaries)} gruppi)\n")
                f.write("="*80 + "\n\n")
                f.write(summary)

            # Salva riassunto HTML (multi-pagina)
            self._save_html_report(summary, analyses, len(analyses), total_chunks, output_dir,
                                   hierarchical=True, num_groups=len(group_summaries),
                                   analysis_config=analysis_config, log_callback=log_callback)

            return summary

        except Exception as e:
            # Salva un riassunto parziale anche in caso di errore
            error_summary = f"ERRORE nel riassunto finale gerarchico: {str(e)}\n\n"
            error_summary += "⚠️ Il riassunto automatico non è stato generato a causa di un errore.\n\n"
            error_summary += f"Numero di chunk analizzati: {len(analyses)}/{total_chunks}\n"
            error_summary += f"Gruppi processati: {len(group_summaries)}\n\n"
            error_summary += "SUGGERIMENTI:\n"
            error_summary += "- Verifica la connessione internet\n"
            error_summary += "- Controlla che l'API key sia valida e abbia crediti\n"
            error_summary += "- Prova a usare 'Post-Elaborazione > Ricerca Rapida' per estrarre informazioni specifiche\n\n"
            error_summary += f"Dettaglio errore tecnico:\n{str(e)}"

            # Salva comunque il file con l'errore
            summary_file = Path(output_dir) / "RIASSUNTO_FINALE.txt"
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write("="*80 + "\n")
                f.write("RIASSUNTO FINALE - ERRORE DURANTE LA GENERAZIONE\n")
                f.write("="*80 + "\n\n")
                f.write(error_summary)

            if log_callback:
                log_callback(f"✗ Errore durante riassunto finale gerarchico: {str(e)}")
                log_callback(f"✓ File RIASSUNTO_FINALE.txt salvato con dettagli errore")

            return error_summary

    def _save_html_summary(self, summary, chunks_analyzed, total_chunks, output_dir,
                          hierarchical=False, num_groups=0):
        """DEPRECATA - Mantenuta per retrocompatibilità"""
        # Questa funzione è stata sostituita da _save_html_report
        pass

    def _save_html_report(self, summary, analyses, chunks_analyzed, total_chunks, output_dir,
                         hierarchical=False, num_groups=0, analysis_config=None, log_callback=None):
        """Crea un report HTML completo multi-pagina con index.html"""
        from datetime import datetime
        import os

        if log_callback:
            log_callback("   Generazione report HTML multi-pagina...")

        # Crea cartella per il report HTML
        html_dir = Path(output_dir) / "report_html"
        html_dir.mkdir(exist_ok=True)

        # 1. Genera index.html (pagina principale)
        self._create_index_page(html_dir, summary, chunks_analyzed, total_chunks,
                               hierarchical, num_groups, analysis_config)

        # 2. Genera pagina configurazioni
        self._create_config_page(html_dir, analysis_config)

        # 3. Genera pagine analisi chunk
        self._create_chunks_pages(html_dir, analyses, chunks_analyzed)

        # 4. Genera CSS condiviso
        self._create_shared_css(html_dir)

        # 5. Crea anche un HTML singolo per retrocompatibilità
        self._create_single_html(output_dir, summary, chunks_analyzed, total_chunks,
                                hierarchical, num_groups, analysis_config)

        if log_callback:
            log_callback(f"   ✓ Report HTML generato in: {html_dir}")

    def _create_shared_css(self, html_dir):
        """Crea il file CSS condiviso"""
        from html_templates import get_shared_css

        css_file = Path(html_dir) / "styles.css"
        with open(css_file, 'w', encoding='utf-8') as f:
            f.write(get_shared_css())

    def _create_index_page(self, html_dir, summary, chunks_analyzed, total_chunks,
                          hierarchical, num_groups, analysis_config):
        """Crea la pagina index.html con il riassunto finale"""
        from html_templates import create_html_page, format_text_to_html
        from datetime import datetime
        import html as html_lib

        # Converti il summary da Markdown a HTML formattato
        summary_html = format_text_to_html(summary)

        # Crea sezione statistiche
        stats_html = f"""
        <div class="card success-box">
            <h2>📊 Statistiche Analisi</h2>
            <table>
                <tr>
                    <th>Metrica</th>
                    <th>Valore</th>
                </tr>
                <tr>
                    <td><strong>Chunk Analizzati</strong></td>
                    <td><span class="badge badge-success">{chunks_analyzed} / {total_chunks}</span></td>
                </tr>
                <tr>
                    <td><strong>Modello AI Utilizzato</strong></td>
                    <td><span class="badge badge-info">{self.model}</span></td>
                </tr>
        """

        if hierarchical:
            stats_html += f"""
                <tr>
                    <td><strong>Approccio</strong></td>
                    <td><span class="badge badge-warning">Gerarchico ({num_groups} gruppi)</span></td>
                </tr>
            """

        if analysis_config:
            if analysis_config.get('analyze_images'):
                stats_html += """
                <tr>
                    <td><strong>Analisi Immagini</strong></td>
                    <td><span class="badge badge-info">✓ Attiva</span></td>
                </tr>
                """

            stats_html += f"""
                <tr>
                    <td><strong>Formato Chunk</strong></td>
                    <td><span class="badge badge-primary">{analysis_config.get('chunk_format', 'txt').upper()}</span></td>
                </tr>
            """

        stats_html += """
            </table>
        </div>
        """

        # Crea contenuto riassunto (già formattato in HTML)
        summary_content = f"""
        <div class="card">
            <h2>📝 Riassunto Finale</h2>
            <div class="content">
                {summary_html}
            </div>
        </div>
        """

        # Link rapidi
        quick_links = """
        <div class="card info-box">
            <h3>🔗 Navigazione Rapida</h3>
            <p>
                <a href="configurazione.html" class="btn">⚙️ Vedi Configurazione Completa</a>
                <a href="analisi_chunks.html" class="btn">📊 Vedi Analisi Dettagliate</a>
            </p>
        </div>
        """

        content = stats_html + summary_content + quick_links

        html_content = create_html_page(
            title='📱 Report Analisi WhatsApp',
            content=content,
            active_page='index',
            subtitle='Riassunto Finale e Statistiche'
        )

        index_file = Path(html_dir) / "index.html"
        with open(index_file, 'w', encoding='utf-8') as f:
            f.write(html_content)

    def _create_config_page(self, html_dir, analysis_config):
        """Crea la pagina configurazione.html"""
        from html_templates import create_html_page
        from datetime import datetime
        import os

        if not analysis_config:
            analysis_config = {}

        # Sezione Configurazione Sistema
        config_html = """
        <div class="card">
            <h2>⚙️ Configurazione Sistema</h2>
            <table>
        """

        config_items = [
            ('📄 File PDF Analizzato', os.path.basename(analysis_config.get('pdf_path', 'N/A'))),
            ('🤖 Modello AI', analysis_config.get('model', 'N/A')),
            ('💻 Tipo Modello', 'Locale (Ollama)' if analysis_config.get('use_local_model') else 'Cloud (API)'),
            ('📦 Formato Chunk', analysis_config.get('chunk_format', 'txt').upper()),
            ('📏 Caratteri per Chunk', f"{analysis_config.get('max_chars', 'N/A'):,}"),
            ('📄 Pagine Totali', analysis_config.get('total_pages', 'N/A')),
            ('🧩 Chunk Totali', analysis_config.get('total_chunks', 'N/A')),
        ]

        for label, value in config_items:
            config_html += f"""
                <tr>
                    <th>{label}</th>
                    <td>{value}</td>
                </tr>
            """

        config_html += """
            </table>
        </div>
        """

        # Sezione Analisi Immagini
        if analysis_config.get('analyze_images'):
            images_html = f"""
            <div class="card success-box">
                <h2>🖼️ Configurazione Analisi Immagini</h2>
                <table>
                    <tr>
                        <th>Stato</th>
                        <td><span class="badge badge-success">✓ Attiva</span></td>
                    </tr>
                    <tr>
                        <th>Cartella Estrazione</th>
                        <td>{analysis_config.get('extraction_folder', 'N/A')}</td>
                    </tr>
                </table>
            </div>
            """
        else:
            images_html = """
            <div class="card warning-box">
                <h2>🖼️ Analisi Immagini</h2>
                <p><span class="badge badge-warning">✗ Non attiva</span></p>
            </div>
            """

        # Sezione Costi e Tempi
        costs_html = f"""
        <div class="card info-box">
            <h2>💰 Stime Costi e Tempi</h2>
            <table>
                <tr>
                    <th>Costo Stimato</th>
                    <td>${analysis_config.get('estimated_cost', 0):.2f}</td>
                </tr>
                <tr>
                    <th>Tempo Stimato</th>
                    <td>~{analysis_config.get('estimated_time', 0)} minuti</td>
                </tr>
            </table>
        </div>
        """

        # Sezione Prompt Personalizzato
        custom_prompt = analysis_config.get('custom_prompt', '')
        if custom_prompt:
            prompt_html = f"""
            <div class="card">
                <h2>📝 Prompt Personalizzato</h2>
                <div class="content" style="background-color: #f5f5f5; padding: 15px; border-radius: 5px;">
                    {custom_prompt}
                </div>
            </div>
            """
        else:
            prompt_html = """
            <div class="card">
                <h2>📝 Prompt Personalizzato</h2>
                <p><em>Nessun prompt personalizzato utilizzato (usato prompt predefinito)</em></p>
            </div>
            """

        # Timestamp
        timestamp_html = f"""
        <div class="card">
            <h2>🕐 Informazioni Temporali</h2>
            <table>
                <tr>
                    <th>Data/Ora Avvio Analisi</th>
                    <td>{analysis_config.get('analysis_start_time', datetime.now()).strftime('%d/%m/%Y %H:%M:%S')}</td>
                </tr>
                <tr>
                    <th>Report Generato il</th>
                    <td>{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</td>
                </tr>
            </table>
        </div>
        """

        content = config_html + images_html + costs_html + prompt_html + timestamp_html

        html_content = create_html_page(
            title='⚙️ Configurazione Analisi',
            content=content,
            active_page='config',
            subtitle='Dettagli della configurazione utilizzata'
        )

        config_file = Path(html_dir) / "configurazione.html"
        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(html_content)

    def _create_chunks_pages(self, html_dir, analyses, chunks_analyzed):
        """Crea la pagina indice chunks e le singole pagine di analisi"""
        from html_templates import create_html_page
        import html as html_lib

        # 1. Crea pagina indice chunks
        chunks_list_html = """
        <div class="card">
            <h2>📊 Lista Analisi Chunk</h2>
            <p>Clicca su un chunk per vedere l'analisi dettagliata</p>
        </div>

        <div class="chunk-list">
        """

        for i in range(1, chunks_analyzed + 1):
            chunks_list_html += f"""
            <div class="chunk-item">
                <a href="chunk_{i:03d}.html">
                    <strong>Chunk {i}</strong><br>
                    <small>Vedi analisi →</small>
                </a>
            </div>
            """

        chunks_list_html += "</div>"

        # Statistiche
        stats_html = f"""
        <div class="card success-box">
            <h3>✓ Analisi Completata</h3>
            <p>Totale chunk analizzati: <strong>{chunks_analyzed}</strong></p>
            <p><a href="index.html" class="btn">← Torna al Riassunto Finale</a></p>
        </div>
        """

        content = chunks_list_html + stats_html

        html_content = create_html_page(
            title='📊 Analisi Dettagliate',
            content=content,
            active_page='chunks',
            subtitle=f'{chunks_analyzed} chunk analizzati'
        )

        chunks_index = Path(html_dir) / "analisi_chunks.html"
        with open(chunks_index, 'w', encoding='utf-8') as f:
            f.write(html_content)

        # 2. Crea pagine individuali per ogni chunk
        for i, analysis in enumerate(analyses, 1):
            self._create_single_chunk_page(html_dir, i, analysis, chunks_analyzed)

    def _create_single_chunk_page(self, html_dir, chunk_num, analysis, total_chunks):
        """Crea una singola pagina per un chunk"""
        from html_templates import create_html_page, format_text_to_html
        import html as html_lib

        # Converti l'analisi da Markdown a HTML formattato
        analysis_html = format_text_to_html(analysis)

        # Navigazione tra chunk
        nav_chunks = '<div class="card info-box"><p>'

        if chunk_num > 1:
            nav_chunks += f'<a href="chunk_{chunk_num-1:03d}.html" class="btn">← Chunk {chunk_num-1}</a> '

        nav_chunks += f'<a href="analisi_chunks.html" class="btn">📊 Torna all\'Indice</a> '

        if chunk_num < total_chunks:
            nav_chunks += f'<a href="chunk_{chunk_num+1:03d}.html" class="btn">Chunk {chunk_num+1} →</a>'

        nav_chunks += '</p></div>'

        # Contenuto analisi (già formattato in HTML)
        analysis_content = f"""
        {nav_chunks}

        <div class="card">
            <h2>Analisi Chunk {chunk_num} / {total_chunks}</h2>
            <div class="content">
                {analysis_html}
            </div>
        </div>

        {nav_chunks}
        """

        html_content = create_html_page(
            title=f'Chunk {chunk_num} / {total_chunks}',
            content=analysis_content,
            active_page='chunks',
            subtitle=f'Analisi dettagliata'
        )

        chunk_file = Path(html_dir) / f"chunk_{chunk_num:03d}.html"
        with open(chunk_file, 'w', encoding='utf-8') as f:
            f.write(html_content)

    def _create_single_html(self, output_dir, summary, chunks_analyzed, total_chunks,
                           hierarchical, num_groups, analysis_config):
        """Crea HTML singolo per retrocompatibilità"""
        from datetime import datetime
        from html_templates import format_text_to_html
        import html as html_lib

        # Converti il summary da Markdown a HTML formattato
        summary_html = format_text_to_html(summary)

        html_content = f"""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Riassunto Finale - WhatsApp Forensic Analyzer</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background-color: white;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        header {{
            border-bottom: 3px solid #25D366;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        h1 {{
            color: #075E54;
            margin: 0;
            font-size: 2.5em;
        }}
        .metadata {{
            background-color: #f0f0f0;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
            border-left: 4px solid #25D366;
        }}
        .metadata p {{
            margin: 5px 0;
            color: #555;
        }}
        .content {{
            margin-top: 30px;
            line-height: 1.8;
            color: #333;
        }}
        .content h1 {{
            color: #075E54;
            font-size: 2em;
            margin-top: 30px;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 3px solid #25D366;
        }}
        .content h2 {{
            color: #128C7E;
            font-size: 1.6em;
            margin-top: 25px;
            margin-bottom: 12px;
            padding-left: 15px;
            border-left: 5px solid #25D366;
        }}
        .content h3 {{
            color: #34B7F1;
            font-size: 1.3em;
            margin-top: 20px;
            margin-bottom: 10px;
        }}
        .content h4 {{
            color: #666;
            font-size: 1.1em;
            margin-top: 15px;
            margin-bottom: 8px;
        }}
        .content p {{
            margin-bottom: 15px;
        }}
        .content ul, .content ol {{
            margin: 15px 0;
            padding-left: 30px;
        }}
        .content li {{
            margin-bottom: 8px;
        }}
        .content strong {{
            color: #075E54;
            font-weight: 600;
        }}
        footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            text-align: center;
            color: #777;
            font-size: 0.9em;
        }}
        .highlight {{
            color: #25D366;
            font-weight: bold;
        }}
        .info-box {{
            background-color: #e6f3ff;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
            border-left: 4px solid #34B7F1;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📱 Riassunto Finale - Analisi WhatsApp</h1>
            <p style="color: #666; font-size: 1.1em; margin-top: 10px;">Analisi Completa del Documento</p>
        </header>

        <div class="info-box">
            <p><strong>💡 Report Interattivo Disponibile!</strong></p>
            <p>È stato generato un report HTML interattivo più completo nella cartella <strong>report_html/</strong></p>
            <p>Apri il file <strong>report_html/index.html</strong> per una migliore esperienza di navigazione.</p>
        </div>

        <div class="metadata">
            <p><strong>Data Analisi:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
            <p><strong>Chunk Analizzati:</strong> <span class="highlight">{chunks_analyzed}</span> / {total_chunks}</p>
            <p><strong>Modello AI:</strong> {self.model}</p>
            {'<p><strong>Approccio:</strong> Riassunto gerarchico (' + str(num_groups) + ' gruppi)</p>' if hierarchical else ''}
        </div>

        <div class="content">
            {summary_html}
        </div>

        <footer>
            <p>Generato da <strong>WhatsApp Forensic Analyzer</strong></p>
            <p>© 2025 Luca Mercatanti - <a href="https://mercatanti.com" style="color: #25D366;">mercatanti.com</a></p>
        </footer>
    </div>
</body>
</html>"""

        html_file = Path(output_dir) / "RIASSUNTO_FINALE.html"
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)

    def quick_search_on_analyses(self, analyses, user_query):
        """
        Esegue ricerca rapida su analisi esistenti

        Args:
            analyses: Lista di analisi già prodotte (contenuto txt files)
            user_query: Domanda dell'utente

        Returns:
            Risposta AI con risultati ricerca
        """

        # Se troppe analisi, usa approccio gerarchico per evitare errore 429
        hierarchical_threshold = self._get_hierarchical_threshold()

        if len(analyses) > hierarchical_threshold:
            return self._hierarchical_quick_search(analyses, user_query)

        # Combina tutte le analisi (solo se sotto la soglia)
        combined_analyses = "\n\n" + "="*80 + "\n\n".join(
            [f"ANALISI CHUNK {i+1}:\n{analysis}" for i, analysis in enumerate(analyses)]
        )

        # Crea prompt per la ricerca
        prompt = f"""Hai a disposizione {len(analyses)} analisi di un report WhatsApp.

DOMANDA UTENTE: {user_query}

Analizza tutte le analisi e rispondi alla domanda fornendo:

1. **Risposta Dettagliata**
   - Rispondi direttamente alla domanda
   - Fornisci tutti i dettagli rilevanti trovati

2. **Citazioni Precise**
   - Per ogni informazione, indica:
     • Chunk di provenienza (es. "Chunk 5")
     • Timestamp (se disponibile)
     • Citazione esatta del testo rilevante

3. **Riferimenti**
   - Lista completa di tutti gli elementi trovati
   - Organizzati in modo chiaro e strutturato

4. **Sintesi Finale**
   - Riepilogo dei risultati
   - Conteggio totale elementi trovati

**IMPORTANTE**:
- Se non trovi elementi rilevanti, indicalo chiaramente
- Mantieni i riferimenti precisi ai chunk originali
- Organizza la risposta in modo strutturato con titoli e liste

ANALISI DISPONIBILI:
{combined_analyses}

Rispondi in modo dettagliato e preciso."""

        try:
            if self.use_local:
                # Modello locale (Ollama)
                response = requests.post(
                    f"{self.local_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False
                    },
                    timeout=600
                )
                response.raise_for_status()
                return response.json()['response']

            elif self.is_anthropic:
                # Anthropic Claude
                message = self.client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                return message.content[0].text

            else:
                # OpenAI
                response = self.client.chat.completions.create(
                    model=self.model,
                    max_tokens=4096,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                return response.choices[0].message.content

        except Exception as e:
            return f"ERRORE nella ricerca: {str(e)}"

    def _hierarchical_quick_search(self, analyses, user_query):
        """
        Esegue ricerca rapida con approccio gerarchico per documenti grandi

        Args:
            analyses: Lista di analisi già prodotte
            user_query: Domanda dell'utente

        Returns:
            Risposta AI aggregata
        """

        # Dividi in gruppi da 20 (come in create_hierarchical_summary)
        group_size = 20
        group_results = []
        num_groups = (len(analyses) + group_size - 1) // group_size

        # Cerca in ogni gruppo
        for i in range(0, len(analyses), group_size):
            group_num = (i // group_size) + 1
            group = analyses[i:i+group_size]

            combined = "\n\n".join([f"CHUNK {i+j+1}: {analysis}"
                                   for j, analysis in enumerate(group)])

            # Ricerca nel gruppo
            prompt = f"""Hai a disposizione un gruppo di {len(group)} analisi di un report WhatsApp.

DOMANDA UTENTE: {user_query}

Cerca informazioni rilevanti per rispondere alla domanda. Se trovi elementi rilevanti:
- Indica il chunk di provenienza
- Cita il testo rilevante
- Fornisci il contesto

Se NON trovi nulla di rilevante in questo gruppo, indica "Nessun elemento rilevante trovato in questo gruppo"

ANALISI DEL GRUPPO:
{combined}

Rispondi in modo conciso ma completo."""

            try:
                if self.use_local:
                    response = requests.post(
                        f"{self.local_url}/api/generate",
                        json={
                            "model": self.model,
                            "prompt": prompt,
                            "stream": False
                        },
                        timeout=300
                    )
                    response.raise_for_status()
                    group_results.append(response.json()['response'])
                elif self.is_anthropic:
                    message = self.client.messages.create(
                        model=self.model,
                        max_tokens=3000,
                        messages=[{"role": "user", "content": prompt}]
                    )
                    group_results.append(message.content[0].text)
                else:
                    response = self.client.chat.completions.create(
                        model=self.model,
                        max_tokens=3000,
                        messages=[{"role": "user", "content": prompt}]
                    )
                    group_results.append(response.choices[0].message.content)

                time.sleep(1)

            except Exception as e:
                group_results.append(f"[ERRORE nel gruppo {group_num}: {str(e)}]")

        # Combina i risultati dei gruppi
        combined_results = "\n\n".join([f"RISULTATO GRUPPO {i+1}:\n{result}"
                                       for i, result in enumerate(group_results)])

        # Richiesta finale di aggregazione
        final_prompt = f"""Ho cercato la risposta alla seguente domanda in {len(group_results)} gruppi di analisi:

DOMANDA ORIGINALE: {user_query}

RISULTATI DA TUTTI I GRUPPI:
{combined_results}

Aggrega tutti i risultati rilevanti e fornisci una risposta completa strutturata come segue:

1. **Risposta Dettagliata**
   - Rispondi direttamente alla domanda
   - Fornisci tutti i dettagli trovati in TUTTI i gruppi

2. **Citazioni Precise**
   - Per ogni informazione indica:
     • Chunk di provenienza
     • Timestamp (se disponibile)
     • Citazione testuale

3. **Sintesi Finale**
   - Riepilogo completo
   - Conteggio totale elementi trovati

**IMPORTANTE**:
- Aggrega informazioni da TUTTI i gruppi
- Mantieni riferimenti precisi
- Se nessun gruppo ha trovato informazioni, indicalo chiaramente

Fornisci una risposta completa e strutturata."""

        try:
            if self.use_local:
                response = requests.post(
                    f"{self.local_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": final_prompt,
                        "stream": False
                    },
                    timeout=600
                )
                response.raise_for_status()
                return response.json()['response']
            elif self.is_anthropic:
                message = self.client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    messages=[{"role": "user", "content": final_prompt}]
                )
                return message.content[0].text
            else:
                response = self.client.chat.completions.create(
                    model=self.model,
                    max_tokens=4096,
                    messages=[{"role": "user", "content": final_prompt}]
                )
                return response.choices[0].message.content

        except Exception as e:
            return f"ERRORE nell'aggregazione finale: {str(e)}\n\nRISULTATI PARZIALI:\n{combined_results}"

    def create_chat_summary(self, chat, output_dir, log_callback=None):
        """
        Crea riassunto dedicato per una singola chat (riutilizza analisi esistenti)

        Args:
            chat: Dizionario con metadati chat
            output_dir: Directory output principale (dove sono le analisi)
            log_callback: Funzione di logging

        Returns:
            Stringa con riassunto della chat
        """
        try:
            # Carica le analisi dei chunk appartenenti a questa chat
            chat_analyses = []
            for chunk_num in chat['chunks']:
                analysis_file = Path(output_dir) / f"analisi_chunk_{chunk_num:03d}.txt"

                if analysis_file.exists():
                    with open(analysis_file, 'r', encoding='utf-8') as f:
                        chat_analyses.append(f.read())
                else:
                    if log_callback:
                        log_callback(f"   ⚠️ Analisi chunk {chunk_num} non trovata, skip")

            if not chat_analyses:
                return "Nessuna analisi disponibile per questa chat."

            # Se troppe analisi nella chat, usa approccio gerarchico
            hierarchical_threshold = self._get_hierarchical_threshold()

            if len(chat_analyses) > hierarchical_threshold:
                if log_callback:
                    log_callback(f"   Chat con {len(chat_analyses)} chunk: uso approccio gerarchico")
                return self._hierarchical_chat_summary(chat, chat_analyses, log_callback)

            # Combina le analisi (solo se sotto la soglia)
            combined = "\n\n" + "="*80 + "\n\n".join(
                [f"CHUNK {chat['chunks'][i]}:\n{analysis}"
                 for i, analysis in enumerate(chat_analyses)]
            )

            # Prepara info chat
            chat_type = "1v1" if chat['type'] == '1v1' else "di gruppo"
            participants_list = ', '.join([p.get('name', p.get('id', '')) for p in chat.get('participants', [])])

            # Crea prompt specifico per la chat
            prompt = f"""Hai le analisi di {len(chat_analyses)} chunk appartenenti a una conversazione WhatsApp {chat_type}.

INFORMAZIONI CHAT:
- Tipo: {"Chat individuale (1v1)" if chat['type'] == '1v1' else f"Chat di gruppo ({len(chat.get('participants', []))} partecipanti)"}
- Partecipanti: {participants_list}
- Periodo: {chat['metadata'].get('start_time', 'N/A')} → {chat['metadata'].get('last_activity', 'N/A')}
- Allegati: {chat['metadata'].get('num_attachments', 0)}

Crea un RIASSUNTO SPECIFICO di questa conversazione strutturato come segue:

## 1. Informazioni Generali
- Riepilogo della conversazione
- Contesto generale
- Periodo di attività

## 2. Argomenti Principali
- Temi discussi nella conversazione
- Argomenti ricorrenti
- Focus principale del dialogo

## 3. Messaggi Chiave
Lista messaggi importanti con:
• Data/Ora: [timestamp preciso]
• Autore: [chi ha scritto]
• Messaggio: [contenuto o sintesi]
• Importanza: [perché è rilevante]

## 4. Relazione tra Partecipanti
- Tipo di relazione emergente (amici, famiglia, lavoro, altro)
- Tono della conversazione (formale/informale, amichevole/ostile)
- Dinamiche interpersonali

## 5. Eventi Rilevanti
- Appuntamenti fissati
- Accordi presi
- Promesse o impegni
- Decisioni importanti

## 6. Allegati e Media Condivisi
- Tipologia di allegati ({chat['metadata'].get('num_attachments', 0)} totali)
- Cosa è stato condiviso
- Rilevanza dei media

## 7. Posizioni e Luoghi Menzionati
- GPS o coordinate condivise
- Riferimenti a luoghi specifici
- Discussioni su spostamenti
- Appuntamenti in luoghi fisici

Indica sempre:
• Luogo: [descrizione]
• Utente: [chi ha menzionato]
• Data/Ora: [timestamp]
• Contesto: [sintesi]
• Riferimento: [chunk originale]

## 8. Contenuti Problematici (se presenti)
⚠️ Rileva eventuali:
- Minacce o linguaggio aggressivo
- Offese o insulti
- Discussioni conflittuali
- Contenuti inappropriati

Per ogni contenuto:
• Tipo: [categoria]
• Gravità: [livello]
• Autore/Destinatario
• Timestamp
• Citazione
• Contesto

## 9. Note Forensi
- Osservazioni rilevanti dal punto di vista investigativo
- Anomalie o pattern significativi
- Elementi di particolare interesse

**IMPORTANTE**:
- Mantieni timestamp e riferimenti precisi (indica sempre il chunk originale)
- Questa è una conversazione specifica, concentrati sui dettagli di QUESTA chat
- Se una sezione non contiene informazioni, indicalo esplicitamente

ANALISI DEI CHUNK DELLA CHAT:
{combined}

Fornisci un riassunto completo, strutturato e dettagliato."""

            # Genera riassunto
            if log_callback:
                log_callback(f"   Generazione riassunto con {len(chat_analyses)} chunk...")

            if self.use_local:
                # Modello locale (Ollama)
                response = requests.post(
                    f"{self.local_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False
                    },
                    timeout=600
                )
                response.raise_for_status()
                return response.json()['response']

            elif self.is_anthropic:
                # Anthropic Claude
                message = self.client.messages.create(
                    model=self.model,
                    max_tokens=6000,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                return message.content[0].text

            else:
                # OpenAI
                response = self.client.chat.completions.create(
                    model=self.model,
                    max_tokens=6000,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                return response.choices[0].message.content

        except Exception as e:
            error_msg = f"ERRORE nella creazione del riassunto chat: {str(e)}"
            if log_callback:
                log_callback(f"   ✗ {error_msg}")
            return error_msg

    def _hierarchical_chat_summary(self, chat, chat_analyses, log_callback=None):
        """
        Crea riassunto chat con approccio gerarchico per chat molto lunghe

        Args:
            chat: Dizionario metadati chat
            chat_analyses: Lista analisi chunk della chat
            log_callback: Funzione logging

        Returns:
            Stringa riassunto
        """
        # Dividi in gruppi da 20
        group_size = 20
        group_summaries = []
        num_groups = (len(chat_analyses) + group_size - 1) // group_size

        chat_type = "1v1" if chat['type'] == '1v1' else "di gruppo"
        participants_list = ', '.join([p.get('name', p.get('id', '')) for p in chat.get('participants', [])])

        # Riassumi ogni gruppo
        for i in range(0, len(chat_analyses), group_size):
            group_num = (i // group_size) + 1
            if log_callback:
                log_callback(f"   Riassunto gruppo chat {group_num}/{num_groups}...")

            group = chat_analyses[i:i+group_size]
            combined = "\n\n".join([f"Chunk {i+j+1}: {analysis}"
                                   for j, analysis in enumerate(group)])

            prompt = f"""Riassumi questo gruppo di analisi di una chat WhatsApp {chat_type}:

INFORMAZIONI CHAT:
- Partecipanti: {participants_list}

ANALISI DEL GRUPPO:
{combined}

Estrai:
- Argomenti discussi
- Messaggi chiave con timestamp
- Eventi rilevanti
- Contenuti problematici (se presenti)

Riassumi in modo conciso."""

            try:
                if self.use_local:
                    response = requests.post(
                        f"{self.local_url}/api/generate",
                        json={
                            "model": self.model,
                            "prompt": prompt,
                            "stream": False
                        },
                        timeout=300
                    )
                    response.raise_for_status()
                    group_summaries.append(response.json()['response'])
                elif self.is_anthropic:
                    message = self.client.messages.create(
                        model=self.model,
                        max_tokens=4096,
                        messages=[{"role": "user", "content": prompt}]
                    )
                    group_summaries.append(message.content[0].text)
                else:
                    response = self.client.chat.completions.create(
                        model=self.model,
                        max_tokens=4096,
                        messages=[{"role": "user", "content": prompt}]
                    )
                    group_summaries.append(response.choices[0].message.content)

                time.sleep(1)

            except Exception as e:
                error_msg = f"Errore nel gruppo {group_num}: {str(e)}"
                group_summaries.append(error_msg)
                if log_callback:
                    log_callback(f"   ✗ {error_msg}")

        # Combina i riassunti di gruppo per il riassunto finale
        combined_summaries = "\n\n".join([f"GRUPPO {i+1}:\n{summary}"
                                         for i, summary in enumerate(group_summaries)])

        # Riassunto finale aggregato
        final_prompt = f"""Ho riassunto una conversazione WhatsApp {chat_type} in {len(group_summaries)} gruppi.

INFORMAZIONI CHAT:
- Tipo: {"Chat individuale (1v1)" if chat['type'] == '1v1' else f"Chat di gruppo ({len(chat.get('participants', []))} partecipanti)"}
- Partecipanti: {participants_list}
- Periodo: {chat['metadata'].get('start_time', 'N/A')} → {chat['metadata'].get('last_activity', 'N/A')}
- Allegati: {chat['metadata'].get('num_attachments', 0)}

Crea un RIASSUNTO FINALE COMPLETO aggregando i riassunti di gruppo:

## 1. Informazioni Generali
## 2. Argomenti Principali
## 3. Messaggi Chiave (con timestamp e autore)
## 4. Relazione tra Partecipanti
## 5. Eventi Rilevanti
## 6. Allegati e Media Condivisi
## 7. Posizioni e Luoghi Menzionati
## 8. Contenuti Problematici (se presenti)
## 9. Note Forensi

RIASSUNTI DEI GRUPPI:
{combined_summaries}

Fornisci un riassunto completo, strutturato e dettagliato."""

        try:
            if log_callback:
                log_callback(f"   Creazione riassunto finale chat...")

            if self.use_local:
                response = requests.post(
                    f"{self.local_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": final_prompt,
                        "stream": False
                    },
                    timeout=600
                )
                response.raise_for_status()
                return response.json()['response']
            elif self.is_anthropic:
                message = self.client.messages.create(
                    model=self.model,
                    max_tokens=6000,
                    messages=[{"role": "user", "content": final_prompt}]
                )
                return message.content[0].text
            else:
                response = self.client.chat.completions.create(
                    model=self.model,
                    max_tokens=6000,
                    messages=[{"role": "user", "content": final_prompt}]
                )
                return response.choices[0].message.content

        except Exception as e:
            error_msg = f"ERRORE nel riassunto finale chat: {str(e)}"
            if log_callback:
                log_callback(f"   ✗ {error_msg}")
            return f"{error_msg}\n\nRISULTATI PARZIALI:\n{combined_summaries}"

    def analyze_chunk_header(self, text_header):
        """
        Usa AI per determinare se un chunk contiene un header di chat WhatsApp
        e estrarre i metadati

        Args:
            text_header: Primi 800 caratteri del chunk

        Returns:
            dict con:
                - is_chat_header: bool (True se è un header)
                - metadata: dict con metadati estratti (participants, start_time, etc.)
        """
        import json

        prompt = f"""Analizza questo testo e determina se contiene un HEADER di inizio conversazione WhatsApp da un report forense (Cellebrite, UFED, Oxygen).

Un header tipico contiene:
- Start Time / Last Activity (date/ore)
- Participants: lista partecipanti
- Identifier: codice identificativo chat (es. wxid o hash esadecimale)
- Account: numero telefono o ID account
- Number of attachments
- Body file: riferimento file (es. chat-123.txt)

TESTO DA ANALIZZARE:
{text_header}

Rispondi SOLO con un oggetto JSON valido nel seguente formato:
{{
  "is_chat_header": true/false,
  "metadata": {{
    "start_time": "data/ora inizio o null",
    "last_activity": "data/ora ultima attività o null",
    "account": "account o numero telefono o null",
    "identifier": "identificativo chat o null",
    "num_attachments": numero o 0,
    "body_file": "nome file body o null",
    "participants": [
      {{"id": "wxid/numero", "name": "nome utente", "owner": true/false}},
      ...
    ]
  }}
}}

**IMPORTANTE**:
- Se NON è un header di chat, restituisci {{"is_chat_header": false, "metadata": {{}}}}
- Restituisci SOLO JSON valido, senza altre spiegazioni
- Per participants, estrai tutti i partecipanti trovati nella sezione "Participants:"
- Indica "owner": true per il proprietario dell'account (se indicato)"""

        try:
            if self.use_local:
                # Modello locale (Ollama)
                response = requests.post(
                    f"{self.local_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False
                    },
                    timeout=60
                )
                response.raise_for_status()
                result_text = response.json()['response']

            elif self.is_anthropic:
                # Anthropic Claude
                message = self.client.messages.create(
                    model=self.model,
                    max_tokens=1500,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                result_text = message.content[0].text

            else:
                # OpenAI
                response = self.client.chat.completions.create(
                    model=self.model,
                    max_tokens=1500,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                result_text = response.choices[0].message.content

            # Parse JSON response
            # Estrai JSON dalla risposta (a volte l'AI aggiunge testo extra)
            result_text = result_text.strip()

            # Cerca blocco JSON nella risposta
            if '```json' in result_text:
                # Estrai da code block
                start = result_text.find('```json') + 7
                end = result_text.find('```', start)
                result_text = result_text[start:end].strip()
            elif '```' in result_text:
                # Code block generico
                start = result_text.find('```') + 3
                end = result_text.find('```', start)
                result_text = result_text[start:end].strip()

            # Parse JSON
            result = json.loads(result_text)
            return result

        except json.JSONDecodeError as e:
            # Fallback: se il JSON non è valido, ritorna no-header
            return {"is_chat_header": False, "metadata": {}}
        except Exception as e:
            # Altri errori: ritorna no-header
            return {"is_chat_header": False, "metadata": {}}
