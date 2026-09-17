import pytest
from logistics.models import ClientPortalUser


def test_client_portal_user_password_methods():
    user = ClientPortalUser(email="lojista@teste.com", name="Lojista Teste")
    user.set_password("SenhaForte123!")
    assert user.passwordHash is not None
    assert user.passwordHash != "SenhaForte123!"
    assert user.check_password("SenhaForte123!") is True
    assert user.check_password("SenhaIncorreta") is False
