"""
Template HTML per il report multi-pagina
Contiene tutte le funzioni per generare le pagine HTML

© 2025 Luca Mercatanti - https://mercatanti.com
"""

from datetime import datetime
from pathlib import Path
import html
import re


def format_text_to_html(text):
    """
    Converte testo con formattazione Markdown/semplice in HTML semantico

    Supporta:
    - # Titolo → <h1>
    - ## Titolo → <h2>
    - ### Titolo → <h3>
    - #### Titolo → <h4>
    - **testo** → <strong>
    - *testo* → <em>
    - - item / * item → <ul><li>
    - 1. item → <ol><li>
    - Paragrafi separati da righe vuote
    """

    # Escape HTML per sicurezza
    text = html.escape(text)

    # Dividi in righe
    lines = text.split('\n')
    result = []
    in_ul = False
    in_ol = False
    in_paragraph = False
    current_paragraph = []

    for line in lines:
        stripped = line.strip()

        # Righe vuote chiudono paragrafi e liste
        if not stripped:
            if current_paragraph:
                result.append('<p>' + ' '.join(current_paragraph) + '</p>')
                current_paragraph = []
                in_paragraph = False
            if in_ul:
                result.append('</ul>')
                in_ul = False
            if in_ol:
                result.append('</ol>')
                in_ol = False
            continue

        # Headers H1 (# Titolo)
        if stripped.startswith('# ') and not stripped.startswith('##'):
            if current_paragraph:
                result.append('<p>' + ' '.join(current_paragraph) + '</p>')
                current_paragraph = []
            if in_ul:
                result.append('</ul>')
                in_ul = False
            if in_ol:
                result.append('</ol>')
                in_ol = False

            title = stripped[2:].strip()
            result.append(f'<h1>{title}</h1>')
            continue

        # Headers H2 (## Titolo)
        if stripped.startswith('## ') and not stripped.startswith('###'):
            if current_paragraph:
                result.append('<p>' + ' '.join(current_paragraph) + '</p>')
                current_paragraph = []
            if in_ul:
                result.append('</ul>')
                in_ul = False
            if in_ol:
                result.append('</ol>')
                in_ol = False

            title = stripped[3:].strip()
            result.append(f'<h2>{title}</h2>')
            continue

        # Headers H3 (### Titolo)
        if stripped.startswith('### ') and not stripped.startswith('####'):
            if current_paragraph:
                result.append('<p>' + ' '.join(current_paragraph) + '</p>')
                current_paragraph = []
            if in_ul:
                result.append('</ul>')
                in_ul = False
            if in_ol:
                result.append('</ol>')
                in_ol = False

            title = stripped[4:].strip()
            result.append(f'<h3>{title}</h3>')
            continue

        # Headers H4 (#### Titolo)
        if stripped.startswith('#### '):
            if current_paragraph:
                result.append('<p>' + ' '.join(current_paragraph) + '</p>')
                current_paragraph = []
            if in_ul:
                result.append('</ul>')
                in_ul = False
            if in_ol:
                result.append('</ol>')
                in_ol = False

            title = stripped[5:].strip()
            result.append(f'<h4>{title}</h4>')
            continue

        # Liste non ordinate (- item o * item)
        if stripped.startswith('- ') or stripped.startswith('* '):
            if current_paragraph:
                result.append('<p>' + ' '.join(current_paragraph) + '</p>')
                current_paragraph = []
            if in_ol:
                result.append('</ol>')
                in_ol = False
            if not in_ul:
                result.append('<ul>')
                in_ul = True

            item = stripped[2:].strip()
            item = format_inline_styles(item)
            result.append(f'<li>{item}</li>')
            continue

        # Liste ordinate (1. item, 2. item, ecc.)
        if re.match(r'^\d+\.\s+', stripped):
            if current_paragraph:
                result.append('<p>' + ' '.join(current_paragraph) + '</p>')
                current_paragraph = []
            if in_ul:
                result.append('</ul>')
                in_ul = False
            if not in_ol:
                result.append('<ol>')
                in_ol = True

            item = re.sub(r'^\d+\.\s+', '', stripped)
            item = format_inline_styles(item)
            result.append(f'<li>{item}</li>')
            continue

        # Testo normale - accumula in paragrafo
        if in_ul or in_ol:
            # Chiudi lista se il testo non è un item
            if in_ul:
                result.append('</ul>')
                in_ul = False
            if in_ol:
                result.append('</ol>')
                in_ol = False

        formatted_line = format_inline_styles(stripped)
        current_paragraph.append(formatted_line)

    # Chiudi eventuali elementi aperti
    if current_paragraph:
        result.append('<p>' + ' '.join(current_paragraph) + '</p>')
    if in_ul:
        result.append('</ul>')
    if in_ol:
        result.append('</ol>')

    return '\n'.join(result)


