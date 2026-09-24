import math
from typing import Iterable, Sequence, Tuple

from finance.models import Contract, KmFaixa


Coordinate = Tuple[float, float]


class PricingConfigurationError(ValueError):
    pass


def parse_coordinate(
    value, *, field_name: str, minimum: float, maximum: float
) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise PricingConfigurationError(
            f"{field_name} deve ser uma coordenada numérica válida."
        ) from exc
    if not math.isfinite(parsed) or parsed < minimum or parsed > maximum:
        raise PricingConfigurationError(
            f"{field_name} deve estar entre {minimum:g} e {maximum:g}."
        )
    return parsed


def estimate_route_distance_km(points: Sequence[Coordinate]) -> float:
    """Estimativa declarada; não se apresenta como distância de malha viária."""
    if len(points) < 2:
        raise PricingConfigurationError("A rota deve possuir origem e destino.")
    earth_radius_km = 6371.0
    straight_line_km = 0.0
    for (lat1, lon1), (lat2, lon2) in zip(points, points[1:]):
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        haversine = (
            math.sin(delta_lat / 2) ** 2
            + math.cos(math.radians(lat1))
            * math.cos(math.radians(lat2))
            * math.sin(delta_lon / 2) ** 2
        )
        arc = 2 * math.atan2(math.sqrt(haversine), math.sqrt(1 - haversine))
        straight_line_km += earth_radius_km * arc
    return straight_line_km * 1.3


def configured_fare_cents(store, distance_km: float) -> int:
    contract = Contract.objects.filter(
        operator_id=store.operator_id, store_id=store.id
    ).first()
    if not contract:
        raise PricingConfigurationError(
            "A loja não possui contrato financeiro configurado."
        )
    price_band = (
        KmFaixa.objects.filter(
            operator_id=store.operator_id,
            contract_id=contract.id,
            kmStart__lte=distance_km,
            kmEnd__gt=distance_km,
        )
        .order_by("kmStart")
        .first()
    )
    if not price_band:
        raise PricingConfigurationError(
            "Não existe faixa de preço no contrato para a distância estimada."
        )
    if price_band.priceCents is None or price_band.priceCents < 0:
        raise PricingConfigurationError("A faixa de preço possui valor inválido.")
    return int(price_band.priceCents)


def price_route(store, points: Iterable[Coordinate]) -> tuple[float, int]:
    normalized_points = list(points)
    distance_km = estimate_route_distance_km(normalized_points)
    return distance_km, configured_fare_cents(store, distance_km)
