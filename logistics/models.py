"""
Módulo Logístico.

Este é o coração operacional do sistema. Contém a modelagem das Lojas (Stores),
Motoristas (Drivers), Zonas de Serviço, Pedidos (Orders), Paradas (Stops), e os
Manifestos de Rotação (Manifests).

Também concentra a telemetria geoespacial de alta performance (Position e GeofenceEvent)
mapeando nativamente para o PostGIS do banco de dados (usando django.contrib.gis.db).
Todos os modelos possuem `managed = False` para manter o contrato de "Database-First".
"""

from django.contrib.gis.db import models as gis_models
from django.db import models
from config.core_models import TenantModel, TimeStampedTenantModel
from accounts.models import Operator, StaffMember


class Client(TimeStampedTenantModel):
    """
    Cliente / Marca parceira do Operador Logístico.
    Representa as redes de fast-food ou empresas embarcadoras de entregas.
    """

    operator = models.ForeignKey(
        Operator, on_delete=models.CASCADE, db_column="operator_id"
    )
    name = models.CharField(
        max_length=255, help_text="Nome da franquia ou cliente embarcador."
    )
    document = models.CharField(max_length=20, help_text="CNPJ do cliente.")
    active = models.BooleanField(default=True)

    class Meta:
        db_table = "Client"
        managed = False
        verbose_name = "Cliente Parceiro"
        verbose_name_plural = "Clientes Parceiros"


class ClientPortalUser(TimeStampedTenantModel):
    """
    Credencial de acesso do cliente.
    Garante acesso ao Portal do Cliente para visualizar as faturas de suas lojas
    ou inserir pedidos manuais de forma segura, limitado via RLS.
    """

    operator = models.ForeignKey(
        Operator, on_delete=models.CASCADE, db_column="operator_id"
    )
    client = models.ForeignKey(Client, on_delete=models.CASCADE, db_column="client_id")
    supabase_uid = models.UUIDField(unique=True, help_text="Vínculo com Auth Seguro.")
    name = models.CharField(max_length=255)
    email = models.CharField(max_length=255)

    class Meta:
        db_table = "ClientPortalUser"
        managed = False


class Store(TimeStampedTenantModel):
    """
    Loja Física / Ponto de Coleta do Cliente.
    Geolocalizada de forma nativa no PostgreSQL (PostGIS) para facilitar o cálculo
    de distâncias, geofencing e alocação de motoristas (ST_DWithin).
    """

    operator = models.ForeignKey(
        Operator, on_delete=models.CASCADE, db_column="operator_id"
    )
    client = models.ForeignKey(Client, on_delete=models.CASCADE, db_column="client_id")
    name = models.CharField(
        max_length=255, help_text="Identificação única da loja na rede."
    )
    averagePrepTimeMinutes = models.IntegerField(
        default=15,
        db_column="averagePrepTimeMinutes",
        help_text="Tempo médio de preparo para estimativa do SLA.",
    )
    geom = gis_models.PointField(
        geography=True,
        srid=4326,
        help_text="Geolocalização (Lat/Lng) da loja para cálculos ST_DWithin.",
    )
    operational = models.BooleanField(default=False)

    class Meta:
        db_table = "Store"
        managed = False
        verbose_name = "Loja"
        verbose_name_plural = "Lojas"

    def __str__(self):
        return self.name


class Turno(TenantModel):
    """
    Turnos Operacionais da Loja.
    Determina as janelas de disponibilidade em que a loja requer motoristas.
    """

    operator = models.ForeignKey(
        Operator, on_delete=models.CASCADE, db_column="operator_id"
    )
    store = models.ForeignKey(Store, on_delete=models.CASCADE, db_column="store_id")
    name = models.CharField(max_length=255)
    startTime = models.TimeField(db_column="startTime")
    endTime = models.TimeField(db_column="endTime")

    class Meta:
        db_table = "Turno"
        managed = False


class Vehicle(TenantModel):
    """Veículos cadastrados sob a gestão do Operador Logístico."""

    class VehicleType(models.TextChoices):
        MOTORCYCLE = "MOTORCYCLE", "Motorcycle"
        BICYCLE = "BICYCLE", "Bicycle"
        CAR = "CAR", "Car"

    operator = models.ForeignKey(
        Operator, on_delete=models.CASCADE, db_column="operator_id"
    )
    plate = models.CharField(
        max_length=10, unique=True, help_text="Placa ou identificação visual."
    )
    type = models.CharField(
        max_length=20, choices=VehicleType.choices, default=VehicleType.MOTORCYCLE
    )
    active = models.BooleanField(default=True)

    class Meta:
        db_table = "Vehicle"
        managed = False


