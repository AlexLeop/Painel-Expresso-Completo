"""Opt-in smoke check for an already-issued platform-admin access token.

This script never creates credentials and never assumes a production host. Both
inputs must be supplied explicitly so an accidental local run cannot contact a
real environment with a forged development token.
"""

import os
import sys
import urllib.error
import urllib.parse
import urllib.request


TARGET_API_URL = os.environ.get("TARGET_API_URL", "").rstrip("/")
ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN", "")
ENDPOINTS = (
    "/api/v1/admin/finance/payout-policy",
    "/api/v1/admin/finance/withdrawals?limit=100",
)


def main() -> int:
    if not TARGET_API_URL or not ACCESS_TOKEN:
        print("Defina TARGET_API_URL e ACCESS_TOKEN explicitamente para executar este smoke test.")
        return 2

    parsed = urllib.parse.urlparse(TARGET_API_URL)
    if parsed.scheme != "https" or not parsed.netloc:
        print("TARGET_API_URL deve ser uma origem HTTPS válida.")
        return 2

    exit_code = 0
    for endpoint in ENDPOINTS:
        request = urllib.request.Request(
            f"{TARGET_API_URL}{endpoint}",
            headers={"Authorization": f"Bearer {ACCESS_TOKEN}"},
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                print(f"[{response.status}] {endpoint}")
        except urllib.error.HTTPError as exc:
            print(f"[{exc.code}] {endpoint}")
            exit_code = 1
        except urllib.error.URLError as exc:
            print(f"[erro de rede] {endpoint}: {exc.reason}")
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
