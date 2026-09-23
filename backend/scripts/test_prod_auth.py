"""Manual end-to-end authentication check against an external environment.

The module is safe for pytest discovery: importing it performs no authentication,
network request, or third-party client initialization. All live values must be
provided at execution time through environment variables.
"""

from __future__ import annotations

import os
import sys
import urllib.parse

__test__ = False

LIVE_OPT_IN_ENV = "RUN_LIVE_PRODUCTION_TESTS"
REQUIRED_ENV_VARS = (
    "LIVE_SUPABASE_URL",
    "LIVE_SUPABASE_ANON_KEY",
    "LIVE_AUTH_EMAIL",
    "LIVE_AUTH_PASSWORD",
    "LIVE_API_BASE_URL",
)


def _require_live_configuration() -> dict[str, str]:
    if os.environ.get(LIVE_OPT_IN_ENV) != "1":
        raise RuntimeError(
            f"Live checks are disabled. Set {LIVE_OPT_IN_ENV}=1 explicitly to run them."
        )

    missing = [name for name in REQUIRED_ENV_VARS if not os.environ.get(name)]
    if missing:
        raise RuntimeError(
            "Missing required live-test environment variables: " + ", ".join(missing)
        )

    configuration = {name: os.environ[name] for name in REQUIRED_ENV_VARS}
    for name in ("LIVE_SUPABASE_URL", "LIVE_API_BASE_URL"):
        parsed_url = urllib.parse.urlparse(configuration[name])
        if parsed_url.scheme != "https" or not parsed_url.netloc:
            raise RuntimeError(f"{name} must be an absolute HTTPS URL.")
    return configuration


def run_auth_check(configuration: dict[str, str]) -> None:
    """Authenticate through Supabase and verify the backend identity endpoint."""
    # Keep optional/live-only dependencies out of pytest's import path.
    import requests
    from supabase import create_client

    client = create_client(
        configuration["LIVE_SUPABASE_URL"],
        configuration["LIVE_SUPABASE_ANON_KEY"],
    )
    result = client.auth.sign_in_with_password(
        {
            "email": configuration["LIVE_AUTH_EMAIL"],
            "password": configuration["LIVE_AUTH_PASSWORD"],
        }
    )
    if not result.session:
        raise RuntimeError("Authentication succeeded without returning a session.")

    response = requests.get(
        f'{configuration["LIVE_API_BASE_URL"].rstrip("/")}/api/auth/me',
        headers={
            "Authorization": f"Bearer {result.session.access_token}",
            "Content-Type": "application/json",
        },
        timeout=15,
    )
    response.raise_for_status()
    print(f"Authentication check succeeded with status {response.status_code}.")


def main() -> int:
    try:
        run_auth_check(_require_live_configuration())
    except (RuntimeError, OSError, ValueError) as exc:
        print(f"Live authentication check failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
