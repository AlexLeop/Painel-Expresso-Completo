"""
Package de conectores externos para o Hub de Integrações.
"""
from .base import BaseConnector, OrderIntent, DeliveryStop
from .generic_webhook import GenericWebhookConnector

__all__ = [
    "BaseConnector",
    "OrderIntent",
    "DeliveryStop",
    "GenericWebhookConnector",
]