class Driver(TimeStampedTenantModel):
    """
    Motorista / Entregador parceiro do Operador.
    Armazena dados financeiros (Chave PIX) e last_ping geoespacial (Posição atual)
    para o despacho em tempo real.
    """

    operator = models.ForeignKey(
        Operator, on_delete=models.CASCADE, db_column="operator_id"
    )
    supabase_uid = models.UUIDField(unique=True)
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    pixKeyType = models.CharField(max_length=20, db_column="pixKeyType")
    pixKey = models.CharField(max_length=255, db_column="pixKey")
    online = models.BooleanField(
        default=False,
        help_text="Flag indicando se o app do motoboy está rodando no background.",
    )
    geom = gis_models.PointField(
        geography=True,
        srid=4326,
        null=True,
        blank=True,
        help_text="Último ping válido do device.",
    )
    heading = models.IntegerField(default=0, null=True, blank=True)
    speedKmh = models.IntegerField(
        default=0, null=True, blank=True, db_column="speedKmh"
    )
    lastPingAt = models.DateTimeField(null=True, blank=True, db_column="lastPingAt")
    active = models.BooleanField(default=True)
    operational_status = models.CharField(
        max_length=30, default="OFFLINE", db_column="operational_status"
    )
    maxActiveOrders = models.IntegerField(default=3, db_column="maxActiveOrders")

    # Onboarding
    onboarding_status = models.CharField(max_length=50, default="INVITED")
    tax_classification = models.CharField(
        max_length=50, default="PESSOA_FISICA_AUTONOMO"
    )
    document = models.CharField(max_length=20, null=True, blank=True)

    class Meta:
        db_table = "Driver"
        managed = False
        verbose_name = "Motorista"
        verbose_name_plural = "Motoristas"

    def __str__(self):
        return self.name


class StoreDriver(TimeStampedTenantModel):
    """
    Tabela de Vínculo Many-to-Many entre Lojas e Motoristas (Hub Model).
    Define quais motoristas estão homologados para operar em quais lojas.
    """

    operator = models.ForeignKey(
        Operator, on_delete=models.CASCADE, db_column="operator_id"
    )
    store = models.ForeignKey(Store, on_delete=models.CASCADE, db_column="store_id")
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, db_column="driver_id")

    class Meta:
        db_table = "StoreDriver"
        managed = False


class Place(TenantModel):
    """
    Endereços (Places) consolidados.
    Endereços geocodificados dos clientes finais (Dropoffs). O uso de geometria local
    impede chamadas repetidas a APIs externas (Google Maps/Mapbox) para endereços já conhecidos.
    """

    operator = models.ForeignKey(
        Operator, on_delete=models.CASCADE, db_column="operator_id"
    )
    street = models.CharField(max_length=255)
    number = models.CharField(max_length=20, null=True, blank=True)
    neighborhood = models.CharField(max_length=100, null=True, blank=True)
    city = models.CharField(max_length=100)
    postalCode = models.CharField(max_length=15, db_column="postalCode")
    accessCode = models.CharField(
        max_length=50, null=True, blank=True, db_column="accessCode"
    )
    geom = gis_models.PointField(geography=True, srid=4326)

    class Meta:
        db_table = "Place"
        managed = False


class ServiceZone(TimeStampedTenantModel):
    """
    Cerca geográfica operacional da Loja ou do Operador.
    Controla raio de restrição utilizando ST_Contains.
    """

    operator = models.ForeignKey(
        Operator, on_delete=models.CASCADE, db_column="operator_id"
    )
    name = models.CharField(max_length=255)
    geom = gis_models.PolygonField(
        geography=True, srid=4326, help_text="Polígono delimitador (Geofence)."
    )

    class Meta:
        db_table = "ServiceZone"
        managed = False


