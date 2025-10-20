"""
Modulo per il processamento e segmentazione di report WhatsApp (PDF)
Specializzato per export da Cellebrite, UFED, Oxygen Forensics

© 2025 Luca Mercatanti - https://mercatanti.com
"""

import PyPDF2
import os
import json
import re
from pathlib import Path
from datetime import datetime

class WhatsAppProcessor:
    def __init__(self, pdf_path, max_chars=15000, chunk_format='txt',
                 extract_images=False, extraction_folder=None):
        self.pdf_path = pdf_path
        self.max_chars = max_chars
        self.text_pages = []
        self.chunk_format = chunk_format  # 'txt' o 'json'
        self.extract_images = extract_images
        self.extraction_folder = extraction_folder

    def get_statistics(self):
        """Ottiene statistiche sul PDF senza estrarre tutto il testo"""
        try:
            with open(self.pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                total_pages = len(pdf_reader.pages)

                # Campiona alcune pagine per stimare la lunghezza media
                sample_size = min(10, total_pages)
                total_chars = 0

                for i in range(0, total_pages, max(1, total_pages // sample_size)):
                    page = pdf_reader.pages[i]
                    text = page.extract_text()
                    total_chars += len(text)

                avg_chars_per_page = total_chars / sample_size if sample_size > 0 else 2000

                # Stima numero di chunk
                total_chars_estimate = avg_chars_per_page * total_pages
                estimated_chunks = int(total_chars_estimate / self.max_chars) + 1

                return {
                    'total_pages': total_pages,
                    'avg_chars_per_page': int(avg_chars_per_page),
                    'estimated_chunks': estimated_chunks
                }

        except Exception as e:
            raise Exception(f"Errore nell'analisi del PDF: {str(e)}")

    def extract_text(self, progress_callback=None):
        """Estrae il testo da tutte le pagine del PDF"""
        try:
            with open(self.pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                total_pages = len(pdf_reader.pages)

                for page_num in range(total_pages):
                    page = pdf_reader.pages[page_num]
                    text = page.extract_text()

                    self.text_pages.append({
                        'page_num': page_num + 1,
                        'text': text,
                        'char_count': len(text)
                    })

                    if progress_callback:
                        progress = ((page_num + 1) / total_pages) * 30  # 30% per estrazione
                        progress_callback(progress)

            return self.text_pages

        except Exception as e:
            raise Exception(f"Errore nell'estrazione del testo: {str(e)}")

    def extract_image_paths(self, text):
        """Estrae i path delle immagini dal testo del PDF Cellebrite"""
        images = []

        # Pattern per trovare i path delle immagini nei report Cellebrite
        # Esempio: EXTRACTION_FFS.zip/data/media/0/Android/media/com.whatsapp/WhatsApp/Media/WhatsApp Images/Sent/IMG-20250505-WA0001.jpg
        pattern = r'EXTRACTION_FFS\.zip/(.*?\.(?:jpg|jpeg|png|gif|mp4|webp))'

        matches = re.findall(pattern, text, re.IGNORECASE)

        for match in matches:
            # Ricostruisci il path completo se abbiamo la cartella di estrazione
            image_info = {
                'cellebrite_path': match,
                'filename': os.path.basename(match),
                'resolved_path': None,
                'exists': False
            }

            if self.extraction_folder:
                # Prova a trovare il file
                full_path = os.path.join(self.extraction_folder, match)
                if os.path.exists(full_path):
                    image_info['resolved_path'] = full_path
                    image_info['exists'] = True
                    try:
                        image_info['size_bytes'] = os.path.getsize(full_path)
                    except:
                        pass

            images.append(image_info)

        # Rimuovi duplicati
        unique_images = []
        seen = set()
        for img in images:
            if img['filename'] not in seen:
                seen.add(img['filename'])
                unique_images.append(img)

        return unique_images

    def create_chunks(self):
        """Crea chunk intelligenti dal testo estratto"""
        chunks = []
        current_chunk = {
            'text': '',
            'pages': [],
            'char_count': 0,
            'images': []
        }

        for page_data in self.text_pages:
            page_text = page_data['text']
            page_num = page_data['page_num']

            # Estrai immagini se richiesto
            page_images = []
            if self.extract_images:
                page_images = self.extract_image_paths(page_text)

            # Se aggiungere questa pagina supera il limite, salva il chunk corrente
            if current_chunk['char_count'] + len(page_text) > self.max_chars and current_chunk['text']:
                chunks.append(current_chunk)
                current_chunk = {
                    'text': '',
                    'pages': [],
                    'char_count': 0,
                    'images': []
                }

            # Aggiungi la pagina al chunk corrente
            current_chunk['text'] += f"\n\n--- PAGINA {page_num} ---\n\n{page_text}"
            current_chunk['pages'].append(page_num)
            current_chunk['char_count'] += len(page_text)
            current_chunk['images'].extend(page_images)

        # Aggiungi l'ultimo chunk
        if current_chunk['text']:
            chunks.append(current_chunk)

        return chunks

    def save_chunks(self, chunks, output_dir, progress_callback=None):
        """Salva i chunk in file separati (TXT o JSON)"""
        os.makedirs(output_dir, exist_ok=True)

        saved_chunks = []

        for i, chunk in enumerate(chunks, 1):
            if self.chunk_format == 'json':
                # Formato JSON
                filename = Path(output_dir) / f"chunk_{i:03d}.json"

                chunk_data = {
                    'chunk_id': i,
                    'total_chunks': len(chunks),
                    'format_version': '1.0',
                    'page_range': [chunk['pages'][0], chunk['pages'][-1]],
                    'text': chunk['text'],
                    'char_count': chunk['char_count'],
                    'token_estimate': chunk['char_count'] // 4,
                    'images': chunk.get('images', []),
                    'metadata': {
                        'created_at': datetime.now().isoformat(),
                        'source_pdf': os.path.basename(self.pdf_path),
                        'has_images': len(chunk.get('images', [])) > 0
                    }
                }

                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(chunk_data, f, indent=2, ensure_ascii=False)

            else:
                # Formato TXT (classico)
                filename = Path(output_dir) / f"chunk_{i:03d}.txt"

                with open(filename, 'w', encoding='utf-8') as f:
                    header = f"""{'='*60}
CHUNK {i} di {len(chunks)}
Pagine: {chunk['pages'][0]}-{chunk['pages'][-1]}
Caratteri: {chunk['char_count']:,}
Token stimati: ~{chunk['char_count']//4:,}
{'='*60}

{chunk['text']}
"""
                    f.write(header)

            saved_chunks.append({
                'path': str(filename),
                'chunk_num': i,
                'pages': chunk['pages'],
                'char_count': chunk['char_count'],
                'format': self.chunk_format,
                'images_count': len(chunk.get('images', []))
            })

            if progress_callback:
                progress = 30 + ((i / len(chunks)) * 20)  # 30-50%
                progress_callback(progress)

        return saved_chunks

    def split_pdf(self, output_dir='pdf_chunks', progress_callback=None):
        """Processo completo: estrai, crea chunk e salva"""

        # Estrai testo
        self.extract_text(progress_callback)

        # Crea chunk
        chunks = self.create_chunks()

        # Salva chunk
        saved_chunks = self.save_chunks(chunks, output_dir, progress_callback)

        return saved_chunks
