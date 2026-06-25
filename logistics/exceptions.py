
class InvalidOrderStatusTransitionError(Exception):
    """
    Erro lançado quando uma transição de status de pedido é inválida,
    conforme as regras de negócio definidas.
    """

    def __init__(self, current_status: str, desired_status: str):
        self.current_status = current_status
        self.desired_status = desired_status
        self.message = f"Transição de status inválida: {current_status} → {desired_status}"
        super().__init__(self.message)
