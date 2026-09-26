import logging
import os
from typing import Sequence, Tuple
import requests

from logistics.pricing import Coordinate, estimate_route_distance_km

logger = logging.getLogger(__name__)


def calculate_route_distance(points: Sequence[Coordinate]) -> Tuple[float, str]:
    """
    Calcula a distância da rota em quilômetros.
    Se ROUTING_ENGINE_URL ou OSRM_URL estiver configurado, consulta a malha viária real via OSRM.
    Caso a URL não esteja configurada ou ocorra timeout/falha de conexão, recorre de forma
    determinística à estimativa geodésica com buffer viário de 30% (HAVERSINE_BUFFERED_30_PERCENT).
    """
    osrm_url = os.getenv("ROUTING_ENGINE_URL") or os.getenv("OSRM_URL")
    if osrm_url and len(points) >= 2:
        try:
            # OSRM espera coordenadas no formato {lon},{lat}
            coords_str = ";".join(f"{lon},{lat}" for lat, lon in points)
            timeout = float(os.getenv("ROUTING_TIMEOUT_SECONDS", "3.0"))
            endpoint = f"{osrm_url.rstrip('/')}/route/v1/driving/{coords_str}?overview=false"
            resp = requests.get(endpoint, timeout=timeout)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("code") == "Ok" and data.get("routes"):
                    distance_meters = data["routes"][0]["distance"]
                    distance_km = round(distance_meters / 1000.0, 3)
                    return distance_km, "OSRM_ROAD_NETWORK"
        except Exception as exc:
            logger.warning(
                "Falha ao consultar serviço de roteamento viário OSRM (%s): %s. Recorrendo ao Haversine buffered.",
                osrm_url,
                exc,
            )

    distance_km = estimate_route_distance_km(points)
    return distance_km, "HAVERSINE_BUFFERED_30_PERCENT"
