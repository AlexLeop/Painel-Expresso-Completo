"""Manual smoke check for the production payout endpoints.

Despite the historical filename, this module is not part of the automated test
suite. It is intentionally inert when imported and only performs network I/O
when invoked directly with an explicit live-test opt-in.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

__test__ = False

LIVE_OPT_IN_ENV = "RUN_LIVE_PRODUCTION_TESTS"
REQUIRED_ENV_VARS = (
    "LIVE_API_BASE_URL",
    "LIVE_TEST_EMAIL",
    "LIVE_TEST_PASSWORD",
)


def _require_live_configuration() -> tuple[str, str, str, str]:
    if os.environ.get(LIVE_OPT_IN_ENV) != "1":
        raise RuntimeError(
            f"Live checks are disabled. Set {LIVE_OPT_IN_ENV}=1 explicitly to run them."
        )

    missing = [name for name in REQUIRED_ENV_VARS if not os.environ.get(name)]
    if missing:
        raise RuntimeError(
            "Missing required live-test environment variables: " + ", ".join(missing)
        )

    base_url = os.environ["LIVE_API_BASE_URL"].rstrip("/")
    parsed_url = urllib.parse.urlparse(base_url)
    if parsed_url.scheme != "https" or not parsed_url.netloc:
        raise RuntimeError("LIVE_API_BASE_URL must be an absolute HTTPS URL.")

    return (
        base_url,
        os.environ["LIVE_TEST_EMAIL"],
        os.environ["LIVE_TEST_PASSWORD"],
        os.environ.get("LIVE_TEST_LABEL", "configured account"),
    )


def run_endpoint_checks(
    base_url: str,
    email: str,
    password: str,
    label: str,
) -> None:
    """Authenticate and print bounded smoke-check responses for one account."""
    print(f"\n--- Testing payout endpoints for {label} ---")
    login_url = f"{base_url}/api/auth/login"
    data = json.dumps({"email": email, "password": password}).encode()
    login_request = urllib.request.Request(
        login_url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(login_request, timeout=15) as response:
        result = json.loads(response.read().decode())
        token = result["access_token"]

    endpoints = (
        "/api/v1/admin/finance/payout-policy",
        "/api/v1/admin/finance/withdrawals?limit=100",
    )
    for endpoint in endpoints:
        endpoint_request = urllib.request.Request(
            f"{base_url}{endpoint}",
            headers={"Authorization": f"Bearer {token}"},
        )
        try:
            with urllib.request.urlopen(endpoint_request, timeout=15) as response:
                body = response.read(4096).decode(errors="replace")
                print(f"[{response.status}] {endpoint}: {body[:150]}")
        except urllib.error.HTTPError as exc:
            body = exc.read(4096).decode(errors="replace")
            print(f"[{exc.code}] {endpoint} HTTPError: {body[:150]}")


def main() -> int:
    try:
        configuration = _require_live_configuration()
        run_endpoint_checks(*configuration)
    except (RuntimeError, OSError, KeyError, ValueError) as exc:
        print(f"Live payout check failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
