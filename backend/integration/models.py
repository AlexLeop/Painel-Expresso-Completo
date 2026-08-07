"""
Módulo de Integração (Gateway e Webhooks).

Responsável por armazenar as credenciais criptografadas e injetar a consistência
eventual nas integrações externas. Utiliza pesadamente o Outbox Pattern para
garantir que nenhum evento (ex: enviar status de pedido) se perca por falha de rede.
"""

from django.db import connection, models
from config.core_models import TimeStampedTenantModel
from accounts.models import Operator
from logistics.models import Store, Order
from django.conf import settings
from cryptography.fernet import Fernet
import base64


def get_cipher():
    """
    Gera um cipher Fernet seguro usando HKDF para derivar a chave.

    HKDF (HMAC-based Key Derivation Function) é o padrão criptográfico
    para derivar chaves de tamanho fixo a partir de material secreto
    de tamanho variável. Usa SHA-256 internamente.

    Diferente do truncamento anterior ([:32]), HKDF garante que:
    - Dois SECRET_KEYs com os mesmos 32 primeiros chars geram chaves DIFERENTES
    - A entropia do SECRET_KEY inteiro é preservada na derivação
    """
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF
    from cryptography.hazmat.primitives import hashes

    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"expresso-neves-fernet-v1",  # Salt fixo por aplicação (não precisa ser secreto)
        info=b"store-integration-encryption",
    )
    derived_key = hkdf.derive(settings.SECRET_KEY.encode("utf-8"))
    return Fernet(base64.urlsafe_b64encode(derived_key))


class StoreIntegration(TimeStampedTenantModel):
    """
    Credenciais de Integração Externa (Hub/Delivery).

    Amarra uma loja específica às suas chaves de API em agregadores (Hubster,
    iFood, etc). As senhas de cliente devem trafegar ofuscadas, limitando a
    visibilidade via RLS.
    """

    operator = models.ForeignKey(
        Operator, on_delete=models.CASCADE, db_column="operator_id"
    )
    store = models.ForeignKey(Store, on_delete=models.CASCADE, db_column="store_id")
    provider = models.CharField(
        max_length=50, help_text="Provedor (Ex: HUBSTER, IFOOD)."
    )
    clientId = models.CharField(
        max_length=255, null=True, blank=True, db_column="clientId"
    )
    clientSecret = models.TextField(
        null=True,
        blank=True,
        db_column="clientSecret",
        help_text="Senha de integração.",
    )
    merchantId = models.CharField(
        max_length=100, null=True, blank=True, db_column="merchantId"
    )
    authMode = models.CharField(max_length=30, default="WEBHOOK", db_column="authMode")
    baseUrl = models.TextField(null=True, blank=True, db_column="baseUrl")
    webhookUrl = models.TextField(null=True, blank=True, db_column="webhookUrl")
    apiKey = models.TextField(null=True, blank=True, db_column="apiKey")
    active = models.BooleanField(default=True)

    class Meta:
        db_table = "StoreIntegration"
        managed = False
        verbose_name = "Integração da Loja"
        verbose_name_plural = "Integrações das Lojas"

    def _is_fernet_token(self, value: str) -> bool:
        """Verifica se o valor já é um token Fernet criptografado."""
        if not value:
            return False
        try:
            # Tokens Fernet são base64 e começam com 'gAAAAA'
            import base64

            decoded = base64.urlsafe_b64decode(value)
            return (
                len(decoded) >= 57
            )  # Header(1) + Timestamp(8) + IV(16) + min_block(16) + HMAC(32)
        except Exception:
            return False

    def save(self, *args, **kwargs):
        """
        Criptografia Fática (Manifesto IV.4):
        Intercepta o save() para garantir que clientSecret e apiKey
        NUNCA sejam gravados em texto puro, independentemente de
        o desenvolvedor ter usado set_client_secret() ou não.
        """
        if self.clientSecret and not self._is_fernet_token(self.clientSecret):
            self.set_client_secret(self.clientSecret)
        if self.apiKey and not self._is_fernet_token(self.apiKey):
            self.set_api_key(self.apiKey)
        super().save(*args, **kwargs)

    def set_client_secret(self, raw_secret: str):
        """Aplica a Criptografia Fática antes de salvar."""
        if raw_secret:
            self.clientSecret = (
                get_cipher().encrypt(raw_secret.encode("utf-8")).decode("utf-8")
            )
        else:
            self.clientSecret = None

    def get_client_secret(self) -> str:
        """Descriptografa o segredo em runtime (Memória). O DB nunca vê o plaintext."""
        if self.clientSecret:
            try:
                return (
                    get_cipher()
                    .decrypt(self.clientSecret.encode("utf-8"))
                    .decode("utf-8")
                )
            except Exception:
                return None
        return None

    def set_api_key(self, raw_key: str):
        if raw_key:
            self.apiKey = get_cipher().encrypt(raw_key.encode("utf-8")).decode("utf-8")
        else:
            self.apiKey = None

    def get_api_key(self) -> str:
        if self.apiKey:
            try:
                return get_cipher().decrypt(self.apiKey.encode("utf-8")).decode("utf-8")
            except Exception:
                return None
        return None