class ScheduleEntry(TimeStampedTenantModel):
    """
    Escala Operacional (Agendamento do Motorista na Loja).
    Base para o cálculo do "Modo Garantida".
    """

    operator = models.ForeignKey(
        Operator, on_delete=models.CASCADE, db_column="operator_id"
    )
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, db_column="driver_id")
    store = models.ForeignKey(Store, on_delete=models.CASCADE, db_column="store_id")
    turno = models.ForeignKey(Turno, on_delete=models.CASCADE, db_column="turno_id")
    date = models.DateField()
    minGuaranteedOverrideCents = models.BigIntegerField(
        null=True, blank=True, db_column="minGuaranteedOverrideCents"
    )

    class Meta:
        db_table = "ScheduleEntry"
        managed = False


class ScheduleEntryAudit(TenantModel):
    """
    Trilha de Auditoria para trocas de escala.
    Registra quem trocou o motorista, de qual loja para qual loja, e o motivo.
    Vital para evitar conflitos de 'quem deveria estar trabalhando'.
    """

    operator = models.ForeignKey(
        Operator, on_delete=models.CASCADE, db_column="operator_id"
    )
    scheduleEntry = models.ForeignKey(
        ScheduleEntry, on_delete=models.CASCADE, db_column="scheduleEntryId"
    )
    staff = models.ForeignKey(
        StaffMember, on_delete=models.RESTRICT, db_column="staffId"
    )
    previousStore = models.ForeignKey(
        Store,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        db_column="previousStoreId",
        related_name="audit_previous",
    )
    newStore = models.ForeignKey(
        Store,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        db_column="newStoreId",
        related_name="audit_new",
    )
    reason = models.TextField(
        help_text="Justificativa obrigatória para a troca de escala."
    )
    createdAt = models.DateTimeField(auto_now_add=True, db_column="createdAt")

    class Meta:
        db_table = "ScheduleEntryAudit"
        managed = False
        verbose_name = "Auditoria de Escala"
        verbose_name_plural = "Auditorias de Escala"


class Manifest(TimeStampedTenantModel):
    """
    Manifesto de Viagem.
    Agrupamento físico de múltiplas ordens de entrega em um único pacote de rota
    para otimizar despacho.
    """

    class ManifestStatus(models.TextChoices):
        OPEN = "OPEN", "Open"
        LOCKED = "LOCKED", "Locked"
        COMPLETED = "COMPLETED", "Completed"
        CANCELED = "CANCELED", "Canceled"

    class GroupingMethod(models.TextChoices):
        MANUAL = "MANUAL", "Manual"
        AUTOMATIC = "AUTOMATIC", "Automatic"

    operator = models.ForeignKey(
        Operator, on_delete=models.CASCADE, db_column="operator_id"
    )
    driver = models.ForeignKey(
        Driver, on_delete=models.SET_NULL, null=True, blank=True, db_column="driver_id"
    )
    status = models.CharField(
        max_length=20, choices=ManifestStatus.choices, default=ManifestStatus.OPEN
    )
    groupingMethod = models.CharField(
        max_length=20,
        choices=GroupingMethod.choices,
        default=GroupingMethod.AUTOMATIC,
        db_column="groupingMethod",
    )
    totalDistanceMeters = models.IntegerField(
        default=0,
        db_column="totalDistanceMeters",
        help_text="Distância acumulada do manifesto.",
    )
    totalEtaSeconds = models.IntegerField(
        default=0, db_column="totalEtaSeconds", help_text="Tempo estimado total."
    )
    lockedAt = models.DateTimeField(null=True, blank=True, db_column="lockedAt")
    completedAt = models.DateTimeField(null=True, blank=True, db_column="completedAt")

    class Meta:
        db_table = "Manifest"
        managed = False
        verbose_name = "Manifesto"
        verbose_name_plural = "Manifestos"


from .exceptions import InvalidOrderStatusTransitionError


