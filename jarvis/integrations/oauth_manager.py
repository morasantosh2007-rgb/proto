"""OAuth credentials and OS Keyring credential storage manager."""

import json
import logging
from typing import Any, Dict, Optional
import keyring

logger = logging.getLogger("jarvis.integrations.oauth")

SERVICE_NAME = "JARVIS_AI_Assistant"


class OAuthManager:
    """Stores and retrieves integration credentials securely via OS Keyring."""

    @classmethod
    def save_credential(cls, service_key: str, data: Dict[str, Any]) -> bool:
        try:
            json_str = json.dumps(data)
            keyring.set_password(SERVICE_NAME, service_key, json_str)
            logger.info(f"Credential securely saved for {service_key}")
            return True
        except Exception as e:
            logger.error(f"Failed to save credential in keyring for {service_key}: {e}")
            return False

    @classmethod
    def get_credential(cls, service_key: str) -> Optional[Dict[str, Any]]:
        try:
            raw = keyring.get_password(SERVICE_NAME, service_key)
            if raw:
                return json.loads(raw)
            return None
        except Exception as e:
            logger.error(f"Failed to retrieve credential for {service_key}: {e}")
            return None

    @classmethod
    def is_connected(cls, service_key: str) -> bool:
        cred = cls.get_credential(service_key)
        return cred is not None and bool(cred.get("token") or cred.get("access_token") or cred.get("api_key"))

    @classmethod
    def disconnect(cls, service_key: str) -> bool:
        try:
            keyring.delete_password(SERVICE_NAME, service_key)
            logger.info(f"Disconnected service: {service_key}")
            return True
        except Exception as e:
            logger.debug(f"Disconnect notice for {service_key}: {e}")
            return True


oauth_manager = OAuthManager()
