"""
Gestore sicuro per le chiavi API
Cifra e memorizza le chiavi API localmente

© 2025 Luca Mercatanti - https://mercatanti.com
"""

import base64
import os
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class APIKeyManager:
    """Gestisce il salvataggio sicuro delle chiavi API"""

    def __init__(self, config_file=".api_keys.enc"):
        """
        Inizializza il gestore chiavi API

        Args:
            config_file: Nome file dove salvare le chiavi cifrate
        """
        self.config_file = Path(config_file)
        self.salt_file = Path(".api_salt")

    def _get_encryption_key(self):
        """
        Genera una chiave di cifratura basata sulla macchina
        Usa informazioni univoche del sistema per creare la chiave
        """
        # Usa il nome macchina + username come base per la chiave
        import platform
        import getpass

        machine_id = f"{platform.node()}-{getpass.getuser()}"

        # Carica o crea salt
        if self.salt_file.exists():
            with open(self.salt_file, 'rb') as f:
                salt = f.read()
        else:
            salt = os.urandom(16)
            with open(self.salt_file, 'wb') as f:
                f.write(salt)

        # Deriva chiave usando PBKDF2HMAC
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(machine_id.encode()))
        return key

    def save_api_key(self, api_key, key_type="openai"):
        """
        Salva una chiave API cifrata

        Args:
            api_key: La chiave API da salvare
            key_type: Tipo di chiave (openai, anthropic, ecc.)
        """
        if not api_key or not api_key.strip():
            return False

        try:
            # Carica chiavi esistenti
            keys = self._load_keys_dict()

            # Aggiungi/aggiorna la chiave
            keys[key_type] = api_key.strip()

            # Cifra e salva
            encryption_key = self._get_encryption_key()
            fernet = Fernet(encryption_key)

            # Converti dict in stringa JSON
            import json
            keys_json = json.dumps(keys)
            encrypted_data = fernet.encrypt(keys_json.encode())

            # Salva su file
            with open(self.config_file, 'wb') as f:
                f.write(encrypted_data)

            return True
        except Exception as e:
            print(f"Errore salvataggio chiave API: {e}")
            return False

    def load_api_key(self, key_type="openai"):
        """
        Carica una chiave API cifrata

        Args:
            key_type: Tipo di chiave da caricare

        Returns:
            La chiave API decifrata o None se non esiste
        """
        try:
            keys = self._load_keys_dict()
            return keys.get(key_type)
        except Exception as e:
            print(f"Errore caricamento chiave API: {e}")
            return None

    def _load_keys_dict(self):
        """Carica il dizionario di tutte le chiavi salvate"""
        if not self.config_file.exists():
            return {}

        try:
            encryption_key = self._get_encryption_key()
            fernet = Fernet(encryption_key)

            with open(self.config_file, 'rb') as f:
                encrypted_data = f.read()

            decrypted_data = fernet.decrypt(encrypted_data)

            import json
            keys = json.loads(decrypted_data.decode())
            return keys
        except Exception:
            return {}

    def delete_api_key(self, key_type="openai"):
        """
        Elimina una chiave API salvata

        Args:
            key_type: Tipo di chiave da eliminare
        """
        try:
            keys = self._load_keys_dict()
            if key_type in keys:
                del keys[key_type]

                # Se non ci sono più chiavi, elimina i file
                if not keys:
                    if self.config_file.exists():
                        os.remove(self.config_file)
                    if self.salt_file.exists():
                        os.remove(self.salt_file)
                    return True

                # Altrimenti salva il dizionario aggiornato
                import json
                encryption_key = self._get_encryption_key()
                fernet = Fernet(encryption_key)
                keys_json = json.dumps(keys)
                encrypted_data = fernet.encrypt(keys_json.encode())

                with open(self.config_file, 'wb') as f:
                    f.write(encrypted_data)

            return True
        except Exception as e:
            print(f"Errore eliminazione chiave API: {e}")
            return False

    def delete_all_keys(self):
        """Elimina tutte le chiavi salvate"""
        try:
            if self.config_file.exists():
                os.remove(self.config_file)
            if self.salt_file.exists():
                os.remove(self.salt_file)
            return True
        except Exception as e:
            print(f"Errore eliminazione chiavi: {e}")
            return False

    def has_saved_key(self, key_type="openai"):
        """
        Controlla se esiste una chiave salvata

        Args:
            key_type: Tipo di chiave da controllare

        Returns:
            True se la chiave esiste
        """
        keys = self._load_keys_dict()
        return key_type in keys and bool(keys[key_type])