class IntegrationOutbox(TimeStampedTenantModel):
    """
    Tabela do Transactional Outbox Pattern.

    Resolve o problema da transação distribuída. Ao atualizar o status de uma Order,
    uma Trigger/Worker insere o evento aqui na MESMA transação atômica do PostgreSQL.
    Um Worker Celery paralelo limpa essa fila disparando HTTP Requests sem travar o banco.
    """

    class OutboxStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PROCESSING = "PROCESSING", "Processing"
        SENT = "SENT", "Sent"
        FAILED = "FAILED", "Failed"

    operator = models.ForeignKey(
        Operator, on_delete=models.CASCADE, db_column="operator_id"
    )
    aggregateType = models.CharField(
        max_length=100,
        db_column="aggregateType",
        help_text="Entidade alvo (Ex: ORDER).",
    )
    aggregateId = models.UUIDField(
        db_column="aggregateId", help_text="ID do registro afetado."
    )
    sequenceNumber = models.BigIntegerField(
        unique=True,
        editable=False,
        db_column="sequenceNumber",
        help_text="Garante FIFO absoluto. Auto-gerado via BIGSERIAL no Postgres.",
    )
    eventType = models.CharField(
        max_length=100,
        db_column="eventType",
        help_text="Ação ocorrida (Ex: ORDER_ACCEPTED).",
    )
    payload = models.JSONField(
        help_text="Snapshot do payload JSON a ser transmitido ao webhook."
    )
    status = models.CharField(
        max_length=50, choices=OutboxStatus.choices, default=OutboxStatus.PENDING
    )
    attempts = models.IntegerField(
        default=0, help_text="Retries com backoff exponencial."
    )
    lastAttemptAt = models.DateTimeField(
        null=True, blank=True, db_column="lastAttemptAt"
    )
    failReason = models.TextField(
        null=True,
        blank=True,
        db_column="failReason",
        help_text="Armazena os status codes ou timeouts (504, 500, etc).",
    )

    class Meta:
        db_table = "IntegrationOutbox"
        managed = False
        verbose_name = "Fila de Integração (Outbox)"
        verbose_name_plural = "Filas de Integração (Outbox)"

    def save(self, *args, **kwargs):
        if self.sequenceNumber is None:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT nextval(pg_get_serial_sequence(%s, %s))",
                    ['"IntegrationOutbox"', "sequenceNumber"],
                )
                self.sequenceNumber = cursor.fetchone()[0]
        super().save(*args, **kwargs)


class IntegrationEventAudit(TimeStampedTenantModel):
    operator = models.ForeignKey(
        Operator, on_delete=models.CASCADE, db_column="operator_id"
    )
    store = models.ForeignKey(Store, on_delete=models.CASCADE, db_column="store_id")
    order = models.ForeignKey(
        Order, null=True, blank=True, on_delete=models.SET_NULL, db_column="order_id"
    )
    provider = models.CharField(max_length=50)
    direction = models.CharField(max_length=20)
    eventType = models.CharField(max_length=100, db_column="eventType")
    externalEventId = models.CharField(
        max_length=255, null=True, blank=True, db_column="externalEventId"
    )
    externalOrderId = models.CharField(
        max_length=255, null=True, blank=True, db_column="externalOrderId"
    )
    merchantReference = models.CharField(
        max_length=100, null=True, blank=True, db_column="merchantReference"
    )
    deliveryStatus = models.CharField(max_length=30, db_column="deliveryStatus")
    httpStatusCode = models.IntegerField(
        null=True, blank=True, db_column="httpStatusCode"
    )
    payload = models.JSONField(default=dict, blank=True)
    responsePayload = models.JSONField(
        default=dict, blank=True, db_column="responsePayload"
    )
    failReason = models.TextField(null=True, blank=True, db_column="failReason")
    processedAt = models.DateTimeField(null=True, blank=True, db_column="processedAt")

    class Meta:
        db_table = "IntegrationEventAudit"
        managed = False
        verbose_name = "Auditoria de Evento de Integração"
        verbose_name_plural = "Auditorias de Eventos de Integração"
