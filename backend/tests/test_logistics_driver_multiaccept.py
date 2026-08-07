from types import SimpleNamespace

from logistics import api_driver
from logistics.models import Order


def test_driver_active_orders_limit_never_below_one():
    assert (
        api_driver._driver_active_orders_limit(SimpleNamespace(maxActiveOrders=0)) == 1
    )
    assert (
        api_driver._driver_active_orders_limit(SimpleNamespace(maxActiveOrders=None))
        == 1
    )
    assert (
        api_driver._driver_active_orders_limit(SimpleNamespace(maxActiveOrders=4)) == 4
    )


def test_driver_reached_capacity_uses_explicit_driver_limit(monkeypatch):
    class FakeOrders:
        def __init__(self, total):
            self.total = total

        def count(self):
            return self.total

    monkeypatch.setattr(
        api_driver,
        "_get_active_driver_orders",
        lambda driver, exclude_order_id=None: FakeOrders(3),
    )

    assert api_driver._driver_reached_capacity(SimpleNamespace(maxActiveOrders=3))
    assert not api_driver._driver_reached_capacity(SimpleNamespace(maxActiveOrders=4))


def test_clear_order_runtime_state_clears_claim_tracker_and_stops(monkeypatch):
    operations = []

    class FakePipeline:
        def srem(self, key, value):
            operations.append(("srem", key, value))
            return self

        def delete(self, key):
            operations.append(("delete", key))
            return self

        def execute(self):
            operations.append(("execute",))
            return True

    class FakeRedis:
        def pipeline(self):
            return FakePipeline()

    class FakeStopQuery:
        def values_list(self, *_args, **_kwargs):
            return ["stop-1", "stop-2"]

    monkeypatch.setattr(api_driver, "r", FakeRedis())
    monkeypatch.setattr(
        api_driver.Stop.objects, "filter", lambda **kwargs: FakeStopQuery()
    )

    order = SimpleNamespace(id="order-1")
    api_driver.clear_order_runtime_state(order, "driver-1")

    assert ("srem", "active_orders:driver:driver-1", "order-1") in operations
    assert ("delete", "public_tracker:order-1:active") in operations
    assert ("delete", "order_claim:order-1") in operations
    assert ("srem", "active_stops:driver:driver-1", "stop-1") in operations
    assert ("srem", "active_stops:driver:driver-1", "stop-2") in operations
    assert operations[-1] == ("execute",)


def test_accept_to_offered_is_allowed_for_operational_release():
    assert (
        Order.OrderStatus.OFFERED in Order.VALID_TRANSITIONS[Order.OrderStatus.ACCEPTED]
    )


def test_point_coordinates_returns_none_for_non_point_like_values():
    assert api_driver._point_coordinates("not-a-point") is None
    assert api_driver._point_coordinates(SimpleNamespace(x=1, y=2)) == (1.0, 2.0)
