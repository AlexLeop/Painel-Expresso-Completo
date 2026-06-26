from types import SimpleNamespace

import config.idempotency as idem
from shared_schemas.logistics import OrderSchema


def test_idempotency_schema_dump_does_not_raise_on_non_dict_geom():
    store = SimpleNamespace(
        id="00000000-0000-0000-0000-000000000001",
        name="Loja",
        averagePrepTimeMinutes=15,
        geom="WKB",
    )
    order = SimpleNamespace(
        id="00000000-0000-0000-0000-000000000002",
        status="OFFERED",
        fareValueCents=1000,
        distanceMeters=100,
        businessDate="2026-06-22",
        requestedAt=None,
        acceptedAt=None,
        startedAt=None,
        arrivedAt=None,
        completedAt=None,
        canceledAt=None,
        store=store,
        driver=None,
        manifest=None,
    )
    dumped = idem._try_schema_dump(OrderSchema, order)
    assert dumped is not None
    assert dumped["store"]["geom"] is None
