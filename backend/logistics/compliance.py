from typing import Any, Dict, Iterable, Optional


SUPPORTED_COMPLIANCE_AUDIENCES = {"DRIVER"}
SUPPORTED_PRIVACY_SUBJECT_TYPES = {"DRIVER", "CLIENT_PORTAL_USER"}
SUPPORTED_PRIVACY_REQUEST_TYPES = {
    "ACCESS",
    "RECTIFICATION",
    "ERASURE",
    "PORTABILITY",
    "RESTRICTION",
    "ANONYMIZATION",
}
SUPPORTED_PRIVACY_REQUEST_STATUSES = {"OPEN", "IN_PROGRESS", "RESOLVED", "REJECTED"}
SUPPORTED_RETENTION_RESOURCE_TYPES = {
    "DRIVER_CONSENT_ACCEPTANCE",
    "DRIVER_DEVICE_SECURITY_EVENT",
    "DRIVER_INCIDENT",
    "DRIVER_OFFLINE_SYNC_BATCH",
    "PROOF",
}


def normalize_compliance_audience(audience_type: str) -> str:
    return (audience_type or "").strip().upper()


def normalize_privacy_subject_type(subject_type: str) -> str:
    return (subject_type or "").strip().upper()


def normalize_privacy_request_type(request_type: str) -> str:
    return (request_type or "").strip().upper()


def normalize_privacy_request_status(status: str) -> str:
    return (status or "").strip().upper()


def normalize_retention_resource_type(resource_type: str) -> str:
    return (resource_type or "").strip().upper()


def minimized_metadata(
    metadata: Optional[Dict[str, Any]],
    *,
    marker: str,
    preserve_keys: Optional[Iterable[str]] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    preserved: Dict[str, Any] = {}
    original = metadata or {}
    for key in preserve_keys or []:
        if key in original and original[key] is not None:
            preserved[key] = original[key]

    return {
        "redacted": True,
        "marker": marker,
        **preserved,
        **(extra or {}),
    }
