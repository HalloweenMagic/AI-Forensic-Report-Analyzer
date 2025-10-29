"""
Generatore di report HTML con mappa interattiva Leaflet
Crea visualizzazione professionale delle posizioni geografiche

© 2025 Luca Mercatanti - https://mercatanti.com
"""

import os
import json
from datetime import datetime


class LocationReportGenerator:
    def __init__(self, analysis_results, output_dir):
        """
        Inizializza il generatore di report

        Args:
            analysis_results: Risultati dell'analisi (locations, errors, stats)
            output_dir: Cartella output principale
        """
        self.results = analysis_results
        self.output_dir = output_dir
        self.report_dir = None

    def generate_report(self):
        """
        Genera il report HTML completo

        Returns:
            str: Percorso del file index.html generato
        """
        from dashboard_manager import DashboardManager

        # Crea cartella REPORT/report_posizioni
        self.report_dir = os.path.join(self.output_dir, "REPORT", "report_posizioni")
        os.makedirs(self.report_dir, exist_ok=True)

        # Salva dati JSON
        self._save_json_data()

        # Genera HTML
        html_path = self._generate_html()

        # Genera CSS
        self._generate_css()

        # Registra il report nella dashboard
        dashboard = DashboardManager(self.output_dir)
        dashboard.register_report('locations', self.results['stats'])

        # Rigenera dashboard
        dashboard.generate_dashboard()

        return html_path

    def _save_json_data(self):
        """Salva i dati in formato JSON per eventuale riutilizzo"""
        json_path = os.path.join(self.report_dir, "locations_data.json")

        data = {
            'generated_at': datetime.now().isoformat(),
            'stats': self.results['stats'],
            'locations': self.results['locations'],
            'geocoding_errors': self.results['geocoding_errors']
        }

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _calculate_map_center(self):
        """
        Calcola il centro della mappa (media coordinate)

        Returns:
            tuple: (lat, lon, zoom)
        """
        locations = self.results['locations']
        if not locations:
            return 41.9028, 12.4964, 6  # Roma, Italia (default)

        avg_lat = sum(loc['lat'] for loc in locations) / len(locations)
        avg_lon = sum(loc['lon'] for loc in locations) / len(locations)

        # Zoom in base a numero posizioni
        if len(locations) == 1:
            zoom = 15
        elif len(locations) <= 5:
            zoom = 12
        elif len(locations) <= 20:
            zoom = 10
        else:
            zoom = 8

        return avg_lat, avg_lon, zoom

    def _generate_html(self):
        """
        Genera il file HTML principale

        Returns:
            str: Percorso file generato
        """
        from html_templates import create_breadcrumb

        locations = self.results['locations']
        stats = self.results['stats']
        errors = self.results['geocoding_errors']

        center_lat, center_lon, zoom = self._calculate_map_center()

        # Genera dati JavaScript per i marker
        markers_js = self._generate_markers_js()

        # Genera breadcrumb
        breadcrumb_items = [
            ('🏠 Dashboard', '../index.html'),
            ('Posizioni Geografiche', None)
        ]
        breadcrumb_html = create_breadcrumb(breadcrumb_items)

        html_content = f"""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Report Posizioni Geografiche</title>

    <!-- Leaflet CSS -->
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />

    <!-- Custom CSS -->
    <link rel="stylesheet" href="styles.css">
    <link rel="stylesheet" href="../styles.css">
</head>
<body>
    <div class="container">
        <!-- Header -->
        <header>
            <h1>🗺️ Report Posizioni Geografiche</h1>
            <div class="stats-bar">
                <div class="stat-item">
                    <span class="stat-label">Posizioni Uniche:</span>
                    <span class="stat-value">{stats['unique_locations']}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Eventi Totali:</span>
                    <span class="stat-value">{stats['total_events']}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Chunk Analizzati:</span>
                    <span class="stat-value">{stats['total_chunks']}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Geocodificate:</span>
                    <span class="stat-value">{stats['locations_geocoded']}/{stats['locations_found']}</span>
                </div>
            </div>
        </header>

        <!-- Breadcrumb -->
        {breadcrumb_html}

        <!-- Mappa -->
        <div class="map-container">
            <div id="map"></div>
        </div>

        <!-- Legenda -->
        <div class="legend">
            <h3>Legenda</h3>
            <div class="legend-items">
                <div class="legend-item">
                    <span class="marker-icon high"></span>
                    <span>Alta confidence (≥70%)</span>
                </div>
                <div class="legend-item">
                    <span class="marker-icon medium"></span>
                    <span>Media confidence (40-69%)</span>
                </div>
                <div class="legend-item">
                    <span class="marker-icon low"></span>
                    <span>Bassa confidence (<40%)</span>
                </div>
            </div>
        </div>

        <!-- Tabella Riepilogativa -->
        <div class="table-container">
            <h2>📋 Riepilogo Posizioni</h2>
            <table id="locationsTable">
                <thead>
                    <tr>
                        <th onclick="sortTable(0)">ID</th>
                        <th onclick="sortTable(1)">Posizione</th>
                        <th onclick="sortTable(2)">Tipo</th>
                        <th onclick="sortTable(3)">Eventi</th>
                        <th>Coordinate</th>
                        <th>Azioni</th>
                    </tr>
                </thead>
                <tbody>
                    {self._generate_table_rows()}
                </tbody>
            </table>
        </div>

        <!-- Sezione Errori Geocoding -->
        {self._generate_errors_section()}

        <!-- Footer -->
        <footer>
            <p>Report generato il {datetime.now().strftime('%d/%m/%Y alle %H:%M:%S')}</p>
            <p>© 2025 Luca Mercatanti - <a href="https://mercatanti.com" target="_blank">mercatanti.com</a></p>
        </footer>
    </div>

    <!-- Leaflet JS -->
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>

    <!-- Custom JavaScript -->
    <script>
        // Inizializza mappa
        const map = L.map('map').setView([{center_lat}, {center_lon}], {zoom});

        // Aggiungi tile layer (OpenStreetMap)
        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            maxZoom: 19
        }}).addTo(map);

        // Dati marker
        const markersData = {markers_js};

        // Funzione per determinare colore marker basato su confidence
        function getMarkerColor(avgConfidence) {{
            if (avgConfidence >= 70) return '#28a745';  // Verde
            if (avgConfidence >= 40) return '#ffc107';  // Giallo
            return '#dc3545';  // Rosso
        }}

        // Aggiungi marker alla mappa
        markersData.forEach(markerData => {{
            // Calcola confidence media
            const avgConfidence = markerData.events.reduce((sum, e) => sum + e.confidence, 0) / markerData.events.length;

            // Crea marker con colore basato su confidence
            const markerColor = getMarkerColor(avgConfidence);
            const marker = L.circleMarker([markerData.lat, markerData.lon], {{
                radius: 8,
                fillColor: markerColor,
                color: '#fff',
                weight: 2,
                opacity: 1,
                fillOpacity: 0.8
            }}).addTo(map);

            // Genera popup content
            let popupContent = `<div class="popup-container">
                <h3>${{markerData.location_text}}</h3>
                <p><strong>Eventi:</strong> ${{markerData.event_count}}</p>
                <hr>`;

            markerData.events.forEach((event, idx) => {{
                popupContent += `
                    <div class="popup-event">
                        <strong>Evento ${{idx + 1}}:</strong><br>
                        <strong>Da:</strong> ${{event.sender}}<br>
                        <strong>Quando:</strong> ${{event.timestamp || 'N/A'}}<br>
                        <strong>Confidence:</strong> ${{event.confidence}}%<br>
                        <strong>Contesto:</strong> "${{event.message_context}}"<br>
                        <a href="../analisi_principale/chunk_${{String(event.chunk_id).padStart(3, '0')}}.html" target="_blank">
                            📄 Vedi chunk originale
                        </a>
                    </div>
                    ${{idx < markerData.events.length - 1 ? '<hr>' : ''}}
                `;
            }});

            popupContent += `</div>`;

            marker.bindPopup(popupContent, {{
                maxWidth: 400,
                className: 'custom-popup'
            }});

            // Highlight riga tabella al click
            marker.on('click', () => {{
                const row = document.querySelector(`tr[data-location-id="${{markerData.location_id}}"]`);
                if (row) {{
                    // Rimuovi highlight precedente
                    document.querySelectorAll('tr.highlight').forEach(r => r.classList.remove('highlight'));
                    // Aggiungi nuovo highlight
                    row.classList.add('highlight');
                    row.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                }}
            }});
        }});

        // Funzione per centrare marker sulla mappa
        function focusLocation(locationId) {{
            const markerData = markersData.find(m => m.location_id === locationId);
            if (markerData) {{
                map.setView([markerData.lat, markerData.lon], 15);
                // Trova e apri popup
                map.eachLayer(layer => {{
                    if (layer instanceof L.CircleMarker) {{
                        const latlng = layer.getLatLng();
                        if (Math.abs(latlng.lat - markerData.lat) < 0.0001 &&
                            Math.abs(latlng.lng - markerData.lon) < 0.0001) {{
                            layer.openPopup();
                        }}
                    }}
                }});
            }}
        }}

        // Funzione sort tabella
        function sortTable(columnIndex) {{
            const table = document.getElementById('locationsTable');
            const rows = Array.from(table.querySelectorAll('tbody tr'));
            const isAscending = table.dataset.sortOrder !== 'asc';

            rows.sort((a, b) => {{
                const aValue = a.cells[columnIndex].textContent;
                const bValue = b.cells[columnIndex].textContent;

                // Prova conversione numerica
                const aNum = parseFloat(aValue);
                const bNum = parseFloat(bValue);

                if (!isNaN(aNum) && !isNaN(bNum)) {{
                    return isAscending ? aNum - bNum : bNum - aNum;
                }} else {{
                    return isAscending ? aValue.localeCompare(bValue) : bValue.localeCompare(aValue);
                }}
            }});

            // Riordina righe
            const tbody = table.querySelector('tbody');
            rows.forEach(row => tbody.appendChild(row));

            // Aggiorna sort order
            table.dataset.sortOrder = isAscending ? 'asc' : 'desc';
        }}

        // Scroll to top button
        window.onscroll = function() {{
            const btn = document.getElementById('scrollTopBtn');
            if (btn) {{
                if (document.body.scrollTop > 300 || document.documentElement.scrollTop > 300) {{
                    btn.style.display = 'block';
                }} else {{
                    btn.style.display = 'none';
                }}
            }}
        }};

        function scrollToTop() {{
            window.scrollTo({{ top: 0, behavior: 'smooth' }});
        }}
    </script>

    <!-- Scroll to top button -->
    <button id="scrollTopBtn" onclick="scrollToTop()">↑</button>
</body>
</html>"""

        html_path = os.path.join(self.report_dir, "index.html")
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        return html_path

    def _generate_markers_js(self):
        """
        Genera JavaScript array dei marker

        Returns:
            str: JSON array dei marker
        """
        markers = []
        for loc in self.results['locations']:
            markers.append({
                'location_id': loc['location_id'],
                'location_text': loc['location_text'],
                'lat': loc['lat'],
                'lon': loc['lon'],
                'location_type': loc['location_type'],
                'event_count': loc['event_count'],
                'events': [{
                    'chunk_id': evt['chunk_id'],
                    'sender': evt['sender'],
                    'timestamp': evt['timestamp'],
                    'message_context': evt['message_context'][:200],  # Limita lunghezza
                    'confidence': evt['confidence_score']
                } for evt in loc['events']]
            })

        return json.dumps(markers, ensure_ascii=False)

    def _generate_table_rows(self):
        """Genera righe tabella HTML"""
        rows = []
        for loc in self.results['locations']:
            location_type_map = {
                'coordinates': 'Coordinate',
                'address': 'Indirizzo',
                'place_name': 'Luogo',
                'poi': 'POI'
            }
            type_label = location_type_map.get(loc['location_type'], loc['location_type'])

            rows.append(f"""
                <tr data-location-id="{loc['location_id']}">
                    <td>{loc['location_id']}</td>
                    <td class="location-name">{loc['location_text']}</td>
                    <td>{type_label}</td>
                    <td>{loc['event_count']}</td>
                    <td>{loc['lat']:.6f}, {loc['lon']:.6f}</td>
                    <td>
                        <button class="btn-focus" onclick="focusLocation({loc['location_id']})">
                            🎯 Mostra in mappa
                        </button>
                    </td>
                </tr>
            """)

        return '\n'.join(rows)

    def _generate_errors_section(self):
        """Genera sezione errori di geocoding"""
        errors = self.results['geocoding_errors']

        if not errors:
            return ""

        rows = []
        for err in errors:
            rows.append(f"""
                <tr>
                    <td>{err['location_text']}</td>
                    <td>Chunk {err['chunk_id']}</td>
                    <td class="error-reason">{err['reason']}</td>
                </tr>
            """)

        return f"""
        <div class="errors-container">
            <h2>⚠️ Posizioni non Geocodificate</h2>
            <p>Le seguenti posizioni non sono state geocodificate e richiedono revisione manuale:</p>
            <table class="errors-table">
                <thead>
                    <tr>
                        <th>Posizione</th>
                        <th>Chunk</th>
                        <th>Motivo</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(rows)}
                </tbody>
            </table>
        </div>
        """

    def _generate_css(self):
        """Genera file CSS personalizzato"""
        css_content = """
/* Reset e base */
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: #333;
    padding: 20px;
}

.container {
    max-width: 1400px;
    margin: 0 auto;
    background: white;
    border-radius: 15px;
    box-shadow: 0 10px 40px rgba(0,0,0,0.2);
    overflow: hidden;
}

/* Header */
header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 30px;
    text-align: center;
}

header h1 {
    font-size: 2.5em;
    margin-bottom: 20px;
}

.stats-bar {
    display: flex;
    justify-content: center;
    gap: 40px;
    flex-wrap: wrap;
}

.stat-item {
    display: flex;
    flex-direction: column;
    align-items: center;
}

.stat-label {
    font-size: 0.9em;
    opacity: 0.9;
    margin-bottom: 5px;
}

.stat-value {
    font-size: 2em;
    font-weight: bold;
}

/* Mappa */
.map-container {
    padding: 30px;
    background: #f8f9fa;
}

#map {
    height: 600px;
    border-radius: 10px;
    box-shadow: 0 4px 15px rgba(0,0,0,0.1);
}

/* Legenda */
.legend {
    padding: 20px 30px;
    background: #fff;
    border-top: 1px solid #e0e0e0;
}

.legend h3 {
    margin-bottom: 15px;
    color: #667eea;
}

.legend-items {
    display: flex;
    gap: 30px;
    flex-wrap: wrap;
}

.legend-item {
    display: flex;
    align-items: center;
    gap: 10px;
}

.marker-icon {
    width: 16px;
    height: 16px;
    border-radius: 50%;
    border: 2px solid #fff;
    box-shadow: 0 2px 5px rgba(0,0,0,0.3);
}

.marker-icon.high {
    background: #28a745;
}

.marker-icon.medium {
    background: #ffc107;
}

.marker-icon.low {
    background: #dc3545;
}

/* Tabella */
.table-container {
    padding: 30px;
}

.table-container h2 {
    margin-bottom: 20px;
    color: #667eea;
}

table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 15px;
}

thead {
    background: #667eea;
    color: white;
}

th {
    padding: 15px;
    text-align: left;
    cursor: pointer;
    user-select: none;
}

th:hover {
    background: #5568d3;
}

td {
    padding: 12px 15px;
    border-bottom: 1px solid #e0e0e0;
}

tr:hover {
    background: #f8f9fa;
}

tr.highlight {
    background: #fff3cd !important;
    transition: background 0.3s;
}

.location-name {
    font-weight: 600;
    color: #667eea;
}

.btn-focus {
    background: #667eea;
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 5px;
    cursor: pointer;
    font-size: 0.9em;
    transition: background 0.3s;
}

.btn-focus:hover {
    background: #5568d3;
}

/* Errori */
.errors-container {
    padding: 30px;
    background: #fff3cd;
    margin: 20px 30px;
    border-radius: 10px;
}

.errors-container h2 {
    color: #856404;
    margin-bottom: 15px;
}

.errors-table {
    background: white;
    margin-top: 20px;
}

.error-reason {
    color: #dc3545;
    font-style: italic;
}

/* Popup personalizzato */
.popup-container {
    max-height: 400px;
    overflow-y: auto;
}

.popup-container h3 {
    color: #667eea;
    margin-bottom: 10px;
}

.popup-event {
    margin: 10px 0;
    line-height: 1.6;
}

.popup-event a {
    color: #667eea;
    text-decoration: none;
    font-weight: 600;
}

.popup-event a:hover {
    text-decoration: underline;
}

/* Footer */
footer {
    background: #f8f9fa;
    padding: 20px;
    text-align: center;
    color: #666;
    border-top: 1px solid #e0e0e0;
}

footer a {
    color: #667eea;
    text-decoration: none;
}

footer a:hover {
    text-decoration: underline;
}

/* Scroll to top button */
#scrollTopBtn {
    display: none;
    position: fixed;
    bottom: 30px;
    right: 30px;
    z-index: 1000;
    background: #667eea;
    color: white;
    border: none;
    border-radius: 50%;
    width: 50px;
    height: 50px;
    font-size: 24px;
    cursor: pointer;
    box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    transition: all 0.3s;
}

#scrollTopBtn:hover {
    background: #5568d3;
    transform: translateY(-3px);
}

/* Responsive */
@media (max-width: 768px) {
    .stats-bar {
        gap: 20px;
    }

    .stat-value {
        font-size: 1.5em;
    }

    #map {
        height: 400px;
    }

    table {
        font-size: 0.9em;
    }

    th, td {
        padding: 10px;
    }
}
"""

        css_path = os.path.join(self.report_dir, "styles.css")
        with open(css_path, 'w', encoding='utf-8') as f:
            f.write(css_content)
