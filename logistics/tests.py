from django.test import SimpleTestCase

from logistics.models import Order
from logistics.exceptions import InvalidOrderStatusTransitionError


class OrderStateMachineTests(SimpleTestCase):
    def test_valid_transition_from_preparing_to_ready_for_dispatch(self):
        """Transição válida: PREPARING → READY_FOR_DISPATCH"""
        Order.validate_status_transition(
            Order.OrderStatus.PREPARING,
            Order.OrderStatus.READY_FOR_DISPATCH,
        )

    def test_valid_transition_from_preparing_to_canceled(self):
        """Transição válida: PREPARING → CANCELED"""
        Order.validate_status_transition(
            Order.OrderStatus.PREPARING,
            Order.OrderStatus.CANCELED,
        )

    def test_invalid_transition_from_preparing_to_completed(self):
        """Transição INVÁLIDA: PREPARING → COMPLETED"""
        with self.assertRaises(InvalidOrderStatusTransitionError):
            Order.validate_status_transition(
                Order.OrderStatus.PREPARING,
                Order.OrderStatus.COMPLETED,
            )

    def test_cannot_change_completed_order(self):
        """Ordem COMPLETADA não pode ser alterada de status"""
        with self.assertRaises(InvalidOrderStatusTransitionError):
            Order.validate_status_transition(
                Order.OrderStatus.COMPLETED,
                Order.OrderStatus.ARRIVED,
            )
