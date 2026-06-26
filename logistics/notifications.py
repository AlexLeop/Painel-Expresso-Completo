import firebase_admin
from firebase_admin import credentials, messaging
import os
import json
import logging

logger = logging.getLogger(__name__)

# Configura o Firebase Admin se as variáveis de ambiente existirem
FIREBASE_CREDS = os.environ.get("FIREBASE_SERVICE_ACCOUNT")
_firebase_initialized = False

try:
    if FIREBASE_CREDS:
        cred_dict = json.loads(FIREBASE_CREDS)
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
        _firebase_initialized = True
    elif os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        cred = credentials.Certificate(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"))
        firebase_admin.initialize_app(cred)
        _firebase_initialized = True
except Exception as e:
    logger.error(f"Falha ao inicializar firebase_admin: {e}")


def send_push_notification(device_token: str, title: str, body: str, data: dict = None):
    """
    Envia uma push notification usando Firebase Cloud Messaging (FCM).
    """
    if not _firebase_initialized:
        logger.warning(
            f"[Mock FCM] title='{title}', body='{body}', token='{device_token}'"
        )
        return False

    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data=data or {},
            token=device_token,
        )
        response = messaging.send(message)
        logger.info(f"Successfully sent message: {response}")
        return True
    except Exception as e:
        logger.error(f"Error sending FCM message: {e}")
        return False
