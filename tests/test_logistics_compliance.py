from logistics.compliance import (
    minimized_metadata,
    normalize_compliance_audience,
    normalize_privacy_request_status,
    normalize_privacy_request_type,
    normalize_retention_resource_type,
)


def test_minimized_metadata_preserves_selected_keys():
    result = minimized_metadata(
        {
            "accepted_via": "driver_api",
            "ip_address": "127.0.0.1",
            "extra": "secret",
        },
        marker="driver_consent_acceptance",
        preserve_keys=("accepted_via",),
        extra={"status": "OPEN"},
    )

    assert result == {
        "redacted": True,
        "marker": "driver_consent_acceptance",
        "accepted_via": "driver_api",
        "status": "OPEN",
    }


def test_normalizers_uppercase_and_trim_values():
    assert normalize_compliance_audience(" driver ") == "DRIVER"
    assert normalize_privacy_request_type(" access ") == "ACCESS"
    assert normalize_privacy_request_status(" resolved ") == "RESOLVED"
    assert normalize_retention_resource_type(" proof ") == "PROOF"