class Order(TenantModel):
    """
    Pedido Central de Entrega.
    O elemento atômico contendo as travas de idempotência e os SLAs.
    Pertence fisicamente a uma loja e é inserido no roteiro de um Manifesto.
    """

    class OrderStatus(models.TextChoices):
        PREPARING = "PREPARING", "Preparing"
        READY_FOR_DISPATCH = "READY_FOR_DISPATCH", "Ready For Dispatch"
        OFFERED = "OFFERED", "Offered"
        ACCEPTED = "ACCEPTED", "Accepted"
        STARTED = "STARTED", "Started"
        ARRIVED = "ARRIVED", "Arrived"
        COMPLETED = "COMPLETED", "Completed"
        CANCELED = "CANCELED", "Canceled"
        CANCELED_IN_TRANSIT = "CANCELED_IN_TRANSIT", "Canceled In Transit"
        RETURNING_TO_STORE = "RETURNING_TO_STORE", "Returning To Store"
        RETURNED = "RETURNED", "Returned"

    # Transições válidas de status conforme Protocolo LOGIPAY
    VALID_TRANSITIONS = {
        OrderStatus.PREPARING: [OrderStatus.READY_FOR_DISPATCH, OrderStatus.CANCELED],
        OrderStatus.READY_FOR_DISPATCH: [OrderStatus.OFFERED, OrderStatus.CANCELED],
        OrderStatus.OFFERED: [
            OrderStatus.ACCEPTED,
            OrderStatus.CANCELED,
            OrderStatus.PREPARING,
        ],
        # ACCEPTED -> OFFERED cobre devolucao pelo motorista e redistribuicao operacional
        # antes do inicio efetivo da corrida.
        OrderStatus.ACCEPTED: [
            OrderStatus.STARTED,
            OrderStatus.CANCELED,
            OrderStatus.OFFERED,
        ],
        OrderStatus.STARTED: [OrderStatus.ARRIVED, OrderStatus.CANCELED_IN_TRANSIT],
        OrderStatus.ARRIVED: [OrderStatus.COMPLETED, OrderStatus.RETURNING_TO_STORE],
        OrderStatus.RETURNING_TO_STORE: [OrderStatus.RETURNED],
        OrderStatus.COMPLETED: [],
        OrderStatus.CANCELED: [],
        OrderStatus.CANCELED_IN_TRANSIT: [OrderStatus.RETURNING_TO_STORE],
        OrderStatus.RETURNED: [],
    }

    operator = models.ForeignKey(
        Operator, on_delete=models.CASCADE, db_column="operator_id"
    )
    store = models.ForeignKey(Store, on_delete=models.CASCADE, db_column="store_id")
    driver = models.ForeignKey(
        Driver, on_delete=models.SET_NULL, null=True, blank=True, db_column="driver_id"
    )
    manifest = models.ForeignKey(
        Manifest,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="manifest_id",
    )
    status = models.CharField(
        max_length=30, choices=OrderStatus.choices, default=OrderStatus.PREPARING
    )

    @classmethod
    def validate_status_transition(cls, current_status: str, desired_status: str):
        allowed = cls.VALID_TRANSITIONS.get(current_status, [])
        if desired_status not in allowed:
            raise InvalidOrderStatusTransitionError(
                current_status=current_status, desired_status=desired_status
            )

    def save(self, *args, **kwargs):
        # Verificar se é uma atualização (tem pk) e se o status mudou
        if self.pk is not None:
            old_order = Order.objects.filter(pk=self.pk).first()
            if old_order is not None and old_order.status != self.status:
                self.validate_status_transition(old_order.status, self.status)
        # Chamar o save original
        super().save(*args, **kwargs)

    fareValueCents = models.IntegerField(
        db_column="fareValueCents",
        help_text="Valor da entrega computado pelas regras financeiras.",
    )
    storeAuthorizedBonusCents = models.IntegerField(
        default=0, db_column="storeAuthorizedBonusCents"
    )
    distanceMeters = models.IntegerField(db_column="distanceMeters")
    businessDate = models.DateField(
        db_column="businessDate", help_text="Data de corte fiscal para a fatura."
    )
    allocationDifficulty = models.BooleanField(
        default=False, db_column="allocationDifficulty"
    )
    requestedAt = models.DateTimeField(auto_now_add=True, db_column="requestedAt")
    acceptedAt = models.DateTimeField(null=True, blank=True, db_column="acceptedAt")
    startedAt = models.DateTimeField(null=True, blank=True, db_column="startedAt")
    arrivedAt = models.DateTimeField(null=True, blank=True, db_column="arrivedAt")
    completedAt = models.DateTimeField(null=True, blank=True, db_column="completedAt")
    canceledAt = models.DateTimeField(null=True, blank=True, db_column="canceledAt")

    external_order_id = models.CharField(
        max_length=255, null=True, blank=True, db_column="external_order_id"
    )
    external_source = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        db_column="external_source",
        help_text="Ex: 'ifood', 'hubster', 'delivery_direto'",
    )

    class Meta:
        db_table = "Order"
        managed = False
        verbose_name = "Pedido de Entrega"
        verbose_name_plural = "Pedidos de Entrega"
        constraints = [
            models.UniqueConstraint(
                fields=["store", "external_source", "external_order_id"],
                name="idx_order_external",
            )
        ]


