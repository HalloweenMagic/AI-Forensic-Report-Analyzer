#!/usr/bin/env python3
"""
License Manager - Sistema di gestione licenze per WhatsApp Forensic Analyzer
Gestisce validazione, salvataggio e telemetria delle licenze

© 2025 Luca Mercatanti - https://mercatanti.com
"""

import os
import platform
import uuid
import hashlib
import json
import requests
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64


class LicenseManager:
    def __init__(self, license_file=".license.enc", api_url="https://tuosito.com/licenza/api.php"):
        """
        Inizializza il License Manager

        Args:
            license_file: Nome file per salvare la licenza cifrata
            api_url: URL dell'API di validazione licenze
        """
        self.license_file = Path(license_file)
        self.api_url = api_url
        self.hardware_id = self._generate_hardware_id()

    def _generate_hardware_id(self):
        """
        Genera un ID hardware univoco e deterministico per questa macchina

        Returns:
            str: Hash SHA256 dell'hardware ID
        """
        # Combina più identificatori hardware
        hostname = platform.node()
        username = os.getenv('USERNAME') or os.getenv('USER') or 'unknown'
        mac_address = hex(uuid.getnode())
        system_info = f"{platform.system()}-{platform.machine()}"

        # Crea una stringa unica
        unique_string = f"{hostname}|{username}|{mac_address}|{system_info}"

        # Hash SHA256 per ottenere un ID pulito
        hardware_id = hashlib.sha256(unique_string.encode()).hexdigest()

        return hardware_id

    def _get_machine_key(self):
        """Genera una chiave di crittografia basata su machine ID"""
        # Usa hostname + username come base per la chiave
        hostname = platform.node()
        username = os.getenv('USERNAME') or os.getenv('USER') or 'unknown'
        machine_string = f"{hostname}_{username}"

        # Usa un salt fisso (per retrocompatibilità con api_key_manager)
        salt = b'license_salt_v1_fixed_2025'

        # Deriva una chiave usando PBKDF2
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(machine_string.encode()))
        return key

    def save_license(self, license_key):
        """
        Salva la chiave di licenza cifrata localmente

        Args:
            license_key: Chiave di licenza da salvare

        Returns:
            bool: True se salvata con successo
        """
        try:
            # Cifra la licenza
            key = self._get_machine_key()
            fernet = Fernet(key)

            data = {
                'license_key': license_key,
                'hardware_id': self.hardware_id
            }

            encrypted_data = fernet.encrypt(json.dumps(data).encode())

            # Salva su file
            with open(self.license_file, 'wb') as f:
                f.write(encrypted_data)

            return True
        except Exception as e:
            print(f"Errore salvataggio licenza: {e}")
            return False

    def load_license(self):
        """
        Carica la chiave di licenza salvata

        Returns:
            dict: {'license_key': str, 'hardware_id': str} o None se non trovata
        """
        if not self.license_file.exists():
            return None

        try:
            # Leggi e decifra
            with open(self.license_file, 'rb') as f:
                encrypted_data = f.read()

            key = self._get_machine_key()
            fernet = Fernet(key)
            decrypted_data = fernet.decrypt(encrypted_data)

            data = json.loads(decrypted_data.decode())
            return data
        except Exception as e:
            print(f"Errore caricamento licenza: {e}")
            return None

    def delete_license(self):
        """Elimina la licenza salvata"""
        try:
            if self.license_file.exists():
                self.license_file.unlink()
            return True
        except Exception as e:
            print(f"Errore eliminazione licenza: {e}")
            return False

    def has_saved_license(self):
        """Verifica se esiste una licenza salvata"""
        return self.license_file.exists()

    def validate_license_online(self, license_key, timeout=10):
        """
        Valida la licenza online tramite API

        Args:
            license_key: Chiave di licenza da validare
            timeout: Timeout richiesta HTTP in secondi

        Returns:
            dict: {'valid': bool, 'message': str, 'license_info': dict}
        """
        try:
            # Prepara i dati per la richiesta
            payload = {
                'action': 'validate',
                'license_key': license_key,
                'hardware_id': self.hardware_id,
                'hostname': platform.node(),
                'os': f"{platform.system()} {platform.release()}"
            }

            # Invia richiesta POST all'API
            response = requests.post(
                self.api_url,
                json=payload,
                timeout=timeout,
                headers={'Content-Type': 'application/json'}
            )

            # Parse risposta
            if response.status_code == 200:
                result = response.json()
                return result
            else:
                return {
                    'valid': False,
                    'message': f'Errore server (HTTP {response.status_code})',
                    'license_info': None
                }

        except requests.exceptions.Timeout:
            return {
                'valid': False,
                'message': 'Timeout: impossibile contattare il server di validazione',
                'license_info': None
            }
        except requests.exceptions.ConnectionError:
            return {
                'valid': False,
                'message': 'Errore connessione: verifica la tua connessione internet',
                'license_info': None
            }
        except Exception as e:
            return {
                'valid': False,
                'message': f'Errore validazione: {str(e)}',
                'license_info': None
            }

    def send_telemetry(self, license_key, app_version="3.2.2", timeout=5):
        """
        Invia telemetria di utilizzo al server (ping)

        Args:
            license_key: Chiave di licenza
            app_version: Versione dell'applicazione
            timeout: Timeout richiesta HTTP in secondi

        Returns:
            bool: True se telemetria inviata con successo
        """
        try:
            payload = {
                'action': 'ping',
                'license_key': license_key,
                'hardware_id': self.hardware_id,
                'hostname': platform.node(),
                'os': f"{platform.system()} {platform.release()}",
                'app_version': app_version
            }

            response = requests.post(
                self.api_url,
                json=payload,
                timeout=timeout,
                headers={'Content-Type': 'application/json'}
            )

            return response.status_code == 200

        except Exception as e:
            # Fallimento telemetria non critico, non blocca l'app
            print(f"Telemetria non inviata: {e}")
            return False

    def get_hardware_id(self):
        """Restituisce l'hardware ID di questa macchina"""
        return self.hardware_id


# Test rapido
if __name__ == "__main__":
    lm = LicenseManager()
    print(f"Hardware ID: {lm.get_hardware_id()}")

    # Test salvataggio/caricamento
    test_key = "TEST-1234-5678-ABCD"
    print(f"\nTest salvataggio licenza: {test_key}")
    lm.save_license(test_key)

    loaded = lm.load_license()
    print(f"Licenza caricata: {loaded}")

    # Cleanup
    lm.delete_license()
    print("Test completato!")
