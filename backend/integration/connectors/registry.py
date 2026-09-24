from typing import Dict, Optional, Type
from .base import BaseConnector
from .generic_webhook import GenericWebhookConnector

_CONNECTOR_REGISTRY: Dict[str, Type[BaseConnector]] = {
    "generic-webhook": GenericWebhookConnector,
}


def register_connector(slug: str, connector_cls: Type[BaseConnector]) -> None:
    """Registra uma classe de conector no registro em runtime."""
    _CONNECTOR_REGISTRY[slug] = connector_cls


def get_connector(slug: str) -> Optional[BaseConnector]:
    """Retorna uma instância do conector registrado para o slug fornecido."""
    connector_cls = _CONNECTOR_REGISTRY.get(slug)
    if connector_cls:
        return connector_cls()
    return None


def list_registered_slugs() -> list[str]:
    """Retorna a lista de slugs de conectores atualmente implementados."""
    return list(_CONNECTOR_REGISTRY.keys())
