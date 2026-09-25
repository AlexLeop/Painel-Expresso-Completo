"""Read-only audit for adopting an existing PostgreSQL schema into the SQL ledger.

This command never creates, alters, drops, or records anything.  It checks
catalog fingerprints for every canonical SQL migration and only recommends a
baseline when the observed history is a contiguous APPLIED prefix followed by
MISSING migrations.  PARTIAL migrations or APPLIED migrations after a gap are
reported as unsafe and require manual reconciliation.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import psycopg

if __package__:
    from .apply_schema import discover_migrations, resolve_migrations_dir
else:
    from apply_schema import discover_migrations, resolve_migrations_dir


@dataclass(frozen=True)
class Probe:
    label: str
    sql: str
    params: tuple[object, ...] = ()


@dataclass(frozen=True)
class MigrationFingerprint:
    name: str
    probes: tuple[Probe, ...]


def table(name: str) -> Probe:
    return Probe(
        f"table:{name}",
        "SELECT to_regclass(%s) IS NOT NULL",
        (f'public."{name}"',),
    )


def plain_table(name: str) -> Probe:
    return Probe(
        f"table:{name}",
        "SELECT to_regclass(%s) IS NOT NULL",
        (f"public.{name}",),
    )


def column(table_name: str, column_name: str) -> Probe:
    return Probe(
        f"column:{table_name}.{column_name}",
        """
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = %s
              AND column_name = %s
        )
        """,
        (table_name, column_name),
    )


def nullable_column(table_name: str, column_name: str) -> Probe:
    return Probe(
        f"nullable:{table_name}.{column_name}",
        """
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = %s
              AND column_name = %s
              AND is_nullable = 'YES'
        )
        """,
        (table_name, column_name),
    )


def index(name: str) -> Probe:
    return Probe(
        f"index:{name}",
        "SELECT to_regclass(%s) IS NOT NULL",
        (f"public.{name}",),
    )


def constraint(name: str) -> Probe:
    return Probe(
        f"constraint:{name}",
        "SELECT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = %s)",
        (name,),
    )


def function(signature: str) -> Probe:
    return Probe(
        f"function:{signature}",
        "SELECT to_regprocedure(%s) IS NOT NULL",
        (signature,),
    )


def policy(table_name: str, policy_name: str) -> Probe:
    return Probe(
        f"policy:{table_name}.{policy_name}",
        """
        SELECT EXISTS (
            SELECT 1 FROM pg_policies
            WHERE schemaname = 'public'
              AND tablename = %s
              AND policyname = %s
        )
        """,
        (table_name, policy_name),
    )


FINGERPRINTS: tuple[MigrationFingerprint, ...] = (
    MigrationFingerprint(
        "20260619200249_initial_schema.sql",
        tuple(
            table(name)
            for name in (
                "Operator",
                "PlatformAdmin",
                "StaffMember",
                "Client",
                "ClientPortalUser",
                "Store",
                "Driver",
                "StoreDriver",
                "Order",
                "Stop",
                "Proof",
                "Contract",
                "Wallet",
                "WalletTransaction",
                "ManualEntry",
                "WithdrawalRequest",
                "StoreIntegration",
                "IntegrationOutbox",
            )
        )
        + (function("current_operator_id()"), function("is_platform_admin()")),
    ),
    MigrationFingerprint(
        "20260621_onboarding_schema.sql",
        (
            column("Driver", "onboarding_status"),
            column("Driver", "tax_classification"),
            column("Driver", "document"),
            table("DriverDocumentRequirement"),
            column("DriverDocument", "document_type"),
            column("Contract", "effective_from"),
            column("Store", "operational"),
        ),
    ),
    MigrationFingerprint(
        "202606220100_driver_enterprise_p0.sql",
        (
            column("Driver", "operational_status"),
            column("Proof", "metadata"),
            table("DriverStatusAudit"),
            table("DriverShiftSession"),
            table("DriverIncident"),
            table("DriverIncidentAttachment"),
        ),
    ),
    MigrationFingerprint(
        "202606220101_driver_enterprise_p1.sql",
        tuple(
            table(name)
            for name in (
                "DriverShiftReservation",
                "DriverDevice",
                "DriverDeviceSecurityEvent",
                "DriverOfflineSyncBatch",
                "DriverExpense",
                "DriverExpenseReceipt",
            )
        ),
    ),
    MigrationFingerprint(
        "202606220102_driver_enterprise_p2.sql",
        tuple(
            table(name)
            for name in (
                "OrderAssignmentAudit",
                "DriverCommunicationThread",
                "DriverCommunicationMessage",
            )
        ),
    ),
    MigrationFingerprint(
        "202606220103_driver_enterprise_p3.sql",
        (table("ComplianceDocument"), table("DriverConsentAcceptance")),
    ),
    MigrationFingerprint(
        "202606220104_driver_enterprise_p4.sql",
        (
            column("DriverConsentAcceptance", "revokedAt"),
            table("PrivacyDataRequest"),
            table("ComplianceRetentionPolicy"),
        ),
    ),
    MigrationFingerprint(
        "202606220201_integration_hardening_p1.sql",
        (table("IntegrationEventAudit"),),
    ),
    MigrationFingerprint(
        "202606220202_integration_hardening_p2.sql",
        (
            column("StoreIntegration", "authMode"),
            column("StoreIntegration", "baseUrl"),
            column("StoreIntegration", "webhookUrl"),
            column("IntegrationEventAudit", "externalEventId"),
        ),
    ),
    MigrationFingerprint(
        "202606220203_driver_timestamp_fix.sql",
        (column("Driver", "updatedAt"),),
    ),
    MigrationFingerprint(
        "202606220204_timestamp_alignment.sql",
        tuple(
            column(name, "updatedAt")
            for name in (
                "Client",
                "ClientPortalUser",
                "Store",
                "StoreDriver",
                "ServiceZone",
                "ScheduleEntry",
                "Manifest",
                "WalletTransaction",
                "DailyCreditCalculation",
                "WithdrawalRequest",
                "DriverDocument",
                "StoreIntegration",
                "IntegrationOutbox",
            )
        ),
    ),
    MigrationFingerprint(
        "202606220205_driver_multiaccept_release.sql",
        (
            column("Driver", "maxActiveOrders"),
            column("OrderAssignmentAudit", "changed_by_driver_id"),
            constraint("order_assignment_actor_xor"),
        ),
    ),
    MigrationFingerprint(
        "202606220206_order_external_alignment.sql",
        (
            column("Order", "external_order_id"),
            column("Order", "external_source"),
            index("idx_order_external"),
        ),
    ),
    MigrationFingerprint(
        "20260627190000_audit_fixes.sql",
        (
            column("Operator", "cnpj"),
            table("TodoCategory"),
            table("Todo"),
            table("TodoAssignment"),
        ),
    ),
    MigrationFingerprint(
        "20260628000000_add_order_stop_metadata.sql",
        (
            column("Order", "metadata"),
            column("Stop", "metadata"),
            index("idx_order_metadata"),
            index("idx_stop_metadata"),
        ),
    ),
    MigrationFingerprint(
        "20260917000000_payout_policy_and_baas_pix.sql",
        (
            table("PayoutPolicyConfig"),
            column("WithdrawalRequest", "baasTransactionId"),
            column("Contract", "customFeeCents"),
        ),
    ),
    MigrationFingerprint(
        "20260917210000_operator_saas_billing.sql",
        (
            column("Operator", "phone"),
            column("Operator", "billingPlanType"),
            column("Operator", "platformCostPerDeliveryCents"),
        ),
    ),
    MigrationFingerprint(
        "20260923000000_whitelabel_and_connector_registry.sql",
        (
            column("Operator", "slug"),
            plain_table("operator_branding"),
            plain_table("integration_connector"),
            plain_table("integration_webhook_log"),
            column("StoreIntegration", "connector_id"),
        ),
    ),
    MigrationFingerprint(
        "20260924010000_driver_tenant_isolation.sql",
        (
            index("uq_driver_active_phone_identity"),
            index("uq_driver_active_document_identity"),
            constraint("fk_storedriver_driver_same_operator"),
            constraint("fk_schedule_driver_same_operator"),
            index("uq_storedriver_tenant_membership"),
        ),
    ),
    MigrationFingerprint(
        "20260924020000_integration_hub_hardening.sql",
        (
            index("uq_webhook_log_dedup"),
            index("uq_order_external_per_store"),
            index("uq_store_connector_integration"),
            policy("integration_webhook_log", "integration_webhook_log_tenant_policy"),
        ),
    ),
    MigrationFingerprint(
        "20260924030000_rls_runtime_enforcement.sql",
        (
            function("resolve_store_integration_operator(uuid)"),
            function("resolve_withdrawal_operator(text,text)"),
        ),
    ),
    MigrationFingerprint(
        "20260924040000_client_portal_access_revocation.sql",
        (
            column("ClientPortalUser", "active"),
            index("idx_client_portal_user_active"),
        ),
    ),
    MigrationFingerprint(
        "20260924050000_store_financial_entries.sql",
        (
            nullable_column("ManualEntry", "driver_id"),
            constraint("manual_entry_has_counterparty"),
        ),
    ),
    MigrationFingerprint(
        "20260924060000_order_distance_unknown.sql",
        (
            nullable_column("Order", "distanceMeters"),
            constraint("order_distance_meters_nonnegative"),
        ),
    ),
    MigrationFingerprint(
        "20260924070000_native_auth_schema_alignment.sql",
        (
            column("PlatformAdmin", "passwordHash"),
            column("StaffMember", "passwordHash"),
            column("ClientPortalUser", "passwordHash"),
            column("Driver", "passwordHash"),
            nullable_column("PlatformAdmin", "supabase_uid"),
            nullable_column("StaffMember", "supabase_uid"),
            nullable_column("Driver", "supabase_uid"),
        ),
    ),
)


def classify(results: Sequence[bool]) -> str:
    if all(results):
        return "APPLIED"
    if any(results):
        return "PARTIAL"
    return "MISSING"


def recommend_baseline(statuses: Sequence[tuple[str, str]]) -> str | None:
    last_applied: str | None = None
    seen_missing = False
    for name, status in statuses:
        if status == "PARTIAL":
            return None
        if status == "MISSING":
            seen_missing = True
            continue
        if seen_missing:
            return None
        last_applied = name
    return last_applied


def validate_fingerprint_manifest(migrations_dir: Path) -> None:
    discovered = [item.name for item in discover_migrations(migrations_dir)]
    declared = [item.name for item in FINGERPRINTS]
    if discovered != declared:
        missing = sorted(set(discovered) - set(declared))
        extra = sorted(set(declared) - set(discovered))
        raise RuntimeError(
            "Fingerprint manifest does not match migrations; "
            f"missing={missing}, extra={extra}, order_matches={discovered == declared}"
        )


def run_audit(connection: psycopg.Connection) -> dict[str, object]:
    reports: list[dict[str, object]] = []
    statuses: list[tuple[str, str]] = []

    with connection.cursor() as cursor:
        cursor.execute("SELECT to_regclass('public.schema_migration') IS NOT NULL")
        ledger_exists = bool(cursor.fetchone()[0])
        ledger_count = 0
        if ledger_exists:
            cursor.execute("SELECT COUNT(*) FROM public.schema_migration")
            ledger_count = int(cursor.fetchone()[0])

        for fingerprint in FINGERPRINTS:
            passed: list[str] = []
            failed: list[str] = []
            probe_results: list[bool] = []
            for probe in fingerprint.probes:
                cursor.execute(probe.sql, probe.params)
                row = cursor.fetchone()
                probe_passed = bool(row and row[0])
                probe_results.append(probe_passed)
                if probe_passed:
                    passed.append(probe.label)
                else:
                    failed.append(probe.label)
            status = classify(probe_results)
            statuses.append((fingerprint.name, status))
            reports.append(
                {
                    "name": fingerprint.name,
                    "status": status,
                    "passed": passed,
                    "failed": failed,
                }
            )

    candidate = recommend_baseline(statuses)
    safe = ledger_count == 0 and candidate is not None
    return {
        "mode": "read-only",
        "ledger_exists": ledger_exists,
        "ledger_rows": ledger_count,
        "safe_to_configure_baseline": safe,
        "recommended_baseline": candidate if safe else None,
        "migrations": reports,
        "instruction": (
            "Review this report before setting SCHEMA_MIGRATION_BASELINE. "
            "A recommendation is emitted only for a contiguous APPLIED prefix."
        ),
    }


def summarize_report(report: dict[str, object]) -> dict[str, object]:
    migrations = list(report["migrations"])
    last_contiguous_applied: str | None = None
    first_non_applied: dict[str, object] | None = None
    applied_after_gap: list[str] = []
    partial_migrations: list[dict[str, object]] = []

    for item in migrations:
        status = item["status"]
        if first_non_applied is None and status == "APPLIED":
            last_contiguous_applied = item["name"]
            continue
        if first_non_applied is None:
            first_non_applied = {
                "name": item["name"],
                "status": status,
                "passed": item["passed"],
                "failed": item["failed"],
            }
        elif status == "APPLIED":
            applied_after_gap.append(item["name"])
        if status == "PARTIAL":
            partial_migrations.append(
                {
                    "name": item["name"],
                    "passed": item["passed"],
                    "failed": item["failed"],
                }
            )

    if report["safe_to_configure_baseline"]:
        reason = "contiguous_applied_prefix"
    elif report["ledger_rows"]:
        reason = "ledger_is_not_empty"
    elif partial_migrations:
        reason = "partial_migration_detected"
    elif applied_after_gap:
        reason = "applied_migration_after_gap"
    else:
        reason = "no_applied_initial_migration"

    return {
        "mode": report["mode"],
        "ledger_exists": report["ledger_exists"],
        "ledger_rows": report["ledger_rows"],
        "safe_to_configure_baseline": report["safe_to_configure_baseline"],
        "recommended_baseline": report["recommended_baseline"],
        "reason": reason,
        "last_contiguous_applied": last_contiguous_applied,
        "first_non_applied": first_non_applied,
        "partial_migrations": partial_migrations,
        "applied_after_gap": applied_after_gap,
        "migration_statuses": [
            {"name": item["name"], "status": item["status"]} for item in migrations
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--summary",
        action="store_true",
        help="print a compact decision report suitable for deployment logs",
    )
    args = parser.parse_args()

    migrations_dir = resolve_migrations_dir()
    validate_fingerprint_manifest(migrations_dir)

    database_url = os.environ.get("DIRECT_URL") or os.environ.get("DATABASE_URL")
    if not database_url:
        print("DIRECT_URL or DATABASE_URL must be configured.", file=sys.stderr)
        return 2

    try:
        with psycopg.connect(
            database_url,
            application_name="schema-baseline-audit",
            connect_timeout=10,
        ) as connection:
            connection.autocommit = False
            report = run_audit(connection)
            connection.rollback()
    except (OSError, RuntimeError, psycopg.Error) as exc:
        print(f"Schema baseline audit failed: {exc}", file=sys.stderr)
        return 1

    output = summarize_report(report) if args.summary else report
    print(json.dumps(output, indent=2, ensure_ascii=False))
    return 0 if report["safe_to_configure_baseline"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