def format_inline_styles(text):
    """Formatta stili inline (grassetto, corsivo)"""
    # **grassetto** → <strong>
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)

    # *corsivo* → <em> (solo se non è già parte di **)
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<em>\1</em>', text)

    # __grassetto__ → <strong>
    text = re.sub(r'__(.+?)__', r'<strong>\1</strong>', text)

    # _corsivo_ → <em>
    text = re.sub(r'(?<!_)_(?!_)(.+?)(?<!_)_(?!_)', r'<em>\1</em>', text)

    return text


def get_shared_css():
    """CSS condiviso tra tutte le pagine"""
    return """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            background-color: white;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            overflow: hidden;
        }

        /* Header */
        header {
            background: linear-gradient(135deg, #075E54 0%, #128C7E 100%);
            color: white;
            padding: 30px 40px;
            position: relative;
        }

        header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 15px;
        }

        header .subtitle {
            font-size: 1.1em;
            opacity: 0.9;
        }

        /* Navigation */
        nav {
            background-color: #25D366;
            padding: 0;
            position: sticky;
            top: 0;
            z-index: 100;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }

        nav ul {
            list-style: none;
            display: flex;
            flex-wrap: wrap;
        }

        nav li {
            flex: 1;
            min-width: 150px;
        }

        nav a {
            display: block;
            padding: 15px 20px;
            color: white;
            text-decoration: none;
            text-align: center;
            transition: all 0.3s;
            border-right: 1px solid rgba(255,255,255,0.2);
        }

        nav a:hover {
            background-color: #128C7E;
            transform: translateY(-2px);
        }

        nav a.active {
            background-color: #075E54;
            font-weight: bold;
        }

        /* Main content */
        main {
            padding: 40px;
        }

        /* Cards */
        .card {
            background-color: #fff;
            border: 1px solid #e0e0e0;
            border-radius: 10px;
            padding: 25px;
            margin-bottom: 25px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            transition: all 0.3s;
        }

        .card:hover {
            box-shadow: 0 5px 20px rgba(0,0,0,0.15);
            transform: translateY(-2px);
        }

        /* Typography */
        h1 {
            color: #075E54;
            margin-bottom: 20px;
            font-size: 2.2em;
            border-bottom: 3px solid #25D366;
            padding-bottom: 10px;
        }

        h2 {
            color: #128C7E;
            margin-top: 30px;
            margin-bottom: 15px;
            font-size: 1.8em;
            border-left: 5px solid #25D366;
            padding-left: 15px;
        }

        h3 {
            color: #34B7F1;
            margin-top: 20px;
            margin-bottom: 10px;
            font-size: 1.4em;
        }

        /* Info boxes */
        .info-box {
            background: linear-gradient(135deg, #f0f8ff 0%, #e6f3ff 100%);
            border-left: 5px solid #34B7F1;
            padding: 20px;
            margin: 20px 0;
            border-radius: 8px;
        }

        .success-box {
            background: linear-gradient(135deg, #f0fff4 0%, #dcfce7 100%);
            border-left: 5px solid #25D366;
            padding: 20px;
            margin: 20px 0;
            border-radius: 8px;
        }

        .warning-box {
            background: linear-gradient(135deg, #fff8f0 0%, #ffedd5 100%);
            border-left: 5px solid #f59e0b;
            padding: 20px;
            margin: 20px 0;
            border-radius: 8px;
        }

        /* Tables */
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            background-color: white;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            border-radius: 8px;
            overflow: hidden;
        }

        th {
            background: linear-gradient(135deg, #075E54 0%, #128C7E 100%);
            color: white;
            padding: 15px;
            text-align: left;
            font-weight: 600;
        }

        td {
            padding: 12px 15px;
            border-bottom: 1px solid #e0e0e0;
        }

        tr:hover {
            background-color: #f5f5f5;
        }

        tr:last-child td {
            border-bottom: none;
        }

        /* Badges */
        .badge {
            display: inline-block;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 600;
            margin: 2px;
        }

        .badge-success {
            background-color: #25D366;
            color: white;
        }

        .badge-info {
            background-color: #34B7F1;
            color: white;
        }

        .badge-warning {
            background-color: #f59e0b;
            color: white;
        }

        .badge-primary {
            background-color: #075E54;
            color: white;
        }

        /* Buttons */
        .btn {
            display: inline-block;
            padding: 10px 20px;
            background-color: #25D366;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            transition: all 0.3s;
            border: none;
            cursor: pointer;
            font-size: 1em;
        }

        .btn:hover {
            background-color: #128C7E;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(37, 211, 102, 0.4);
        }

        /* Footer */
        footer {
            background-color: #075E54;
            color: white;
            text-align: center;
            padding: 25px;
            margin-top: 40px;
        }

        footer a {
            color: #25D366;
            text-decoration: none;
            font-weight: 600;
        }

        footer a:hover {
            text-decoration: underline;
        }

        /* Content formatting */
        .content {
            line-height: 1.8;
            color: #333;
            font-size: 1.05em;
        }

        .content h1 {
            color: #075E54;
            font-size: 2em;
            margin-top: 30px;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 3px solid #25D366;
        }

        .content h2 {
            color: #128C7E;
            font-size: 1.6em;
            margin-top: 25px;
            margin-bottom: 12px;
            padding-left: 15px;
            border-left: 5px solid #25D366;
        }

        .content h3 {
            color: #34B7F1;
            font-size: 1.3em;
            margin-top: 20px;
            margin-bottom: 10px;
        }

        .content h4 {
            color: #666;
            font-size: 1.1em;
            margin-top: 15px;
            margin-bottom: 8px;
            font-weight: 600;
        }

        .content p {
            margin-bottom: 15px;
            text-align: justify;
        }

        .content ul, .content ol {
            margin: 15px 0;
            padding-left: 30px;
        }

        .content li {
            margin-bottom: 8px;
            line-height: 1.6;
        }

        .content strong {
            color: #075E54;
            font-weight: 600;
        }

        .content em {
            font-style: italic;
            color: #555;
        }

        /* Chunk list */
        .chunk-list {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }

        .chunk-item {
            background: white;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            padding: 15px;
            text-align: center;
            transition: all 0.3s;
        }

        .chunk-item:hover {
            border-color: #25D366;
            transform: scale(1.05);
            box-shadow: 0 5px 15px rgba(37, 211, 102, 0.3);
        }

        .chunk-item a {
            color: #075E54;
            text-decoration: none;
            font-weight: 600;
            font-size: 1.1em;
        }

        /* Responsive */
        @media (max-width: 768px) {
            nav ul {
                flex-direction: column;
            }

            nav li {
                min-width: 100%;
            }

            nav a {
                border-right: none;
                border-bottom: 1px solid rgba(255,255,255,0.2);
            }

            main {
                padding: 20px;
            }

            header h1 {
                font-size: 1.8em;
            }

            .chunk-list {
                grid-template-columns: 1fr;
            }
        }

        /* Animations */
        @keyframes fadeIn {
            from {
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        .card {
            animation: fadeIn 0.5s ease-out;
        }

        /* Scroll to top button */
        .scroll-top {
            position: fixed;
            bottom: 30px;
            right: 30px;
            background-color: #25D366;
            color: white;
            width: 50px;
            height: 50px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
            transition: all 0.3s;
            z-index: 1000;
        }

        .scroll-top:hover {
            background-color: #128C7E;
            transform: translateY(-5px);
        }
    """


