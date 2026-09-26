import os
from unittest.mock import MagicMock, patch
from django.test import SimpleTestCase

from logistics.routing import calculate_route_distance
from logistics.pricing import price_route, price_route_with_method


class LogisticsRoutingTests(SimpleTestCase):
    def setUp(self):
        self.points = [
            (-19.7712, -43.9876),  # Origem (Ribeirão das Neves)
            (-19.7800, -43.9900),  # Destino
        ]

    def test_routing_fallback_when_no_osrm_configured(self):
        with patch.dict(os.environ, {}, clear=True):
            distance_km, method = calculate_route_distance(self.points)
            self.assertGreater(distance_km, 0)
            self.assertEqual(method, "HAVERSINE_BUFFERED_30_PERCENT")

    def test_routing_osrm_success(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "code": "Ok",
            "routes": [{"distance": 2540.0, "duration": 310.0}],
        }

        with patch.dict(os.environ, {"ROUTING_ENGINE_URL": "http://osrm-test:5000"}):
            with patch("requests.get", return_value=mock_response) as mock_get:
                distance_km, method = calculate_route_distance(self.points)
                self.assertEqual(distance_km, 2.54)
                self.assertEqual(method, "OSRM_ROAD_NETWORK")
                mock_get.assert_called_once()
                self.assertIn("http://osrm-test:5000/route/v1/driving/", mock_get.call_args[0][0])

    def test_routing_osrm_failure_resilient_fallback(self):
        with patch.dict(os.environ, {"ROUTING_ENGINE_URL": "http://osrm-down:5000"}):
            with patch("requests.get", side_effect=Exception("Connection refused")):
                distance_km, method = calculate_route_distance(self.points)
                self.assertGreater(distance_km, 0)
                self.assertEqual(method, "HAVERSINE_BUFFERED_30_PERCENT")

    def test_price_route_with_method_contract_integration(self):
        store = MagicMock()
        store.operator_id = "op-1"
        store.id = "store-1"

        contract = MagicMock()
        contract.id = "contract-1"

        faixa = MagicMock()
        faixa.priceCents = 1250

        with patch("finance.models.Contract.objects.filter") as mock_contract_filter, \
             patch("finance.models.KmFaixa.objects.filter") as mock_faixa_filter:
            mock_contract_filter.return_value.first.return_value = contract
            mock_faixa_filter.return_value.order_by.return_value.first.return_value = faixa

            distance_km, fare_cents, method = price_route_with_method(store, self.points)
            self.assertGreater(distance_km, 0)
            self.assertEqual(fare_cents, 1250)
            self.assertEqual(method, "HAVERSINE_BUFFERED_30_PERCENT")
