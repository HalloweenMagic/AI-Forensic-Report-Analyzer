"""
Version Checker - Controlla disponibilità nuove versioni app
Integrato con il sistema licenze backend

© 2025 Luca Mercatanti - https://mercatanti.com
"""

import requests
from pathlib import Path
from datetime import datetime, timedelta
import json


class VersionChecker:
    def __init__(self, api_url, current_version):
        """
        Inizializza il version checker

        Args:
            api_url: URL backend API (es. https://tuosito.com/licenza/api.php)
            current_version: Versione corrente app (es. "3.4.0")
        """
        self.api_url = api_url
        self.current_version = current_version
        self.preferences_file = Path(".update_preferences.json")

    def should_check(self):
        """
        Verifica se è il momento di controllare aggiornamenti
        Controlla MAX 1 volta al giorno per non essere invasivo

        Returns:
            bool: True se deve controllare, False altrimenti
        """
        prefs = self._load_preferences()

        if 'last_check' not in prefs:
            return True

        try:
            last_check = datetime.fromisoformat(prefs['last_check'])
            return (datetime.now() - last_check) > timedelta(days=1)
        except:
            return True

    def check_for_updates(self):
        """
        Controlla se disponibile nuova versione

        Returns:
            dict con info update o None se nessun update/errore
        """
        try:
            response = requests.post(
                self.api_url,
                json={'action': 'check_version'},
                timeout=10
            )

            data = response.json()

            if not data.get('success'):
                return None

            # Salva timestamp controllo
            self._save_check_timestamp()

            latest = data['latest_version']

            # Confronta versioni
            if self._compare_versions(latest, self.current_version) > 0:
                # Controlla se utente ha ignorato questa versione
                prefs = self._load_preferences()
                if latest in prefs.get('ignored_versions', []):
                    return None  # Utente ha scelto di ignorare

                return {
                    'update_available': True,
                    'latest_version': latest,
                    'release_date': data['release_date'],
                    'download_url': data['download_url'],
                    'changelog': data.get('changelog', '')
                }

            return None  # Nessun update disponibile

        except Exception as e:
            print(f"Errore controllo versione: {e}")
            return None

    def _compare_versions(self, v1, v2):
        """
        Confronta due versioni in formato "X.Y.Z"

        Args:
            v1: Prima versione (es. "4.0.0")
            v2: Seconda versione (es. "3.4.0")

        Returns:
            int: 1 se v1 > v2, -1 se v1 < v2, 0 se uguali
        """
        try:
            parts1 = [int(x) for x in v1.split('.')]
            parts2 = [int(x) for x in v2.split('.')]

            for p1, p2 in zip(parts1, parts2):
                if p1 > p2:
                    return 1
                elif p1 < p2:
                    return -1
            return 0
        except:
            return 0  # In caso di errore, considera uguali

    def ignore_version(self, version):
        """
        Ignora una versione specifica (non mostrare più notifiche)

        Args:
            version: Versione da ignorare (es. "4.0.0")
        """
        prefs = self._load_preferences()

        if 'ignored_versions' not in prefs:
            prefs['ignored_versions'] = []

        if version not in prefs['ignored_versions']:
            prefs['ignored_versions'].append(version)
            self._save_preferences(prefs)

    def _load_preferences(self):
        """
        Carica preferenze utente da file

        Returns:
            dict: Preferenze utente
        """
        if not self.preferences_file.exists():
            return {}

        try:
            with open(self.preferences_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}

    def _save_preferences(self, prefs):
        """
        Salva preferenze utente su file

        Args:
            prefs: Dict preferenze da salvare
        """
        try:
            with open(self.preferences_file, 'w', encoding='utf-8') as f:
                json.dump(prefs, f, indent=4)
        except Exception as e:
            print(f"Errore salvataggio preferenze: {e}")

    def _save_check_timestamp(self):
        """Salva timestamp ultimo controllo"""
        prefs = self._load_preferences()
        prefs['last_check'] = datetime.now().isoformat()
        self._save_preferences(prefs)


# Test standalone
if __name__ == "__main__":
    # Test rapido
    checker = VersionChecker(
        api_url="https://www.winesommelier.it/licenza/api.php",
        current_version="3.4.0"
    )

    print(f"Current version: {checker.current_version}")
    print(f"Should check: {checker.should_check()}")

    print("\nChecking for updates...")
    update_info = checker.check_for_updates()

    if update_info:
        print(f"✓ Update available!")
        print(f"  Latest version: {update_info['latest_version']}")
        print(f"  Release date: {update_info['release_date']}")
        print(f"  Download URL: {update_info['download_url']}")
        if update_info['changelog']:
            print(f"  Changelog:\n{update_info['changelog']}")
    else:
        print("✓ No updates available or already on latest version")