def create_navigation(active_page='index'):
    """Crea la barra di navigazione"""
    pages = {
        'index': ('index.html', '🏠 Home'),
        'config': ('configurazione.html', '⚙️ Configurazione'),
        'chunks': ('analisi_chunks.html', '📊 Analisi Chunk'),
    }

    nav_html = '<nav><ul>'
    for page_id, (url, label) in pages.items():
        active_class = ' class="active"' if page_id == active_page else ''
        nav_html += f'<li><a href="{url}"{active_class}>{label}</a></li>'
    nav_html += '</ul></nav>'

    return nav_html


def create_header(title, subtitle=''):
    """Crea l'header della pagina"""
    subtitle_html = f'<p class="subtitle">{subtitle}</p>' if subtitle else ''

    return f"""
    <header>
        <h1>{title}</h1>
        {subtitle_html}
    </header>
    """


def create_footer():
    """Crea il footer della pagina"""
    return f"""
    <footer>
        <p><strong>WhatsApp Forensic Analyzer</strong> - Report Generato il {datetime.now().strftime('%d/%m/%Y alle %H:%M:%S')}</p>
        <p>© 2025 <a href="https://mercatanti.com" target="_blank">Luca Mercatanti</a> - Tutti i diritti riservati</p>
    </footer>

    <!-- Scroll to top button -->
    <div class="scroll-top" onclick="window.scrollTo({{top: 0, behavior: 'smooth'}})">
        ↑
    </div>
    """