class Stop(TenantModel):
    """
    Ponto de Parada da Rota.
    Guarda o Pin code de segurança (POD) caso seja um Dropoff que exija validação no ato.
    """

    class StopType(models.TextChoices):
        PICKUP = "PICKUP", "Pickup"
        DROPOFF = "DROPOFF", "Dropoff"
        RETURN = "RETURN", "Return"

    operator = models.ForeignKey(
        Operator, on_delete=models.CASCADE, db_column="operator_id"
    )
    order = models.ForeignKey(Order, on_delete=models.CASCADE, db_column="order_id")
    sequence = models.IntegerField()
    type = models.CharField(
        max_length=20, choices=StopType.choices, default=StopType.DROPOFF
    )
    geom = gis_models.PointField(geography=True, srid=4326)
    requiresPin = models.BooleanField(default=False, db_column="requiresPin")
    deliveryPinHash = models.TextField(
        null=True, blank=True, db_column="deliveryPinHash"
    )
    completedAt = models.DateTimeField(null=True, blank=True, db_column="completedAt")

    class Meta:
        db_table = "Stop"
        managed = False


class ManifestStop(TenantModel):
    """
    Tabela pivô ordenando as Paradas dentro de um Manifesto.
    """

    operator = models.ForeignKey(
        Operator, on_delete=models.CASCADE, db_column="operator_id"
    )
    manifest = models.ForeignKey(
        Manifest, on_delete=models.CASCADE, db_column="manifest_id"
    )
    stop = models.ForeignKey(Stop, on_delete=models.CASCADE, db_column="stop_id")
    sequence = models.IntegerField()

    class Meta:
        db_table = "ManifestStop"
        managed = False


class Position(TenantModel):
    """
    Telemetria em massa (Raw Data).
    Esta tabela no futuro deverá ser particionada fisicamente por data.
    """

    operator = models.ForeignKey(
        Operator, on_delete=models.CASCADE, db_column="operator_id"
    )
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, db_column="driver_id")
    geom = gis_models.PointField(geography=True, srid=4326)
    heading = models.IntegerField()
    speedKmh = models.IntegerField(db_column="speedKmh")
    capturedAt = models.DateTimeField(db_column="capturedAt")

    class Meta:
        db_table = "Position"
        managed = False


class Proof(TenantModel):
    """
    Proof of Delivery (POD - Prova de Entrega).
    Registra fotos e assinaturas digitalizadas na nuvem (AWS/Supabase Storage)
    para proteção legal.
    """

    class ProofType(models.TextChoices):
        PHOTO = "PHOTO", "Photo"
        SIGNATURE = "SIGNATURE", "Signature"
        SCAN = "SCAN", "Scan"

    operator = models.ForeignKey(
        Operator, on_delete=models.CASCADE, db_column="operator_id"
    )
    stop = models.ForeignKey(Stop, on_delete=models.CASCADE, db_column="stop_id")
    type = models.CharField(
        max_length=20, choices=ProofType.choices, default=ProofType.PHOTO
    )
    stage = models.CharField(max_length=20, default="DELIVERY")
    fileUrl = models.TextField(
        db_column="fileUrl", help_text="URI do arquivo físico armazenado."
    )
    geom = gis_models.PointField(geography=True, srid=4326, null=True, blank=True)
    gpsAccuracyMeters = models.IntegerField(
        null=True, blank=True, db_column="gpsAccuracyMeters"
    )
    deviceIdentifier = models.CharField(
        max_length=255, null=True, blank=True, db_column="deviceIdentifier"
    )
    confirmationCode = models.CharField(
        max_length=100, null=True, blank=True, db_column="confirmationCode"
    )
    qrCode = models.CharField(max_length=255, null=True, blank=True, db_column="qrCode")
    barcode = models.TextField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    capturedAt = models.DateTimeField(auto_now_add=True, db_column="capturedAt")

    class Meta:
        db_table = "Proof"
        managed = False


