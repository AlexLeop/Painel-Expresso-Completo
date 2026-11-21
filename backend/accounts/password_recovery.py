import hashlib
import secrets
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core import signing
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.db import transaction, connection
from ninja.errors import HttpError

from accounts.models import PlatformAdmin, StaffMember
from accounts.security import hash_password
from logistics.models import ClientPortalUser


IDENTITIES = {"admin": PlatformAdmin, "staff": StaffMember, "client": ClientPortalUser}
SALT = "native-password-recovery-v1"


def version(account):
    return hashlib.sha256((account.passwordHash or "").encode()).hexdigest()


@transaction.atomic
def request_recovery(email):
    email = email.strip().lower()
    try:
        validate_email(email)
    except ValidationError as exc:
        raise HttpError(422, "Informe um e-mail válido.") from exc
    login_url = getattr(settings, "PASSWORD_RESET_URL", "")
    if not login_url:
        raise HttpError(503, "A recuperação de acesso está temporariamente indisponível.")
    throttle = "auth:recovery:" + hashlib.sha256(email.encode()).hexdigest()
    if not cache.add(throttle, True, timeout=60):
        return {"success": True}
    for kind, model in IDENTITIES.items():
        query = model.objects.filter(email__iexact=email)
        if kind != "admin":
            query = query.filter(active=True)
        account = query.first()
        if not account:
            continue
        token = signing.dumps({
            "kind": kind, "uid": str(account.pk), "version": version(account),
            "operator_id": str(getattr(account, "operator_id", "") or ""),
            "nonce": secrets.token_hex(16),
        }, salt=SALT)
        link = login_url.split("#")[0] + "#" + urlencode({"type": "recovery", "token": token})
        send_mail(
            "Redefinição de acesso",
            f"Use o link para redefinir sua senha em até 15 minutos:\n{link}\n"
            "Se você não solicitou a alteração, ignore esta mensagem.",
            settings.DEFAULT_FROM_EMAIL, [email], fail_silently=False,
        )
        break
    return {"success": True}


@transaction.atomic
def reset_password(token, password):
    try:
        payload = signing.loads(token, salt=SALT, max_age=900)
        model = IDENTITIES[payload["kind"]]
        if connection.vendor == "postgresql" and payload.get("operator_id"):
            import json
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT set_config('request.jwt.claims', %s, true)",
                    [json.dumps({"app_metadata": {"operator_id": payload["operator_id"]}})],
                )
        account = model.objects.select_for_update().get(pk=payload["uid"])
    except (signing.BadSignature, KeyError, ValueError, ValidationError) as exc:
        raise HttpError(422, "Link inválido ou expirado. Solicite outro link.") from exc
    except tuple(model.DoesNotExist for model in IDENTITIES.values()) as exc:
        raise HttpError(422, "Link inválido ou expirado. Solicite outro link.") from exc
    if (payload["kind"] != "admin" and not account.active) or not secrets.compare_digest(payload["version"], version(account)):
        raise HttpError(422, "Link inválido ou já utilizado.")
    try:
        if len(password) < 10:
            raise ValidationError("Use uma senha de pelo menos 10 caracteres.")
        validate_password(password, user=account)
    except ValidationError as exc:
        raise HttpError(422, " ".join(exc.messages)) from exc
    account.passwordHash = hash_password(password)
    account.save(update_fields=["passwordHash"])
    return {"success": True}
