"""
Dashboard Manager - Gestione dashboard centrale REPORT/index.html
Rileva automaticamente report disponibili e genera interfaccia unificata

© 2025 Luca Mercatanti - https://mercatanti.com
"""

import os
import json
from pathlib import Path
from datetime import datetime


class DashboardManager:
    """Gestisce la dashboard centrale per tutti i report generati"""

    def __init__(self, output_dir):
        """
        Inizializza il manager della dashboard

        Args:
            output_dir: Cartella output principale (es. output_20251028_153045/)
        """
        self.output_dir = Path(output_dir)
        self.report_dir = self.output_dir / "REPORT"
        self.dashboard_data_file = self.report_dir / ".dashboard_data.json"

        # Dati dei report registrati
        self.reports_data = self._load_dashboard_data()

    def _load_dashboard_data(self):
        """Carica dati dashboard salvati"""
        if self.dashboard_data_file.exists():
            try:
                with open(self.dashboard_data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass

        # Default vuoto
        return {
            'generated_at': datetime.now().isoformat(),
            'reports': {}
        }

    def _save_dashboard_data(self):
        """Salva dati dashboard"""
        self.report_dir.mkdir(exist_ok=True)
        with open(self.dashboard_data_file, 'w', encoding='utf-8') as f:
            json.dump(self.reports_data, f, indent=2, ensure_ascii=False)

    def register_report(self, report_type, stats):
        """
        Registra un report come disponibile

        Args:
            report_type: Tipo report ('main', 'chat', 'locations')
            stats: Dizionario con statistiche del report
        """
        self.reports_data['reports'][report_type] = {
            'generated_at': datetime.now().isoformat(),
            'stats': stats
        }
        self._save_dashboard_data()

    def detect_available_reports(self):
        """
        Rileva automaticamente quali report esistono

        Returns:
            dict: {'main': True/False, 'chat': True/False, 'locations': True/False}
        """
        available = {
            'main': (self.report_dir / "analisi_principale" / "index.html").exists(),
            'chat': (self.report_dir / "report_chat" / "index.html").exists(),
            'locations': (self.report_dir / "report_posizioni" / "index.html").exists()
        }
        return available

    def generate_suggestions_box(self):
        """
        Genera HTML del box suggerimenti post-elaborazione (versione compatta)

        Returns:
            str: HTML del banner compatto
        """
        available = self.detect_available_reports()

        missing_reports = []

        # Report Chat
        if not available['chat']:
            missing_reports.append({
                'icon': '💬',
                'title': 'Report per Chat',
                'description': 'Genera riassunti dedicati per ogni conversazione rilevata'
            })

        # Report Posizioni
        if not available['locations']:
            missing_reports.append({
                'icon': '🗺️',
                'title': 'Analisi Posizioni Geografiche',
                'description': 'Estrai e mappa tutte le location menzionate'
            })

        # Funzioni sempre disponibili
        always_available = [
            {'icon': '🔍', 'title': 'Ricerca Rapida', 'description': 'Query mirate sulle analisi esistenti'},
            {'icon': '🔁', 'title': 'Re-Analisi Avanzata', 'description': 'Filtra e rianalizza chunk specifici'}
        ]

        # Se tutti i report generabili sono stati creati
        if not missing_reports:
            return """
            <div class="info-banner success-banner">
                <div class="info-banner-content">
                    <span class="info-icon">✅</span>
                    <div class="info-text">
                        <strong>Tutte le analisi completate!</strong> -
                        Puoi comunque utilizzare <em>Ricerca Rapida</em> e <em>Re-Analisi Avanzata</em> dal menu Post-Elaborazione.
                    </div>
                </div>
            </div>
            """

        # Conta report mancanti
        num_missing = len(missing_reports)
        missing_text = f"{num_missing} analisi aggiuntive disponibili" if num_missing > 1 else "1 analisi aggiuntiva disponibile"

        # Genera lista dettagli per sezione espandibile
        details_html = ""

        if missing_reports:
            details_html += "<h4>📋 Report non ancora generati:</h4><ul>"
            for report in missing_reports:
                details_html += f"<li>{report['icon']} <strong>{report['title']}</strong> - {report['description']}</li>"
            details_html += "</ul>"

        details_html += "<h4>✓ Funzioni sempre disponibili:</h4><ul>"
        for func in always_available:
            details_html += f"<li>{func['icon']} <strong>{func['title']}</strong> - {func['description']}</li>"
        details_html += "</ul>"

        details_html += '<p class="suggestions-footer"><strong>💡 Come utilizzare:</strong> Torna alla GUI principale → Menu <em>Post-Elaborazione</em> → Seleziona l\'analisi desiderata</p>'

        # HTML banner compatto
        html = f"""
        <div class="info-banner">
            <div class="info-banner-content">
                <span class="info-icon">💡</span>
                <div class="info-text">
                    <strong>Post-Elaborazione Disponibile</strong> -
                    {missing_text}. Puoi estrarre ulteriori dati utilizzando le funzioni di Post-Elaborazione dalla GUI.
                </div>
                <a href="javascript:void(0);" class="info-link" onclick="toggleSuggestions()">Scopri di più →</a>
            </div>
        </div>

        <div id="suggestions-detail" class="suggestions-detail" style="display: none;">
            <div class="suggestions-compact">
                {details_html}
            </div>
        </div>

        <script>
        function toggleSuggestions() {{
            var detail = document.getElementById('suggestions-detail');
            var link = document.querySelector('.info-link');
            if (detail.style.display === 'none') {{
                detail.style.display = 'block';
                link.textContent = 'Nascondi ↑';
            }} else {{
                detail.style.display = 'none';
                link.textContent = 'Scopri di più →';
            }}
        }}
        </script>
        """

        return html

    def generate_report_cards(self):
        """
        Genera le card dei report disponibili per la dashboard

        Returns:
            str: HTML delle card report
        """
        available = self.detect_available_reports()
        cards_html = ""

        # Card Analisi Principale (sempre presente)
        if available['main']:
            main_stats = self.reports_data['reports'].get('main', {}).get('stats', {})
            chunks = main_stats.get('chunks_analyzed', 'N/A')
            total_chunks = main_stats.get('total_chunks', 'N/A')
            model = main_stats.get('model', 'N/A')
            images = main_stats.get('analyze_images', False)

            cards_html += f"""
            <div class="report-card available">
                <div class="card-icon">📱</div>
                <div class="card-header">
                    <h2>Analisi Principale</h2>
                    <span class="badge badge-success">✓ Disponibile</span>
                </div>
                <p class="card-description">Riassunto completo AI del documento analizzato</p>
                <ul class="card-stats">
                    <li><strong>Modello:</strong> {model}</li>
                    <li><strong>Chunk:</strong> {chunks}/{total_chunks}</li>
                    <li><strong>Immagini:</strong> {'✓ Analizzate' if images else '✗ Non analizzate'}</li>
                </ul>
                <div class="card-actions">
                    <a href="analisi_principale/index.html" class="btn btn-primary">Apri Report →</a>
                    <a href="analisi_principale/configurazione.html" class="btn btn-secondary">⚙️ Config</a>
                </div>
            </div>
            """

        # Card Report Chat
        if available['chat']:
            chat_stats = self.reports_data['reports'].get('chat', {}).get('stats', {})
            chats_1v1 = chat_stats.get('chats_1v1', 0)
            chats_group = chat_stats.get('chats_group', 0)
            total_chats = chats_1v1 + chats_group

            cards_html += f"""
            <div class="report-card available">
                <div class="card-icon">💬</div>
                <div class="card-header">
                    <h2>Report Conversazioni</h2>
                    <span class="badge badge-success">✓ Disponibile</span>
                </div>
                <p class="card-description">Riassunti dedicati per ogni chat rilevata nel documento</p>
                <ul class="card-stats">
                    <li><strong>Chat 1v1:</strong> {chats_1v1}</li>
                    <li><strong>Gruppi:</strong> {chats_group}</li>
                    <li><strong>Totale:</strong> {total_chats} conversazioni</li>
                </ul>
                <div class="card-actions">
                    <a href="report_chat/index.html" class="btn btn-primary">Apri Report →</a>
                </div>
            </div>
            """
        else:
            cards_html += """
            <div class="report-card unavailable">
                <div class="card-icon">💬</div>
                <div class="card-header">
                    <h2>Report Conversazioni</h2>
                    <span class="badge badge-secondary">Non generato</span>
                </div>
                <p class="card-description">Riassunti dedicati per ogni chat rilevata</p>
                <div class="card-info">
                    <em>Genera questo report dal menu Post-Elaborazione della GUI</em>
                </div>
            </div>
            """

        # Card Posizioni Geografiche
        if available['locations']:
            loc_stats = self.reports_data['reports'].get('locations', {}).get('stats', {})
            unique_locations = loc_stats.get('unique_locations', 0)
            total_events = loc_stats.get('total_events', 0)
            geocoded = loc_stats.get('locations_geocoded', 0)
            found = loc_stats.get('locations_found', 0)

            cards_html += f"""
            <div class="report-card available">
                <div class="card-icon">🗺️</div>
                <div class="card-header">
                    <h2>Posizioni Geografiche</h2>
                    <span class="badge badge-success">✓ Disponibile</span>
                </div>
                <p class="card-description">Mappa interattiva con location geocodificate</p>
                <ul class="card-stats">
                    <li><strong>Posizioni uniche:</strong> {unique_locations}</li>
                    <li><strong>Eventi totali:</strong> {total_events}</li>
                    <li><strong>Geocodificate:</strong> {geocoded}/{found}</li>
                </ul>
                <div class="card-actions">
                    <a href="report_posizioni/index.html" class="btn btn-primary">Apri Mappa →</a>
                </div>
            </div>
            """
        else:
            cards_html += """
            <div class="report-card unavailable">
                <div class="card-icon">🗺️</div>
                <div class="card-header">
                    <h2>Posizioni Geografiche</h2>
                    <span class="badge badge-secondary">Non generato</span>
                </div>
                <p class="card-description">Mappa interattiva delle location menzionate</p>
                <div class="card-info">
                    <em>Genera questo report dal menu Post-Elaborazione della GUI</em>
                </div>
            </div>
            """

        return cards_html

    def generate_stats_overview(self):
        """
        Genera statistiche aggregate panoramiche

        Returns:
            str: HTML statistiche overview
        """
        main_stats = self.reports_data['reports'].get('main', {}).get('stats', {})
        chat_stats = self.reports_data['reports'].get('chat', {}).get('stats', {})
        loc_stats = self.reports_data['reports'].get('locations', {}).get('stats', {})

        chunks = main_stats.get('chunks_analyzed', 0)
        total_chats = chat_stats.get('chats_1v1', 0) + chat_stats.get('chats_group', 0)
        locations = loc_stats.get('unique_locations', 0)

        html = f"""
        <section class="stats-overview">
            <div class="stat-box">
                <span class="stat-icon">📄</span>
                <span class="stat-value">{chunks}</span>
                <span class="stat-label">Chunk analizzati</span>
            </div>
            <div class="stat-box">
                <span class="stat-icon">💬</span>
                <span class="stat-value">{total_chats if total_chats > 0 else '-'}</span>
                <span class="stat-label">Chat rilevate</span>
            </div>
            <div class="stat-box">
                <span class="stat-icon">🗺️</span>
                <span class="stat-value">{locations if locations > 0 else '-'}</span>
                <span class="stat-label">Posizioni</span>
            </div>
        </section>
        """

        return html

    def generate_dashboard(self):
        """
        Genera la dashboard HTML completa (REPORT/index.html)

        Returns:
            str: Path del file index.html generato
        """
        # Crea cartella REPORT
        self.report_dir.mkdir(exist_ok=True)

        # Genera componenti
        suggestions_box = self.generate_suggestions_box()
        stats_overview = self.generate_stats_overview()
        report_cards = self.generate_report_cards()

        # CSS personalizzato per dashboard
        dashboard_css = self._get_dashboard_css()

        # HTML completo
        html_content = f"""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard Analisi Forense WhatsApp</title>
    <link rel="stylesheet" href="styles.css">
    <style>
        {dashboard_css}
    </style>
</head>
<body>
    <div class="container dashboard-container">
        <!-- Header -->
        <header class="dashboard-header">
            <h1>📊 Dashboard Analisi Forense WhatsApp</h1>
            <p class="subtitle">Report generato il {datetime.now().strftime('%d/%m/%Y alle %H:%M:%S')}</p>
        </header>

        <main>
            <!-- Box Suggerimenti Post-Elaborazione -->
            {suggestions_box}

            <!-- Statistiche Overview -->
            {stats_overview}

            <!-- Grid Report Disponibili -->
            <section class="reports-section">
                <h2 class="section-title">📋 Report Disponibili</h2>
                <div class="reports-grid">
                    {report_cards}
                </div>
            </section>

            <!-- Quick Links -->
            <section class="quick-links-section">
                <h3>🔗 Link Rapidi</h3>
                <div class="quick-links">
                    <a href="analisi_principale/analisi_chunks.html" class="quick-link">
                        <span class="link-icon">📊</span>
                        <span>Tutte le analisi chunk</span>
                    </a>
                    <a href="analisi_principale/configurazione.html" class="quick-link">
                        <span class="link-icon">⚙️</span>
                        <span>Configurazione completa</span>
                    </a>
                </div>
            </section>
        </main>

        <!-- Footer -->
        <footer>
            <p><strong>AI Forensics Report Analyzer</strong> - © 2025 <a href="https://mercatanti.com" target="_blank">Luca Mercatanti</a></p>
        </footer>
    </div>
</body>
</html>"""

        # Salva file
        dashboard_file = self.report_dir / "index.html"
        with open(dashboard_file, 'w', encoding='utf-8') as f:
            f.write(html_content)

        # Genera anche CSS base condiviso
        self._create_shared_css()

        return str(dashboard_file)

    def _get_dashboard_css(self):
        """CSS specifico per la dashboard"""
        return """
        /* Dashboard specific styles */
        .dashboard-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            text-align: center;
        }

        .dashboard-header h1 {
            font-size: 2.8em;
        }

        /* Stats Overview */
        .stats-overview {
            display: flex;
            justify-content: center;
            gap: 40px;
            margin: 40px 0;
            flex-wrap: wrap;
        }

        .stat-box {
            background: white;
            border-radius: 15px;
            padding: 30px;
            text-align: center;
            min-width: 180px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            transition: all 0.3s;
        }

        .stat-box:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.15);
        }

        .stat-icon {
            font-size: 3em;
            display: block;
            margin-bottom: 10px;
        }

        .stat-value {
            font-size: 2.5em;
            font-weight: bold;
            color: #667eea;
            display: block;
            margin-bottom: 5px;
        }

        .stat-label {
            font-size: 0.95em;
            color: #666;
            display: block;
        }

        /* Info Banner Compatto */
        .info-banner {
            background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
            border-left: 4px solid #2196f3;
            padding: 15px 25px;
            margin: 20px 0;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }

        .info-banner.success-banner {
            background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%);
            border-left: 4px solid #4caf50;
        }

        .info-banner-content {
            display: flex;
            align-items: center;
            gap: 15px;
            width: 100%;
        }

        .info-icon {
            font-size: 1.8em;
            flex-shrink: 0;
        }

        .info-text {
            flex: 1;
            font-size: 0.95em;
            line-height: 1.5;
        }

        .info-text strong {
            color: #1976d2;
        }

        .info-link {
            color: #2196f3;
            text-decoration: none;
            font-weight: 600;
            white-space: nowrap;
            padding: 6px 12px;
            border-radius: 5px;
            transition: all 0.3s;
        }

        .info-link:hover {
            background-color: rgba(33, 150, 243, 0.1);
            text-decoration: underline;
        }

        /* Dettagli espandibili */
        .suggestions-detail {
            margin: 0 0 20px 0;
            animation: slideDown 0.3s ease-out;
        }

        @keyframes slideDown {
            from {
                opacity: 0;
                max-height: 0;
            }
            to {
                opacity: 1;
                max-height: 500px;
            }
        }

        .suggestions-compact {
            background: #f8f9fa;
            padding: 20px 25px;
            border-radius: 8px;
            border: 1px solid #e0e0e0;
        }

        .suggestions-compact h4 {
            color: #667eea;
            font-size: 1.1em;
            margin: 15px 0 10px 0;
        }

        .suggestions-compact h4:first-child {
            margin-top: 0;
        }

        .suggestions-compact ul {
            list-style: none;
            padding: 0;
            margin: 10px 0 0 0;
        }

        .suggestions-compact li {
            padding: 8px 0;
            font-size: 0.95em;
            line-height: 1.5;
            border-bottom: 1px solid #e8e8e8;
        }

        .suggestions-compact li:last-child {
            border-bottom: none;
        }

        .suggestions-compact strong {
            color: #333;
        }

        .suggestions-footer {
            margin-top: 15px;
            padding-top: 15px;
            border-top: 2px solid #e0e0e0;
            font-size: 0.9em;
            color: #666;
        }

        .suggestions-footer strong {
            color: #667eea;
        }

        /* Reports Grid */
        .reports-section {
            margin: 50px 0;
        }

        .section-title {
            font-size: 2em;
            color: #333;
            margin-bottom: 30px;
            padding-bottom: 15px;
            border-bottom: 3px solid #667eea;
        }

        .reports-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 30px;
            margin-top: 30px;
        }

        .report-card {
            background: white;
            border-radius: 15px;
            padding: 30px;
            border: 2px solid #e0e0e0;
            transition: all 0.3s;
            position: relative;
        }

        .report-card.available {
            border-color: #667eea;
        }

        .report-card.available:hover {
            transform: translateY(-8px);
            box-shadow: 0 15px 40px rgba(102, 126, 234, 0.25);
        }

        .report-card.unavailable {
            opacity: 0.65;
            background: #f8f9fa;
        }

        .card-icon {
            font-size: 3.5em;
            text-align: center;
            margin-bottom: 15px;
        }

        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }

        .card-header h2 {
            margin: 0;
            font-size: 1.5em;
            color: #333;
        }

        .card-description {
            color: #666;
            margin-bottom: 20px;
            line-height: 1.6;
        }

        .card-stats {
            list-style: none;
            padding: 0;
            margin: 20px 0;
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
        }

        .card-stats li {
            padding: 5px 0;
            color: #555;
            font-size: 0.95em;
        }

        .card-stats strong {
            color: #333;
        }

        .card-actions {
            display: flex;
            gap: 10px;
            margin-top: 20px;
        }

        .card-info {
            padding: 15px;
            background: #fff9e6;
            border-radius: 8px;
            text-align: center;
            margin-top: 15px;
        }

        .card-info em {
            color: #856404;
            font-size: 0.9em;
        }

        /* Quick Links */
        .quick-links-section {
            margin: 40px 0;
            padding: 30px;
            background: linear-gradient(135deg, #f0f4ff 0%, #e0e7ff 100%);
            border-radius: 15px;
        }

        .quick-links-section h3 {
            margin: 0 0 20px 0;
            color: #667eea;
        }

        .quick-links {
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
        }

        .quick-link {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 12px 20px;
            background: white;
            border-radius: 8px;
            text-decoration: none;
            color: #333;
            transition: all 0.3s;
            border: 2px solid transparent;
        }

        .quick-link:hover {
            border-color: #667eea;
            transform: translateX(5px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.2);
        }

        .link-icon {
            font-size: 1.5em;
        }

        /* Responsive */
        @media (max-width: 768px) {
            .dashboard-header h1 {
                font-size: 2em;
            }

            .stats-overview {
                gap: 20px;
            }

            .stat-box {
                min-width: 140px;
                padding: 20px;
            }

            .stat-icon {
                font-size: 2.5em;
            }

            .stat-value {
                font-size: 2em;
            }

            .reports-grid {
                grid-template-columns: 1fr;
            }

            .info-banner-content {
                flex-wrap: wrap;
            }

            .info-icon {
                font-size: 1.5em;
            }

            .info-text {
                font-size: 0.9em;
            }

            .info-link {
                width: 100%;
                text-align: center;
                margin-top: 10px;
            }
        }
        """

    def _create_shared_css(self):
        """Crea il file CSS base condiviso"""
        from html_templates import get_shared_css

        css_file = self.report_dir / "styles.css"
        with open(css_file, 'w', encoding='utf-8') as f:
            f.write(get_shared_css())