class GeofenceEvent(TenantModel):
    """
    Eventos de Geofence (Entrada e Saída).
    Computados na Fast Lane para detectar o SLA real de presença em loja ou ponto do cliente.
    """

    class EventType(models.TextChoices):
        ENTER = "ENTER", "Enter"
        EXIT = "EXIT", "Exit"

    operator = models.ForeignKey(
        Operator, on_delete=models.CASCADE, db_column="operator_id"
    )
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, db_column="driver_id")
    stop = models.ForeignKey(Stop, on_delete=models.CASCADE, db_column="stop_id")
    type = models.CharField(max_length=10, choices=EventType.choices)
    capturedAt = models.DateTimeField(auto_now_add=True, db_column="capturedAt")

    class Meta:
        db_table = "GeofenceEvent"
        managed = False


class DriverDocumentRequirement(models.Model):
    """Regras de obrigatoriedade de documentos baseado na classificação fiscal."""

    id = models.UUIDField(primary_key=True)
    tax_class = models.CharField(max_length=50)
    document_type = models.CharField(max_length=50)
    is_required = models.BooleanField(default=True)

    class Meta:
        db_table = "DriverDocumentRequirement"
        managed = False


class DriverDocument(TimeStampedTenantModel):
    """
    Documentos enviados pelo Motorista no app.
    Usado para validação de onboarding.
    """

    operator = models.ForeignKey(
        Operator, on_delete=models.CASCADE, db_column="operator_id"
    )
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, db_column="driver_id")
    name = models.CharField(max_length=255)
    fileUrl = models.TextField(db_column="fileUrl")
    expiresAt = models.DateField(null=True, blank=True, db_column="expiresAt")

    document_type = models.CharField(max_length=50, default="CNH")
    status = models.CharField(max_length=50, default="PENDING_APPROVAL")
    rejectReason = models.TextField(null=True, blank=True, db_column="rejectReason")

    class Meta:
        db_table = "DriverDocument"
        managed = False


class DriverStatusAudit(TenantModel):
    operator = models.ForeignKey(
        Operator, on_delete=models.CASCADE, db_column="operator_id"
    )
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, db_column="driver_id")
    previous_status = models.CharField(max_length=30, db_column="previous_status")
    new_status = models.CharField(max_length=30, db_column="new_status")
    reason = models.TextField(null=True, blank=True)
    createdAt = models.DateTimeField(auto_now_add=True, db_column="createdAt")

    class Meta:
        db_table = "DriverStatusAudit"
        managed = False


class DriverShiftSession(TenantModel):
    operator = models.ForeignKey(
        Operator, on_delete=models.CASCADE, db_column="operator_id"
    )
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, db_column="driver_id")
    scheduleEntry = models.ForeignKey(
        ScheduleEntry,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        db_column="scheduleEntryId",
    )
    status = models.CharField(max_length=20, default="OPEN")
    checkInAt = models.DateTimeField(db_column="checkInAt")
    checkOutAt = models.DateTimeField(null=True, blank=True, db_column="checkOutAt")
    reason = models.TextField(null=True, blank=True)
    createdAt = models.DateTimeField(auto_now_add=True, db_column="createdAt")

    class Meta:
        db_table = "DriverShiftSession"
        managed = False


class DriverIncident(TenantModel):
    operator = models.ForeignKey(
        Operator, on_delete=models.CASCADE, db_column="operator_id"
    )
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, db_column="driver_id")
    order = models.ForeignKey(
        Order, null=True, blank=True, on_delete=models.SET_NULL, db_column="order_id"
    )
    stop = models.ForeignKey(
        Stop, null=True, blank=True, on_delete=models.SET_NULL, db_column="stop_id"
    )
    type = models.CharField(max_length=50)
    status = models.CharField(max_length=20, default="OPEN")
    description = models.TextField()
    geom = gis_models.PointField(geography=True, srid=4326, null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    resolvedAt = models.DateTimeField(null=True, blank=True, db_column="resolvedAt")
    createdAt = models.DateTimeField(auto_now_add=True, db_column="createdAt")

    class Meta:
        db_table = "DriverIncident"
        managed = False


class DriverIncidentAttachment(TenantModel):
    operator = models.ForeignKey(
        Operator, on_delete=models.CASCADE, db_column="operator_id"
    )
    incident = models.ForeignKey(
        DriverIncident, on_delete=models.CASCADE, db_column="incident_id"
    )
    type = models.CharField(max_length=20)
    fileUrl = models.TextField(db_column="fileUrl")
    metadata = models.JSONField(default=dict, blank=True)
    createdAt = models.DateTimeField(auto_now_add=True, db_column="createdAt")

    class Meta:
        db_table = "DriverIncidentAttachment"
        managed = False


class DriverShiftReservation(TenantModel):
    operator = models.ForeignKey(
        Operator, on_delete=models.CASCADE, db_column="operator_id"
    )
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, db_column="driver_id")
    store = models.ForeignKey(Store, on_delete=models.CASCADE, db_column="store_id")
    turno = models.ForeignKey(Turno, on_delete=models.CASCADE, db_column="turno_id")
    date = models.DateField()
    status = models.CharField(max_length=20, default="REQUESTED")
    note = models.TextField(null=True, blank=True)
    decidedAt = models.DateTimeField(null=True, blank=True, db_column="decidedAt")
    createdAt = models.DateTimeField(auto_now_add=True, db_column="createdAt")

    class Meta:
        db_table = "DriverShiftReservation"
        managed = False