def create_html_page(title, content, active_page='index', subtitle=''):
    """Crea una pagina HTML completa"""
    return f"""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - WhatsApp Forensic Analyzer</title>
    <link rel="stylesheet" href="styles.css">
</head>
<body>
    <div class="container">
        {create_header(title, subtitle)}
        {create_navigation(active_page)}
        <main>
            {content}
        </main>
        {create_footer()}
    </div>
</body>
</html>"""


# ===== FUNZIONI PER REPORT CHAT (v3.2) =====

def create_chat_index_page(chat_summaries, output_dir, get_display_name_func):
    """
    Crea la pagina indice per il report chat (index_chat.html)

    Args:
        chat_summaries: Lista di dict {'chat': chat_obj, 'summary': summary_text}
        output_dir: Directory output (report_chat/)
        get_display_name_func: Funzione per ottenere il nome visualizzato della chat

    Returns:
        Path del file index_chat.html creato
    """
    # Separa 1v1 da gruppi
    chats_1v1 = [item for item in chat_summaries if item['chat']['type'] == '1v1']
    chats_group = [item for item in chat_summaries if item['chat']['type'] == 'group']

    # Statistiche
    stats_html = f"""
    <div class="card success-box">
        <h2>📊 Statistiche</h2>
        <table>
            <tr>
                <th>Chat 1v1</th>
                <td><span class="badge badge-info">{len(chats_1v1)}</span></td>
            </tr>
            <tr>
                <th>Gruppi</th>
                <td><span class="badge badge-success">{len(chats_group)}</span></td>
            </tr>
            <tr>
                <th>Totale conversazioni</th>
                <td><span class="badge badge-primary">{len(chat_summaries)}</span></td>
            </tr>
        </table>
    </div>
    """

    # Sezione Chat 1v1
    chats_1v1_html = ""
    if chats_1v1:
        chats_1v1_html = """
        <div class="card">
            <h2>💬 Chat Individuali (1v1)</h2>
            <div class="chunk-list">
        """

        for item in chats_1v1:
            chat = item['chat']
            display_name = get_display_name_func(chat)
            safe_filename = f"chat_{chat['chat_id']}_{sanitize_filename(display_name)}.html"

            num_participants = len(chat.get('participants', []))
            num_chunks = len(chat.get('chunks', []))
            num_attachments = chat['metadata'].get('num_attachments', 0)
            start_time = chat['metadata'].get('start_time', 'N/A')
            last_activity = chat['metadata'].get('last_activity', 'N/A')

            chats_1v1_html += f"""
            <div class="chunk-item">
                <a href="{safe_filename}">
                    <strong>{html.escape(display_name)}</strong><br>
                    <small style="color: #666;">
                        👤 {num_participants} partecipanti<br>
                        🧩 {num_chunks} chunk<br>
                        📎 {num_attachments} allegati<br>
                        📅 {format_date_range(start_time, last_activity)}
                    </small>
                </a>
            </div>
            """

        chats_1v1_html += """
            </div>
        </div>
        """

    # Sezione Gruppi
    chats_group_html = ""
    if chats_group:
        chats_group_html = """
        <div class="card">
            <h2>👥 Gruppi</h2>
            <div class="chunk-list">
        """

        for item in chats_group:
            chat = item['chat']
            display_name = get_display_name_func(chat)
            safe_filename = f"chat_{chat['chat_id']}_{sanitize_filename(display_name)}.html"

            num_participants = len(chat.get('participants', []))
            num_chunks = len(chat.get('chunks', []))
            num_attachments = chat['metadata'].get('num_attachments', 0)
            start_time = chat['metadata'].get('start_time', 'N/A')
            last_activity = chat['metadata'].get('last_activity', 'N/A')

            chats_group_html += f"""
            <div class="chunk-item">
                <a href="{safe_filename}">
                    <strong>{html.escape(display_name)}</strong><br>
                    <small style="color: #666;">
                        👥 {num_participants} partecipanti<br>
                        🧩 {num_chunks} chunk<br>
                        📎 {num_attachments} allegati<br>
                        📅 {format_date_range(start_time, last_activity)}
                    </small>
                </a>
            </div>
            """

        chats_group_html += """
            </div>
        </div>
        """

    # Link al report principale
    back_link_html = """
    <div class="card info-box">
        <h3>🔗 Navigazione</h3>
        <p>
            <a href="../report_html/index.html" class="btn">← Torna al Report Principale</a>
        </p>
    </div>
    """

    content = stats_html + chats_1v1_html + chats_group_html + back_link_html

    html_content = f"""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Report per Chat - WhatsApp Forensic Analyzer</title>
    <link rel="stylesheet" href="styles.css">
</head>
<body>
    <div class="container">
        {create_header('💬 Report per Chat', 'Riassunti individuali delle conversazioni')}
        <main>
            {content}
        </main>
        {create_footer()}
    </div>
</body>
</html>"""

    index_file = Path(output_dir) / "index_chat.html"
    with open(index_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

    # Crea anche il CSS
    css_file = Path(output_dir) / "styles.css"
    with open(css_file, 'w', encoding='utf-8') as f:
        f.write(get_shared_css())

    return str(index_file)


def create_chat_detail_page(chat, summary, output_dir, get_display_name_func):
    """
    Crea la pagina dettaglio per una singola chat

    Args:
        chat: Dizionario con metadati chat
        summary: Testo riassunto generato dall'AI
        output_dir: Directory output (report_chat/)
        get_display_name_func: Funzione per ottenere il nome visualizzato

    Returns:
        Path del file creato
    """
    display_name = get_display_name_func(chat)
    safe_filename = f"chat_{chat['chat_id']}_{sanitize_filename(display_name)}.html"

    # Info chat
    chat_type = "💬 Chat 1v1" if chat['type'] == '1v1' else "👥 Gruppo"
    participants_list = '<br>'.join([
        f"{'👑 ' if p.get('owner') else '👤 '}{html.escape(p.get('name', p.get('id', 'Sconosciuto')))}"
        for p in chat.get('participants', [])
    ])

    info_html = f"""
    <div class="card info-box">
        <h2>ℹ️ Informazioni Chat</h2>
        <table>
            <tr>
                <th>Tipo</th>
                <td><span class="badge {'badge-info' if chat['type'] == '1v1' else 'badge-success'}">{chat_type}</span></td>
            </tr>
            <tr>
                <th>Partecipanti</th>
                <td>{participants_list}</td>
            </tr>
            <tr>
                <th>Periodo</th>
                <td>{chat['metadata'].get('start_time', 'N/A')} → {chat['metadata'].get('last_activity', 'N/A')}</td>
            </tr>
            <tr>
                <th>Allegati</th>
                <td>{chat['metadata'].get('num_attachments', 0)}</td>
            </tr>
            <tr>
                <th>Chunk analizzati</th>
                <td>{len(chat.get('chunks', []))}</td>
            </tr>
        </table>
    </div>
    """

    # Riassunto AI (converti markdown → HTML)
    summary_html = format_text_to_html(summary)

    summary_content = f"""
    <div class="card">
        <h2>📝 Riassunto Conversazione</h2>
        <div class="content">
            {summary_html}
        </div>
    </div>
    """

    # Link ai chunk originali
    chunks_links = []
    for chunk_num in chat.get('chunks', []):
        chunks_links.append(f'<a href="../report_html/chunk_{chunk_num:03d}.html" class="btn">Chunk {chunk_num}</a>')

    chunks_html = f"""
    <div class="card">
        <h3>🔗 Analisi Dettagliate Chunk</h3>
        <p>
            {' '.join(chunks_links)}
        </p>
    </div>
    """

    # Link navigazione
    nav_html = """
    <div class="card info-box">
        <p>
            <a href="index_chat.html" class="btn">← Torna all'Elenco Chat</a>
            <a href="../report_html/index.html" class="btn">🏠 Report Principale</a>
        </p>
    </div>
    """

    content = nav_html + info_html + summary_content + chunks_html + nav_html

    html_content = f"""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Chat: {html.escape(display_name)} - WhatsApp Forensic Analyzer</title>
    <link rel="stylesheet" href="styles.css">
</head>
<body>
    <div class="container">
        {create_header(f'{chat_type}: {html.escape(display_name)}', 'Riassunto conversazione')}
        <main>
            {content}
        </main>
        {create_footer()}
    </div>
</body>
</html>"""

    detail_file = Path(output_dir) / safe_filename
    with open(detail_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

    return str(detail_file)


def sanitize_filename(name):
    """Rende un nome sicuro per un filename"""
    # Rimuovi caratteri speciali e spazi
    safe_name = re.sub(r'[^\w\s-]', '', name)
    safe_name = re.sub(r'[\s]+', '_', safe_name)
    safe_name = safe_name.strip('_').lower()

    # Limita lunghezza
    if len(safe_name) > 50:
        safe_name = safe_name[:50]

    return safe_name or 'unnamed'


def format_date_range(start, end):
    """Formatta un range di date in modo compatto"""
    if start == 'N/A' or not start:
        return 'N/A'

    # Estrai solo la data (rimuovi ora)
    try:
        start_date = start.split()[0] if start else ''
        end_date = end.split()[0] if end and end != 'N/A' else ''

        if start_date and end_date and start_date != end_date:
            return f"{start_date} → {end_date}"
        elif start_date:
            return start_date
        else:
            return 'N/A'
    except:
        return start if start else 'N/A'
