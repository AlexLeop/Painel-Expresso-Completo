import hashlib
import hmac
from types import SimpleNamespace

from integration.adapters import (
    build_outbound_event_payload,
    extract_external_order_id,
    extract_inbound_status,
    extract_merchant_reference,
    map_inbound_order_status,
    normalize_provider,
    should_apply_inbound_status,
    verify_inbound_signature,
)


def test_normalize_provider_aliases():
    assert normalize_provider("ifood") == "IFOOD"
    assert normalize_provider("99-food") == "99FOOD"
    assert normalize_provider("delivery direto") == "DELIVERY_DIRETO"


def test_extract_references_from_payload_and_headers():
    payload = {
        "order": {"id": "pedido-1", "storeId": "loja-abc"},
    }
    headers = {"X-DeliveryDireto-ID": "header-loja"}

    assert extract_external_order_id(payload) == "pedido-1"
    assert (
        extract_merchant_reference("delivery_direto", headers, payload) == "header-loja"
    )


def test_extract_anota_ai_references_from_payload():
    payload = {
        "_id": "order-anota-1",
        "pageId": "store-anota-1",
    }
    assert extract_external_order_id(payload) == "order-anota-1"
    assert extract_merchant_reference("anota_ai", {}, payload) == "store-anota-1"


def test_verify_delivery_direto_signature():
    raw_body = b'{"id":"123"}'
    secret = "segredo-super"
    signature = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()

    assert verify_inbound_signature(
        "DELIVERY_DIRETO",
        raw_body,
        {"X-DeliveryDireto-Signature": signature},
        secret,
    )
    assert not verify_inbound_signature(
        "DELIVERY_DIRETO",
        raw_body,
        {"X-DeliveryDireto-Signature": "invalida"},
        secret,
    )


def test_verify_anota_ai_token_signature_from_query_param():
    assert verify_inbound_signature(
        "ANOTA_AI",
        b"{}",
        {},
        "token-seguro",
        {"token": "token-seguro"},
    )
    assert not verify_inbound_signature(
        "ANOTA_AI",
        b"{}",
        {},
        "token-seguro",
        {"token": "outro-token"},
    )


def test_build_outbound_event_payload_maps_status():
    order = SimpleNamespace(
        id="order-local-1",
        external_order_id="order-1",
        status="COMPLETED",
        businessDate=None,
        requestedAt=None,
        acceptedAt=None,
        startedAt=None,
        arrivedAt=None,
        completedAt=None,
        driver_id=None,
        store_id=None,
    )
    proof = SimpleNamespace(
        stage="DELIVERY",
        type="PHOTO",
        confirmationCode="1234",
        qrCode=None,
        barcode=None,
        fileUrl="proofs/order-1/file.jpg",
        capturedAt=None,
        deviceIdentifier="device-1",
        gpsAccuracyMeters=5,
        geom=None,
        metadata={"source": "app"},
    )
    payload = build_outbound_event_payload(
        "ifood",
        "ORDER_COMPLETED",
        {
            "order_id": "order-1",
            "merchant_id": "store-1",
            "status": "COMPLETED",
            "occurred_at": "2026-06-21T12:00:00Z",
        },
        order=order,
        delivery_proof=proof,
        event_id="evt-1",
    )

    assert payload["id"] == "evt-1"
    assert payload["provider"] == "IFOOD"
    assert payload["orderStatus"] == "DELIVERED"
    assert payload["merchantId"] == "store-1"
    assert payload["deliveryConfirmation"]["confirmationCode"] == "1234"
    assert payload["acknowledgement"]["mode"] == "POLL_AND_ACK"


def test_map_inbound_order_status_to_ready_for_dispatch():
    payload = {"code": "READY_TO_PICKUP"}
    assert extract_inbound_status("IFOOD", payload) == "READY_TO_PICKUP"
    assert map_inbound_order_status("IFOOD", payload) == "READY_FOR_DISPATCH"


def test_should_apply_inbound_status_without_regression():
    assert should_apply_inbound_status("PREPARING", "READY_FOR_DISPATCH")
    assert not should_apply_inbound_status("STARTED", "READY_FOR_DISPATCH")


def test_map_ifood_mercado_statuses():
    assert map_inbound_order_status("IFOOD", {"status": "PE0"}) == "READY_FOR_DISPATCH"
    assert map_inbound_order_status("IFOOD", {"status": "FIN"}) == "COMPLETED"
    assert map_inbound_order_status("IFOOD", {"status": "CAN"}) == "CANCELED"


def test_map_anota_ai_statuses():
    assert (
        map_inbound_order_status("ANOTA_AI", {"status": "READY"})
        == "READY_FOR_DISPATCH"
    )
    assert map_inbound_order_status("ANOTA_AI", {"status": "DELIVERED"}) == "COMPLETED"
