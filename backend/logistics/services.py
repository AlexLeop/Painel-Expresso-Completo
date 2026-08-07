from typing import List
from django.db.models.expressions import RawSQL
from .models import Store, Stop, Manifest, ManifestStop


class TSPEngine:
    """
    Motor TSP Engine (Manifest Builder).
    Responsável por sequenciar paradas e otimizar rotas.
    """

    @staticmethod
    def sequence_stops(store: Store, stops: List[Stop]) -> List[Stop]:
        """
        Phase 1: Greedy Nearest-Neighbor usando PostGIS.
        Começa da loja (Store) e itera para o ponto mais próximo (operador <-> do PostGIS),
        construindo uma sequência gulosa.
        """
        if not stops:
            return []

        sequenced = []
        unsequenced = {s.id: s for s in stops}
        current_geom = store.geom

        while unsequenced:
            ids = tuple(unsequenced.keys())

            # PostGIS nearest-neighbor logic (<->)
            # Em vez de ST_Distance que calcula a distância esférica exata e é mais custoso,
            # o operador <-> usa a Bounding Box (GIST index) para achar o vizinho mais próximo com máxima performance.
            nearest = (
                Stop.objects.filter(id__in=ids)
                .annotate(
                    knn_dist=RawSQL(
                        "geom <-> ST_SetSRID(ST_MakePoint(%s, %s), 4326)",
                        (current_geom.x, current_geom.y),
                    )
                )
                .order_by("knn_dist")
                .first()
            )

            nearest_id = nearest.id if nearest else ids[0]

            nearest_obj = unsequenced.pop(nearest_id)
            sequenced.append(nearest_obj)
            current_geom = nearest_obj.geom

        return sequenced

    @staticmethod
    def build_manifest(operator_id, store: Store, stops: List[Stop]) -> Manifest:
        """
        Cria um manifesto otimizado a partir de uma lista de Stops.
        """
        sequenced_stops = TSPEngine.sequence_stops(store, stops)

        manifest = Manifest.objects.create(
            operator_id=operator_id, status=Manifest.ManifestStatus.OPEN
        )

        manifest_stops_to_create = []
        for i, stop in enumerate(sequenced_stops):
            # ManifestStop controls the sequence across all stops in the manifest
            manifest_stops_to_create.append(
                ManifestStop(
                    operator_id=operator_id,
                    manifest=manifest,
                    stop=stop,
                    sequence=i + 1,
                )
            )

        ManifestStop.objects.bulk_create(manifest_stops_to_create)
        return manifest