class DriverDevice(TenantModel):
    operator = models.ForeignKey(
        Operator, on_delete=models.CASCADE, db_column="operator_id"
    )
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, db_column="driver_id")
    deviceIdentifier = models.CharField(max_length=255, db_column="deviceIdentifier")
    platform = models.CharField(max_length=30)
    label = models.CharField(max_length=120)
    status = models.CharField(max_length=20, default="ACTIVE")
    trusted = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    lastSeenAt = models.DateTimeField(null=True, blank=True, db_column="lastSeenAt")
    createdAt = models.DateTimeField(auto_now_add=True, db_column="createdAt")

    class Meta:
        db_table = "DriverDevice"
        managed = False


class DriverDeviceSecurityEvent(TenantModel):
    operator = models.ForeignKey(
        Operator, on_delete=models.CASCADE, db_column="operator_id"
    )
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, db_column="driver_id")
    device = models.ForeignKey(
        DriverDevice, on_delete=models.CASCADE, db_column="device_id"
    )
    riskLevel = models.CharField(max_length=20, db_column="riskLevel")
    flags = models.JSONField(default=dict, blank=True)
    createdAt = models.DateTimeField(auto_now_add=True, db_column="createdAt")

    class Meta:
        db_table = "DriverDeviceSecurityEvent"
        managed = False


class DriverOfflineSyncBatch(TenantModel):
    operator = models.ForeignKey(
        Operator, on_delete=models.CASCADE, db_column="operator_id"
    )
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, db_column="driver_id")
    deviceIdentifier = models.CharField(max_length=255, db_column="deviceIdentifier")
    payload = models.JSONField(default=dict, blank=True)
    itemCount = models.IntegerField(default=0, db_column="itemCount")
    status = models.CharField(max_length=20, default="RECEIVED")
    failReason = models.TextField(null=True, blank=True, db_column="failReason")
    createdAt = models.DateTimeField(auto_now_add=True, db_column="createdAt")

    class Meta:
        db_table = "DriverOfflineSyncBatch"
        managed = False


class OrderAssignmentAudit(TenantModel):
    operator = models.ForeignKey(
        Operator, on_delete=models.CASCADE, db_column="operator_id"
    )
    order = models.ForeignKey(Order, on_delete=models.CASCADE, db_column="order_id")
    previousDriver = models.ForeignKey(
        Driver,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assignment_audits_previous",
        db_column="previous_driver_id",
    )
    newDriver = models.ForeignKey(
        Driver,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assignment_audits_new",
        db_column="new_driver_id",
    )
    changedByStaff = models.ForeignKey(
        StaffMember,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        db_column="changed_by_staff_id",
    )
    changedByClient = models.ForeignKey(
        ClientPortalUser,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        db_column="changed_by_client_id",
    )
    changedByDriver = models.ForeignKey(
        Driver,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assignment_audits_actor",
        db_column="changed_by_driver_id",
    )
    reason = models.TextField()
    createdAt = models.DateTimeField(auto_now_add=True, db_column="createdAt")

    class Meta:
        db_table = "OrderAssignmentAudit"
        managed = False


