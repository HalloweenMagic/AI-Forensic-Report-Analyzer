"""
Core analyzer per estrazione e geocoding delle posizioni geografiche
Gestisce LLM analysis, geocoding APIs e normalizzazione dati

© 2025 Luca Mercatanti - https://mercatanti.com
"""

import os
import json
import time
import requests
from glob import glob
from urllib.parse import urlencode


class LocationAnalyzer:
    def __init__(self, ai_analyzer, config, log_callback=None, progress_callback=None):
        """
        Inizializza l'analyzer per posizioni geografiche

        Args:
            ai_analyzer: Istanza di AIAnalyzer
            config: Dict con configurazione (provider, threshold, etc.)
            log_callback: Funzione per logging
            progress_callback: Funzione per progress bar
        """
        self.ai_analyzer = ai_analyzer
        self.config = config
        self.log_callback = log_callback
        self.progress_callback = progress_callback

        self.locations = []
        self.geocoding_errors = []

    def log(self, message):
        """Invia messaggio al log se callback disponibile"""
        if self.log_callback:
            self.log_callback(message)

    def update_progress(self, value):
        """Aggiorna progress bar se callback disponibile"""
        if self.progress_callback:
            self.progress_callback(value)

    def _call_llm(self, prompt, max_tokens=4000, temperature=0.3):
        """
        Chiama l'LLM configurato in AIAnalyzer

        Args:
            prompt: Prompt da inviare
            max_tokens: Max token di risposta
            temperature: Temperatura (0.0 - 1.0)

        Returns:
            str: Risposta del modello
        """
        try:
            if self.ai_analyzer.use_local:
                # Ollama locale
                response = requests.post(
                    f"{self.ai_analyzer.local_url}/api/generate",
                    json={
                        "model": self.ai_analyzer.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": temperature,
                            "num_predict": max_tokens
                        }
                    },
                    timeout=300
                )
                response.raise_for_status()
                return response.json()['response']

            elif self.ai_analyzer.is_anthropic:
                # Anthropic Claude
                message = self.ai_analyzer.client.messages.create(
                    model=self.ai_analyzer.model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                return message.content[0].text

            else:
                # OpenAI / Azure OpenAI
                response = self.ai_analyzer.client.chat.completions.create(
                    model=self.ai_analyzer.model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                return response.choices[0].message.content

        except Exception as e:
            raise Exception(f"Errore chiamata LLM: {str(e)}")

    def load_chunks(self, chunks_dir):
        """
        Carica i chunk dalla cartella chunk (auto-rilevamento formato)

        Args:
            chunks_dir: Percorso cartella chunk

        Returns:
            list: Lista di dict {chunk_id, text, format}
        """
        chunks = []

        # Prova formato JSON
        json_files = sorted(glob(os.path.join(chunks_dir, "chunk_*.json")))
        if json_files:
            self.log(f"📄 Rilevato formato chunk: JSON ({len(json_files)} file)")
            for json_file in json_files:
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        chunk_id = int(os.path.basename(json_file).replace('chunk_', '').replace('.json', ''))
                        chunks.append({
                            'chunk_id': chunk_id,
                            'text': data.get('text', ''),
                            'format': 'json',
                            'metadata': data
                        })
                except Exception as e:
                    self.log(f"⚠️ Errore lettura {json_file}: {e}")
        else:
            # Prova formato TXT
            txt_files = sorted(glob(os.path.join(chunks_dir, "chunk_*.txt")))
            if txt_files:
                self.log(f"📄 Rilevato formato chunk: TXT ({len(txt_files)} file)")
                for txt_file in txt_files:
                    try:
                        with open(txt_file, 'r', encoding='utf-8') as f:
                            text = f.read()
                            chunk_id = int(os.path.basename(txt_file).replace('chunk_', '').replace('.txt', ''))
                            chunks.append({
                                'chunk_id': chunk_id,
                                'text': text,
                                'format': 'txt',
                                'metadata': {}
                            })
                    except Exception as e:
                        self.log(f"⚠️ Errore lettura {txt_file}: {e}")

        return chunks

    def extract_locations_from_chunks(self, chunks):
        """
        Estrae le posizioni da tutti i chunk usando LLM

        Args:
            chunks: Lista di chunk caricati

        Returns:
            list: Lista di posizioni estratte
        """
        self.log("\n" + "="*60)
        self.log("🔍 FASE 1: ESTRAZIONE POSIZIONI CON LLM")
        self.log("="*60)

        all_locations = []
        total_chunks = len(chunks)

        # Calcola delay intelligente basato su limiti TPM configurati
        rate_limit_delay = self.ai_analyzer._calculate_rate_limit_delay(self.log_callback)

        for i, chunk in enumerate(chunks, 1):
            self.log(f"\n📍 Analisi chunk {i}/{total_chunks} (ID: {chunk['chunk_id']})...")

            # Costruisci prompt per LLM
            prompt = self._build_extraction_prompt(
                chunk['text'],
                self.config.get('context_deduction', False)
            )

            try:
                # Chiamata LLM
                response = self._call_llm(
                    prompt=prompt,
                    max_tokens=4000,
                    temperature=0.3  # Bassa temperatura per output strutturato
                )

                # Parsing JSON response
                locations = self._parse_llm_response(response, chunk['chunk_id'])

                # Filtra per confidence threshold
                threshold = self.config.get('confidence_threshold', 50)
                filtered = [loc for loc in locations if loc['confidence_score'] >= threshold]

                self.log(f"   ✓ Trovate {len(locations)} posizioni")
                if len(filtered) < len(locations):
                    self.log(f"   🔽 Filtrate {len(locations) - len(filtered)} posizioni sotto soglia {threshold}%")
                self.log(f"   ✅ Posizioni valide: {len(filtered)}")

                all_locations.extend(filtered)

            except Exception as e:
                self.log(f"   ✗ Errore analisi chunk {chunk['chunk_id']}: {str(e)}")

            # Aggiorna progress
            progress = int((i / total_chunks) * 50)  # Prima metà progress (0-50%)
            self.update_progress(progress)

            # Rate limiting: attendi tra una chiamata e l'altra (eccetto l'ultima)
            if i < total_chunks:
                self.log(f"   ⏳ Attesa {rate_limit_delay:.1f}s (rate limiting TPM)...")
                time.sleep(rate_limit_delay)

        self.log(f"\n📊 Totale posizioni estratte: {len(all_locations)}")
        return all_locations

    def _build_extraction_prompt(self, text, context_deduction):
        """
        Costruisce il prompt per l'estrazione delle posizioni

        Args:
            text: Testo del chunk
            context_deduction: Se True, attiva deduzione dal contesto

        Returns:
            str: Prompt strutturato
        """
        base_prompt = f"""Analizza il seguente testo e identifica TUTTE le posizioni geografiche menzionate.

Per ogni posizione trovata, estrai:
- location_text: Il testo esatto che descrive la posizione (es: "Via Roma 10, Milano")
- location_type: Tipo di posizione tra 'coordinates', 'address', 'place_name', 'poi'
- sender: Chi ha menzionato la posizione (nome mittente se disponibile, altrimenti "Unknown")
- timestamp: Data/ora del messaggio (formato come appare nel testo, altrimenti null)
- message_context: La frase completa o il contesto in cui appare la posizione (max 200 caratteri)
- confidence_score: Punteggio 0-100 che indica quanto sei sicuro che sia una posizione reale

Tipi di posizioni:
- coordinates: Coordinate GPS esplicite (es: "45.464204, 9.189982")
- address: Indirizzi completi (es: "Via Dante 15, Firenze")
- place_name: Nomi di luoghi (es: "Milano", "Piazza Duomo")
- poi: Punti di interesse (es: "bar centrale", "stazione", "centro commerciale")

Confidence score:
- 80-100: Posizione esplicita e chiara (coordinate, indirizzi completi)
- 50-79: Luogo nominato in modo chiaro (città, vie, piazze)
- 20-49: Riferimento generico o ambiguo (es: "al bar", "in centro")
- 0-19: Possibile falso positivo (nomi propri, metafore)
"""

        if context_deduction:
            base_prompt += """
DEDUZIONE DAL CONTESTO ATTIVA:
Cerca anche di dedurre posizioni implicite:
- "torno a casa" → cerca l'indirizzo di casa nei messaggi precedenti
- "ci vediamo al solito posto" → cerca luoghi già menzionati
- Riferimenti indiretti a luoghi già discussi

Per deduzioni, usa confidence_score più basso (30-60) e aggiungi nota nel message_context.
"""

        base_prompt += f"""
Restituisci SOLO un JSON valido nel seguente formato:
{{
  "locations": [
    {{
      "location_text": "string",
      "location_type": "coordinates|address|place_name|poi",
      "sender": "string",
      "timestamp": "string or null",
      "message_context": "string",
      "confidence_score": 0-100
    }}
  ]
}}

TESTO DA ANALIZZARE:
{text}

JSON OUTPUT:"""

        return base_prompt

    def _parse_llm_response(self, response, chunk_id):
        """
        Parsing della risposta LLM in JSON

        Args:
            response: Risposta testuale dall'LLM
            chunk_id: ID del chunk analizzato

        Returns:
            list: Lista di posizioni estratte
        """
        try:
            # Prova parsing diretto
            data = json.loads(response)
        except json.JSONDecodeError:
            # Fallback: cerca JSON tra { e }
            start = response.find('{')
            end = response.rfind('}') + 1
            if start != -1 and end > start:
                try:
                    data = json.loads(response[start:end])
                except:
                    return []
            else:
                return []

        locations = []
        for loc in data.get('locations', []):
            locations.append({
                'chunk_id': chunk_id,
                'location_text': loc.get('location_text', ''),
                'location_type': loc.get('location_type', 'place_name'),
                'sender': loc.get('sender', 'Unknown'),
                'timestamp': loc.get('timestamp'),
                'message_context': loc.get('message_context', ''),
                'confidence_score': int(loc.get('confidence_score', 50)),
                'lat': None,
                'lon': None,
                'geocoded': False
            })

        return locations

    def geocode_locations(self, locations):
        """
        Geocodifica le posizioni usando il provider configurato

        Args:
            locations: Lista di posizioni da geocodificare

        Returns:
            list: Posizioni con coordinate aggiunte
        """
        self.log("\n" + "="*60)
        self.log("🌍 FASE 2: GEOCODING POSIZIONI")
        self.log("="*60)

        provider = self.config.get('geocoding_provider', 'nominatim')
        self.log(f"🔧 Provider: {provider.upper()}")

        total = len(locations)
        geocoded_count = 0

        for i, location in enumerate(locations, 1):
            self.log(f"\n📍 Geocoding {i}/{total}: {location['location_text'][:50]}...")

            try:
                if provider == "nominatim":
                    lat, lon = self._geocode_nominatim(location['location_text'])
                else:  # google
                    lat, lon = self._geocode_google(location['location_text'])

                if lat and lon:
                    location['lat'] = lat
                    location['lon'] = lon
                    location['geocoded'] = True
                    geocoded_count += 1
                    self.log(f"   ✓ Coordinate: {lat:.6f}, {lon:.6f}")
                else:
                    self.log(f"   ✗ Posizione non trovata")
                    self.geocoding_errors.append({
                        'location_text': location['location_text'],
                        'chunk_id': location['chunk_id'],
                        'reason': 'Location not found by geocoding service'
                    })

            except Exception as e:
                self.log(f"   ✗ Errore: {str(e)}")
                self.geocoding_errors.append({
                    'location_text': location['location_text'],
                    'chunk_id': location['chunk_id'],
                    'reason': str(e)
                })

            # Rate limiting (1.5 sec per Nominatim, 0.5 per Google)
            delay = 1.5 if provider == "nominatim" else 0.5
            if i < total:  # Non aspettare dopo l'ultimo
                time.sleep(delay)

            # Aggiorna progress (50-100%)
            progress = 50 + int((i / total) * 50)
            self.update_progress(progress)

        self.log(f"\n📊 Geocoding completato: {geocoded_count}/{total} posizioni")
        if self.geocoding_errors:
            self.log(f"⚠️ {len(self.geocoding_errors)} posizioni non geocodificate")

        return locations

    def _geocode_nominatim(self, location_text):
        """
        Geocoding con Nominatim (OpenStreetMap)

        Args:
            location_text: Testo posizione da geocodificare

        Returns:
            tuple: (lat, lon) o (None, None) se non trovato
        """
        base_url = "https://nominatim.openstreetmap.org/search"
        params = {
            'q': location_text,
            'format': 'json',
            'limit': 1
        }
        headers = {
            'User-Agent': 'WhatsAppForensicAnalyzer/3.4.0'
        }

        response = requests.get(base_url, params=params, headers=headers, timeout=10)
        response.raise_for_status()

        data = response.json()
        if data and len(data) > 0:
            return float(data[0]['lat']), float(data[0]['lon'])

        return None, None

    def _geocode_google(self, location_text):
        """
        Geocoding con Google Maps Geocoding API

        Args:
            location_text: Testo posizione da geocodificare

        Returns:
            tuple: (lat, lon) o (None, None) se non trovato
        """
        api_key = self.config.get('google_api_key')
        if not api_key:
            raise ValueError("Google Maps API key not configured")

        base_url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            'address': location_text,
            'key': api_key
        }

        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()
        if data['status'] == 'OK' and len(data['results']) > 0:
            location = data['results'][0]['geometry']['location']
            return location['lat'], location['lng']

        return None, None

    def normalize_and_deduplicate(self, locations):
        """
        Normalizza e deduplica le posizioni

        Args:
            locations: Lista di posizioni geocodificate

        Returns:
            list: Posizioni normalizzate e deduplicate
        """
        self.log("\n" + "="*60)
        self.log("🔄 FASE 3: NORMALIZZAZIONE E DEDUPLICAZIONE")
        self.log("="*60)

        # Filtra solo posizioni geocodificate
        geocoded = [loc for loc in locations if loc['geocoded']]
        self.log(f"📍 Posizioni da processare: {len(geocoded)}")

        if not geocoded:
            return []

        # Raggruppa per coordinate simili (tolleranza ~100 metri)
        tolerance = 0.001  # Circa 100 metri
        groups = []

        for loc in geocoded:
            found_group = False
            for group in groups:
                # Controlla se coordinate simili
                ref = group[0]
                if (abs(loc['lat'] - ref['lat']) < tolerance and
                    abs(loc['lon'] - ref['lon']) < tolerance):
                    group.append(loc)
                    found_group = True
                    break

            if not found_group:
                groups.append([loc])

        self.log(f"🎯 Gruppi di posizioni simili: {len(groups)}")

        # Crea posizioni unificate
        unified_locations = []
        for i, group in enumerate(groups, 1):
            # Calcola coordinate medie
            avg_lat = sum(loc['lat'] for loc in group) / len(group)
            avg_lon = sum(loc['lon'] for loc in group) / len(group)

            # Usa il nome più comune/dettagliato
            location_names = [loc['location_text'] for loc in group]
            main_name = max(location_names, key=len)  # Usa il più dettagliato

            # Raccogli tutti gli eventi (chi/quando)
            events = []
            for loc in group:
                events.append({
                    'chunk_id': loc['chunk_id'],
                    'sender': loc['sender'],
                    'timestamp': loc['timestamp'],
                    'message_context': loc['message_context'],
                    'original_text': loc['location_text'],
                    'confidence_score': loc['confidence_score']
                })

            unified_locations.append({
                'location_id': i,
                'location_text': main_name,
                'lat': avg_lat,
                'lon': avg_lon,
                'location_type': group[0]['location_type'],
                'events': events,
                'event_count': len(events)
            })

            # Log se più eventi
            if len(events) > 1:
                self.log(f"   🔗 Gruppo {i}: '{main_name}' ({len(events)} eventi)")

        self.log(f"\n✅ Posizioni finali uniche: {len(unified_locations)}")

        return unified_locations

    def analyze(self):
        """
        Esegue l'analisi completa delle posizioni

        Returns:
            dict: Risultati analisi con locations, errors, stats
        """
        try:
            # Fase 1: Carica chunk
            self.log("📂 Caricamento chunk...")
            chunks = self.load_chunks(self.config['chunks_dir'])
            if not chunks:
                raise ValueError("Nessun chunk trovato")

            # Se modalità test attiva, limita i chunk
            original_total = len(chunks)
            if self.config.get('test_mode', False):
                max_chunks = self.config.get('test_chunks', 5)
                chunks = chunks[:max_chunks]
                self.log(f"🧪 MODALITÀ TEST ATTIVA: Analisi limitata ai primi {len(chunks)} chunk (su {original_total} totali)")
                self.log(f"   ⚠️ Questa è un'analisi preliminare per verificare l'estrazione posizioni")

            # Fase 2: Estrai posizioni con LLM
            raw_locations = self.extract_locations_from_chunks(chunks)
            if not raw_locations:
                self.log("\n⚠️ Nessuna posizione trovata nel documento")
                return {
                    'locations': [],
                    'geocoding_errors': [],
                    'stats': {
                        'total_chunks': len(chunks),
                        'locations_found': 0,
                        'locations_geocoded': 0,
                        'unique_locations': 0,
                        'total_events': 0
                    }
                }

            # Fase 3: Geocoding
            geocoded_locations = self.geocode_locations(raw_locations)

            # Fase 4: Normalizza e deduplica
            final_locations = self.normalize_and_deduplicate(geocoded_locations)

            # Statistiche
            stats = {
                'total_chunks': len(chunks),
                'locations_found': len(raw_locations),
                'locations_geocoded': len([l for l in geocoded_locations if l['geocoded']]),
                'unique_locations': len(final_locations),
                'total_events': sum(loc['event_count'] for loc in final_locations)
            }

            self.log("\n" + "="*60)
            if self.config.get('test_mode', False):
                self.log("✅ ANALISI PRELIMINARE COMPLETATA")
            else:
                self.log("✅ ANALISI COMPLETATA")
            self.log("="*60)
            self.log(f"📊 Statistiche:")
            self.log(f"   • Chunk analizzati: {stats['total_chunks']}")
            self.log(f"   • Posizioni trovate: {stats['locations_found']}")
            self.log(f"   • Posizioni geocodificate: {stats['locations_geocoded']}")
            self.log(f"   • Posizioni uniche: {stats['unique_locations']}")
            self.log(f"   • Eventi totali: {stats['total_events']}")

            if self.config.get('test_mode', False):
                self.log(f"\n   ⚠️ ATTENZIONE: Analisi limitata ai primi {self.config.get('test_chunks', 5)} chunk (su {original_total} totali)")
                self.log(f"   💡 Per analizzare tutti i chunk, disattiva la modalità test e rilancia")

            return {
                'locations': final_locations,
                'geocoding_errors': self.geocoding_errors,
                'stats': stats
            }

        except Exception as e:
            self.log(f"\n✗ ERRORE FATALE: {str(e)}")
            raise