class DriverCommunicationThread(TimeStampedTenantModel):
    operator = models.ForeignKey(
        Operator, on_delete=models.CASCADE, db_column="operator_id"
    )
    order = models.ForeignKey(
        Order, null=True, blank=True, on_delete=models.SET_NULL, db_column="order_id"
    )
    store = models.ForeignKey(
        Store, null=True, blank=True, on_delete=models.SET_NULL, db_column="store_id"
    )
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, db_column="driver_id")
    sourceType = models.CharField(
        max_length=20, db_column="sourceType", default="STORE"
    )
    status = models.CharField(max_length=20, default="OPEN")
    subject = models.CharField(max_length=255, null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "DriverCommunicationThread"
        managed = False


class DriverCommunicationMessage(TenantModel):
    operator = models.ForeignKey(
        Operator, on_delete=models.CASCADE, db_column="operator_id"
    )
    thread = models.ForeignKey(
        DriverCommunicationThread, on_delete=models.CASCADE, db_column="thread_id"
    )
    senderType = models.CharField(max_length=20, db_column="senderType")
    senderName = models.CharField(
        max_length=255, null=True, blank=True, db_column="senderName"
    )
    message = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    createdAt = models.DateTimeField(auto_now_add=True, db_column="createdAt")

    class Meta:
        db_table = "DriverCommunicationMessage"
        managed = False


class ComplianceDocument(TimeStampedTenantModel):
    operator = models.ForeignKey(
        Operator, on_delete=models.CASCADE, db_column="operator_id"
    )
    audienceType = models.CharField(
        max_length=20, db_column="audienceType", default="DRIVER"
    )
    code = models.CharField(max_length=100)
    title = models.CharField(max_length=255)
    version = models.CharField(max_length=50)
    body = models.TextField()
    required = models.BooleanField(default=True)
    active = models.BooleanField(default=True)
    effectiveAt = models.DateTimeField(db_column="effectiveAt")
    archivedAt = models.DateTimeField(null=True, blank=True, db_column="archivedAt")
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "ComplianceDocument"
        managed = False


class DriverConsentAcceptance(TenantModel):
    operator = models.ForeignKey(
        Operator, on_delete=models.CASCADE, db_column="operator_id"
    )
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, db_column="driver_id")
    document = models.ForeignKey(
        ComplianceDocument, on_delete=models.CASCADE, db_column="document_id"
    )
    deviceIdentifier = models.CharField(
        max_length=255, null=True, blank=True, db_column="deviceIdentifier"
    )
    ipAddress = models.CharField(
        max_length=64, null=True, blank=True, db_column="ipAddress"
    )
    userAgent = models.TextField(null=True, blank=True, db_column="userAgent")
    metadata = models.JSONField(default=dict, blank=True)
    acceptedAt = models.DateTimeField(auto_now_add=True, db_column="acceptedAt")
    revokedAt = models.DateTimeField(null=True, blank=True, db_column="revokedAt")
    revokedReason = models.TextField(null=True, blank=True, db_column="revokedReason")

    class Meta:
        db_table = "DriverConsentAcceptance"
        managed = False


class PrivacyDataRequest(TimeStampedTenantModel):
    operator = models.ForeignKey(
        Operator, on_delete=models.CASCADE, db_column="operator_id"
    )
    subjectType = models.CharField(
        max_length=30, db_column="subjectType", default="DRIVER"
    )
    driver = models.ForeignKey(
        Driver, null=True, blank=True, on_delete=models.CASCADE, db_column="driver_id"
    )
    clientPortalUser = models.ForeignKey(
        ClientPortalUser,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        db_column="client_portal_user_id",
    )
    requestType = models.CharField(max_length=30, db_column="requestType")
    status = models.CharField(max_length=30, default="OPEN")
    description = models.TextField()
    resolution = models.TextField(null=True, blank=True)
    resolvedAt = models.DateTimeField(null=True, blank=True, db_column="resolvedAt")
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "PrivacyDataRequest"
        managed = False


class ComplianceRetentionPolicy(TimeStampedTenantModel):
    operator = models.ForeignKey(
        Operator, on_delete=models.CASCADE, db_column="operator_id"
    )
    resourceType = models.CharField(max_length=50, db_column="resourceType")
    retentionDays = models.IntegerField(db_column="retentionDays")
    active = models.BooleanField(default=True)
    lastExecutedAt = models.DateTimeField(
        null=True, blank=True, db_column="lastExecutedAt"
    )
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "ComplianceRetentionPolicy"
        managed = False
